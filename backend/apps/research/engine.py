"""
Auto-research engine.

``run_job`` asks Claude (with the server-side web search tool) for a manager or
company profile in the snapshot schema, then writes it into the database using
the same field cleaning and derivations as the snapshot importer.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.companies.models import Company, Position, ValuationRound
from apps.importer.services import _company_fields, _derive, _f, _i, _l, _manager_fields, _s
from apps.managers.models import Fund, KeyPerson, Manager
from apps.tracking.models import ChangeEvent

from .models import ResearchJob
from .prompts import company_prompt, manager_prompt

log = logging.getLogger('apps.research')


class ResearchError(RuntimeError):
    pass


# ── Claude call ───────────────────────────────────────────────────────────────
def request_cost(model: str, input_tokens: int, output_tokens: int, searches: int) -> float:
    """Price one API request (Haiku is cheaper for prompts up to 100K tokens)."""
    p = settings.RESEARCH_MODELS.get(model, {}).get('price') or (2.0, 10.0, 2.0, 10.0)
    pin, pout = (p[0], p[1]) if input_tokens <= 100_000 else (p[2], p[3])
    return input_tokens * pin / 1e6 + output_tokens * pout / 1e6 + searches * settings.RESEARCH_SEARCH_PRICE


def ask_claude(system: str, user: str, max_searches: int, max_tokens: int = 16000, model: str = '') -> tuple[str, dict]:
    """Run one research conversation with web search; follow pause_turn; return final text + usage."""
    if not settings.ANTHROPIC_API_KEY:
        raise ResearchError('Auto-research is off: set ANTHROPIC_API_KEY in the Railway service variables.')
    import anthropic  # imported lazily so the API works without the package configured

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=3, timeout=600)
    tools = [{'type': 'web_search_20250305', 'name': 'web_search', 'max_uses': max_searches}]
    messages: list[dict[str, Any]] = [{'role': 'user', 'content': user}]
    model = model or settings.RESEARCH_MODEL
    usage = {'input_tokens': 0, 'output_tokens': 0, 'searches': 0, 'cost': 0.0}
    blocks: list[Any] = []
    for _ in range(6):  # initial turn + up to 5 pause_turn continuations
        resp = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                                      messages=messages, tools=tools)
        u = resp.usage
        tin = (u.input_tokens or 0) + (getattr(u, 'cache_read_input_tokens', 0) or 0) + (getattr(u, 'cache_creation_input_tokens', 0) or 0)
        tout = u.output_tokens or 0
        n_search = getattr(getattr(u, 'server_tool_use', None), 'web_search_requests', 0) or 0
        usage['input_tokens'] += tin
        usage['output_tokens'] += tout
        usage['searches'] += n_search
        usage['cost'] += request_cost(model, tin, tout, n_search)
        blocks.extend(resp.content)
        if resp.stop_reason != 'pause_turn':
            if resp.stop_reason == 'max_tokens':
                log.warning('Research reply hit max_tokens; JSON may be truncated')
            break
        # send the paused assistant turn back unchanged so the model continues it
        messages = [messages[0], {'role': 'assistant', 'content': blocks}]
    text = ''.join(b.text for b in blocks if getattr(b, 'type', '') == 'text')
    return text, usage


def parse_json(text: str) -> dict:
    """Take the last ```json block (or the outermost {...}) from the model's reply."""
    blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S)
    raw = blocks[-1] if blocks else text[text.find('{'): text.rfind('}') + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ResearchError(f'Research reply was not valid JSON ({e}).') from e
    if not isinstance(data, dict):
        raise ResearchError('Research reply was not a JSON object.')
    return data


# ── helpers ───────────────────────────────────────────────────────────────────
def norm(name: str) -> str:
    s = re.sub(r'\(.*?\)', '', (name or '').lower())
    s = re.sub(r'\b(inc|corp|corporation|ltd|llc|technologies|labs?|co|ai|the|hq)\b\.?', '', s)
    return re.sub(r'[^a-z0-9]+', '', s)


def unique_slug(model, name: str, max_len: int) -> str:
    base = slugify(name)[: max_len - 4] or 'item'
    slug, n = base, 2
    while model.objects.filter(slug=slug).exists():
        slug, n = f'{base}-{n}', n + 1
    return slug


def find_company(name: str, website: str = '') -> Company | None:
    key = norm(name)
    if not key:
        return None
    hit = Company.objects.filter(slug=slugify(name)).first() or Company.objects.filter(name__iexact=name.strip()).first()
    if hit:
        return hit
    host = re.sub(r'^https?://(www\.)?', '', website or '').split('/')[0].lower()
    for c in Company.objects.only('id', 'name', 'slug', 'website'):
        if norm(c.name) == key or (host and host in (c.website or '').lower()):
            return c
    return None


def find_manager(name: str) -> Manager | None:
    key = norm(name)
    hit = Manager.objects.filter(slug=slugify(name)).first() or Manager.objects.filter(name__iexact=name.strip()).first()
    if hit:
        return hit
    for m in Manager.objects.only('id', 'name', 'slug'):
        if key and norm(m.name) == key:
            return m
    return None


def recompute(company: Company) -> None:
    """Re-derive step-up, val/revenue and every position's entry mark / markup from stored rows."""
    fields = {f: getattr(company, f) for f in ('latest_valuation_usd_bn', 'revenue_usd_bn', 'revenue_metric',
                                               'first_mark_usd_bn', 'first_mark_date')}
    rounds = [{'date': r.date, 'round': r.round, 'post_money_usd_bn': r.post_money_usd_bn}
              for r in company.rounds.all()]
    pos = list(company.positions.all())
    gps = [{'first_invest_year': p.first_invest_year, 'entry_round': p.entry_round, 'entry_post_usd_bn': None}
           for p in pos]
    fields['first_mark_usd_bn'] = None
    _derive(fields, rounds, gps)
    for k in ('first_mark_usd_bn', 'first_mark_date', 'step_up_x', 'ev_rev_x'):
        setattr(company, k, fields[k] if fields.get(k) is not None else ('' if k == 'first_mark_date' else None))
    company.save()
    for p, g in zip(pos, gps):
        p.entry_post_usd_bn, p.markup_x = g['entry_post_usd_bn'], g['markup_x']
        p.save(update_fields=['entry_post_usd_bn', 'markup_x'])


def upsert_position(company: Company, manager: Manager, info: dict, via: str = '') -> bool:
    pos, created = Position.objects.get_or_create(company=company, manager=manager)
    changed = created
    for fld, val in (('first_invest_year', _i(info.get('first_invest_year'))),
                     ('entry_round', _s(info.get('entry_round'), 255)), ('fund', _s(info.get('fund'), 255))):
        if val and not getattr(pos, fld):
            setattr(pos, fld, val)
            changed = True
    if info.get('lead') and not pos.lead:
        pos.lead, changed = True, True
    if created and via:
        pos.via = via
    if changed:
        pos.save()
    return created


# ── manager ───────────────────────────────────────────────────────────────────
def run_manager(job: ResearchJob) -> str:
    limit = job.portfolio_limit or settings.RESEARCH_MAX_PORTFOLIO
    system, user = manager_prompt(job.name, job.website, limit if job.include_portfolio else 0)
    text, usage = ask_claude(system, user, max_searches=16 if job.include_portfolio else 10, model=job.model)
    _record_usage(job, usage)
    data = parse_json(text)
    firm = data.get('firm') if isinstance(data.get('firm'), dict) else data
    firm = dict(firm, id=job.slug)
    firm['name'] = _s(firm.get('name')) or job.name
    firm['last_verified'] = dt.date.today().isoformat()

    with transaction.atomic():
        mgr = Manager.objects.get(slug=job.slug)
        fields = _manager_fields(firm)
        fields['is_stub'] = False
        for k, v in fields.items():
            setattr(mgr, k, v)
        mgr.save()
        if _l(firm.get('recent_funds')):
            mgr.funds.all().delete()
            Fund.objects.bulk_create([Fund(manager=mgr, name=_s(x.get('name'), 255) or 'Fund', size_usd_bn=_f(x.get('size_usd_bn')),
                                           vintage=_i(x.get('vintage')), label=_s(x.get('label'), 20))
                                      for x in _l(firm.get('recent_funds')) if isinstance(x, dict)])
        if _l(firm.get('key_people')):
            mgr.people.all().delete()
            KeyPerson.objects.bulk_create([KeyPerson(manager=mgr, name=_s(p.get('name'), 255), title=_s(p.get('title'), 255),
                                                     focus=_s(p.get('focus')), order=i)
                                           for i, p in enumerate(_l(firm.get('key_people'))) if isinstance(p, dict) and p.get('name')])

    linked = spawned = 0
    if job.include_portfolio:
        for item in _l(data.get('portfolio'))[: limit * 2]:
            if not isinstance(item, dict) or not _s(item.get('name')):
                continue
            name = _s(item['name'], 255)
            existing = find_company(name, _s(item.get('website')))
            if existing:
                if upsert_position(existing, mgr, item, via='auto-research'):
                    linked += 1
                    recompute(existing)
                continue
            if spawned >= limit:
                continue
            co = Company.objects.create(slug=unique_slug(Company, name, 96), name=name, website=_s(item.get('website'), 500),
                                        added_via='user', research_status='queued')
            Position.objects.create(company=co, manager=mgr, first_invest_year=_i(item.get('first_invest_year')),
                                    entry_round=_s(item.get('entry_round'), 255), lead=bool(item.get('lead')))
            pm = job.portfolio_model or settings.RESEARCH_PORTFOLIO_MODEL
            ResearchJob.objects.create(kind='company', name=name, website=co.website, slug=co.slug, parent=job, model=pm,
                                       created_by=job.created_by, position={'manager': mgr.slug})
            spawned += 1
    return (f'{mgr.name}: profile filled; {linked} existing companies linked; {spawned} new companies queued for research.'
            if job.include_portfolio else f'{mgr.name}: profile filled.')


# ── company ───────────────────────────────────────────────────────────────────
def run_company(job: ResearchJob) -> str:
    roster = list(Manager.objects.filter(is_stub=False).values_list('slug', 'name'))
    via = None
    if job.position.get('manager'):
        via = Manager.objects.filter(slug=job.position['manager']).values_list('name', flat=True).first()
    system, user = company_prompt(job.name, job.website, roster, via)
    text, usage = ask_claude(system, user, max_searches=6, max_tokens=12000, model=job.model)
    _record_usage(job, usage)
    data = parse_json(text)
    data['id'] = job.slug
    data['name'] = _s(data.get('name')) or job.name
    data['last_verified'] = dt.date.today().isoformat()

    with transaction.atomic():
        co = Company.objects.get(slug=job.slug)
        fields = _company_fields(data)
        for k in ('legacy', 'valuation_stale', 'first_mark_usd_bn', 'first_mark_date', 'step_up_x', 'ev_rev_x'):
            fields.pop(k, None)
        fields['valuation_stale'] = bool(fields['valuation_date'] and fields['valuation_date'][:4] < '2024')
        for k, v in fields.items():
            setattr(co, k, v)
        co.save()
        rounds = [v for v in _l(data.get('valuation_history')) if isinstance(v, dict)]
        if rounds:
            co.rounds.all().delete()
            ValuationRound.objects.bulk_create([
                ValuationRound(company=co, date=_s(v.get('date'), 20), round=_s(v.get('round'), 255),
                               post_money_usd_bn=_f(v.get('post_money_usd_bn')), lead=_s(v.get('lead'), 500))
                for v in sorted(rounds, key=lambda r: _s(r.get('date')))])
        ids = {m.slug: m for m in Manager.objects.all()}
        linked = 0
        for t in _l(data.get('tracked_investors')):
            if isinstance(t, dict) and _s(t.get('id')) in ids:
                linked += upsert_position(co, ids[_s(t['id'])], t, via='auto-research')
        for inv in fields['other_investors']:
            m = find_manager(_s(inv))
            if m:
                linked += upsert_position(co, m, {}, via='investor list')
        recompute(co)
    return f'{co.name}: profile filled; {co.positions.count()} tracked managers on the cap table.'


def _record_usage(job: ResearchJob, usage: dict) -> None:
    job.searches += usage['searches']
    job.input_tokens += usage['input_tokens']
    job.output_tokens += usage['output_tokens']
    job.cost += usage.get('cost', 0.0)
    job.save(update_fields=['searches', 'input_tokens', 'output_tokens', 'cost'])


# ── job lifecycle ─────────────────────────────────────────────────────────────
def _target(job: ResearchJob):
    if job.kind == 'shortlist':
        from apps.shortlist.models import ShortlistItem
        return ShortlistItem.objects.filter(id=int(job.slug) if job.slug.isdigit() else 0)
    return (Manager if job.kind == 'manager' else Company).objects.filter(slug=job.slug)


def _run(job: ResearchJob) -> str:
    if job.kind == 'shortlist':
        from apps.shortlist.engine import run_refresh
        return run_refresh(job)
    return run_manager(job) if job.kind == 'manager' else run_company(job)


def run_job(job: ResearchJob) -> None:
    _target(job).update(research_status='running')
    try:
        job.summary = _run(job)
        job.status, job.error = 'done', ''
        _target(job).update(research_status='')
        if job.kind == 'shortlist':
            job.finished_at = timezone.now()
            job.save()
            return
        from apps.shortlist.engine import after_profile
        after_profile(job)
        ChangeEvent.objects.create(
            date=timezone.localdate(), type='added' if not job.parent_id else 'new_position',
            company=Company.objects.filter(slug=job.slug).first() if job.kind == 'company' else None,
            company_name=job.name, manager=Manager.objects.filter(slug=job.slug).first() if job.kind == 'manager' else None,
            detail=f'Auto-research: {job.summary}')
    except Exception as e:  # noqa: BLE001 — any failure is recorded on the job for the user to retry
        log.exception('Research job %s failed', job.id)
        msg = str(e)
        if 'authentication_error' in msg or 'invalid x-api-key' in msg:
            msg = 'The ANTHROPIC_API_KEY in Railway was rejected. Check the key, redeploy, then retry.'
        elif 'credit balance' in msg or 'billing' in msg.lower():
            msg = 'The Anthropic account has no credit left. Add credit at console.anthropic.com, then retry.'
        elif 'rate_limit' in msg or 'overloaded' in msg:
            msg = 'The Claude API was busy or rate-limited. Retry in a few minutes.'
        job.status, job.error = 'failed', msg[:2000]
        _target(job).update(research_status='failed')
        if job.kind == 'shortlist':
            _target(job).update(last_error=msg[:2000])
    job.finished_at = timezone.now()
    job.save()


def claim_next() -> ResearchJob | None:
    with transaction.atomic():
        job = (ResearchJob.objects.select_for_update(skip_locked=True)
               .filter(status='queued').order_by('created_at').first())
        if job is None:
            return None
        job.status, job.started_at = 'running', timezone.now()
        job.save(update_fields=['status', 'started_at'])
        return job
