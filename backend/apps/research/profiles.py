"""
Profile research: a structured, sourced business profile for a company or a manager (GP), shown in the detail drawers.

Jobs: ResearchJob(kind='coprofile' | 'gpprofile', slug=<company / manager slug>) on the shared research worker.
Progress is tracked in `profile_status` (not `research_status`) so the tables do not show "being researched" badges.
"""
from __future__ import annotations

import datetime as dt
import json

from django.utils import timezone

from apps.companies.models import Company
from apps.importer.services import _f, _l, _s
from apps.managers.models import Manager

from .engine import ask_claude, parse_json, recompute
from .prompts import RULES

LABELS = ('HARD', 'REPORTED', 'ESTIMATE')

COMPANY = """Write a concise, factual business profile of the company "{name}"{website} for an institutional investor.
Not an IC memo: clear, specific, reasonably detailed but not excessive. Each text field 1-3 sentences unless stated.

What the tracker holds (may be stale or incomplete):
{known}

Use web search (company site, filings, credible press, industry reports). Return JSON:
{{
  "summary": "2-3 sentences: what the company is and why it matters",
  "products": [{{"name": "product / product line", "description": "what it is and who uses it"}}],
  "customers": "who buys it (segments, size, notable named customers where public)",
  "business_model": "how it makes money: pricing, contract type, usage vs seat, hardware vs software mix",
  "financials": {{
    "revenue_metric": "ARR | Revenue | Run-rate revenue | Bookings", "revenue_usd_bn": 0.0, "revenue_date": "YYYY-MM",
    "growth": "e.g. ~3x YoY", "gross_margin": "e.g. ~60% (or null)", "profitability": "operating margin / burn / profitable",
    "headcount": 0, "label": "HARD | REPORTED | ESTIMATE", "note": "1 sentence context, e.g. revenue mix or guidance"
  }},
  "value_chain": {{
    "chain": [{{"layer": "short layer name, upstream first", "examples": "2-3 example companies in that layer", "current": false}}],
    "position": "1-2 sentences: where the company sits, what it depends on upstream and who it sells into downstream"
  }},
  "competition": [{{"name": "competitor", "note": "how it compares (scale, approach, pricing)"}}],
  "competitive_position": "1-2 sentences: leader / challenger / niche and why",
  "moat": "what is defensible (data, distribution, switching costs, IP, scale) and what is not",
  "industry": {{"market": "market size and growth with source and year, or a qualitative description",
                "trends": ["3-5 industry trends that matter for this company"]}},
  "risks": ["3-4 key business risks"],
  "sources": ["https://..."]
}}
The value chain must have 3-6 layers ordered from upstream (inputs) to downstream (end customers), with exactly one
layer marked "current": true. List 3-6 competitors. Use null for any figure you cannot verify; do not guess margins."""

MANAGER = """Write a concise, factual profile of the venture / growth investment manager (GP) "{name}"{website} for an
institutional LP. Not an IC memo: clear, specific, reasonably detailed but not excessive.

What the tracker holds (may be stale or incomplete):
{known}

Use web search (the firm's site, SEC Form D / ADV, LP disclosures such as CalPERS / UTIMCO / Washington State,
credible press). Return JSON:
{{
  "summary": "2-3 sentences: who they are and what they are known for",
  "strategy": {{"stages": "e.g. Seed to Series B", "check_size": "e.g. $5-25m initial", "sectors": "focus sectors",
                "geography": "where they invest", "style": "lead vs follow, board seats, ownership targets, concentration"}},
  "funds": "1-3 sentences: current fund family and sizes, latest vintage, fundraising status",
  "team": "key partners and decision-makers, recent hires / departures, succession",
  "track_record": "notable wins and exits, and any disclosed fund performance (net IRR / TVPI / DPI with source and as-of date)",
  "differentiation": "what makes them different from peers (sourcing, platform, thesis, brand)",
  "platform": "value-add for founders (talent, GTM, government / defense, scientific network, etc.)",
  "peers": [{{"name": "peer firm", "note": "how it compares"}}],
  "current_themes": ["3-5 themes they are actively investing behind now"],
  "lp_considerations": ["3-4 points an LP should weigh: access, fees / carry if known, concentration, key-person, style drift"],
  "sources": ["https://..."]
}}
List 3-5 peers. Use null when you cannot verify; never invent performance figures."""


