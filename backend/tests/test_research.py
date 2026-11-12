"""Auto-research flow with Claude mocked: add manager → profile + portfolio fan-out; add company → linking."""
import copy
import json
from pathlib import Path
from unittest import mock

import pytest
from django.test import Client, override_settings

from apps.companies.models import Company, Position
from apps.importer.services import import_payload
from apps.managers.models import Manager
from apps.research import engine
from apps.research.models import ResearchJob
from apps.users.models import User

SEED = json.loads((Path(__file__).resolve().parent.parent / 'data' / 'tracker.json').read_text())

FIRM = {'firm': {'name': 'Obvious Ventures', 'website': 'https://obvious.com', 'hq': 'San Francisco, CA', 'founded': 2014,
                 'type': 'Multi-stage VC', 'aum_usd_bn': 1.0, 'aum_label': 'REPORTED', 'overview': 'World-positive VC.',
                 'recent_funds': [{'name': 'Fund IV', 'size_usd_bn': 0.36, 'vintage': 2022, 'label': 'HARD'}],
                 'stages': ['Seed', 'Series A'], 'focus_areas': ['Climate / energy'],
                 'key_people': [{'name': 'Vishal Vasishth', 'title': 'Co-founder'}], 'sources': ['https://obvious.com']},
        'portfolio': [{'name': 'Anthropic', 'first_invest_year': 2023, 'entry_round': 'Series C'},
                      {'name': 'Brand New Robotics Co', 'website': 'https://bnr.example', 'first_invest_year': 2025,
                       'entry_round': 'Seed', 'lead': True}]}
CO = {'name': 'Brand New Robotics Co', 'sector': 'Deep tech', 'focus_tags': ['Robotics'], 'status': 'Private',
      'latest_valuation_usd_bn': 0.5, 'valuation_date': '2026-06', 'valuation_label': 'REPORTED',
      'valuation_history': [{'date': '2025-02', 'round': 'Seed', 'post_money_usd_bn': 0.05, 'lead': 'Obvious Ventures'},
                            {'date': '2026-06', 'round': 'Series A', 'post_money_usd_bn': 0.5, 'lead': 'Lux Capital'}],
      'other_investors': ['Obvious Ventures', 'Lux Capital'],
      'tracked_investors': [{'id': 'lux', 'first_invest_year': 2026, 'entry_round': 'Series A', 'lead': True}]}


CALLS = []


def fake_claude(system, user, max_searches, max_tokens=16000, model=''):
    CALLS.append(model)
    data = FIRM if 'investment manager' in user else CO
    cost = engine.request_cost(model, 1000, 500, 3)
    return f'Here you go.\n```json\n{json.dumps(data)}\n```', {'input_tokens': 1000, 'output_tokens': 500, 'searches': 3, 'cost': cost}


@pytest.fixture
def setup(db):
    import_payload(copy.deepcopy(SEED), source='test')
    User.objects.create_user('a@example.com', 'a-long-test-password', role='analyst')
    User.objects.create_user('v@example.com', 'a-long-test-password', role='viewer')


def login(email):
    c = Client()
    tok = c.post('/api/v1/auth/token/', {'email': email, 'password': 'a-long-test-password'},
                 content_type='application/json').json()['access']
    return c, {'HTTP_AUTHORIZATION': f'Bearer {tok}'}


@override_settings(ANTHROPIC_API_KEY='')
def test_research_off_without_key(setup):
    c, h = login('a@example.com')
    r = c.post('/api/v1/research/', {'kind': 'manager', 'name': 'Obvious Ventures'}, content_type='application/json', **h)
    assert r.status_code == 503


@override_settings(ANTHROPIC_API_KEY='sk-test')
def test_viewer_cannot_add(setup):
    c, h = login('v@example.com')
    r = c.post('/api/v1/research/', {'kind': 'manager', 'name': 'Obvious Ventures'}, content_type='application/json', **h)
    assert r.status_code == 403


