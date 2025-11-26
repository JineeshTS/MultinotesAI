from django.urls import path
from .views import (
    UserListView,
    DashboardStatsView,
    SystemHealthView,
)

urlpatterns = [
    path('users/', UserListView.as_view(), name='admin-users'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('system/health/', SystemHealthView.as_view(), name='admin-system-health'),
]