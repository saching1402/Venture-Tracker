"""
Shortlist refresh: Claude + web search re-checks one shortlisted company or fund, then

- writes newer valuation / revenue / rounds (companies) or AUM / funds (GPs) back to the tracker,
- logs new, de-duplicated news,
- records a dated mark for the progress log,
- sets Claude's priority (L1-L3) with a rationale, logging any change.

Runs as a ResearchJob of kind "shortlist" (slug = item id) on the shared research worker.
"""
from __future__ import annotations

import datetime as dt
import json
import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.importer.services import _f, _i, _l, _s
from apps.managers.models import Fund
from apps.research.engine import ask_claude, parse_json, recompute
from apps.research.prompts import RULES
from apps.tracking.models import ChangeEvent

from .models import NewsItem, PriorityChange, ShortlistItem, ShortlistMark

LENS = """The reader is an institutional LP (Abu Dhabi family-office style allocator investing in the US and Europe)
who has SHORTLISTED this name to track closely and expects to invest across several rounds (directs,
co-investments, SPVs, secondaries) or, for a manager, across several fund vintages. Be critical, non-promotional
and specific: what changed, what it means for entry price and access, and what could go wrong."""

PRIORITY_RUBRIC = """Set "claude_priority" for this LP:
- "L1": top priority. Strong, improving fundamentals AND a realistic allocation window soon (round, tender,
  co-invest or fund close within ~6-9 months) at a price that can still compound. Track weekly.
- "L2": high quality, monitor monthly. Fundamentals good, but access, timing or valuation is less compelling now.
- "L3": watch list. Thesis still forming, priced for perfection, crowded category, or material risks.
Explain in "priority_rationale" (2-3 sentences) and say what would move it up or down a level."""

COMPANY = """Monitor the company "{name}"{website} for the LP.
{lens}

What the tracker holds today (may be stale):
{known}

Already-logged headlines (do NOT repeat these):
{seen}

Using web search, find what is material since {since}: priced rounds, tenders / secondaries (and secondary-market
pricing), valuation marks, revenue / ARR / run-rate updates, margins and burn, major products, customers and
contracts, leadership changes, regulatory or legal issues, IPO preparation, M&A. Prefer primary sources.

{rubric}

Return JSON:
{{
  "brief": "3-5 sentences: where the company stands now and what changed since the last check",
  "momentum": "up | flat | down",
  "status": "Private | Public (TICKER) | Acquired (by X, YYYY) | Shut down",
  "valuation": {{"latest_valuation_usd_bn": 0.0, "valuation_date": "YYYY-MM", "valuation_label": "HARD|REPORTED|ESTIMATE",
                 "valuation_basis": "Latest round / tender | Secondary | Market cap"}},
  "new_rounds": [{{"date": "YYYY-MM", "round": "Series F / Tender", "post_money_usd_bn": 0.0, "lead": "..."}}],
  "revenue": {{"revenue_metric": "ARR | Revenue | Run-rate revenue", "revenue_usd_bn": 0.0, "revenue_date": "YYYY-MM",
               "revenue_label": "HARD|REPORTED|ESTIMATE", "growth": "...", "profitability": "..."}},
  "performance": "1-2 sentences on revenue, growth, margins / burn",
  "next_round": "1-2 sentences: signals on the next raise, tender or IPO, expected price, and how an LP gets allocation",
  "news": [{{"date": "YYYY-MM-DD", "headline": "...", "summary": "1-2 sentences, why it matters", "category": "{cats}",
             "importance": "high | medium | low", "source": "publication", "url": "https://..."}}],
  "catalysts": [{{"text": "...", "severity": "high|medium|low"}}],
  "risks": [{{"text": "...", "severity": "high|medium|low"}}],
  "claude_priority": "L1 | L2 | L3",
  "priority_rationale": "...",
  "sources": ["https://..."]
}}
Use null for anything you cannot verify. "new_rounds" lists only rounds not already in the tracker. "news" holds up to
12 items, newest first, not already logged."""

