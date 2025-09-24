from rest_framework import serializers
from .models import TradingStrategy, BacktestJob, BacktestResult
from datetime import date, timedelta

class TradingStrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingStrategy
        fields = ['id', 'name', 'description', 'default_config', 'is_active', 'created_at']
        read_only_fields = ['created_at']

class BacktestJobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestJob
        fields = [
            'strategy', 'start_date', 'end_date', 'initial_balance', 
            'pairs', 'timeframe', 'strategy_config'
        ]
    
    def validate(self, data):
        # Validate date range
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be after start date")
        
        # Don't allow backtests too far in the future
        if data['end_date'] > date.today():
            raise serializers.ValidationError("End date cannot be in the future")
        
        # Reasonable time range (max 3 years for performance)
        if (data['end_date'] - data['start_date']).days > 1095:
            raise serializers.ValidationError("Date range cannot exceed 3 years")
        
        # Validate pairs format
        if not data.get('pairs') or not isinstance(data['pairs'], list):
            raise serializers.ValidationError("At least one trading pair is required")
        
        # Basic validation of pair format
        for pair in data['pairs']:
            if not isinstance(pair, str) or '/' not in pair:
                raise serializers.ValidationError(f"Invalid pair format: {pair}")
        
        # Validate timeframe
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        if data.get('timeframe') not in valid_timeframes:
            raise serializers.ValidationError(f"Timeframe must be one of: {valid_timeframes}")
        
        return data

class BacktestResultSerializer(serializers.ModelSerializer):
    win_loss_ratio = serializers.ReadOnlyField()
    expectancy = serializers.ReadOnlyField()
    
    class Meta:
        model = BacktestResult
        fields = [
            'total_trades', 'winning_trades', 'losing_trades',
            'total_return_pct', 'total_return_abs', 'annual_return_pct',
            'max_drawdown_pct', 'max_drawdown_abs', 'sharpe_ratio', 'calmar_ratio',
            'win_rate', 'profit_factor', 'win_loss_ratio', 'expectancy',
            'avg_winning_trade', 'avg_losing_trade', 'avg_trade_duration_hours',
            'final_balance', 'created_at'
        ]

class BacktestJobSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    result = BacktestResultSerializer(read_only=True)
    
    class Meta:
        model = BacktestJob
        fields = [
            'id', 'strategy', 'strategy_name', 'start_date', 'end_date',
            'initial_balance', 'pairs', 'timeframe', 'strategy_config',
            'status', 'progress', 'error_message',
            'created_at', 'started_at', 'completed_at', 'result'
        ]
        read_only_fields = [
            'id', 'status', 'progress', 'error_message', 
            'created_at', 'started_at', 'completed_at'
        ]

class BacktestJobListSerializer(serializers.ModelSerializer):
    """Lighter serializer for job listings"""
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    duration_days = serializers.SerializerMethodField()
    
    class Meta:
        model = BacktestJob
        fields = [
            'id', 'strategy_name', 'start_date', 'end_date', 'duration_days',
            'pairs', 'timeframe', 'status', 'progress', 'created_at'
        ]
    
    def get_duration_days(self, obj):
        return (obj.end_date - obj.start_date).days

class BacktestResultDetailSerializer(serializers.ModelSerializer):
    """Detailed result serializer including trade data"""
    job_info = BacktestJobListSerializer(source='job', read_only=True)
    win_loss_ratio = serializers.ReadOnlyField()
    expectancy = serializers.ReadOnlyField()
    
    class Meta:
        model = BacktestResult
        fields = [
            'job_info',
            'total_trades', 'winning_trades', 'losing_trades',
            'total_return_pct', 'total_return_abs', 'annual_return_pct',
            'max_drawdown_pct', 'max_drawdown_abs', 'sharpe_ratio', 'calmar_ratio',
            'win_rate', 'profit_factor', 'win_loss_ratio', 'expectancy',
            'avg_winning_trade', 'avg_losing_trade', 'avg_trade_duration_hours',
            'final_balance', 'trades_data', 'daily_stats', 'equity_curve',
            'created_at'
        ]