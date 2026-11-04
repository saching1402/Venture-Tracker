"""Track record: XIRR, gross/net metrics, CRUD + permissions, fund commitments, commentary, PDF."""
import copy
import datetime as dt
import json
from pathlib import Path

import pytest
from django.test import Client

from apps.importer.services import import_payload
from apps.trackrecord.metrics import xirr
from apps.users.models import User

SEED = json.loads((Path(__file__).resolve().parent.parent / 'data' / 'tracker.json').read_text())


def test_xirr_known_values():
    assert xirr([(dt.date(2020, 1, 1), -100), (dt.date(2022, 1, 1), 121)]) == pytest.approx(0.10, abs=1e-3)
    assert xirr([(dt.date(2020, 1, 1), -100), (dt.date(2021, 1, 1), 50)]) == pytest.approx(-0.5, abs=1e-3)
    assert xirr([(dt.date(2020, 1, 1), -100)]) is None


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


DIRECT = {
    'name': 'Anthropic', 'company_id': 'anthropic', 'structure': 'spv', 'vehicle': 'AI Co-Invest SPV I', 'round': 'Series E',
    'invest_date': '2023-03-01', 'invested_usd_m': 10, 'entry_valuation_usd_bn': 61.5,
    'current_value_usd_m': 30, 'value_date': '2026-03-01', 'value_basis': 'Last round',
    'mgmt_fee_pct': 2, 'carry_pct': 20, 'capacity_usd_m': 5, 'lead_investors': 'Lightspeed, ICONIQ',
    'co_investors': ['Menlo Ventures'], 'pros': ['Revenue growth', {'text': 'Top team', 'severity': 'high'}],
    'risks': [{'text': 'Compute costs', 'severity': 'high'}], 'thesis': 'Frontier lab with enterprise traction.',
    'cashflows': [{'date': '2024-03-01', 'amount_usd_m': -5, 'note': 'Follow-on'},
                  {'date': '2025-09-01', 'amount_usd_m': 6, 'note': 'Tender'}],
}
FUND = {
    'name': 'Lux Ventures VIII', 'manager_id': 'lux', 'structure': 'l1', 'vehicle': 'Lux Ventures VIII', 'vintage': 2022,
    'invest_date': '2022-06-01', 'commitment_usd_m': 25, 'invested_usd_m': 15, 'current_value_usd_m': 21,
    'realised_usd_m': 2, 'value_date': '2026-06-30', 'net_moic_reported': 1.48, 'net_irr_reported': 14.5, 'dpi_reported': 0.12,
}


def test_crud_metrics_and_permissions(setup):
    c, h = login('a@example.com')
    r = c.post('/api/v1/track-record/investments/', DIRECT, content_type='application/json', **h)
    assert r.status_code == 201, r.content
    m = r.json()['metrics']
    assert m['invested_usd_m'] == 15 and m['realised_usd_m'] == 6 and m['current_usd_m'] == 30
    assert m['gross_moic'] == pytest.approx(36 / 15, abs=1e-3) and m['dpi'] == pytest.approx(0.4)
    assert 0 < m['net_moic'] < m['gross_moic'] and m['net_basis'] == 'estimate'
    assert m['gross_irr'] > m['net_irr'] > 0
    assert m['ownership_pct'] == pytest.approx(10 / 61500 * 100, rel=1e-3)
    assert m['implied_markup_x'] and m['suggested_value_usd_m']
    assert r.json()['pros'][0] == {'text': 'Revenue growth', 'severity': 'medium'}
    assert r.json()['lead_investors'] == ['Lightspeed', 'ICONIQ']

    f = c.post('/api/v1/track-record/investments/', FUND, content_type='application/json', **h).json()
    assert f['is_fund'] and f['manager_name'].startswith('Lux')
    assert f['metrics']['net_moic'] == 1.48 and f['metrics']['net_irr'] == pytest.approx(0.145) and f['metrics']['unfunded_usd_m'] == 10
    assert f['metrics']['net_basis'] == 'reported'

    lst = c.get('/api/v1/track-record/investments/', **h).json()
    assert lst['summary']['count'] == 2 and lst['summary_funds']['count'] == 1 and lst['can_edit']
    assert lst['summary']['capacity_usd_m'] == 5

    inv_id = r.json()['id']
    assert c.post(f'/api/v1/track-record/investments/{inv_id}/comments/', {'text': 'Discussed at IC'},
                  content_type='application/json', **h).status_code == 201
    bad = c.post('/api/v1/track-record/investments/', dict(DIRECT, carry_pct=150), content_type='application/json', **h)
    assert bad.status_code == 400

    vc, vh = login('v@example.com')
    assert vc.get('/api/v1/track-record/investments/', **vh).status_code == 200
    assert vc.post('/api/v1/track-record/investments/', DIRECT, content_type='application/json', **vh).status_code == 403

    pdf = c.get('/api/v1/track-record/pdf/?commentary=1', **h)
    assert pdf.status_code == 200 and pdf['Content-Type'] == 'application/pdf' and pdf.content[:4] == b'%PDF'

    pre = c.get('/api/v1/track-record/prefill/?company=anthropic', **h).json()
    assert pre['name'] == 'Anthropic' and pre['rounds']

    # a later snapshot without Anthropic must keep it because it is in the track record
    snap = copy.deepcopy(SEED)
    snap['companies'] = [x for x in snap['companies'] if x['id'] != 'anthropic']
    import_payload(snap | {'asof': '2030-01-01'}, source='test', force=True)
    assert c.get(f'/api/v1/track-record/investments/{inv_id}/', **h).json()['company_id'] == 'anthropic'