FUND = """Monitor the investment manager (GP) "{name}"{website} for the LP.
{lens}

What the tracker holds today (may be stale):
{known}

Already-logged headlines (do NOT repeat these):
{seen}

Using web search, find what is material since {since}: fund launches and closes (incl. SEC Form D filings), target
and hard caps, AUM, fund-level performance disclosed by public pensions (CalPERS, CalSTRS, UTIMCO, Washington State,
Oregon, Florida SBA, etc.), notable portfolio marks, exits and write-downs, partner hires and departures,
succession, strategy drift, regulatory issues.

{rubric}
For a GP, "allocation window" means the next fund close or re-up, or a co-invest programme.

Return JSON:
{{
  "brief": "3-5 sentences: where the firm stands now and what changed since the last check",
  "momentum": "up | flat | down",
  "aum": {{"aum_usd_bn": 0.0, "aum_date": "YYYY-MM", "aum_label": "HARD|REPORTED|ESTIMATE"}},
  "funds": [{{"name": "Fund VI", "size_usd_bn": 0.0, "vintage": 2026, "label": "HARD|REPORTED|ESTIMATE", "status": "Raising | Closed"}}],
  "performance": "2-3 sentences: latest disclosed net IRR / TVPI / DPI by fund, with source and as-of date, or 'Not publicly disclosed'",
  "next_round": "1-2 sentences: next fund, expected size and timing, re-up / co-invest access",
  "news": [{{"date": "YYYY-MM-DD", "headline": "...", "summary": "1-2 sentences, why it matters", "category": "{cats}",
             "importance": "high | medium | low", "source": "publication", "url": "https://..."}}],
  "catalysts": [{{"text": "...", "severity": "high|medium|low"}}],
  "risks": [{{"text": "...", "severity": "high|medium|low"}}],
  "claude_priority": "L1 | L2 | L3",
  "priority_rationale": "...",
  "sources": ["https://..."]
}}
Use null for anything you cannot verify. "news" holds up to 12 items, newest first, not already logged."""


def _company_known(item: ShortlistItem) -> str:
    co = item.company
    if not co:
        return '(not in the tracker yet)'
    rounds = [f'{r.date} {r.round} post ${r.post_money_usd_bn}bn (lead {r.lead or "n/a"})' for r in co.rounds.all()]
    return json.dumps({
        'status': co.status, 'description': co.description, 'sector': co.sector,
        'latest_valuation_usd_bn': co.latest_valuation_usd_bn, 'valuation_date': co.valuation_date,
        'valuation_label': co.valuation_label, 'rounds': rounds[-10:],
        'revenue': {'metric': co.revenue_metric, 'usd_bn': co.revenue_usd_bn, 'date': co.revenue_date},
        'growth': co.growth, 'profitability': co.profitability, 'notes': co.notes,
    }, default=str, indent=1)


def _fund_known(item: ShortlistItem) -> str:
    m = item.manager
    if not m:
        return '(not in the tracker yet)'
    return json.dumps({
        'type': m.type, 'hq': m.hq, 'aum_usd_bn': m.aum_usd_bn, 'aum_date': m.aum_date,
        'funds': [f'{f.name} ${f.size_usd_bn}bn ({f.vintage})' for f in m.funds.all()],
        'performance': m.performance, 'recent_activity': m.recent_activity, 'watch_items': m.watch_items,
    }, default=str, indent=1)


def build_prompt(item: ShortlistItem) -> tuple[str, str]:
    seen = '\n'.join(f'- {n.date} {n.headline}' for n in item.news.all()[:25]) or '(none yet)'
    since = (item.last_refreshed_at.date() - dt.timedelta(days=3)).isoformat() if item.last_refreshed_at else 'the start of 2025'
    target = item.company if item.kind == 'company' else item.manager
    website = f' ({target.website})' if target and target.website else ''
    tpl, known = (COMPANY, _company_known(item)) if item.kind == 'company' else (FUND, _fund_known(item))
    user = tpl.format(name=item.name, website=website, lens=LENS, known=known, seen=seen, since=since,
                      rubric=PRIORITY_RUBRIC, cats=' | '.join(NewsItem.CATEGORIES))
    return RULES.format(today=dt.date.today().isoformat()), user


