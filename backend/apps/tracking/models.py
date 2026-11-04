"""Refresh history, detected changes, and per-user watchlists."""
from django.conf import settings
from django.db import models

from apps.companies.models import Company
from apps.managers.models import Manager


class Snapshot(models.Model):
    """One row per data import (weekly refresh)."""
    asof = models.DateField(db_index=True)
    managers = models.PositiveIntegerField(default=0)
    companies = models.PositiveIntegerField(default=0)
    changes_detected = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=64, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'snapshots'
        ordering = ['-imported_at']


class ChangeEvent(models.Model):
    TYPES = [('added', 'Added'), ('removed', 'Removed'), ('valuation', 'Valuation'),
             ('revenue', 'Revenue'), ('status', 'Status'), ('new_position', 'New position')]
    date = models.DateField(db_index=True)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='changes')
    company_name = models.CharField(max_length=255, blank=True)
    manager = models.ForeignKey(Manager, null=True, blank=True, on_delete=models.SET_NULL, related_name='changes')
    type = models.CharField(max_length=20, choices=TYPES)
    from_value = models.FloatField(null=True, blank=True)
    to_value = models.FloatField(null=True, blank=True)
    detail = models.TextField(blank=True)

    class Meta:
        db_table = 'change_events'
        ordering = ['-date', '-id']


class WatchItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watch_items')
    manager = models.ForeignKey(Manager, null=True, blank=True, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'watch_items'
        constraints = [
            models.UniqueConstraint(fields=['user', 'manager'], name='uniq_watch_manager'),
            models.UniqueConstraint(fields=['user', 'company'], name='uniq_watch_company'),
        ]
