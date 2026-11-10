"""Shortlist: seed, linking, priorities + log, permissions, refresh apply (mocked Claude), import protection."""
import copy
import json
from pathlib import Path

import pytest
from django.test import Client

from apps.companies.models import Company
from apps.importer.services import import_payload
from apps.research.models import ResearchJob
from apps.shortlist import engine
from apps.shortlist.models import NewsItem, PriorityChange, ShortlistItem
from apps.users.models import User

SEED = json.loads((Path(__file__).resolve().parent.parent / 'data' / 'tracker.json').read_text())


@pytest.fixture
def setup(db):
    import_payload(copy.deepcopy(SEED), source='test')
    User.objects.create_user('a@example.com', 'a-long-test-password', role='analyst', full_name='Sachin')
    User.objects.create_user('v@example.com', 'a-long-test-password', role='viewer')


def login(email):
    c = Client()
    tok = c.post('/api/v1/auth/token/', {'email': email, 'password': 'a-long-test-password'},
                 content_type='application/json').json()['access']
    return c, {'HTTP_AUTHORIZATION': f'Bearer {tok}'}


def test_seed_links_and_lists(setup):
    c, h = login('v@example.com')
    r = c.get('/api/v1/shortlist/', **h).json()
    names = {i['name'] for i in r['items']}
    assert {'Anthropic', 'OpenAI', 'Anduril Industries', 'Physical Intelligence', 'Baseten', 'Fireworks AI'} <= names
    a = next(i for i in r['items'] if i['name'] == 'Anthropic')
    assert a['company']['id'] == 'anthropic' and a['company']['latest_valuation_usd_bn']
    assert a['my_priority'] == 'L1' and a['my_priority_since'] and a['claude_priority'] == 'L1'
    assert {p['track'] for p in a['priority_log']} == {'mine', 'claude'}
    assert r['can_edit'] is False


def test_priority_change_is_logged_and_viewer_blocked(setup):
    item = ShortlistItem.objects.get(name='Baseten')
    v, vh = login('v@example.com')
    assert v.patch(f'/api/v1/shortlist/{item.id}/', {'my_priority': 'L2'}, content_type='application/json', **vh).status_code == 403
    c, h = login('a@example.com')
    r = c.patch(f'/api/v1/shortlist/{item.id}/', {'my_priority': 'L2', 'note': 'Margins unclear'},
                content_type='application/json', **h).json()
    assert r['my_priority'] == 'L2'
    log = r['priority_log'][0]
    assert (log['track'], log['old'], log['new'], log['note'], log['changed_by']) == ('mine', 'L1', 'L2', 'Margins unclear', 'Sachin')
    assert c.patch(f'/api/v1/shortlist/{item.id}/', {'my_priority': 'L9'}, content_type='application/json', **h).status_code == 400
    # same level again is not a change
    c.patch(f'/api/v1/shortlist/{item.id}/', {'my_priority': 'L2'}, content_type='application/json', **h)
    assert PriorityChange.objects.filter(item=item, track='mine').count() == 2


def test_add_existing_company_and_fund(setup):
    c, h = login('a@example.com')
    co = Company.objects.exclude(shortlist_items__isnull=False).order_by('-latest_valuation_usd_bn').first()
    r = c.post('/api/v1/shortlist/', {'kind': 'company', 'id': co.slug, 'my_priority': 'L3', 'thesis': 'x'},
               content_type='application/json', **h)
    assert r.status_code == 201 and r.json()['my_priority'] == 'L3' and r.json()['company']['id'] == co.slug
    assert c.post('/api/v1/shortlist/', {'kind': 'company', 'id': co.slug}, content_type='application/json', **h).status_code == 409
    r = c.post('/api/v1/shortlist/', {'kind': 'fund', 'name': SEED['firms'][0]['name'], 'my_priority': 'L1'},
               content_type='application/json', **h)
    assert r.status_code == 201 and r.json()['kind'] == 'fund' and r.json()['manager']['id'] == SEED['firms'][0]['id']


