"""Venture / growth managers (GPs), their funds and key people."""
from django.db import models


class Manager(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    website = models.URLField(max_length=500, blank=True)
    portfolio_url = models.URLField(max_length=500, blank=True)
    hq = models.CharField(max_length=255, blank=True)
    other_offices = models.JSONField(default=list, blank=True)
    founded = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=100, blank=True)
    aum_usd_bn = models.FloatField(null=True, blank=True)
    aum_label = models.CharField(max_length=20, blank=True)
    aum_date = models.CharField(max_length=20, blank=True)
    overview = models.TextField(blank=True)
    check_size = models.TextField(blank=True)
    stages = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    team_size = models.CharField(max_length=255, blank=True)
    team_label = models.CharField(max_length=20, blank=True)
    performance = models.TextField(blank=True)
    performance_label = models.CharField(max_length=20, blank=True)
    best_performers = models.JSONField(default=list, blank=True)
    notable_exits = models.JSONField(default=list, blank=True)
    recent_activity = models.TextField(blank=True)
    watch_items = models.TextField(blank=True)
    sources = models.JSONField(default=list, blank=True)
    last_verified = models.CharField(max_length=20, blank=True)
    is_stub = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'managers'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Fund(models.Model):
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE, related_name='funds')
    name = models.CharField(max_length=255)
    size_usd_bn = models.FloatField(null=True, blank=True)
    vintage = models.IntegerField(null=True, blank=True)
    label = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'manager_funds'
        ordering = ['-vintage', 'name']


class KeyPerson(models.Model):
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE, related_name='people')
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)
    focus = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'manager_people'
        ordering = ['order']
