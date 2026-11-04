"""Portfolio companies, their priced rounds, and tracked-manager positions."""
from django.db import models

from apps.managers.models import Manager


class Company(models.Model):
    slug = models.SlugField(max_length=96, unique=True)
    name = models.CharField(max_length=255, db_index=True)
    website = models.URLField(max_length=500, blank=True)
    hq = models.CharField(max_length=255, blank=True)
    founded = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    sector = models.CharField(max_length=64, blank=True, db_index=True)
    focus_tags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=255, blank=True, default='Private')

    latest_valuation_usd_bn = models.FloatField(null=True, blank=True, db_index=True)
    valuation_date = models.CharField(max_length=20, blank=True)
    valuation_label = models.CharField(max_length=20, blank=True)
    valuation_basis = models.CharField(max_length=64, blank=True)
    valuation_stale = models.BooleanField(default=False)
    legacy = models.BooleanField(default=False, help_text='Pre-2010 holding long since listed or sold')
    first_mark_usd_bn = models.FloatField(null=True, blank=True)
    first_mark_date = models.CharField(max_length=20, blank=True)
    step_up_x = models.FloatField(null=True, blank=True)

    total_raised_usd_bn = models.FloatField(null=True, blank=True)
    revenue_metric = models.CharField(max_length=100, blank=True)
    revenue_usd_bn = models.FloatField(null=True, blank=True)
    revenue_date = models.CharField(max_length=20, blank=True)
    revenue_label = models.CharField(max_length=20, blank=True)
    ev_rev_x = models.FloatField(null=True, blank=True)
    growth = models.TextField(blank=True)
    profitability = models.TextField(blank=True)
    employees = models.IntegerField(null=True, blank=True)
    ceo = models.CharField(max_length=255, blank=True)
    other_investors = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    sources = models.JSONField(default=list, blank=True)
    last_verified = models.CharField(max_length=20, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    managers = models.ManyToManyField(Manager, through='Position', related_name='companies')

    class Meta:
        db_table = 'companies'
        ordering = ['-latest_valuation_usd_bn', 'name']
        verbose_name_plural = 'companies'

    def __str__(self) -> str:
        return self.name


class ValuationRound(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='rounds')
    date = models.CharField(max_length=20, blank=True, db_index=True)
    round = models.CharField(max_length=255, blank=True)
    post_money_usd_bn = models.FloatField(null=True, blank=True)
    lead = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'valuation_rounds'
        ordering = ['date', 'id']


class Position(models.Model):
    """A tracked manager's position in a company."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='positions')
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE, related_name='positions')
    first_invest_year = models.IntegerField(null=True, blank=True)
    entry_round = models.CharField(max_length=255, blank=True)
    fund = models.CharField(max_length=255, blank=True)
    lead = models.BooleanField(default=False)
    via = models.CharField(max_length=64, blank=True, help_text='"investor list" when inferred, not confirmed')
    entry_post_usd_bn = models.FloatField(null=True, blank=True)
    markup_x = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'positions'
        unique_together = [('company', 'manager')]
