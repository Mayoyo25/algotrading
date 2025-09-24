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

## Prerequisites

Before setting up the project, ensure you have the following installed:

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y build-essential python3-dev python3-pip redis-server git

# macOS (using Homebrew)
brew install python redis git

# CentOS/RHEL
sudo yum install -y gcc gcc-c++ python3-devel redis git
```

### TA-Lib Installation

TA-Lib is required by Freqtrade for technical analysis indicators:

```bash
# Ubuntu/Debian
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd .. && rm -rf ta-lib*

# macOS
brew install ta-lib

# Windows (using conda)
conda install -c conda-forge ta-lib
```

### Python Environment

```bash
# Check Python version (3.8+ required)
python3 --version

# Install virtualenv if not available
pip3 install virtualenv
```

## Installation & Setup

### 1. Clone and Setup Project

```bash
# Clone the repository
git clone <your-repository-url>
cd algotradingbots

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate     # Windows

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Create database migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser
```

### 3. Initial Data Setup

```bash
# Setup default trading strategies
python manage.py setup_strategies

# Download sample market data (optional but recommended)
python manage.py download_sample_data --days 90
```

### 4. Start Required Services

You'll need 4 terminal windows/tabs:

**Terminal 1: Redis Server**

```bash
redis-server
# Redis should start on localhost:6379
```

**Terminal 2: Django Development Server**

```bash
source .venv/bin/activate
python manage.py runserver
# Django will be available at http://localhost:8000
```

**Terminal 3: Celery Worker**

```bash
source .venv/bin/activate
celery -A algotradingbots worker --loglevel=info --queues=backtest,data,maintenance
```

**Terminal 4: Celery Beat (Scheduler)**

```bash
source .venv/bin/activate
celery -A algotradingbots beat --loglevel=info
```

### 5. Verify Installation

```bash
# Test with a sample backtest
python manage.py run_sample_backtest

# Check that services are running:
# - Django Admin: http://localhost:8000/admin/
# - API Root: http://localhost:8000/api/v1/backtest/api/
# - API Info: http://localhost:8000/
```

## Project Architecture

### Directory Structure

```
algotradingbots/
├── algotradingbots/          # Django project configuration
│   ├── settings.py           # Main settings (DB, Celery, etc.)
│   ├── urls.py              # URL routing
│   ├── celery.py            # Celery task queue configuration
│   └── wsgi.py              # WSGI application for deployment
├── backtest/                 # Main Django application
│   ├── models.py            # Database models (Strategy, Job, Result)
│   ├── serializers.py       # DRF serializers for API
│   ├── views.py             # API viewsets and endpoints
│   ├── tasks.py             # Celery background tasks
│   ├── admin.py             # Django admin configuration
│   ├── urls.py              # App-specific URL patterns
│   └── management/commands/  # Custom management commands
│       ├── setup_strategies.py      # Initialize default strategies
│       ├── download_sample_data.py  # Download market data
│       └── run_sample_backtest.py   # Test backtest execution
├── strategies/               # Freqtrade strategy files
│   └── SMAStrategy.py       # Sample SMA crossover strategy
├── user_data/               # Freqtrade data directory
│   ├── data/                # Downloaded market data (OHLCV)
│   └── backtest_results/    # Temporary backtest output files
├── logs/                    # Application log files
│   ├── django.log          # Django application logs
│   └── celery.log          # Celery task execution logs
├── db.sqlite3              # SQLite database (default)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Data Flow

1. **API Request**: Client creates backtest job via REST API
2. **Job Queue**: Django saves job to database and queues Celery task
3. **Background Processing**: Celery worker picks up task and runs Freqtrade
4. **Results Storage**: Parsed results saved to database
5. **Client Access**: Results available via API endpoints

### Database Models

- **TradingStrategy**: Stores strategy metadata and configuration
- **BacktestJob**: Tracks backtest execution status and parameters
- **BacktestResult**: Stores performance metrics and trade data
- **MarketData**: Caches downloaded market data (optional)

## API Documentation

### Authentication

The API currently supports both authenticated and anonymous access:

- **Authenticated users**: See only their own jobs and results
- **Anonymous users**: See only public (user=null) results

### Core Endpoints

#### Strategies

```http
GET /api/v1/backtest/api/strategies/
GET /api/v1/backtest/api/strategies/{id}/
GET /api/v1/backtest/api/strategies/{id}/performance_stats/
```

#### Backtest Jobs

```http
GET  /api/v1/backtest/api/jobs/                    # List jobs
POST /api/v1/backtest/api/jobs/                    # Create new job
GET  /api/v1/backtest/api/jobs/{id}/               # Job details
POST /api/v1/backtest/api/jobs/{id}/cancel/        # Cancel job
POST /api/v1/backtest/api/jobs/{id}/retry/         # Retry failed job
```

#### Results & Analytics

```http
GET /api/v1/backtest/api/results/                  # List results
GET /api/v1/backtest/api/results/{id}/             # Result details
GET /api/v1/backtest/api/results/leaderboard/      # Top performers
GET /api/v1/backtest/api/results/{id}/equity_curve/ # Chart data
GET /api/v1/backtest/api/results/{id}/trades/      # Individual trades
```

