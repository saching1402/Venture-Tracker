"""API smoke tests: auth gate, seed import, change detection, partial-snapshot guard, watchlist."""
import copy
import json
from pathlib import Path

import pytest
from django.test import Client, override_settings

from apps.companies.models import Company
from apps.importer.services import ImportRejected, import_payload
from apps.tracking.models import ChangeEvent
from apps.users.models import User

SEED = json.loads((Path(__file__).resolve().parent.parent / 'data' / 'tracker.json').read_text())


@pytest.fixture
def seeded(db):
    import_payload(copy.deepcopy(SEED), source='test')


@pytest.fixture
def auth(db):
    User.objects.create_user('analyst@example.com', 'a-long-test-password')
    c = Client()
    tok = c.post('/api/v1/auth/token/', {'email': 'analyst@example.com', 'password': 'a-long-test-password'},
                 content_type='application/json').json()['access']
    return {'HTTP_AUTHORIZATION': f'Bearer {tok}'}


def test_health_is_public(db):
    assert Client().get('/health/').json() == {'status': 'ok'}


def test_data_requires_login(seeded):
    assert Client().get('/api/v1/companies/').status_code == 401


def test_lists_and_details(seeded, auth):
    c = Client()
    cos = c.get('/api/v1/companies/?page_size=5000', **auth).json()
    assert cos['count'] == len(SEED['companies'])
    mgrs = c.get('/api/v1/managers/?page_size=500', **auth).json()
    assert mgrs['count'] >= 50
    one = c.get('/api/v1/companies/anthropic/', **auth).json()
    assert one['valuation_history'] and one['gp_positions']
    gp = c.get('/api/v1/managers/a16z/', **auth).json()
    assert gp['holdings']


def test_reimport_logs_changes_and_rejects_partial(seeded):
    nxt = copy.deepcopy(SEED)
    nxt['asof'] = '2030-01-05'
    target = next(x for x in nxt['companies'] if x['id'] == 'anthropic')
    target['latest_valuation_usd_bn'] = (target['latest_valuation_usd_bn'] or 1) * 1.5
    stats = import_payload(nxt, source='test')
    assert stats['changes'] >= 1
    assert ChangeEvent.objects.filter(type='valuation', company__slug='anthropic').exists()
    with pytest.raises(ImportRejected):
        import_payload({'asof': '2030-01-12', 'firms': nxt['firms'], 'companies': nxt['companies'][:10]})
    assert Company.objects.count() == len(SEED['companies'])


@override_settings(IMPORT_TOKEN='t0ken')
def test_import_endpoint_needs_token(seeded):
    c = Client()
    assert c.post('/api/v1/import/', '{}', content_type='application/json').status_code == 401
    r = c.get('/api/v1/export/', HTTP_X_IMPORT_TOKEN='t0ken')
    assert r.status_code == 200 and len(r.json()['companies']) == len(SEED['companies'])


def test_watchlist_round_trip(seeded, auth):
    c = Client()
    r = c.post('/api/v1/watchlist/', {'kind': 'company', 'id': 'anthropic', 'on': True}, content_type='application/json', **auth)
    assert r.json()['companies'] == ['anthropic']
    r = c.post('/api/v1/watchlist/', {'kind': 'company', 'id': 'anthropic', 'on': False}, content_type='application/json', **auth)
    assert r.json()['companies'] == []