@override_settings(ANTHROPIC_API_KEY='sk-test', RESEARCH_MAX_PORTFOLIO=5)
def test_add_manager_researches_profile_and_portfolio(setup):
    c, h = login('a@example.com')
    r = c.post('/api/v1/research/', {'kind': 'manager', 'name': 'Obvious Ventures'}, content_type='application/json', **h)
    assert r.status_code == 202
    slug = r.json()['id']
    assert Manager.objects.get(slug=slug).research_status == 'queued'
    dup = c.post('/api/v1/research/', {'kind': 'manager', 'name': 'obvious ventures'}, content_type='application/json', **h)
    assert dup.status_code == 409

    with mock.patch.object(engine, 'ask_claude', side_effect=fake_claude):
        while (job := engine.claim_next()):
            engine.run_job(job)

    m = Manager.objects.get(slug=slug)
    assert m.research_status == '' and m.aum_usd_bn == 1.0 and m.funds.count() == 1 and not m.is_stub
    assert Position.objects.filter(manager=m, company__slug='anthropic').exists()  # existing company linked
    new = Company.objects.get(name='Brand New Robotics Co')
    assert new.latest_valuation_usd_bn == 0.5 and new.step_up_x == 10.0 and new.added_via == 'user'
    assert set(new.positions.values_list('manager__slug', flat=True)) >= {slug, 'lux'}
    pos = new.positions.get(manager=m)
    assert pos.entry_post_usd_bn == 0.05 and pos.markup_x == 10.0
    assert ResearchJob.objects.filter(status='done').count() == 2

    listing = c.get('/api/v1/research/', **h).json()
    assert listing['jobs'][0]['children_total'] == 1 and listing['jobs'][0]['children_done'] == 1

    # a later weekly snapshot without these rows must not delete user-added entries
    import_payload(copy.deepcopy(SEED) | {'asof': '2030-01-01'}, source='test')
    assert Company.objects.filter(name='Brand New Robotics Co').exists() and Manager.objects.filter(slug=slug).exists()


@override_settings(ANTHROPIC_API_KEY='sk-test')
def test_failed_job_can_retry(setup):
    c, h = login('a@example.com')
    r = c.post('/api/v1/research/', {'kind': 'company', 'name': 'Brand New Robotics Co'}, content_type='application/json', **h)
    job_id = r.json()['job']['id']
    with mock.patch.object(engine, 'ask_claude', side_effect=engine.ResearchError('boom')):
        engine.run_job(engine.claim_next())
    assert Company.objects.get(slug=r.json()['id']).research_status == 'failed'
    assert c.post(f'/api/v1/research/{job_id}/retry/', **h).json()['retried'] == 1
    with mock.patch.object(engine, 'ask_claude', side_effect=fake_claude):
        engine.run_job(engine.claim_next())
    co = Company.objects.get(slug=r.json()['id'])
    assert co.research_status == '' and co.positions.filter(manager__slug='lux').exists()


def test_parse_json_takes_last_block():
    assert engine.parse_json('a ```json\n{"x":1}\n``` b ```json\n{"x":2}\n```') == {'x': 2}


@override_settings(ANTHROPIC_API_KEY='sk-test')
def test_model_choice_and_costing(setup):
    c, h = login('a@example.com')
    menu = c.get('/api/v1/research/', **h).json()
    ids = [m['id'] for m in menu['models']]
    assert {'claude-haiku-5-5', 'claude-sonnet-5-5', 'claude-opus-5-5'} <= set(ids)
    haiku = next(m for m in menu['models'] if m['id'] == 'claude-haiku-5-5')
    sonnet = next(m for m in menu['models'] if m['id'] == 'claude-sonnet-5-5')
    assert haiku['est_company'] < sonnet['est_company']
    r = c.post('/api/v1/research/', {'kind': 'manager', 'name': 'Obvious Ventures', 'model': 'claude-opus-5-5',
                                     'portfolio_model': 'claude-haiku-5-5', 'portfolio_limit': 'abc'},
               content_type='application/json', **h)
    assert r.status_code == 202 and r.json()['job']['model'] == 'claude-opus-5-5'
    bad = c.post('/api/v1/research/', {'kind': 'company', 'name': 'X Corp', 'model': 'gpt-4'}, content_type='application/json', **h)
    assert bad.json()['job']['model'] == 'claude-sonnet-5-5'   # unknown model ids fall back to the default
    CALLS.clear()
    with mock.patch.object(engine, 'ask_claude', side_effect=fake_claude):
        while (job := engine.claim_next()):
            engine.run_job(job)
    assert CALLS[0] == 'claude-opus-5-5' and 'claude-haiku-5-5' in CALLS
    child = ResearchJob.objects.get(parent__isnull=False)
    assert child.model == 'claude-haiku-5-5' and child.cost == pytest.approx(0.0001 + 0.00025 + 0.03)
    top = next(j for j in c.get('/api/v1/research/', **h).json()['jobs'] if j['kind'] == 'manager')
    assert top['cost_usd'] == pytest.approx(round(engine.request_cost('claude-opus-5-5', 1000, 500, 3) + child.cost, 3))