# ── applying the reply ────────────────────────────────────────────────────────
def _key(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (s or '').lower())[:80]


def _date(v) -> str:
    s = _s(v, 10)
    return s if re.match(r'^\d{4}(-\d{2}){0,2}$', s) else ''


def _points(v) -> list[dict]:
    out = []
    for p in _l(v)[:10]:
        if isinstance(p, dict) and _s(p.get('text')):
            sev = p.get('severity') if p.get('severity') in ('high', 'medium', 'low') else 'medium'
            out.append({'text': _s(p['text'], 600), 'severity': sev})
    return out


def add_news(item: ShortlistItem, news: list) -> int:
    have_urls = set(item.news.exclude(url='').values_list('url', flat=True))
    have_heads = {_key(h) for h in item.news.values_list('headline', flat=True)}
    rows = []
    for n in _l(news)[:15]:
        if not isinstance(n, dict) or not _s(n.get('headline')):
            continue
        url = _s(n.get('url'), 1000)
        url = url if url.startswith('http') else ''
        head = _s(n.get('headline'), 500)
        if (url and url in have_urls) or _key(head) in have_heads:
            continue
        have_urls.add(url)
        have_heads.add(_key(head))
        cat = _s(n.get('category'), 20).lower()
        rows.append(NewsItem(item=item, date=_date(n.get('date')), headline=head, summary=_s(n.get('summary')),
                             category=cat if cat in NewsItem.CATEGORIES else 'other',
                             importance=n.get('importance') if n.get('importance') in ('high', 'medium', 'low') else 'medium',
                             source=_s(n.get('source'), 255), url=url))
    NewsItem.objects.bulk_create(rows)
    return len(rows)


def set_claude_priority(item: ShortlistItem, level, rationale: str) -> bool:
    level = level if level in ('L1', 'L2', 'L3') else ''
    if not level:
        return False
    changed = level != item.claude_priority
    if changed:
        PriorityChange.objects.create(item=item, track='claude', old=item.claude_priority, new=level,
                                      note=rationale[:2000], changed_by='Claude (refresh)')
        item.claude_priority, item.claude_priority_since = level, timezone.now()
    item.claude_rationale = rationale
    return changed


