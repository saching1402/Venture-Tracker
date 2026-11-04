"""Auto-research jobs: Claude + web search fills a manager or company profile."""
import uuid

from django.conf import settings
from django.db import models


class ResearchJob(models.Model):
    KINDS = [('manager', 'Manager'), ('company', 'Company')]
    STATUSES = [('queued', 'Queued'), ('running', 'Running'), ('done', 'Done'), ('failed', 'Failed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=10, choices=KINDS)
    name = models.CharField(max_length=255, help_text='Name as typed by the user')
    website = models.CharField(max_length=500, blank=True)
    slug = models.SlugField(max_length=96, help_text='Target manager / company slug')
    include_portfolio = models.BooleanField(default=False, help_text='Manager jobs: also research its portfolio companies')
    position = models.JSONField(default=dict, blank=True, help_text='Company jobs spawned by a manager job: the position to record')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    status = models.CharField(max_length=10, choices=STATUSES, default='queued', db_index=True)
    error = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    searches = models.PositiveIntegerField(default=0)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'research_jobs'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.kind}:{self.slug} [{self.status}]'

    @property
    def cost_usd(self) -> float:
        """Rough cost: Sonnet-class token pricing plus $10 per 1,000 searches."""
        return round(self.input_tokens * 2e-6 + self.output_tokens * 10e-6 + self.searches * 0.01, 2)
