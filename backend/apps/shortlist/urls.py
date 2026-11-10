from django.urls import path

from . import views

urlpatterns = [
    path('', views.shortlist, name='shortlist'),
    path('refresh/', views.refresh_all, name='shortlist-refresh-all'),
    path('news/<int:news_id>/', views.dismiss_news, name='shortlist-news-dismiss'),
    path('<int:pk>/', views.shortlist_item, name='shortlist-item'),
    path('<int:pk>/refresh/', views.refresh_item, name='shortlist-refresh'),
]