def test_manager_assessment(setup):
    c, h = login('a@example.com')
    r = c.put('/api/v1/track-record/managers/lux/assessment/',
              {'view': 'Core deep-tech relationship.', 'pros': ['Science network'], 'cons': [{'text': 'Concentration', 'severity': 'high'}]},
              content_type='application/json', **h)
    assert r.status_code == 200 and r.json()['cons'][0]['severity'] == 'high' and r.json()['updated_by'] == 'Sachin'
    r = c.post('/api/v1/track-record/managers/lux/comments/', {'text': 'Met the GP in Abu Dhabi'}, content_type='application/json', **h)
    assert r.status_code == 201 and r.json()['comments'][0]['text'].startswith('Met')
    cid = r.json()['comments'][0]['id']
    vc, vh = login('v@example.com')
    assert vc.get('/api/v1/track-record/managers/lux/assessment/', **vh).json()['view'].startswith('Core')
    assert vc.delete(f'/api/v1/track-record/manager-comments/{cid}/', **vh).status_code == 403
    assert c.delete(f'/api/v1/track-record/manager-comments/{cid}/', **h).status_code == 204


def test_fund_programme_sheet(setup):
    c, h = login('a@example.com')
    c.post('/api/v1/track-record/investments/', DIRECT, content_type='application/json', **h)
    c.post('/api/v1/track-record/investments/', FUND, content_type='application/json', **h)
    c.post('/api/v1/track-record/investments/', dict(FUND, name='DCVC VII', manager_id='dcvc', vehicle='DCVC Fund VII', vintage=2023,
                                                    invest_date='2023-06-01', commitment_usd_m=20, invested_usd_m=9,
                                                    current_value_usd_m=10.4, realised_usd_m=0, net_moic_reported=None,
                                                    net_irr_reported=None, dpi_reported=None),
           content_type='application/json', **h)
    fp = c.get('/api/v1/track-record/investments/', **h).json()['fund_programme']
    assert fp['count'] == 2 and fp['gps'] == 2 and fp['commitment_usd_m'] == 45 and fp['called_usd_m'] == 24
    assert fp['tvpi'] == pytest.approx((2 + 21 + 10.4) / 24, abs=1e-3) and fp['pct_called'] == pytest.approx(24 / 45, abs=1e-4)
    assert [b['vintage'] for b in fp['by_vintage']] == [2022, 2023]
    assert fp['by_vintage'][0]['net_irr'] == pytest.approx(0.145)  # single fund: equals its GP-reported IRR
    for kind, name in (('funds', 'fund-programme'), ('direct', 'direct-investments'), ('all', 'track-record')):
        r = c.get(f'/api/v1/track-record/pdf/?kind={kind}&commentary=1', **h)
        assert r.status_code == 200 and r.content[:4] == b'%PDF' and name in r['Content-Disposition']


def test_view_filters(setup):
    c, h = login('a@example.com')
    c.post('/api/v1/track-record/investments/', DIRECT, content_type='application/json', **h)
    c.post('/api/v1/track-record/investments/', FUND, content_type='application/json', **h)
    base = '/api/v1/track-record/investments/'
    allv = c.get(base, **h).json()
    assert allv['summary']['count'] == 2 and allv['facets'] == allv['facets'] | {'total': 2, 'direct': 1, 'funds': 1}
    funds = c.get(base + '?view=funds', **h).json()
    assert [i['name'] for i in funds['investments']] == ['Lux Ventures VIII'] and funds['summary']['count'] == 1
    direct = c.get(base + '?view=direct', **h).json()
    assert [i['name'] for i in direct['investments']] == ['Anthropic'] and direct['facets']['total'] == 2
    assert c.get(base + '?structure=l1,spv', **h).json()['summary']['count'] == 2
    assert c.get(base + '?q=menlo', **h).json()['summary']['count'] == 1           # matches co-investor
    assert c.get(base + '?status=realised', **h).json()['summary']['count'] == 0
    r = c.get('/api/v1/track-record/pdf/?view=funds&q=lux', **h)
    assert r.status_code == 200 and 'fund-programme' in r['Content-Disposition']
