from django.urls import path

from .views import analyze, health, provider_status

urlpatterns = [
    path('health', health, name='health'),
    path('providers/status', provider_status, name='provider-status'),
    path('routes/analyze', analyze, name='route-analyze'),
]
