# algotradingbots/urls.py
"""
URL configuration for algotradingbots project.
"""
from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('backtest/', include('backtest.urls')),
    path('api/v1/backtest/', include('backtest.urls')),
] + debug_toolbar_urls()

# Simple home view
from django.http import JsonResponse

def api_info(request):
    return JsonResponse({
        'service': 'SmartTradeBots Backtesting API',
        'version': '1.0',
        'endpoints': {
            'strategies': '/api/v1/backtest/api/strategies/',
            'jobs': '/api/v1/backtest/api/jobs/',
            'results': '/api/v1/backtest/api/results/',
            'admin': '/admin/'
        },
        'docs': 'https://smarttradebots.com/docs'
    })

urlpatterns.insert(0, path('', api_info, name='api_info'))