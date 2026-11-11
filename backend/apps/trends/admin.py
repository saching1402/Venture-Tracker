from django.contrib import admin

from .models import Theme, TrendBrief, TrendResource

admin.site.register([Theme, TrendResource, TrendBrief])