REPLY = {
    'brief': 'Raised again.', 'momentum': 'up', 'status': 'Private',
    'valuation': {'latest_valuation_usd_bn': 20.0, 'valuation_date': '2026-11', 'valuation_label': 'REPORTED'},
    'new_rounds': [{'date': '2026-11', 'round': 'Series G', 'post_money_usd_bn': 20.0, 'lead': 'IVP'}],
    'revenue': {'revenue_metric': 'ARR', 'revenue_usd_bn': 1.1, 'revenue_date': '2026-10', 'revenue_label': 'REPORTED'},
    'news': [{'date': '2026-11-05', 'headline': 'Baseten raises Series E', 'url': 'https://example.com/a', 'importance': 'high', 'category': 'funding'},
             {'date': '2026-11-01', 'headline': 'Baseten raises Series E!', 'url': 'https://example.com/b'}],
    'risks': [{'text': 'GPU pricing', 'severity': 'high'}],
    'claude_priority': 'L1', 'priority_rationale': 'Momentum and access.',
}


def test_refresh_applies_reply(setup, monkeypatch):
    item = ShortlistItem.objects.get(name='Baseten')
    engine.link_target(item)
    monkeypatch.setattr(engine, 'ask_claude', lambda *a, **k: ('```json\n' + json.dumps(REPLY) + '\n```',
                                                                 {'searches': 3, 'input_tokens': 10, 'output_tokens': 5, 'cost': 0.1}))
    job = ResearchJob.objects.create(kind='shortlist', name=item.name, slug=str(item.id))
    summary = engine.run_refresh(job)
    item.refresh_from_db()
    co = Company.objects.get(slug='baseten')
    assert co.latest_valuation_usd_bn == 20.0 and co.revenue_usd_bn == 1.1
    assert co.rounds.filter(round='Series G').count() == 1
    assert item.news.count() == 1  # second headline is a near-duplicate
    assert item.claude_priority == 'L1' and item.priority_log.filter(track='claude', old='L2', new='L1').exists()
    assert item.marks.count() == 1 and item.last_refreshed_at and item.risks[0]['text'] == 'GPU pricing'
    assert 'L1' in summary
    # a second refresh with the same reply adds nothing new
    engine.run_refresh(job)
    assert item.news.count() == 1 and co.rounds.filter(round='Series G').count() == 1
    assert item.priority_log.filter(track='claude').count() == 2
    # dismissed news stays hidden and is not re-added
    c, h = login('a@example.com')
    n = NewsItem.objects.get(item=item)
    assert c.delete(f'/api/v1/shortlist/news/{n.id}/', **h).status_code == 204
    engine.run_refresh(job)
    r = c.get(f'/api/v1/shortlist/{item.id}/', **h).json()
    assert r['news'] == []


def test_shortlisted_company_survives_import(setup):
    c, h = login('v@example.com')
    c.get('/api/v1/shortlist/', **h)  # links seed items
    snap = copy.deepcopy(SEED)
    snap['companies'] = [x for x in snap['companies'] if x['id'] != 'fireworks']
    import_payload(snap, source='test')
    assert Company.objects.filter(slug='fireworks').exists()


def test_newer_round_lifts_stale_valuation(setup, monkeypatch):
    item = ShortlistItem.objects.get(name='Baseten')
    engine.link_target(item)
    co = Company.objects.get(slug='baseten')
    newest = max(co.rounds.all(), key=lambda r: r.date)
    assert newest.date > co.valuation_date  # the seed has a newer round than its headline mark
    monkeypatch.setattr(engine, 'ask_claude', lambda *a, **k: ('{"brief": "x"}', {'searches': 0, 'input_tokens': 0, 'output_tokens': 0, 'cost': 0}))
    engine.run_refresh(ResearchJob.objects.create(kind='shortlist', name=item.name, slug=str(item.id)))
    co.refresh_from_db()
    assert co.latest_valuation_usd_bn == newest.post_money_usd_bn and co.valuation_date == newest.date
