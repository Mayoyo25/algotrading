from django.core.management.base import BaseCommand
from django.conf import settings
from backtest.models import TradingStrategy
import os

class Command(BaseCommand):
    help = 'Setup initial trading strategies'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--strategies-dir',
            default='strategies',
            help='Directory containing strategy files'
        )
    
    def handle(self, *args, **options):
        strategies_dir = options['strategies_dir']
        
        # Create strategies directory if it doesn't exist
        if not os.path.exists(strategies_dir):
            os.makedirs(strategies_dir)
            self.stdout.write(f'Created strategies directory: {strategies_dir}')
        
        # Sample strategies to create
        sample_strategies = [
            {
                'name': 'SMAStrategy',
                'description': 'Simple Moving Average crossover strategy with RSI filter',
                'file_path': f'{strategies_dir}/SMAStrategy.py',
                'default_config': {
                    'fast_sma': 9,
                    'slow_sma': 21,
                    'minimal_roi': {
                        '60': 0.01,
                        '30': 0.02, 
                        '0': 0.04
                    },
                    'stoploss': -0.10
                }
            },
            {
                'name': 'BBRSIStrategy',
                'description': 'Bollinger Bands with RSI strategy',
                'file_path': f'{strategies_dir}/BBRSIStrategy.py',
                'default_config': {
                    'bb_period': 20,
                    'bb_std': 2,
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30
                }
            },
            {
                'name': 'MACDStrategy', 
                'description': 'MACD signal line crossover with volume filter',
                'file_path': f'{strategies_dir}/MACDStrategy.py',
                'default_config': {
                    'macd_fast': 12,
                    'macd_slow': 26,
                    'macd_signal': 9,
                    'volume_threshold': 1.2
                }
            }
        ]
        
        created_count = 0
        for strategy_data in sample_strategies:
            strategy, created = TradingStrategy.objects.get_or_create(
                name=strategy_data['name'],
                defaults=strategy_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created strategy: {strategy.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Strategy already exists: {strategy.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSetup complete! Created {created_count} new strategies.')
        )
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nNext steps:\n'
                    f'1. Implement strategy files in {strategies_dir}/ directory\n'
                    f'2. Run: python manage.py download_sample_data\n'
                    f'3. Test backtesting via admin or API\n'
                )
            )