### API Usage Examples

#### Creating a Backtest Job

```python
import requests

# Job configuration
job_data = {
    "strategy": 1,  # Strategy ID from /strategies/ endpoint
    "start_date": "2024-01-01",
    "end_date": "2024-03-01",
    "initial_balance": "10000",
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "timeframe": "1h",
    "strategy_config": {
        "fast_sma": 9,
        "slow_sma": 21,
        "minimal_roi": {"0": 0.05},
        "stoploss": -0.10
    }
}

# Create job
response = requests.post(
    'http://localhost:8000/api/v1/backtest/api/jobs/',
    json=job_data,
    headers={'Content-Type': 'application/json'}
)

print("Job created:", response.json())
```

#### Monitoring Job Progress

```python
job_id = response.json()['id']

# Poll job status
while True:
    status_response = requests.get(f'http://localhost:8000/api/v1/backtest/api/jobs/{job_id}/')
    job_status = status_response.json()

    print(f"Status: {job_status['status']} ({job_status['progress']}%)")

    if job_status['status'] in ['completed', 'failed']:
        break

    time.sleep(5)  # Wait 5 seconds before checking again
```

#### Retrieving Results

```python
if job_status['status'] == 'completed':
    # Get detailed results
    results_response = requests.get(
        f'http://localhost:8000/api/v1/backtest/api/results/',
        params={'job__id': job_id}
    )

    results = results_response.json()['results'][0]

    print(f"Total Return: {results['total_return_pct']}%")
    print(f"Max Drawdown: {results['max_drawdown_pct']}%")
    print(f"Win Rate: {results['win_rate']}%")
    print(f"Total Trades: {results['total_trades']}")
```

## Creating Custom Trading Strategies

### Strategy File Structure

Create new strategy files in the `strategies/` directory:

```python
# strategies/MyCustomStrategy.py
from freqtrade.strategy import IStrategy
import talib.abstract as ta
from pandas import DataFrame
from typing import Optional

class MyCustomStrategy(IStrategy):
    """
    Custom trading strategy using RSI and MACD
    """

    # Strategy metadata
    INTERFACE_VERSION = 3

    # Strategy parameters
    minimal_roi = {
        "60": 0.01,   # 1% after 1 hour
        "30": 0.02,   # 2% after 30 minutes
        "0": 0.04     # 4% immediate
    }

    stoploss = -0.10  # 10% stop loss

    timeframe = '5m'  # 5-minute candles

    # Strategy-specific parameters
    rsi_period = 14
    rsi_overbought = 70
    rsi_oversold = 30
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add technical indicators to the dataframe
        """
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)

        # MACD
        macd = ta.MACD(dataframe,
                      fastperiod=self.macd_fast,
                      slowperiod=self.macd_slow,
                      signalperiod=self.macd_signal)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # Simple Moving Averages
        dataframe['sma_short'] = ta.SMA(dataframe, timeperiod=10)
        dataframe['sma_long'] = ta.SMA(dataframe, timeperiod=50)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define buy/entry conditions
        """
        dataframe.loc[
            (
                # RSI oversold
                (dataframe['rsi'] < self.rsi_oversold) &
                # MACD bullish crossover
                (dataframe['macd'] > dataframe['macdsignal']) &
                # Price above short MA
                (dataframe['close'] > dataframe['sma_short']) &
                # Volume confirmation
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define sell/exit conditions
        """
        dataframe.loc[
            (
                # RSI overbought
                (dataframe['rsi'] > self.rsi_overbought) &
                # MACD bearish crossover
                (dataframe['macd'] < dataframe['macdsignal'])
            ),
            'exit_long'] = 1

        return dataframe

    def custom_stoploss(self, pair: str, trade: object, current_time: 'datetime',
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Custom trailing stop loss (optional)
        """
        if current_profit > 0.1:  # If profit > 10%
            return 0.05  # Set stop loss to 5% below current price
        return self.stoploss  # Use default stop loss
```

### Registering New Strategies

After creating a strategy file:

```bash
# Add strategy to database
python manage.py shell
```

```python
from backtest.models import TradingStrategy

strategy = TradingStrategy.objects.create(
    name='MyCustomStrategy',
    description='RSI and MACD based strategy with trailing stop',
    file_path='strategies/MyCustomStrategy.py',
    default_config={
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'minimal_roi': {
            '60': 0.01,
            '30': 0.02,
            '0': 0.04
        },
        'stoploss': -0.10
    }
)
```

Or use the management command to setup multiple strategies at once by editing `setup_strategies.py`.

## Configuration

### Django Settings

Key configuration options in `settings.py`:

```python
# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Change to postgresql for production
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Celery Configuration

Task routing and scheduling in `celery.py`:

```python
# Task routing
app.conf.task_routes = {
    'backtest.tasks.run_backtest_task': {'queue': 'backtest'},
    'backtest.tasks.download_market_data': {'queue': 'data'},
    'backtest.tasks.cleanup_old_jobs': {'queue': 'maintenance'},
}