def test_haiku_long_prompt_tier():
    from apps.research.engine import request_cost
    assert request_cost('claude-haiku-5-5', 100_000, 0, 0) == pytest.approx(0.01)
    assert request_cost('claude-haiku-5-5', 200_000, 0, 0) == pytest.approx(0.10)


# ── business profiles ─────────────────────────────────────────────────────────
def _profile_reply(kind):
    if kind == 'co':
        return {'summary': 'Makes widgets.', 'products': [{'name': 'Widget', 'description': 'A widget'}],
                'financials': {'revenue_metric': 'ARR', 'revenue_usd_bn': 0.12, 'revenue_date': '2026-09', 'label': 'REPORTED',
                               'gross_margin': '70%'},
                'value_chain': {'chain': [{'layer': 'Chips', 'current': True}, {'layer': 'Apps', 'current': True}], 'position': 'Mid'},
                'competition': [{'name': 'Rival', 'note': 'bigger'}], 'industry': {'market': '$10bn', 'trends': ['AI']},
                'risks': ['Competition'], 'sources': ['https://example.com', 'not a url']}
    return {'summary': 'A GP.', 'strategy': {'stages': 'Seed-A'}, 'peers': [{'name': 'Other GP'}], 'current_themes': ['AI']}


def test_profiles_bulk_and_run(db, monkeypatch, settings):
    import json as _json
    from django.test import Client
    from apps.companies.models import Company
    from apps.managers.models import Manager
    from apps.research import engine, profiles
    from apps.research.models import ResearchJob
    from apps.users.models import User
    settings.ANTHROPIC_API_KEY = 'test'
    Company.objects.create(slug='widgetco', name='WidgetCo', latest_valuation_usd_bn=2.0)
    Company.objects.create(slug='oldco', name='OldCo', legacy=True)
    Manager.objects.create(slug='gp1', name='GP One', aum_usd_bn=5)
    User.objects.create_user('a@example.com', 'a-long-test-password', role='analyst')
    c = Client()
    tok = c.post('/api/v1/auth/token/', {'email': 'a@example.com', 'password': 'a-long-test-password'},
                 content_type='application/json').json()['access']
    h = {'HTTP_AUTHORIZATION': f'Bearer {tok}'}
    st = c.get('/api/v1/research/profiles/', **h).json()
    assert st['companies'] == {'total': 1, 'with_profile': 0, 'queued': 0} and st['models'][0]['est_profile'] > 0
    r = c.post('/api/v1/research/profiles/', {'kind': 'both', 'scope': 'missing'}, content_type='application/json', **h).json()
    assert r['queued'] == 2 and r['estimated_cost'] > 0
    assert Company.objects.get(slug='widgetco').profile_status == 'queued'
    assert Company.objects.get(slug='widgetco').research_status == ''  # tables are not flagged
    # a user-initiated job jumps ahead of bulk profiles
    ResearchJob.objects.create(kind='company', name='Urgent', slug='widgetco')
    assert engine.claim_next().name == 'Urgent'
    replies = iter([('```json\n' + _json.dumps(_profile_reply('gp')) + '\n```', {'searches': 1, 'input_tokens': 1, 'output_tokens': 1, 'cost': 0.05}),
                    ('```json\n' + _json.dumps(_profile_reply('co')) + '\n```', {'searches': 1, 'input_tokens': 1, 'output_tokens': 1, 'cost': 0.05})])
    monkeypatch.setattr(profiles, 'ask_claude', lambda *a, **k: next(replies))
    for _ in range(2):
        engine.run_job(engine.claim_next())
    co = Company.objects.get(slug='widgetco')
    assert co.profile_status == '' and co.profile['summary'] == 'Makes widgets.'
    assert [x['current'] for x in co.profile['value_chain']['chain']] == [True, False]   # exactly one highlighted
    assert co.profile['sources'] == ['https://example.com']
    assert co.revenue_usd_bn == 0.12 and co.revenue_metric == 'ARR'                     # gap filled from the profile
    assert Manager.objects.get(slug='gp1').profile['peers'][0]['name'] == 'Other GP'
    detail = c.get('/api/v1/companies/widgetco/', **h).json()
    assert detail['profile']['financials']['gross_margin'] == '70%'
    # cancel
    c.post('/api/v1/research/profiles/', {'kind': 'company', 'ids': ['widgetco']}, content_type='application/json', **h)
    assert c.delete('/api/v1/research/profiles/', **h).json()['cancelled'] == 1
    assert Company.objects.get(slug='widgetco').profile_status == ''