def _apply_company(item: ShortlistItem, data: dict) -> list[str]:
    co = item.company
    notes: list[str] = []
    if not co:
        return notes
    today = timezone.localdate()
    val = data.get('valuation') if isinstance(data.get('valuation'), dict) else {}
    v, vd = _f(val.get('latest_valuation_usd_bn')), _date(val.get('valuation_date'))
    if v and v > 0 and vd and vd >= (co.valuation_date or ''):
        old = co.latest_valuation_usd_bn
        if old and abs(v - old) / old > 0.005:
            ChangeEvent.objects.create(date=today, company=co, company_name=co.name, type='valuation', from_value=old,
                                       to_value=v, detail=f'Shortlist refresh: valuation ${old:g}bn → ${v:g}bn ({(v / old - 1) * 100:+.0f}%)')
            notes.append(f'valuation ${old:g}bn → ${v:g}bn')
        co.latest_valuation_usd_bn, co.valuation_date = v, vd
        co.valuation_label = _s(val.get('valuation_label'), 20) or co.valuation_label
        co.valuation_basis = _s(val.get('valuation_basis'), 64) or co.valuation_basis
        co.valuation_stale = vd[:4] < '2024'
    rev = data.get('revenue') if isinstance(data.get('revenue'), dict) else {}
    r, rd = _f(rev.get('revenue_usd_bn')), _date(rev.get('revenue_date'))
    if r and r > 0 and rd and rd >= (co.revenue_date or ''):
        if co.revenue_usd_bn and abs(r - co.revenue_usd_bn) / co.revenue_usd_bn > 0.005:
            ChangeEvent.objects.create(date=today, company=co, company_name=co.name, type='revenue', from_value=co.revenue_usd_bn,
                                       to_value=r, detail=f'Shortlist refresh: {rev.get("revenue_metric") or "revenue"} ${co.revenue_usd_bn:g}bn → ${r:g}bn')
        co.revenue_usd_bn, co.revenue_date = r, rd
        co.revenue_metric = _s(rev.get('revenue_metric'), 100) or co.revenue_metric
        co.revenue_label = _s(rev.get('revenue_label'), 20) or co.revenue_label
    for fld in ('growth', 'profitability'):
        if _s(rev.get(fld)):
            setattr(co, fld, _s(rev.get(fld)))
    status = _s(data.get('status'), 255)
    if status and status.split(' ')[0] in ('Private', 'Public', 'Acquired', 'Shut') and status != co.status:
        ChangeEvent.objects.create(date=today, company=co, company_name=co.name, type='status',
                                   detail=f'Shortlist refresh: status {co.status or "Private"} → {status}')
        co.status = status
    co.last_verified = today.isoformat()
    co.save()
    existing = {(r.date[:7], _key(r.round)) for r in co.rounds.all()}
    marks = {round(r.post_money_usd_bn, 2) for r in co.rounds.all() if r.post_money_usd_bn}
    added = 0
    for nr in _l(data.get('new_rounds'))[:5]:
        if not isinstance(nr, dict):
            continue
        d, pm = _date(nr.get('date'))[:7], _f(nr.get('post_money_usd_bn'))
        if not d or (d, _key(_s(nr.get('round')))) in existing or (pm and round(pm, 2) in marks):
            continue
        co.rounds.create(date=d, round=_s(nr.get('round'), 255), post_money_usd_bn=pm, lead=_s(nr.get('lead'), 500))
        added += 1
    if added:
        notes.append(f'{added} new round{"s" if added > 1 else ""}')
    # a priced round newer than the headline mark becomes the mark (keeps valuation in step with rounds)
    latest = max((r for r in co.rounds.all() if r.post_money_usd_bn), key=lambda r: r.date or '', default=None)
    if latest and (latest.date or '') > (co.valuation_date or '')[:7]:
        old = co.latest_valuation_usd_bn
        notes.append(f'valuation set to {latest.round} post-money ${latest.post_money_usd_bn:g}bn ({latest.date})')
        if old and abs(latest.post_money_usd_bn - old) / old > 0.005:
            ChangeEvent.objects.create(date=today, company=co, company_name=co.name, type='valuation', from_value=old,
                                       to_value=latest.post_money_usd_bn,
                                       detail=f'Shortlist refresh: valuation ${old:g}bn → ${latest.post_money_usd_bn:g}bn ({latest.round}, {latest.date})')
        co.latest_valuation_usd_bn, co.valuation_date = latest.post_money_usd_bn, latest.date
        co.valuation_basis, co.valuation_stale = 'Latest round / tender', latest.date[:4] < '2024'
        co.save()
    recompute(co)
    ShortlistMark.objects.create(item=item, as_of=today, valuation_usd_bn=co.latest_valuation_usd_bn,
                                 valuation_date=co.valuation_date, revenue_usd_bn=co.revenue_usd_bn,
                                 revenue_metric=co.revenue_metric, revenue_date=co.revenue_date, note='; '.join(notes)[:500])
    return notes


def _apply_fund(item: ShortlistItem, data: dict) -> list[str]:
    m = item.manager
    notes: list[str] = []
    if not m:
        return notes
    aum = data.get('aum') if isinstance(data.get('aum'), dict) else {}
    a, ad = _f(aum.get('aum_usd_bn')), _date(aum.get('aum_date'))
    if a and a > 0 and ad and ad >= (m.aum_date or ''):
        if m.aum_usd_bn and abs(a - m.aum_usd_bn) / m.aum_usd_bn > 0.005:
            notes.append(f'AUM ${m.aum_usd_bn:g}bn → ${a:g}bn')
        m.aum_usd_bn, m.aum_date = a, ad
        m.aum_label = _s(aum.get('aum_label'), 20) or m.aum_label
    have = {_key(f.name) for f in m.funds.all()}
    for f in _l(data.get('funds'))[:8]:
        if isinstance(f, dict) and _s(f.get('name')) and _key(_s(f['name'])) not in have:
            Fund.objects.create(manager=m, name=_s(f['name'], 255), size_usd_bn=_f(f.get('size_usd_bn')),
                                vintage=_i(f.get('vintage')), label=_s(f.get('label'), 20))
            have.add(_key(_s(f['name'])))
            notes.append(f'new fund: {_s(f["name"])}')
    if _s(data.get('performance')) and 'not publicly disclosed' not in _s(data.get('performance')).lower():
        m.performance = _s(data.get('performance'))
    m.last_verified = timezone.localdate().isoformat()
    m.save()
    ShortlistMark.objects.create(item=item, as_of=timezone.localdate(), aum_usd_bn=m.aum_usd_bn, note='; '.join(notes)[:500])
    return notes


