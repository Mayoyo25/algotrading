from celery import shared_task
from django.utils import timezone
from decimal import Decimal
import subprocess
import json
import tempfile
import os
import logging
from pathlib import Path

from .models import BacktestJob, BacktestResult, TradingStrategy

logger = logging.getLogger(__name__)

@shared_task
def run_backtest_task(job_id):
    """
    Run a backtest using Freqtrade
    """
    try:
        job = BacktestJob.objects.get(id=job_id)
        logger.info(f"Starting backtest job {job_id}")
        
        # Update job status
        job.status = 'running'
        job.started_at = timezone.now()
        job.progress = 10
        job.save()
        
        # Prepare freqtrade config
        config = prepare_freqtrade_config(job)
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f, indent=2)
            config_file = f.name
        
        try:
            job.progress = 30
            job.save()
            
            # Run freqtrade backtest
            result = run_freqtrade_backtest(config_file, job)
            
            job.progress = 80
            job.save()
            
            # Parse and save results
            backtest_result = parse_and_save_results(job, result)
            
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.progress = 100
            job.save()
            
            logger.info(f"Completed backtest job {job_id} successfully")
            return f"Backtest completed with {backtest_result.total_trades} trades"
            
        finally:
            # Clean up temp file
            try:
                os.unlink(config_file)
            except:
                pass
                
    except BacktestJob.DoesNotExist:
        logger.error(f"Backtest job {job_id} not found")
        return f"Job {job_id} not found"
        
    except Exception as e:
        logger.error(f"Backtest job {job_id} failed: {str(e)}")
        
        # Update job with error
        try:
            job = BacktestJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
        except:
            pass
            
        return f"Backtest failed: {str(e)}"

def prepare_freqtrade_config(job):
    """
    Prepare Freqtrade configuration for the backtest
    """
    base_config = {
        "trading_mode": "backtest",
        "dry_run": True,
        "timeframe": job.timeframe,
        "timeframe_detail": "1m",  # For better accuracy
        "startup_candle_count": 400,
        "process_only_new_candles": True,
        
        # Strategy
        "strategy": job.strategy.name,
        "strategy_path": [str(Path(job.strategy.file_path).parent)],
        
        # Exchange settings
        "exchange": {
            "name": "binance",  # Default exchange
            "sandbox": False,
            "key": "",
            "secret": "",
            "ccxt_config": {},
            "ccxt_async_config": {},
            "pair_whitelist": job.pairs,
            "pair_blacklist": []
        },
        
        # Backtest specific
        "backtest": {
            "initial_balance": float(job.initial_balance),
            "start_date": job.start_date.strftime("%Y-%m-%d"),
            "end_date": job.end_date.strftime("%Y-%m-%d"),
            "trade_source": "ohlcv",
            "enable_protections": False,
            "backtest_breakdown": ["day", "week", "month"]
        },
        
        # Data settings
        "datadir": "user_data/data/binance",
        "pairs": job.pairs,
        "timeframes": {job.timeframe: job.timeframe},
        
        # Entry/Exit settings
        "entry_pricing": {
            "price_side": "same",
            "use_order_book": False,
            "order_book_top": 1,
            "price_last_balance": 0.0,
            "check_depth_of_market": {
                "enabled": False
            }
        },
        
        "exit_pricing": {
            "price_side": "same",
            "use_order_book": False,
            "order_book_top": 1,
            "price_last_balance": 0.0
        },
        
        # Logging
        "logging": {
            "verbosity": 2
        },
        
        # Telegram (disabled for backtest)
        "telegram": {
            "enabled": False
        },
        
        # API (disabled for backtest)
        "api_server": {
            "enabled": False
        }
    }
    
    # Merge strategy-specific config
    if job.strategy_config:
        base_config.update(job.strategy_config)
    
    # Add default config from strategy
    if job.strategy.default_config:
        base_config.update(job.strategy.default_config)
    
    return base_config

def run_freqtrade_backtest(config_file, job):
    """
    Execute freqtrade backtest command
    """
    cmd = [
        'freqtrade',
        'backtesting',
        '--config', config_file,
        '--strategy', job.strategy.name,
        '--timerange', f"{job.start_date.strftime('%Y%m%d')}-{job.end_date.strftime('%Y%m%d')}",
        '--breakdown', 'day',
        '--export', 'trades',
        '--export-filename', f'backtest_result_{job.id}.json'
    ]
    
    # Add pairs to command
    for pair in job.pairs:
        cmd.extend(['--pairs', pair])
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    # Run the command
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=3600  # 1 hour timeout
    )
    
    if result.returncode != 0:
        error_msg = f"Freqtrade failed: {result.stderr}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    return result.stdout

