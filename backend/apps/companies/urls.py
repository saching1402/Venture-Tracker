from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CompanyViewSet, recent_rounds

router = DefaultRouter()
router.register('', CompanyViewSet, basename='company')
urlpatterns = [
    path('rounds/recent/', recent_rounds, name='recent-rounds'),
    path('', include(router.urls)),
]
