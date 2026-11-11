from django.urls import path

from . import views

urlpatterns = [
    path('', views.trends, name='trends'),
    path('import/', views.trends_import, name='trends-import'),
    path('export/', views.trends_export, name='trends-export'),
    path('resources/', views.resource_add, name='trends-resource-add'),
    path('resources/<int:pk>/', views.resource_item, name='trends-resource'),
    path('themes/<slug:slug>/', views.theme_update, name='trends-theme'),
    path('themes/<slug:slug>/refresh/', views.theme_refresh, name='trends-theme-refresh'),
]
