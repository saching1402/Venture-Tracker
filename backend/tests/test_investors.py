"""Investor sweep: GP matching, positions, other investors, additive merge, token auth."""
import copy
import json
from pathlib import Path

import pytest
from django.test import Client, override_settings

from apps.companies.investors import ManagerIndex
from apps.companies.models import Company, Position
from apps.importer.services import import_payload
from apps.tracking.models import ChangeEvent

SEED = json.loads((Path(__file__).resolve().parent.parent / 'data' / 'tracker.json').read_text())


@pytest.fixture
def seeded(db):
    import_payload(copy.deepcopy(SEED), source='test')


def test_matching(seeded):
    ix = ManagerIndex()
    ok = {'Accel': 'accel', 'Lightspeed': 'lightspeed', 'Thrive': 'thrive', 'a16z': 'a16z', 'KPCB': 'kleinerperkins',
          'Founders Fund': 'foundersfund', 'Eclipse Ventures': 'eclipse', 'NEA': 'nea', 'Sequoia': 'sequoia'}
    for name, slug_part in ok.items():
        m = ix.match(name)
        assert m and slug_part.replace('kleinerperkins', 'kleiner') in m.slug.replace('-', '') or slug_part in m.name.lower().replace(' ', ''), name
    for name in ['Bain Capital', 'Accel-KKR', 'Sequoia Capital China', 'Index', 'Insight', 'Founders', 'US', 'Kindred Capital']:
        assert ix.match(name) is None, name


@override_settings(IMPORT_TOKEN='tok')
def test_merge_endpoint(seeded):
    c = Client()
    body = {'companies': [{'id': 'fractile', 'sources': ['https://example.com/fractile'], 'investors': [
        {'name': 'Accel', 'lead': True, 'round': 'Series B', 'year': 2026}, {'name': 'Founders Fund', 'lead': True},
        {'name': 'Felicis'}, {'name': 'Inovia Capital', 'round': 'Seed', 'year': 2024},
        {'name': 'NATO Innovation Fund'}, 'Kindred Capital', {'name': 'kindred capital'}]}, {'id': 'nope', 'investors': ['Accel']}]}
    assert c.post('/api/v1/companies/investors/', body, content_type='application/json').status_code in (401, 403)
    r = c.post('/api/v1/companies/investors/', body, content_type='application/json', HTTP_X_IMPORT_TOKEN='tok').json()
    co = Company.objects.get(slug='fractile')
    mgrs = set(co.positions.values_list('manager__name', flat=True))
    assert {'Accel', 'Founders Fund', 'Felicis', 'Inovia Capital'} <= mgrs
    assert r['positions_added'] == 2 and r['unknown_companies'] == ['nope']
    acc = Position.objects.get(company=co, manager__name='Accel')
    assert acc.lead and acc.entry_round == 'Series B' and acc.first_invest_year == 2026 and acc.via == 'investor sweep'
    assert Position.objects.get(company=co, manager__name='Inovia Capital').first_invest_year == 2024  # enriched, not duplicated
    assert co.other_investors.count('Kindred Capital') == 1 and 'NATO Innovation Fund' in co.other_investors
    assert co.investor_sources == ['https://example.com/fractile'] and co.investors_updated_at
    assert ChangeEvent.objects.filter(company=co, type='new_position').count() == 2
    # idempotent
    r2 = c.post('/api/v1/companies/investors/', body, content_type='application/json', HTTP_X_IMPORT_TOKEN='tok').json()
    assert r2['positions_added'] == 0 and r2['others_added'] == 0
    # the company detail and the GP holdings both show it
    assert co.positions.filter(manager__slug__isnull=False).count() >= 4
