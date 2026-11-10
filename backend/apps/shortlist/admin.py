from django.contrib import admin

from .models import NewsItem, PriorityChange, ShortlistItem, ShortlistMark

admin.site.register([ShortlistItem, PriorityChange, NewsItem, ShortlistMark])
