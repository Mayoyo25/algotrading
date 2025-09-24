from django.db import models
from django.contrib.auth.models import User
import json
from decimal import Decimal

class TradingStrategy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    file_path = models.CharField(max_length=255)  # path to .py strategy file
    default_config = models.JSONField(default=dict)  # default strategy parameters
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trading_strategies'
        
    def __str__(self):
        return self.name

class BacktestJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    strategy = models.ForeignKey(TradingStrategy, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Backtest parameters
    start_date = models.DateField()
    end_date = models.DateField()
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('10000'))
    pairs = models.JSONField(default=list)  # ['BTC/USDT', 'ETH/USDT']
    timeframe = models.CharField(max_length=10, default='1h')
    
    # Strategy specific config
    strategy_config = models.JSONField(default=dict)
    
    # Job status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)  # 0-100
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'backtest_jobs'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.strategy.name} - {self.start_date} to {self.end_date}"

class BacktestResult(models.Model):
    job = models.OneToOneField(BacktestJob, on_delete=models.CASCADE, related_name='result')
    
    # Performance Metrics
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    
    # Returns
    total_return_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    total_return_abs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    annual_return_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Risk Metrics
    max_drawdown_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    max_drawdown_abs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sharpe_ratio = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    calmar_ratio = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    
    # Win Rate
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # percentage
    profit_factor = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    
    # Average metrics
    avg_winning_trade = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    avg_losing_trade = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    avg_trade_duration_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Final balance
    final_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Raw data storage
    trades_data = models.JSONField(default=list)  # List of all trades
    daily_stats = models.JSONField(default=dict)  # Daily performance data
    equity_curve = models.JSONField(default=list)  # For charting
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'backtest_results'
        
    def __str__(self):
        return f"Result for {self.job.strategy.name} - {self.total_return_pct}%"
    
    @property
    def win_loss_ratio(self):
        if self.losing_trades == 0:
            return float('inf') if self.winning_trades > 0 else 0
        return self.winning_trades / self.losing_trades
    
    @property 
    def expectancy(self):
        if self.total_trades == 0:
            return 0
        win_rate = self.win_rate / 100
        avg_win = float(self.avg_winning_trade)
        avg_loss = float(abs(self.avg_losing_trade))
        return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

class MarketData(models.Model):
    """Cache for market data to avoid repeated API calls"""
    pair = models.CharField(max_length=20)  # BTC/USDT
    timeframe = models.CharField(max_length=10)  # 1h, 4h, 1d
    date = models.DateField()
    
    # OHLCV data
    open_price = models.DecimalField(max_digits=20, decimal_places=8)
    high_price = models.DecimalField(max_digits=20, decimal_places=8) 
    low_price = models.DecimalField(max_digits=20, decimal_places=8)
    close_price = models.DecimalField(max_digits=20, decimal_places=8)
    volume = models.DecimalField(max_digits=20, decimal_places=8)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'market_data'
        unique_together = ['pair', 'timeframe', 'date']
        indexes = [
            models.Index(fields=['pair', 'timeframe', 'date']),
        ]
        
    def __str__(self):
        return f"{self.pair} {self.timeframe} {self.date}"