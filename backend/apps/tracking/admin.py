from django.contrib import admin

from .models import ChangeEvent, Snapshot, WatchItem


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ['asof', 'managers', 'companies', 'changes_detected', 'source', 'imported_at']


@admin.register(ChangeEvent)
class ChangeEventAdmin(admin.ModelAdmin):
    list_display = ['date', 'company_name', 'type', 'detail']
    list_filter = ['type', 'date']
    search_fields = ['company_name', 'detail']


@admin.register(WatchItem)
class WatchItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'manager', 'company', 'created_at']