def _known_company(c: Company) -> str:
    return json.dumps({
        'name': c.name, 'website': c.website, 'hq': c.hq, 'founded': c.founded, 'sector': c.sector, 'status': c.status,
        'description': c.description, 'valuation_usd_bn': c.latest_valuation_usd_bn, 'valuation_date': c.valuation_date,
        'revenue': {'metric': c.revenue_metric, 'usd_bn': c.revenue_usd_bn, 'date': c.revenue_date, 'label': c.revenue_label},
        'growth': c.growth, 'profitability': c.profitability, 'employees': c.employees, 'ceo': c.ceo,
        'investors': (c.other_investors or [])[:12], 'notes': c.notes,
    }, default=str)


def _known_manager(m: Manager) -> str:
    return json.dumps({
        'name': m.name, 'website': m.website, 'hq': m.hq, 'founded': m.founded, 'type': m.type,
        'aum_usd_bn': m.aum_usd_bn, 'aum_date': m.aum_date, 'overview': m.overview, 'stages': m.stages,
        'focus_areas': m.focus_areas, 'performance': m.performance,
        'funds': [f'{f.name} ${f.size_usd_bn}bn ({f.vintage})' for f in m.funds.all()][:8],
        'people': [f'{p.name} ({p.title})' for p in m.people.all()][:10],
    }, default=str)


def _txt(v, n: int = 900) -> str:
    return _s(v, n) if isinstance(v, (str, int, float)) else ''


def _strs(v, n: int = 8, ln: int = 300) -> list[str]:
    return [_s(x, ln) for x in _l(v)[:n] if isinstance(x, str) and _s(x)]


def _named(v, n: int = 8) -> list[dict]:
    return [{'name': _s(x.get('name'), 120), 'note': _s(x.get('note') or x.get('description'), 400)}
            for x in _l(v)[:n] if isinstance(x, dict) and _s(x.get('name'))]


def _urls(v) -> list[str]:
    return [u for u in (_s(x, 1000) for x in _l(v)[:15]) if u.startswith('http')]


def clean_company(d: dict) -> dict:
    fin = d.get('financials') if isinstance(d.get('financials'), dict) else {}
    vc = d.get('value_chain') if isinstance(d.get('value_chain'), dict) else {}
    chain = [{'layer': _s(x.get('layer'), 80), 'examples': _s(x.get('examples'), 200), 'current': bool(x.get('current'))}
             for x in _l(vc.get('chain'))[:7] if isinstance(x, dict) and _s(x.get('layer'))]
    if chain and sum(x['current'] for x in chain) != 1:  # keep exactly one highlighted layer
        first = next((i for i, x in enumerate(chain) if x['current']), None)
        for i, x in enumerate(chain):
            x['current'] = i == first
    ind = d.get('industry') if isinstance(d.get('industry'), dict) else {}
    label = _s(fin.get('label'), 12).upper()
    return {
        'summary': _txt(d.get('summary'), 1200),
        'products': [{'name': _s(x.get('name'), 120), 'description': _s(x.get('description'), 400)}
                     for x in _l(d.get('products'))[:8] if isinstance(x, dict) and _s(x.get('name'))],
        'customers': _txt(d.get('customers')), 'business_model': _txt(d.get('business_model')),
        'financials': {
            'revenue_metric': _s(fin.get('revenue_metric'), 60), 'revenue_usd_bn': _f(fin.get('revenue_usd_bn')),
            'revenue_date': _s(fin.get('revenue_date'), 10), 'growth': _txt(fin.get('growth'), 200),
            'gross_margin': _txt(fin.get('gross_margin'), 200), 'profitability': _txt(fin.get('profitability'), 300),
            'headcount': _f(fin.get('headcount')), 'label': label if label in LABELS else '', 'note': _txt(fin.get('note'), 400),
        },
        'value_chain': {'chain': chain, 'position': _txt(vc.get('position'))},
        'competition': _named(d.get('competition')), 'competitive_position': _txt(d.get('competitive_position')),
        'moat': _txt(d.get('moat')),
        'industry': {'market': _txt(ind.get('market')), 'trends': _strs(ind.get('trends'), 6)},
        'risks': _strs(d.get('risks'), 6), 'sources': _urls(d.get('sources')),
    }