def parse_and_save_results(job, freqtrade_output):
    """
    Parse Freqtrade output and save results to database
    """
    # Try to find the results file
    results_file = f"user_data/backtest_results/backtest_result_{job.id}.json"
    
    if not os.path.exists(results_file):
        # Fallback: parse from stdout
        results_data = parse_freqtrade_stdout(freqtrade_output)
    else:
        with open(results_file, 'r') as f:
            results_data = json.load(f)
    
    # Extract key metrics
    strategy_stats = results_data['strategy'][job.strategy.name]
    
    # Create BacktestResult
    backtest_result = BacktestResult.objects.create(
        job=job,
        total_trades=strategy_stats.get('total_trades', 0),
        winning_trades=strategy_stats.get('wins', 0),
        losing_trades=strategy_stats.get('losses', 0),
        
        # Returns
        total_return_pct=Decimal(str(strategy_stats.get('profit_total_pct', 0))),
        total_return_abs=Decimal(str(strategy_stats.get('profit_total_abs', 0))),
        annual_return_pct=Decimal(str(strategy_stats.get('profit_total_pct', 0) * 365 / max(1, (job.end_date - job.start_date).days))),
        
        # Risk metrics
        max_drawdown_pct=Decimal(str(abs(strategy_stats.get('max_drawdown', 0)))),
        max_drawdown_abs=Decimal(str(abs(strategy_stats.get('max_drawdown_abs', 0)))),
        sharpe_ratio=Decimal(str(strategy_stats.get('sharpe', 0))),
        calmar_ratio=Decimal(str(strategy_stats.get('calmar', 0))),
        
        # Win rate and ratios
        win_rate=Decimal(str(strategy_stats.get('win_rate', 0))),
        profit_factor=Decimal(str(strategy_stats.get('profit_factor', 0))),
        
        # Average trades
        avg_winning_trade=Decimal(str(strategy_stats.get('avg_profit', 0))),
        avg_losing_trade=Decimal(str(strategy_stats.get('avg_loss', 0))),
        avg_trade_duration_hours=Decimal(str(convert_duration_to_hours(strategy_stats.get('avg_duration', '0:00:00')))),
        
        # Final balance
        final_balance=Decimal(str(float(job.initial_balance) + strategy_stats.get('profit_total_abs', 0))),
        
        # Raw data
        trades_data=results_data.get('trades', []),
        daily_stats=strategy_stats.get('daily_stats', {}),
        equity_curve=generate_equity_curve(results_data.get('trades', []), float(job.initial_balance))
    )
    
    # Clean up results file
    try:
        os.unlink(results_file)
    except:
        pass
    
    return backtest_result

def parse_freqtrade_stdout(output):
    """
    Parse freqtrade output when JSON file is not available
    """
    # Basic parsing of freqtrade stdout
    # This is a fallback and may need adjustment based on freqtrade output format
    
    lines = output.split('\n')
    results = {
        'strategy': {},
        'trades': []
    }
    
    # Try to extract basic stats from output
    for line in lines:
        if 'BACKTESTING REPORT' in line:
            # Start parsing results section
            continue
        # Add more parsing logic here based on freqtrade output format
    
    return results

def convert_duration_to_hours(duration_str):
    """
    Convert duration string like '2 days, 3:45:30' to hours
    """
    if not duration_str or duration_str == '0:00:00':
        return 0
    
    try:
        # Handle various duration formats
        if 'day' in duration_str:
            parts = duration_str.split(', ')
            days = int(parts[0].split()[0])
            time_part = parts[1] if len(parts) > 1 else '0:00:00'
        else:
            days = 0
            time_part = duration_str
        
        # Parse time part (H:M:S)
        time_parts = time_part.split(':')
        hours = int(time_parts[0])
        minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
        seconds = int(time_parts[2]) if len(time_parts) > 2 else 0
        
        total_hours = days * 24 + hours + minutes / 60 + seconds / 3600
        return round(total_hours, 2)
        
    except (ValueError, IndexError):
        return 0

def generate_equity_curve(trades, initial_balance):
    """
    Generate equity curve data from trades
    """
    if not trades:
        return []
    
    equity_curve = []
    current_balance = initial_balance
    
    for trade in trades:
        current_balance += trade.get('profit_abs', 0)
        equity_curve.append({
            'timestamp': trade.get('close_date', ''),
            'balance': round(current_balance, 2),
            'profit_pct': round((current_balance - initial_balance) / initial_balance * 100, 4)
        })
    
    return equity_curve

@shared_task
def cleanup_old_jobs():
    """
    Clean up old backtest jobs and results (run daily)
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)  # Keep for 30 days
    
    # Delete old failed/cancelled jobs
    old_jobs = BacktestJob.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['failed', 'cancelled']
    )
    
    count = old_jobs.count()
    old_jobs.delete()
    
    logger.info(f"Cleaned up {count} old backtest jobs")
    return f"Cleaned up {count} old jobs"

@shared_task
def download_market_data(pairs, timeframe, start_date, end_date):
    """
    Download market data for backtesting
    """
    cmd = [
        'freqtrade',
        'download-data',
        '--exchange', 'binance',
        '--timeframes', timeframe,
        '--timerange', f"{start_date.replace('-', '')}-{end_date.replace('-', '')}",
        '--pairs'
    ] + pairs
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"Data download failed: {result.stderr}")
            
        logger.info(f"Downloaded data for {pairs} ({timeframe})")
        return f"Downloaded data for {len(pairs)} pairs"
        
    except subprocess.TimeoutExpired:
        raise Exception("Data download timed out")
    except Exception as e:
        logger.error(f"Data download failed: {str(e)}")
        raise