from django.core.management.base import BaseCommand
from backtest.models import TradingStrategy, BacktestJob
from datetime import datetime, timedelta
from decimal import Decimal

class Command(BaseCommand):
    help = 'Run a sample backtest to verify setup'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--strategy',
            default='SMAStrategy',
            help='Strategy name to test'
        )
    
    def handle(self, *args, **options):
        strategy_name = options['strategy']
        
        try:
            strategy = TradingStrategy.objects.get(name=strategy_name)
        except TradingStrategy.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Strategy "{strategy_name}" not found')
            )
            return
        
        # Create sample backtest job
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)  # 30 days
        
        job = BacktestJob.objects.create(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            initial_balance=Decimal('10000'),
            pairs=['BTC/USDT', 'ETH/USDT'],
            timeframe='1h'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created sample backtest job: {job.id}')
        )
        self.stdout.write(f'Strategy: {strategy.name}')
        self.stdout.write(f'Date range: {start_date} to {end_date}')
        self.stdout.write(f'Pairs: {job.pairs}')
        self.stdout.write(f'Timeframe: {job.timeframe}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nBacktest queued! Check status in:\n'
                f'- Admin: /admin/backtest/backtestjob/{job.id}/\n'
                f'- API: /api/v1/backtest/api/jobs/{job.id}/'
            )
        )