"""python manage.py research_worker — runs queued auto-research jobs (started by start.sh)."""
import datetime as dt
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from apps.research.engine import claim_next, run_job
from apps.research.models import ResearchJob

log = logging.getLogger('apps.research')


def _work() -> bool:
    close_old_connections()
    job = claim_next()
    if job is None:
        return False
    log.info('Research job %s started: %s %s', job.id, job.kind, job.name)
    run_job(job)
    log.info('Research job %s finished: %s', job.id, job.status)
    close_old_connections()
    return True


class Command(BaseCommand):
    help = 'Process queued Add-manager / Add-company research jobs.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Drain the queue once, then exit')

    def handle(self, once=False, **opts):
        # jobs left "running" by a previous container are re-queued
        stale = timezone.now() - dt.timedelta(minutes=30)
        n = ResearchJob.objects.filter(status='running', started_at__lt=stale).update(status='queued')
        if n:
            log.info('Re-queued %s interrupted research jobs', n)
        workers = max(1, settings.RESEARCH_CONCURRENCY)
        self.stdout.write(f'Research worker running ({workers} parallel, model {settings.RESEARCH_MODEL}, '
                          f'API key {"set" if settings.ANTHROPIC_API_KEY else "MISSING"})')
        with ThreadPoolExecutor(max_workers=workers) as pool:
            while True:
                busy = list(pool.map(lambda _: _work(), range(workers)))
                if once and not any(busy):
                    return
                if not any(busy):
                    time.sleep(3)
