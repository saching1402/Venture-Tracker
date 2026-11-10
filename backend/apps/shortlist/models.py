"""
Shortlist: companies and funds the LP tracks closely and expects to back across several rounds / vintages.

Two priority tracks per item (yours and Claude's), each L1 / L2 / L3 with every change logged,
plus a news feed and a dated log of marks written by each web refresh.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

PRIORITIES = [('L1', 'L1 · most important'), ('L2', 'L2'), ('L3', 'L3')]


class ShortlistItem(models.Model):
    KINDS = [('company', 'Direct / co-investment'), ('fund', 'Fund / GP')]
    MOMENTUM = [('up', 'Improving'), ('flat', 'Steady'), ('down', 'Deteriorating')]

    kind = models.CharField(max_length=10, choices=KINDS, db_index=True)
    company = models.ForeignKey('companies.Company', null=True, blank=True, on_delete=models.SET_NULL, related_name='shortlist_items')
    manager = models.ForeignKey('managers.Manager', null=True, blank=True, on_delete=models.SET_NULL, related_name='shortlist_items')
    name = models.CharField(max_length=255)

    my_priority = models.CharField(max_length=2, choices=PRIORITIES, blank=True)
    my_priority_since = models.DateTimeField(null=True, blank=True)
    claude_priority = models.CharField(max_length=2, choices=PRIORITIES, blank=True)
    claude_priority_since = models.DateTimeField(null=True, blank=True)
    claude_rationale = models.TextField(blank=True)

    thesis = models.TextField(blank=True, help_text='Why you are tracking it')
    rounds_plan = models.TextField(blank=True, help_text='Which rounds / vintages you intend to back, access route')
    target_allocation_usd_m = models.FloatField(null=True, blank=True)

    # written by each refresh
    brief = models.TextField(blank=True)
    momentum = models.CharField(max_length=5, choices=MOMENTUM, blank=True)
    performance = models.TextField(blank=True, help_text='Companies: revenue / growth / margins. Funds: fund performance')
    next_round = models.TextField(blank=True, help_text='Next raise / tender / IPO, or next fund and re-up window')
    catalysts = models.JSONField(default=list, blank=True)
    risks = models.JSONField(default=list, blank=True)
    sources = models.JSONField(default=list, blank=True)
    research_status = models.CharField(max_length=12, blank=True, help_text='queued / running / failed while a refresh runs')
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shortlist_items'
        ordering = ['my_priority', 'name']
        constraints = [
            models.UniqueConstraint(fields=['company'], condition=Q(company__isnull=False), name='shortlist_unique_company'),
            models.UniqueConstraint(fields=['manager'], condition=Q(manager__isnull=False), name='shortlist_unique_manager'),
        ]

    def __str__(self) -> str:
        return f'{self.name} ({self.kind})'


class PriorityChange(models.Model):
    TRACKS = [('mine', 'My priority'), ('claude', "Claude's priority")]
    item = models.ForeignKey(ShortlistItem, on_delete=models.CASCADE, related_name='priority_log')
    track = models.CharField(max_length=6, choices=TRACKS)
    old = models.CharField(max_length=2, blank=True)
    new = models.CharField(max_length=2, blank=True)
    note = models.TextField(blank=True)
    changed_by = models.CharField(max_length=255, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'shortlist_priority_log'
        ordering = ['-changed_at', '-id']


class NewsItem(models.Model):
    CATEGORIES = ['funding', 'valuation', 'revenue', 'product', 'customers', 'people', 'regulatory', 'legal',
                  'ipo', 'm&a', 'fundraise', 'performance', 'portfolio', 'other']
    IMPORTANCE = [('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]
    item = models.ForeignKey(ShortlistItem, on_delete=models.CASCADE, related_name='news')
    date = models.CharField(max_length=10, blank=True, db_index=True, help_text='YYYY-MM-DD (or YYYY-MM)')
    headline = models.CharField(max_length=500)
    summary = models.TextField(blank=True)
    category = models.CharField(max_length=20, blank=True)
    importance = models.CharField(max_length=6, choices=IMPORTANCE, default='medium')
    source = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=1000, blank=True)
    hidden = models.BooleanField(default=False, help_text='Dismissed by the user')
    found_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shortlist_news'
        ordering = ['-date', '-id']


class ShortlistMark(models.Model):
    """One row per refresh: what the item looked like that day (valuation / revenue, or AUM for a GP)."""
    item = models.ForeignKey(ShortlistItem, on_delete=models.CASCADE, related_name='marks')
    as_of = models.DateField(db_index=True)
    valuation_usd_bn = models.FloatField(null=True, blank=True)
    valuation_date = models.CharField(max_length=20, blank=True)
    revenue_usd_bn = models.FloatField(null=True, blank=True)
    revenue_metric = models.CharField(max_length=100, blank=True)
    revenue_date = models.CharField(max_length=20, blank=True)
    aum_usd_bn = models.FloatField(null=True, blank=True)
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'shortlist_marks'
        ordering = ['-as_of', '-id']
