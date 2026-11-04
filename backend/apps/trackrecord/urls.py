from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('investments', views.InvestmentViewSet, basename='lp-investment')

urlpatterns = [
    path('settings/', views.sheet_settings, name='sheet-settings'),
    path('prefill/', views.prefill, name='track-record-prefill'),
    path('pdf/', views.pdf, name='track-record-pdf'),
    path('comments/<int:comment_id>/', views.delete_comment, name='lp-comment-delete'),
    path('managers/<slug:slug>/assessment/', views.manager_assessment, name='manager-assessment'),
    path('managers/<slug:slug>/comments/', views.manager_comment, name='manager-comment'),
    path('manager-comments/<int:comment_id>/', views.delete_manager_comment, name='manager-comment-delete'),
    path('', include(router.urls)),
]
