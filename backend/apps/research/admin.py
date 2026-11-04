from django.contrib import admin

from .models import ResearchJob


@admin.register(ResearchJob)
class ResearchJobAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'kind', 'name', 'status', 'searches', 'cost_usd', 'created_by']
    list_filter = ['kind', 'status']
    search_fields = ['name', 'slug', 'error']
    readonly_fields = ['cost_usd']
