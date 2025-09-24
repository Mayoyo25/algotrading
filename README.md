# SmartTradeBots - Trading Bot Backtesting Platform

A lean MVP Django application for backtesting trading bots using Freqtrade, designed for performance and scalability.

## Features

- 🚀 **Async Backtesting**: Queue backtests using Celery for non-blocking execution
- 📊 **Comprehensive Metrics**: Track returns, drawdown, Sharpe ratio, win rates, and more
- 🎯 **Strategy Management**: Easy strategy creation and configuration
- 📈 **Performance Analytics**: Detailed performance analysis and leaderboards
- 🔧 **REST API**: Full API access for integrations
- 👨‍💼 **Admin Interface**: Comprehensive Django admin for management
- ⚡ **Redis Caching**: Fast data access and session management

## Tech Stack

- **Backend**: Django 5.2.6 + Django REST Framework
- **Task Queue**: Celery + Redis
- **Database**: SQLite (easily upgradeable to PostgreSQL)
- **Trading Engine**: Freqtrade 2025.8
- **Caching**: Redis
- **Frontend**: REST API ready for any frontend framework

## Quick Start

### 1. Prerequisites

```bash
# Install Redis (Ubuntu/Debian)
sudo apt install redis-server

# Install TA-Lib (required by Freqtrade)
sudo apt install build-essential
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
```

### 2. Project Setup

```bash
# Clone or setup your project
cd algotradingbots

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (already done)
pip install -r requirements.txt

# Apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Setup initial strategies
python manage.py setup_strategies

# Download sample data
python manage.py download_sample_data
```

### 3. Start Services

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Django
python manage.py runserver

# Terminal 3: Start Celery Worker
celery -A algotradingbots worker --loglevel=info --queues=backtest,data,maintenance

# Terminal 4: Start Celery Beat (for scheduled tasks)
celery -A algotradingbots beat --loglevel=info
```

### 4. Test the Setup

```bash
# Run a sample backtest
python manage.py run_sample_backtest

# Check admin interface
# Visit: http://localhost:8000/admin/

# Test API
# Visit: http://localhost:8000/api/v1/backtest/api/
```

## API Endpoints

### Core Endpoints

```
GET  /                                    # API info
GET  /admin/                             # Django admin
GET  /api/v1/backtest/api/               # API root

# Strategies
GET  /api/v1/backtest/api/strategies/                    # List strategies
GET  /api/v1/backtest/api/strategies/{id}/               # Strategy details
GET  /api/v1/backtest/api/strategies/{id}/performance_stats/  # Strategy performance

# Backtest Jobs
GET  /api/v1/backtest/api/jobs/                         # List jobs
POST /api/v1/backtest/api/jobs/                         # Create job
GET  /api/v1/backtest/api/jobs/{id}/                    # Job details
POST /api/v1/backtest/api/jobs/{id}/cancel/             # Cancel job
POST /api/v1/backtest/api/jobs/{id}/retry/              # Retry failed job

# Results
GET  /api/v1/backtest/api/results/                      # List results
GET  /api/v1/backtest/api/results/{id}/                 # Result details
GET  /api/v1/backtest/api/results/leaderboard/          # Performance leaderboard
GET  /api/v1/backtest/api/results/{id}/equity_curve/    # Equity curve data
GET  /api/v1/backtest/api/results/{id}/trades/          # Trade details
```

`````## Main Endpoints:
- `http://localhost:8000/`
- `http://localhost:8000/admin/`
- `http://localhost:8000/api-auth/`

## Backtest API (Non-versioned):
- `http://localhost:8000/backtest/api/strategies/`
- `http://localhost:8000/backtest/api/strategies/1/`
- `http://localhost:8000/backtest/api/jobs/`
- `http://localhost:8000/backtest/api/jobs/1/`
- `http://localhost:8000/backtest/api/results/`
- `http://localhost:8000/backtest/api/results/1/`

## Backtest API (Versioned):
- `http://localhost:8000/api/v1/backtest/api/strategies/`
- `http://localhost:8000/api/v1/backtest/api/strategies/1/`
- `http://localhost:8000/api/v1/backtest/api/jobs/`
- `http://localhost:8000/api/v1/backtest/api/jobs/1/`
- `http://localhost:8000/api/v1/backtest/api/results/`
- `http://localhost:8000/api/v1/backtest/api/results/1/` ````

### Sample API Usage

```python
import requests

# Create a backtest job
job_data = {
    "strategy": 1,
    "start_date": "2024-01-01",
    "end_date": "2024-03-01",
    "initial_balance": "10000",
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "timeframe": "1h",
    "strategy_config": {
        "fast_sma": 9,
        "slow_sma": 21
    }
}

response = requests.post(
    'http://localhost:8000/api/v1/backtest/api/jobs/',
    json=job_data
)
print(response.json())

# Check job status
job_id = response.json()['id']
status = requests.get(f'http://localhost:8000/api/v1/backtest/api/jobs/{job_id}/')
print(status.json())

# Get results when complete
results = requests.get(f'http://localhost:8000/api/v1/backtest/api/results/')
print(results.json())
`````

## Project Structure

```
algotradingbots/
├── algotradingbots/          # Django project settings
│   ├── settings.py           # Main settings
│   ├── urls.py              # URL routing
│   ├── celery.py            # Celery configuration
│   └── wsgi.py              # WSGI application
├── backtest/                 # Main application
│   ├── models.py            # Database models
│   ├── serializers.py       # API serializers
│   ├── views.py             # API views
│   ├── tasks.py             # Celery tasks
│   ├── admin.py             # Django admin
│   └── management/          # Management commands
├── strategies/               # Trading strategies
│   └── SMAStrategy.py       # Sample strategy
├── user_data/               # Freqtrade data
│   ├── data/                # Market data
│   └── backtest_results/    # Backtest outputs
├── logs/                    # Application logs
└── requirements.txt         # Python dependencies
```

## Creating Custom Strategies

1. Create a new strategy file in `strategies/`:

```python
# strategies/MyStrategy.py
from freqtrade.strategy import IStrategy
import talib.abstract as ta
from pandas import DataFrame

class MyStrategy(IStrategy):
    INTERFACE_VERSION = 3
    minimal_roi = {"0": 0.05}
    stoploss = -0.10
    timeframe = '1h'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Add your indicators
        dataframe['sma'] = ta.SMA(dataframe, timeperiod=20)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Define entry conditions
        dataframe.loc[(dataframe['close'] > dataframe['sma']), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Define exit conditions
        dataframe.loc[(dataframe['close'] < dataframe['sma']), 'exit_long']
```
