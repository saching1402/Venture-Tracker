"""Trends: seed import, payload resolution against the tracker, stages, reading list, import/export, theme refresh."""
import copy
import json
from pathlib import Path

import pytest
from django.test import Client, override_settings

from apps.companies.models import Company
from apps.importer.services import import_payload
from apps.research.models import ResearchJob
from apps.trends import engine
from apps.trends.models import Theme, TrendBrief, TrendResource
from apps.trends.services import import_trends, stage_of
from apps.users.models import User

DATA = Path(__file__).resolve().parent.parent / 'data'
TRACKER = json.loads((DATA / 'tracker.json').read_text())
TRENDS = json.loads((DATA / 'trends.json').read_text())
TOKEN = 'test-import-token'


@pytest.fixture
def setup(db):
    import_payload(copy.deepcopy(TRACKER), source='test')
    import_trends(copy.deepcopy(TRENDS), source='seed')
    User.objects.create_user('a@example.com', 'a-long-test-password', role='analyst')
    User.objects.create_user('v@example.com', 'a-long-test-password', role='viewer')


def login(email):
    c = Client()
    tok = c.post('/api/v1/auth/token/', {'email': email, 'password': 'a-long-test-password'},
                 content_type='application/json').json()['access']
    return c, {'HTTP_AUTHORIZATION': f'Bearer {tok}'}


def test_stage_rule():
    assert stage_of(0.4, 'Private') == 'early'
    assert stage_of(1.0, 'Private') == 'growth'
    assert stage_of(50, 'Public (CBRS)') == 'public'
    assert stage_of(None, 'Acquired (by X)') == 'acquired'
    assert stage_of(None, 'Private', 'growth') == 'growth'


def test_payload_resolves_tracker_and_newer_marks(setup):
    c, h = login('v@example.com')
    r = c.get('/api/v1/trends/', **h).json()
    assert len(r['themes']) == 18 and r['brief']['headline'] and r['brief']['playbook']
    phys = next(t for t in r['themes'] if t['id'] == 'physical-ai-robotics')
    pi = next(x for s in phys['segments'] for x in s['companies'] if x['name'] == 'Physical Intelligence')
    assert pi['tracked'] and pi['valuation_usd_bn'] == 11.0 and pi['valuation_date'] == '2026-03'  # newer sourced mark wins
    figure = next(x for s in phys['segments'] for x in s['companies'] if x['name'] == 'Figure AI')
    assert figure['valuation_usd_bn'] == 39 and figure['stage'] == 'growth'
    assert phys['stats']['companies'] >= 15 and phys['marks'] and phys['resources']
    defense = next(t for t in r['themes'] if t['id'] == 'defense-tech')
    shield = next(x for s in defense['segments'] for x in s['companies'] if x['name'] == 'Shield AI')
    assert shield['valuation_usd_bn'] == 12.7
    assert r['can_edit'] is False and r['resources']


def test_follow_note_and_links(setup):
    v, vh = login('v@example.com')
    assert v.patch('/api/v1/trends/themes/quantum/', {'followed': False}, content_type='application/json', **vh).status_code == 403
    c, h = login('a@example.com')
    r = c.patch('/api/v1/trends/themes/quantum/', {'followed': False, 'user_note': 'Kill if no logical qubits by 2028'},
                content_type='application/json', **h)
    assert r.status_code == 200 and Theme.objects.get(slug='quantum').followed is False
    r = c.post('/api/v1/trends/resources/', {'theme': 'quantum', 'title': 'My note', 'url': 'https://example.com/q', 'kind': 'podcast'},
               content_type='application/json', **h)
    assert r.status_code == 201 and r.json()['pinned'] is True and r.json()['kind'] == 'podcast'
    assert c.post('/api/v1/trends/resources/', {'theme': 'quantum', 'title': 'dup', 'url': 'https://example.com/q'},
                  content_type='application/json', **h).status_code == 400
    rid = r.json()['id']
    assert c.delete(f'/api/v1/trends/resources/{rid}/', **h).status_code == 204
    # a weekly import cannot bring a hidden link back
    import_trends({'themes': [{'id': 'quantum', 'resources': [{'title': 'again', 'url': 'https://example.com/q'}]}]})
    assert not TrendResource.objects.filter(url='https://example.com/q', hidden=False).exists()


