"""
Trends: investable themes across venture and growth, refreshed weekly.

- Theme: one investable theme (e.g. Physical AI & robotics) with its thesis, heat, deploy view by stage
  (early vs growth), reported funding figures, risks / catalysts, and a market map (segments → companies).
- TrendResource: the reading list — reports, articles, GP interviews, podcasts, videos, data — per theme or global.
- TrendBrief: one row per weekly update (headline, deploy-now list, market stats, heat per theme) so heat can be
  tracked over time.

Stage convention: EARLY = latest post-money below EARLY_MAX_USD_BN; GROWTH = at or above it (private);
PUBLIC / EXITED shown separately.
"""
from django.conf import settings
from django.db import models

EARLY_MAX_USD_BN = 1.0

SIGNALS = [('accelerating', 'Accelerating'), ('hot', 'Hot'), ('steady', 'Steady'), ('emerging', 'Emerging'), ('cooling', 'Cooling')]
DEPLOY = [('overweight', 'Overweight'), ('selective', 'Selective'), ('watch', 'Watch'), ('avoid', 'Avoid')]


class Theme(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=60, blank=True)
    order = models.IntegerField(default=100)
    color = models.CharField(max_length=9, blank=True)

    summary = models.TextField(blank=True)
    why_now = models.TextField(blank=True)
    deploy_view = models.TextField(blank=True)
    signal = models.CharField(max_length=14, choices=SIGNALS, blank=True)
    heat = models.IntegerField(null=True, blank=True, help_text='0-100, calculated by heat.compute (stored for history)')
    conviction = models.CharField(max_length=8, blank=True)
    horizon = models.CharField(max_length=20, blank=True, help_text='now / 1-3y / 3-7y / 7y+ to large outcomes')
    deploy_early = models.CharField(max_length=12, choices=DEPLOY, blank=True)
    deploy_growth = models.CharField(max_length=12, choices=DEPLOY, blank=True)

    inputs = models.JSONField(default=dict, blank=True, help_text='Sourced heat inputs: capital_growth_x, capital_note, exits_12m, mega_exit, exits_note')
    funding = models.JSONField(default=list, blank=True, help_text='[{period, stage, capital_usd_bn, deals, note, source, url, label}]')
    valuation_notes = models.TextField(blank=True)
    risks = models.JSONField(default=list, blank=True)
    catalysts = models.JSONField(default=list, blank=True)
    kpis = models.JSONField(default=list, blank=True, help_text='Signals to watch')
    segments = models.JSONField(default=list, blank=True, help_text='[{name, companies:[{name, id?, domain, stage, ...}]}]')
    news = models.JSONField(default=list, blank=True, help_text='Latest dated headlines [{date, headline, url, source, summary}]')
    sources = models.JSONField(default=list, blank=True)

    followed = models.BooleanField(default=True)
    user_note = models.TextField(blank=True)
    research_status = models.CharField(max_length=12, blank=True)
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trend_themes'
        ordering = ['order', 'name']

    def __str__(self) -> str:
        return self.name


class TrendResource(models.Model):
    KINDS = [('report', 'Report'), ('article', 'Article'), ('news', 'News'), ('interview', 'GP interview'),
             ('podcast', 'Podcast'), ('video', 'Video'), ('newsletter', 'Newsletter'), ('data', 'Data / tracker')]
    theme = models.ForeignKey(Theme, null=True, blank=True, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=1000)
    source = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=12, choices=KINDS, default='article')
    date = models.CharField(max_length=10, blank=True, db_index=True)
    summary = models.TextField(blank=True)
    added_via = models.CharField(max_length=10, default='weekly', help_text='weekly / refresh / user')
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    pinned = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trend_resources'
        ordering = ['-pinned', '-date', '-id']
        constraints = [models.UniqueConstraint(fields=['theme', 'url'], name='trend_resource_unique_url')]


class TrendBrief(models.Model):
    as_of = models.DateField(db_index=True)
    headline = models.CharField(max_length=500, blank=True)
    summary = models.TextField(blank=True)
    highlights = models.JSONField(default=list, blank=True)
    deploy_now = models.JSONField(default=list, blank=True, help_text='[{theme, stage, why}]')
    watch = models.JSONField(default=list, blank=True)
    cooling = models.JSONField(default=list, blank=True)
    market = models.JSONField(default=dict, blank=True, help_text='Headline market stats with sources')
    playbook = models.JSONField(default=list, blank=True, help_text='How to stay on top: [{title, detail, cadence, links}]')
    heat = models.JSONField(default=dict, blank=True, help_text='{theme slug: heat} at this date')
    source = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trend_briefs'
        ordering = ['-as_of', '-id']
