from django.urls import path

from . import views

urlpatterns = [
    path('meta/', views.meta, name='meta'),
    path('changes/', views.changes, name='changes'),
    path('watchlist/', views.watchlist, name='watchlist'),
]