@override_settings(IMPORT_TOKEN=TOKEN)
def test_import_export_round_trip(setup):
    c = Client()
    assert c.get('/api/v1/trends/export/').status_code in (401, 403)
    exp = c.get('/api/v1/trends/export/', HTTP_X_IMPORT_TOKEN=TOKEN).json()
    assert len(exp['themes']) == 18 and exp['brief']['playbook']
    Theme.objects.filter(slug='space').update(followed=False, user_note='mine')
    t = next(x for x in exp['themes'] if x['id'] == 'space')
    t['inputs'] = {'capital_growth_x': 4.0, 'capital_note': 'test'}
    t['news'] = [{'date': '2026-11-12', 'headline': 'New space round', 'url': 'https://example.com/s'}]
    d = next(x for x in exp['themes'] if x['id'] == 'defense-tech')
    d['news'] = [{'date': '2026-11-12', 'headline': 'New defense round', 'url': 'https://example.com/d'}]
    exp['brief']['headline'] = 'Week 2'
    exp['asof'] = '2026-11-18'
    r = c.post('/api/v1/trends/import/?source=weekly-brief', exp, content_type='application/json', HTTP_X_IMPORT_TOKEN=TOKEN)
    assert r.status_code == 201, r.content
    space = Theme.objects.get(slug='space')
    assert space.inputs['capital_growth_x'] == 4.0 and space.followed is False and space.user_note == 'mine'  # user fields kept
    assert space.heat == TrendBrief.objects.first().heat['space']  # stored heat is the calculated one
    assert space.news[0]['headline'] == 'New space round'
    defense = Theme.objects.get(slug='defense-tech')
    assert defense.news[0]['headline'] == 'New defense round' and len(defense.news) > 1  # older headlines kept
    assert TrendBrief.objects.count() == 2
    v, vh = login('v@example.com')
    body = v.get('/api/v1/trends/', **vh).json()
    assert body['heat_prev']['space'] < body['history'][-1]['heat']['space'] and len(body['history']) == 2
    sp = next(t for t in body['themes'] if t['id'] == 'space')
    assert sp['score']['components'][0]['id'] == 'capital' and sp['score']['components'][0]['score'] == 100
    assert body['framework']['heat']['components'] and body['framework']['deploy']['levels']
    assert c.post('/api/v1/trends/import/', {'nope': 1}, content_type='application/json', HTTP_X_IMPORT_TOKEN=TOKEN).status_code == 400


def test_theme_refresh_applies_reply(setup, monkeypatch):
    reply = {'heat': 3, 'signal': 'cooling', 'inputs': {'capital_growth_x': 2.0, 'exits_12m': 4}, 'summary': 'Updated.', 'segments': [{'name': 'New seg', 'companies': [{'name': 'NewCo', 'domain': 'newco.ai', 'valuation_usd_bn': 0.3}]}],
             'resources': [{'title': 'Great report', 'url': 'https://example.com/r', 'kind': 'report'}]}
    monkeypatch.setattr(engine, 'ask_claude', lambda *a, **k: ('```json\n' + json.dumps(reply) + '\n```',
                                                                 {'searches': 2, 'input_tokens': 1, 'output_tokens': 1, 'cost': 0.2}))
    job = ResearchJob.objects.create(kind='theme', name='Physical AI', slug='physical-ai-robotics')
    msg = engine.run_theme(job)
    t = Theme.objects.get(slug='physical-ai-robotics')
    assert t.heat != 3 and t.signal != 'cooling'  # heat/signal are calculated, never taken from the reply
    assert t.inputs['capital_growth_x'] == 2.0 and t.inputs['exits_12m'] == 4
    assert t.summary == 'Updated.' and t.segments[0]['name'] == 'New seg'
    assert t.resources.filter(url='https://example.com/r', added_via='refresh').exists()
    assert '1 new' in msg and job.cost == pytest.approx(0.2)
    assert Company.objects.filter(slug='physicalintelligence').exists()


def test_heat_formula():
    import datetime as dt
    from apps.trends import heat
    today = dt.date(2026, 11, 11)
    cos = [
        {'name': 'A', 'stage': 'growth', 'rounds': [{'date': '2025-01', 'post_money_usd_bn': 1.0}, {'date': '2026-05', 'post_money_usd_bn': 2.0}],
         'gp_entries': [('g1', 2025), ('g2', 2020)]},
        {'name': 'B', 'stage': 'early', 'rounds': [{'date': '2024-01', 'post_money_usd_bn': 0.1}, {'date': '2025-01', 'post_money_usd_bn': 0.2}],
         'gp_entries': [('g3', None)]},
        {'name': 'C', 'stage': 'early', 'rounds': [], 'last_round': '$50M Series A, Q3 2026', 'gp_entries': []},
        {'name': 'P', 'stage': 'public', 'rounds': [], 'gp_entries': [('g1', 2025)]},
    ]
    r = heat.compute(cos, {'capital_growth_x': 2.0, 'exits_12m': 1, 'mega_exit': True}, None, today)
    c = {x['id']: x for x in r['components']}
    assert c['capital']['score'] == 75 and c['exits']['score'] == 55
    assert c['velocity']['value'] == '2 of 3' and c['velocity']['score'] == 83   # A and C fresh; text date counted
    assert c['valuation']['score'] == 75                                           # median of 2x and 2x
    assert c['conviction']['value'] == '3 GPs' and c['conviction']['score'] == 15
    assert r['heat'] == round(75 * .3 + 83.33 * .2 + 75 * .15 + 55 * .15 + 15 * .2)
    assert r['heat'] == 62 and r['signal'] == 'emerging'                            # below 65 with capital >= 1.2x
    assert heat.compute(cos, {'capital_growth_x': 0.8}, None, today)['signal'] == 'cooling'
    missing = heat.compute(cos, {}, None, today)
    assert {x['id']: x['scored'] for x in missing['components']}['capital'] is False
    assert heat.text_dates('raised in Mar 2026 after H1 2025') == ['2026-03', '2025-06']
