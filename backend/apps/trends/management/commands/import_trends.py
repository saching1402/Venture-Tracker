"""python manage.py import_trends data/trends.json [--if-empty]"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.trends.models import Theme
from apps.trends.services import import_trends


class Command(BaseCommand):
    help = 'Load a trends.json snapshot (themes, market map, reading list, weekly brief).'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('--if-empty', action='store_true', help='Only load when no themes exist yet')

    def handle(self, path, if_empty=False, **opts):
        if if_empty and Theme.objects.exists():
            self.stdout.write('Themes present: skipping trends seed.')
            return
        try:
            with open(path, encoding='utf-8') as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            raise CommandError(f'Could not read {path}: {e}')
        self.stdout.write(self.style.SUCCESS(f'Trends imported: {import_trends(payload, source="seed")}'))
