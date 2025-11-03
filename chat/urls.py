from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ChatSessionViewSet

app_name = 'chat'

router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='session')

urlpatterns = [
    path('api/', include(router.urls)),
]
