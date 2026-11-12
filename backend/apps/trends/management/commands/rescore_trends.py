"""python manage.py rescore_trends [--seed-inputs data/trends.json]

Fills heat inputs that are missing on existing themes from the seed file (never overwrites newer weekly inputs),
then recalculates heat and signal for every theme.
"""
import json

from django.core.management.base import BaseCommand

from apps.trends.models import Theme
from apps.trends.services import rescore


class Command(BaseCommand):
    help = 'Recalculate theme heat and signal; optionally backfill missing inputs from the seed.'

    def add_arguments(self, parser):
        parser.add_argument('--seed-inputs', default='')

    def handle(self, seed_inputs='', **opts):
        filled = 0
        if seed_inputs:
            try:
                seed = {t['id']: t.get('inputs') or {} for t in json.load(open(seed_inputs, encoding='utf-8')).get('themes', [])}
            except (OSError, ValueError):
                seed = {}
            for t in Theme.objects.all():
                add = {k: v for k, v in seed.get(t.slug, {}).items() if k not in (t.inputs or {})}
                if add:
                    t.inputs = {**(t.inputs or {}), **add}
                    t.save(update_fields=['inputs'])
                    filled += 1
        rescore()
        self.stdout.write(self.style.SUCCESS(f'Trends rescored ({filled} themes had inputs filled from the seed).'))
