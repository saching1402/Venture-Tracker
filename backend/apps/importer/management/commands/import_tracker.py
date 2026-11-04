"""python manage.py import_tracker data/tracker.json [--force]"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.importer.services import ImportRejected, import_payload


class Command(BaseCommand):
    help = 'Load a tracker.json snapshot (managers, companies, rounds, positions) into the database.'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('--force', action='store_true', help='Accept a snapshot much smaller than the live data')

    def handle(self, path, force=False, **opts):
        try:
            with open(path, encoding='utf-8') as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            raise CommandError(f'Could not read {path}: {e}')
        try:
            stats = import_payload(payload, source='command', force=force)
        except ImportRejected as e:
            raise CommandError(str(e))
        self.stdout.write(self.style.SUCCESS(f'Imported: {stats}'))