# Scheduled tasks
app.conf.beat_schedule = {
    'cleanup-old-jobs': {
        'task': 'backtest.tasks.cleanup_old_jobs',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

### Freqtrade Configuration

The system dynamically generates Freqtrade configs for each backtest. Key defaults:

- **Exchange**: Binance (configurable)
- **Data Source**: Local files in `user_data/data/`
- **Timeframes**: Configurable per job (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
- **Initial Balance**: Configurable per job
- **Fee**: 0.1% (Binance default)

## Monitoring & Logging

### Application Logs

```bash
# Django application logs
tail -f logs/django.log

# Celery task logs
tail -f logs/celery.log

# Real-time log monitoring
tail -f logs/django.log logs/celery.log
```

### Celery Monitoring

```bash
# Monitor active workers
celery -A algotradingbots inspect active

# Monitor scheduled tasks
celery -A algotradingbots inspect scheduled

# Monitor task statistics
celery -A algotradingbots inspect stats
```

### Redis Monitoring

```bash
# Connect to Redis CLI
redis-cli

# Monitor Redis commands
redis-cli monitor

# Check memory usage
redis-cli info memory
```

## Deployment

### Production Setup

1. **Database Migration**:

```bash
# Use PostgreSQL for production
pip install psycopg2-binary

# Update DATABASES in settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'smarttradebots',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

2. **Environment Variables**:

```bash
# Create .env file
cat > .env << EOF
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:password@localhost/smarttradebots
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
EOF
```

3. **Web Server Setup** (using Gunicorn + Nginx):

```bash
# Install Gunicorn
pip install gunicorn

# Create Gunicorn config
cat > gunicorn.conf.py << EOF
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
EOF

# Run with Gunicorn
gunicorn -c gunicorn.conf.py algotradingbots.wsgi:application
```

4. **Process Management** (using Supervisor):

```ini
# /etc/supervisor/conf.d/smarttradebots.conf
[program:smarttradebots_django]
command=/path/to/venv/bin/gunicorn -c gunicorn.conf.py algotradingbots.wsgi:application
directory=/path/to/algotradingbots
user=www-data
autostart=true
autorestart=true

[program:smarttradebots_celery]
command=/path/to/venv/bin/celery -A algotradingbots worker --loglevel=info --queues=backtest,data,maintenance
directory=/path/to/algotradingbots
user=www-data
autostart=true
autorestart=true

[program:smarttradebots_beat]
command=/path/to/venv/bin/celery -A algotradingbots beat --loglevel=info
directory=/path/to/algotradingbots
user=www-data
autostart=true
autorestart=true
```

## Troubleshooting

### Common Issues

**1. TA-Lib Import Error**

```
ImportError: No module named 'talib'
```

Solution: Install TA-Lib system library first, then Python wrapper.

**2. Celery Connection Error**

```
kombu.exceptions.OperationalError: [Errno 111] Connection refused
```

Solution: Ensure Redis server is running on port 6379.

**3. Freqtrade Strategy Not Found**

```
ImportError: No module named 'strategies.MyStrategy'
```

Solution: Ensure strategy file exists and class name matches filename.

**4. Data Download Fails**

```
ccxt.NetworkError: binance GET https://api.binance.com/...
```

Solution: Check internet connection and API rate limits.

### Performance Optimization

**Database Optimization**:

```python
# Add database indexes for better query performance
python manage.py dbshell

CREATE INDEX idx_backtest_jobs_status ON backtest_jobs(status);
CREATE INDEX idx_backtest_jobs_created ON backtest_jobs(created_at);
CREATE INDEX idx_backtest_results_return ON backtest_results(total_return_pct);
```

**Celery Worker Scaling**:

```bash
# Run multiple workers for parallel processing
celery -A algotradingbots worker --concurrency=4 --queues=backtest
celery -A algotradingbots worker --concurrency=2 --queues=data,maintenance
```

### Memory Management

**Large Dataset Handling**:

- Limit backtest date ranges for memory efficiency
- Use data pagination in API responses
- Clean up old backtest results regularly

**Monitoring Memory Usage**:

```bash
# Monitor Python memory usage
python -m memory_profiler manage.py run_sample_backtest

# Monitor system resources
htop
```

## Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use Django naming conventions
- Document all public functions and classes
- Add type hints where appropriate

### Testing

```bash
# Run tests
python manage.py test

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request with clear description

## Support & Resources

### Documentation

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Freqtrade Documentation](https://www.freqtrade.io/en/stable/)

### Community

- GitHub Issues: Report bugs and request features
- Discord/Slack: Community discussions (add your links)

### License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Next Steps for Development:**

1. Add user authentication and authorization
2. Implement strategy performance comparison tools
3. Add real-time trading capabilities
4. Create web-based frontend interface
5. Add more exchanges beyond Binance
6. Implement portfolio optimization features
7. Add machine learning strategy generation
