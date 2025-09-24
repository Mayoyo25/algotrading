# backtest/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'strategies', views.TradingStrategyViewSet, basename='strategies')
router.register(r'jobs', views.BacktestJobViewSet, basename='jobs')
router.register(r'results', views.BacktestResultViewSet, basename='results')

app_name = 'backtest'

urlpatterns = [
    path('api/', include(router.urls)),
]