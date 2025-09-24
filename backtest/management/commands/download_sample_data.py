from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from backtest.tasks import download_market_data

class Command(BaseCommand):
    help = 'Download sample market data for backtesting'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--pairs',
            nargs='+',
            default=['BTC/USDT', 'ETH/USDT', 'ADA/USDT'],
            help='Trading pairs to download'
        )
        parser.add_argument(
            '--timeframes',
            nargs='+', 
            default=['1h', '4h', '1d'],
            help='Timeframes to download'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days of historical data'
        )
    
    def handle(self, *args, **options):
        pairs = options['pairs']
        timeframes = options['timeframes'] 
        days = options['days']
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        self.stdout.write(f'Downloading data for {len(pairs)} pairs')
        self.stdout.write(f'Timeframes: {", ".join(timeframes)}')
        self.stdout.write(f'Date range: {start_str} to {end_str}')
        
        for timeframe in timeframes:
            self.stdout.write(f'\nDownloading {timeframe} data...')
            
            try:
                # Queue download task
                task = download_market_data.delay(pairs, timeframe, start_str, end_str)
                result = task.get(timeout=300)  # 5 minute timeout
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {timeframe}: {result}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ {timeframe}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nData download complete!')
        )