def clean_manager(d: dict) -> dict:
    st = d.get('strategy') if isinstance(d.get('strategy'), dict) else {}
    return {
        'summary': _txt(d.get('summary'), 1200),
        'strategy': {k: _txt(st.get(k), 300) for k in ('stages', 'check_size', 'sectors', 'geography', 'style')},
        'funds': _txt(d.get('funds')), 'team': _txt(d.get('team')), 'track_record': _txt(d.get('track_record'), 1200),
        'differentiation': _txt(d.get('differentiation')), 'platform': _txt(d.get('platform')),
        'peers': _named(d.get('peers'), 6), 'current_themes': _strs(d.get('current_themes'), 6),
        'lp_considerations': _strs(d.get('lp_considerations'), 6), 'sources': _urls(d.get('sources')),
    }


def run_profile(job) -> str:
    today = dt.date.today().isoformat()
    if job.kind == 'coprofile':
        obj = Company.objects.get(slug=job.slug)
        prompt = COMPANY.format(name=obj.name, website=f' ({obj.website})' if obj.website else '', known=_known_company(obj))
    else:
        obj = Manager.objects.prefetch_related('funds', 'people').get(slug=job.slug)
        prompt = MANAGER.format(name=obj.name, website=f' ({obj.website})' if obj.website else '', known=_known_manager(obj))
    text, usage = ask_claude(RULES.format(today=today), prompt, max_searches=5, max_tokens=8000, model=job.model)
    job.searches += usage['searches']
    job.input_tokens += usage['input_tokens']
    job.output_tokens += usage['output_tokens']
    job.cost += usage.get('cost', 0.0)
    job.save(update_fields=['searches', 'input_tokens', 'output_tokens', 'cost'])
    data = parse_json(text)
    prof = clean_company(data) if job.kind == 'coprofile' else clean_manager(data)
    if not prof['summary']:
        raise ValueError('The reply had no usable profile; retry, or try a larger model.')
    prof.update(as_of=today, model=job.model)
    obj.profile, obj.profile_updated_at = prof, timezone.now()
    fields = ['profile', 'profile_updated_at']
    filled = []
    if job.kind == 'coprofile':
        fin = prof['financials']
        # fill gaps in the tracker's headline figures; never overwrite a newer existing mark
        if fin['revenue_usd_bn'] and fin['revenue_date'] and fin['revenue_date'] >= (obj.revenue_date or '') and not obj.revenue_usd_bn:
            obj.revenue_usd_bn, obj.revenue_date = fin['revenue_usd_bn'], fin['revenue_date']
            obj.revenue_metric, obj.revenue_label = fin['revenue_metric'] or 'Revenue', fin['label'] or 'ESTIMATE'
            fields += ['revenue_usd_bn', 'revenue_date', 'revenue_metric', 'revenue_label']
            filled.append('revenue')
        if not obj.description:
            obj.description = prof['summary'][:1000]
            fields.append('description')
            filled.append('description')
    obj.save(update_fields=fields)
    if 'revenue' in filled:
        recompute(obj)
    extra = f' (also filled {", ".join(filled)})' if filled else ''
    return f'{obj.name}: profile written{extra}.'
