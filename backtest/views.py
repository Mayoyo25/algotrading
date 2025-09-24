# backtest\views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import logging

from .models import TradingStrategy, BacktestJob, BacktestResult
from .serializers import (
    TradingStrategySerializer, BacktestJobCreateSerializer, 
    BacktestJobSerializer, BacktestJobListSerializer,
    BacktestResultSerializer, BacktestResultDetailSerializer
)
from .tasks import run_backtest_task  # We'll create this next

logger = logging.getLogger(__name__)

class TradingStrategyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing available trading strategies
    """
    queryset = TradingStrategy.objects.filter(is_active=True)
    serializer_class = TradingStrategySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']
    
    @action(detail=True, methods=['get'])
    def performance_stats(self, request, pk=None):
        """Get aggregated performance stats for a strategy"""
        strategy = self.get_object()
        
        completed_jobs = BacktestJob.objects.filter(
            strategy=strategy, 
            status='completed'
        ).select_related('result')
        
        if not completed_jobs.exists():
            return Response({
                'message': 'No completed backtests found for this strategy',
                'total_backtests': 0
            })
        
        # Aggregate stats
        results = BacktestResult.objects.filter(job__in=completed_jobs)
        stats = results.aggregate(
            avg_return=Avg('total_return_pct'),
            avg_drawdown=Avg('max_drawdown_pct'),
            avg_win_rate=Avg('win_rate'),
            avg_sharpe=Avg('sharpe_ratio'),
            total_backtests=Count('id')
        )
        
        # Best and worst performing backtests
        best = results.order_by('-total_return_pct').first()
        worst = results.order_by('total_return_pct').first()
        
        return Response({
            'strategy_name': strategy.name,
            'total_backtests': stats['total_backtests'],
            'average_stats': {
                'return_pct': round(float(stats['avg_return'] or 0), 2),
                'max_drawdown_pct': round(float(stats['avg_drawdown'] or 0), 2),
                'win_rate': round(float(stats['avg_win_rate'] or 0), 2),
                'sharpe_ratio': round(float(stats['avg_sharpe'] or 0), 3)
            },
            'best_performance': {
                'return_pct': float(best.total_return_pct) if best else None,
                'job_id': best.job.id if best else None
            },
            'worst_performance': {
                'return_pct': float(worst.total_return_pct) if worst else None,
                'job_id': worst.job.id if worst else None
            }
        })

class BacktestJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing backtest jobs
    """
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['strategy', 'status', 'timeframe']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = BacktestJob.objects.select_related('strategy', 'result')
        
        # Filter by user if authenticated
        if self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)
        else:
            # For anonymous users, show only public results
            queryset = queryset.filter(user__isnull=True)
            
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BacktestJobCreateSerializer
        elif self.action == 'list':
            return BacktestJobListSerializer
        return BacktestJobSerializer
    
    def perform_create(self, serializer):
        # Set user if authenticated
        job = serializer.save(
            user=self.request.user if self.request.user.is_authenticated else None
        )
        
        # Queue the backtest task
        try:
            run_backtest_task.delay(job.id)
            logger.info(f"Queued backtest job {job.id}")
        except Exception as e:
            logger.error(f"Failed to queue backtest job {job.id}: {e}")
            job.status = 'failed'
            job.error_message = f"Failed to queue job: {str(e)}"
            job.save()
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending or running backtest job"""
        job = self.get_object()
        
        if job.status not in ['pending', 'running']:
            return Response(
                {'error': 'Job cannot be cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job.status = 'cancelled'
        job.error_message = 'Cancelled by user'
        job.save()
        
        # TODO: Cancel celery task if running
        
        return Response({'message': 'Job cancelled successfully'})
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed backtest job"""
        job = self.get_object()
        
        if job.status != 'failed':
            return Response(
                {'error': 'Only failed jobs can be retried'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset job status
        job.status = 'pending'
        job.error_message = ''
        job.progress = 0
        job.started_at = None
        job.completed_at = None
        job.save()
        
        # Delete old result if exists
        if hasattr(job, 'result'):
            job.result.delete()
        
        # Queue the job again
        try:
            run_backtest_task.delay(job.id)
            logger.info(f"Retrying backtest job {job.id}")
        except Exception as e:
            logger.error(f"Failed to retry backtest job {job.id}: {e}")
            job.status = 'failed'
            job.error_message = f"Failed to queue retry: {str(e)}"
            job.save()
        
        return Response({'message': 'Job queued for retry'})

class BacktestResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing backtest results
    """
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['job__strategy', 'job__timeframe']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = BacktestResult.objects.select_related('job__strategy')
        
        # Filter by user if authenticated
        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                Q(job__user=self.request.user) | Q(job__user__isnull=True)
            )
        else:
            # Anonymous users see only public results
            queryset = queryset.filter(job__user__isnull=True)
            
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BacktestResultDetailSerializer
        return BacktestResultSerializer
    
    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """Get top performing strategies"""
        limit = int(request.query_params.get('limit', 10))
        timeframe = request.query_params.get('timeframe', None)
        
        queryset = self.get_queryset()
        
        if timeframe:
            queryset = queryset.filter(job__timeframe=timeframe)
        
        # Get top performers by total return
        top_results = queryset.order_by('-total_return_pct')[:limit]
        
        leaderboard = []
        for result in top_results:
            leaderboard.append({
                'rank': len(leaderboard) + 1,
                'strategy_name': result.job.strategy.name,
                'total_return_pct': float(result.total_return_pct),
                'max_drawdown_pct': float(result.max_drawdown_pct),
                'win_rate': float(result.win_rate),
                'sharpe_ratio': float(result.sharpe_ratio),
                'total_trades': result.total_trades,
                'timeframe': result.job.timeframe,
                'pairs': result.job.pairs,
                'duration_days': (result.job.end_date - result.job.start_date).days,
                'job_id': result.job.id,
                'created_at': result.created_at
            })
        
        return Response({
            'leaderboard': leaderboard,
            'filters': {
                'timeframe': timeframe,
                'limit': limit
            }
        })
    
    @action(detail=True, methods=['get'])
    def equity_curve(self, request, pk=None):
        """Get equity curve data for charting"""
        result = self.get_object()
        return Response({
            'job_id': result.job.id,
            'strategy_name': result.job.strategy.name,
            'equity_curve': result.equity_curve,
            'initial_balance': float(result.job.initial_balance),
            'final_balance': float(result.final_balance)
        })
    
    @action(detail=True, methods=['get'])
    def trades(self, request, pk=None):
        """Get trade data with pagination"""
        result = self.get_object()
        page_size = int(request.query_params.get('page_size', 50))
        page = int(request.query_params.get('page', 1))
        
        trades = result.trades_data
        total_trades = len(trades)
        
        # Simple pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_trades = trades[start_idx:end_idx]
        
        return Response({
            'trades': paginated_trades,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_trades': total_trades,
                'total_pages': (total_trades + page_size - 1) // page_size
            }
        })