def run_refresh(job) -> str:
    """Entry point for the research worker (job.kind == 'shortlist', job.slug == item id)."""
    item = ShortlistItem.objects.select_related('company', 'manager').get(id=int(job.slug))
    link_target(item)
    system, user = build_prompt(item)
    text, usage = ask_claude(system, user, max_searches=8, max_tokens=12000, model=job.model)
    job.searches += usage['searches']
    job.input_tokens += usage['input_tokens']
    job.output_tokens += usage['output_tokens']
    job.cost += usage.get('cost', 0.0)
    job.save(update_fields=['searches', 'input_tokens', 'output_tokens', 'cost'])
    data = parse_json(text)
    with transaction.atomic():
        item = ShortlistItem.objects.select_for_update().get(id=item.id)
        notes = _apply_company(item, data) if item.kind == 'company' else _apply_fund(item, data)
        n_news = add_news(item, data.get('news'))
        moved = set_claude_priority(item, data.get('claude_priority'), _s(data.get('priority_rationale')))
        for fld in ('brief', 'performance', 'next_round'):
            if _s(data.get(fld)):
                setattr(item, fld, _s(data.get(fld)))
        item.momentum = data.get('momentum') if data.get('momentum') in ('up', 'flat', 'down') else item.momentum
        item.catalysts = _points(data.get('catalysts')) or item.catalysts
        item.risks = _points(data.get('risks')) or item.risks
        item.sources = [s for s in (_s(x, 1000) for x in _l(data.get('sources'))) if s.startswith('http')][:20] or item.sources
        item.last_refreshed_at, item.last_error = timezone.now(), ''
        item.save()
    bits = [f'{n_news} new headline{"s" if n_news != 1 else ""}'] + notes
    if moved:
        bits.append(f"Claude's priority now {item.claude_priority}")
    return f'{item.name}: refreshed; ' + ', '.join(bits) + '.'


# ── linking & queueing ────────────────────────────────────────────────────────
def link_target(item: ShortlistItem) -> None:
    """Attach the tracker row when the item was created by name (seed data, or before research finished)."""
    from apps.research.engine import find_company, find_manager
    if item.kind == 'company' and not item.company_id:
        co = find_company(item.name)
        if co and not ShortlistItem.objects.filter(company=co).exists():
            item.company = co
            item.save(update_fields=['company'])
    elif item.kind == 'fund' and not item.manager_id:
        m = find_manager(item.name)
        if m and not ShortlistItem.objects.filter(manager=m).exists():
            item.manager = m
            item.save(update_fields=['manager'])


def queue_refresh(item: ShortlistItem, model: str = '', user=None):
    from apps.research.models import ResearchJob
    if ResearchJob.objects.filter(kind='shortlist', slug=str(item.id), status__in=['queued', 'running']).exists():
        return None
    model = model if model in settings.RESEARCH_MODELS else settings.RESEARCH_COMPANY_MODEL
    job = ResearchJob.objects.create(kind='shortlist', name=item.name, slug=str(item.id), model=model, created_by=user)
    item.research_status = 'queued'
    item.save(update_fields=['research_status'])
    return job


def after_profile(job) -> None:
    """When a company / manager profile finishes researching, refresh shortlist items that are waiting on it."""
    field = 'company__slug' if job.kind == 'company' else 'manager__slug'
    for item in ShortlistItem.objects.filter(**{field: job.slug}, last_refreshed_at__isnull=True):
        queue_refresh(item, user=job.created_by)
