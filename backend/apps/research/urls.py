from django.urls import path

from . import views

urlpatterns = [
    path('research/', views.research, name='research'),
    path('research/<uuid:job_id>/retry/', views.retry, name='research-retry'),
    path('research/profiles/', views.profiles, name='research-profiles'),
]
