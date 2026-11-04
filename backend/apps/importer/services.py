"""
Snapshot import / export.

The weekly refresh job produces a ``tracker.json`` snapshot (same format the
original HTML tracker used). ``import_payload`` upserts it into PostgreSQL,
records what moved since the previous snapshot as ChangeEvents, and logs a
Snapshot row. ``export_payload`` rebuilds the same format from the database so
the next refresh can start from what is live.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Any

from django.db import transaction

from apps.companies.models import Company, Position, ValuationRound
from apps.managers.models import Fund, KeyPerson, Manager
from apps.tracking.models import ChangeEvent, Snapshot

log = logging.getLogger('apps.importer')

MANAGER_TEXT = ['name', 'website', 'portfolio_url', 'hq', 'type', 'aum_label', 'aum_date', 'overview', 'check_size',
                'team_size', 'team_label', 'performance', 'performance_label', 'recent_activity', 'watch_items',
                'last_verified']
MANAGER_LIST = ['other_offices', 'stages', 'focus_areas', 'best_performers', 'notable_exits', 'sources']
COMPANY_TEXT = ['name', 'website', 'hq', 'description', 'sector', 'status', 'valuation_date', 'valuation_label',
                'valuation_basis', 'first_mark_date', 'revenue_metric', 'revenue_date', 'revenue_label', 'growth',
                'profitability', 'ceo', 'notes', 'last_verified']
COMPANY_FLOAT = ['latest_valuation_usd_bn', 'first_mark_usd_bn', 'step_up_x', 'total_raised_usd_bn',
                 'revenue_usd_bn', 'ev_rev_x']
COMPANY_LIST = ['focus_tags', 'other_investors', 'sources']


class ImportRejected(ValueError):
    """Raised when a snapshot looks partial or malformed; nothing is written."""


def _s(v: Any, n: int | None = None) -> str:
    if v is None:
        return ''
    s = str(v).strip()
    return s[:n] if n else s


def _f(v: Any) -> float | None:
    if v is None or v == '':
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _i(v: Any) -> int | None:
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r'\d[\d,]*', str(v))
    return int(m.group(0).replace(',', '')) if m else None


def _l(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _manager_fields(f: dict) -> dict:
    d = {k: _s(f.get(k)) for k in MANAGER_TEXT}
    d.update({k: _l(f.get(k)) for k in MANAGER_LIST})
    d['name'] = d['name'] or f['id']
    d['founded'] = _i(f.get('founded'))
    d['aum_usd_bn'] = _f(f.get('aum_usd_bn'))
    d['is_stub'] = bool(f.get('stub'))
    d['website'] = d['website'][:500]
    d['portfolio_url'] = d['portfolio_url'][:500]
    return d


def _company_fields(c: dict) -> dict:
    d = {k: _s(c.get(k)) for k in COMPANY_TEXT}
    d.update({k: _f(c.get(k)) for k in COMPANY_FLOAT})
    d.update({k: _l(c.get(k)) for k in COMPANY_LIST})
    d['name'] = d['name'] or c['id']
    d['status'] = d['status'] or 'Private'
    d['website'] = d['website'][:500]
    d['founded'] = _i(c.get('founded'))
    d['employees'] = _i(c.get('employees'))
    d['legacy'] = bool(c.get('legacy'))
    d['valuation_stale'] = bool(c.get('valuation_stale'))
    for k, n in [('valuation_date', 20), ('revenue_date', 20), ('first_mark_date', 20), ('last_verified', 20),
                 ('valuation_label', 20), ('revenue_label', 20), ('sector', 64), ('valuation_basis', 64),
                 ('revenue_metric', 100), ('status', 255), ('ceo', 255), ('hq', 255), ('name', 255)]:
        d[k] = d[k][:n]
    return d


def _derive(fields: dict, rounds: list[dict], positions: list[dict]) -> None:
    """Recompute step-up, valuation/revenue and per-manager entry marks (mirrors pipeline/merge.py)."""
    priced = sorted([r for r in rounds if _f(r.get('post_money_usd_bn'))], key=lambda r: _s(r.get('date')))
    lv, rv = fields['latest_valuation_usd_bn'], fields['revenue_usd_bn']
    if priced:
        fields['first_mark_usd_bn'] = _f(priced[0]['post_money_usd_bn'])
        fields['first_mark_date'] = _s(priced[0].get('date'), 20)
    fm = fields['first_mark_usd_bn']
    fields['step_up_x'] = round(lv / fm, 1) if lv and fm else None
    quarterly = 'quarter' in fields['revenue_metric'].lower()
    ev = round(lv / (rv * (4 if quarterly else 1)), 1) if lv and rv and rv > 0 else None
    fields['ev_rev_x'] = ev if ev is None or ev <= 1000 else None
    for g in positions:
        y = _i(g.get('first_invest_year'))
        entry = _f(g.get('entry_post_usd_bn'))
        if entry is None and y:
            same = [r for r in priced if _s(r.get('date'))[:4] == str(y)]
            rnd = _s(g.get('entry_round')).lower()
            pick = [r for r in same if rnd and rnd in _s(r.get('round')).lower()] or same
            entry = _f(pick[0]['post_money_usd_bn']) if pick else None
        g['entry_post_usd_bn'] = entry
        g['markup_x'] = round(lv / entry, 1) if lv and entry else None


def _money(v: float | None) -> str:
    return '—' if v is None else f'${v:g}bn'


@transaction.atomic
def import_payload(payload: dict, source: str = 'api', force: bool = False) -> dict:
    firms = payload.get('firms') or []
    comps = payload.get('companies') or []
    if not isinstance(firms, list) or not isinstance(comps, list) or not comps:
        raise ImportRejected('Payload must contain non-empty "firms" and "companies" arrays.')
    asof = dt.date.fromisoformat(_s(payload.get('asof')) or dt.date.today().isoformat())

    existing_n = Company.objects.count()
    first_import = existing_n == 0
    if not force and existing_n and len(comps) < 0.7 * existing_n:
        raise ImportRejected(f'Snapshot has {len(comps)} companies vs {existing_n} live; '
                             'looks partial. Re-send with force=1 to accept.')

    # ---- managers ----
    mgr_by_slug: dict[str, Manager] = {}
    for f in firms:
        if not f.get('id'):
            continue
        slug = _s(f['id'], 64)
        m, _ = Manager.objects.update_or_create(slug=slug, defaults=_manager_fields(f))
        mgr_by_slug[slug] = m
        m.funds.all().delete()
        Fund.objects.bulk_create([Fund(manager=m, name=_s(x.get('name'), 255) or 'Fund', size_usd_bn=_f(x.get('size_usd_bn')),
                                       vintage=_i(x.get('vintage')), label=_s(x.get('label'), 20))
                                  for x in _l(f.get('recent_funds')) if isinstance(x, dict)])
        m.people.all().delete()
        KeyPerson.objects.bulk_create([KeyPerson(manager=m, name=_s(p.get('name'), 255), title=_s(p.get('title'), 255),
                                                 focus=_s(p.get('focus')), order=i)
                                       for i, p in enumerate(_l(f.get('key_people'))) if isinstance(p, dict) and p.get('name')])

    def manager(slug: str) -> Manager:
        if slug not in mgr_by_slug:
            mgr_by_slug[slug], _ = Manager.objects.get_or_create(slug=slug, defaults={'name': slug, 'is_stub': True})
        return mgr_by_slug[slug]

    # ---- companies ----
    before = {c.slug: c for c in Company.objects.all()}
    before_pos = set(Position.objects.values_list('company__slug', 'manager__slug'))
    events: list[ChangeEvent] = []
    seen: set[str] = set()
    for c in comps:
        if not c.get('id'):
            continue
        slug = _s(c['id'], 96)
        seen.add(slug)
        fields = _company_fields(c)
        rounds = [v for v in _l(c.get('valuation_history')) if isinstance(v, dict)]
        gps = [dict(g) for g in _l(c.get('gp_positions')) if isinstance(g, dict)]
        _derive(fields, rounds, gps)
        old = before.get(slug)
        obj, _ = Company.objects.update_or_create(slug=slug, defaults=fields)

        obj.rounds.all().delete()
        ValuationRound.objects.bulk_create([
            ValuationRound(company=obj, date=_s(v.get('date'), 20), round=_s(v.get('round'), 255),
                           post_money_usd_bn=_f(v.get('post_money_usd_bn')), lead=_s(v.get('lead'), 500))
            for v in rounds])

        obj.positions.all().delete()
        pos, seen_m = [], set()
        for g in gps:
            fid = _s(g.get('firm_id'), 64)
            if not fid or fid in seen_m:
                continue
            seen_m.add(fid)
            pos.append(Position(company=obj, manager=manager(fid), first_invest_year=_i(g.get('first_invest_year')),
                                entry_round=_s(g.get('entry_round'), 255), fund=_s(g.get('fund'), 255),
                                lead=bool(g.get('lead')), via=_s(g.get('via'), 64),
                                entry_post_usd_bn=_f(g.get('entry_post_usd_bn')), markup_x=_f(g.get('markup_x'))))
        Position.objects.bulk_create(pos)

        if first_import:
            continue
        if old is None:
            events.append(ChangeEvent(date=asof, company=obj, company_name=obj.name, type='added',
                                      detail='Added to tracker'))
            continue
        for fld, typ, label in [('latest_valuation_usd_bn', 'valuation', 'Valuation'),
                                ('revenue_usd_bn', 'revenue', obj.revenue_metric or 'Revenue')]:
            a, b = getattr(old, fld), fields[fld]
            if a and b and abs(b - a) / a > 0.005:
                events.append(ChangeEvent(date=asof, company=obj, company_name=obj.name, type=typ, from_value=a,
                                          to_value=b, detail=f'{label} {_money(a)} → {_money(b)} ({(b / a - 1) * 100:+.0f}%)'))
        if (old.status or 'Private') != fields['status']:
            events.append(ChangeEvent(date=asof, company=obj, company_name=obj.name, type='status',
                                      detail=f'Status: {old.status or "Private"} → {fields["status"]}'))
        for fid in seen_m:
            if (slug, fid) not in before_pos:
                m = mgr_by_slug[fid]
                events.append(ChangeEvent(date=asof, company=obj, company_name=obj.name, manager=m, type='new_position',
                                          detail=f'{m.name} now on cap table'))

    removed = [s for s in before if s not in seen and before[s].added_via != 'user']
    for s in removed:
        events.append(ChangeEvent(date=asof, company=None, company_name=before[s].name, type='removed',
                                  detail='Removed from tracker'))
    Company.objects.filter(slug__in=removed).delete()
    if firms:
        (Manager.objects.exclude(slug__in=list(mgr_by_slug)).exclude(added_via='user')
         .filter(positions__isnull=True).delete())

    if first_import:  # carry the snapshot's own history in on the very first load
        for ch in _l(payload.get('changes')):
            co = Company.objects.filter(slug=ch.get('company_id')).first()
            try:
                d = dt.date.fromisoformat(_s(ch.get('date')))
            except ValueError:
                continue
            typ = {'latest_valuation_usd_bn': 'valuation', 'revenue_usd_bn': 'revenue'}.get(ch.get('type'), ch.get('type'))
            events.append(ChangeEvent(date=d, company=co, company_name=co.name if co else '', type=_s(typ, 20) or 'status',
                                      from_value=_f(ch.get('from')), to_value=_f(ch.get('to')), detail=_s(ch.get('detail'))))
    ChangeEvent.objects.bulk_create(events)

    snap = Snapshot.objects.create(asof=asof, managers=Manager.objects.filter(is_stub=False).count(),
                                   companies=Company.objects.count(), changes_detected=len(events), source=source)
    stats = {'asof': asof.isoformat(), 'managers': snap.managers, 'companies': snap.companies,
             'changes': len(events), 'removed': len(removed), 'first_import': first_import}
    log.info('Imported snapshot %s', stats)
    return stats


def export_payload() -> dict:
    """Rebuild the tracker.json format from the database."""
    snap = Snapshot.objects.first()
    firms = []
    for m in Manager.objects.prefetch_related('funds', 'people'):
        f = {'id': m.slug, 'founded': m.founded, 'aum_usd_bn': m.aum_usd_bn, 'stub': m.is_stub}
        f.update({k: getattr(m, k) for k in MANAGER_TEXT + MANAGER_LIST})
        f['recent_funds'] = [{'name': x.name, 'size_usd_bn': x.size_usd_bn, 'vintage': x.vintage, 'label': x.label}
                             for x in m.funds.all()]
        f['key_people'] = [{'name': p.name, 'title': p.title, 'focus': p.focus} for p in m.people.all()]
        firms.append(f)
    comps = []
    for c in Company.objects.prefetch_related('rounds', 'positions__manager'):
        d = {'id': c.slug, 'founded': c.founded, 'employees': c.employees, 'legacy': c.legacy,
             'valuation_stale': c.valuation_stale}
        d.update({k: getattr(c, k) for k in COMPANY_TEXT + COMPANY_FLOAT + COMPANY_LIST})
        d['valuation_history'] = [{'date': r.date, 'round': r.round, 'post_money_usd_bn': r.post_money_usd_bn,
                                   'lead': r.lead} for r in c.rounds.all()]
        d['gp_positions'] = [{'firm_id': p.manager.slug, 'first_invest_year': p.first_invest_year,
                              'entry_round': p.entry_round, 'fund': p.fund, 'lead': p.lead, 'via': p.via,
                              'entry_post_usd_bn': p.entry_post_usd_bn, 'markup_x': p.markup_x}
                             for p in c.positions.all()]
        comps.append(d)
    return {
        'asof': snap.asof.isoformat() if snap else None,
        'firms': firms,
        'companies': comps,
        'refresh_log': [{'date': s.asof.isoformat(), 'firms': s.managers, 'companies': s.companies}
                        for s in Snapshot.objects.order_by('imported_at')],
        'changes': [{'date': e.date.isoformat(), 'company_id': e.company.slug if e.company else None,
                     'type': e.type, 'from': e.from_value, 'to': e.to_value, 'detail': e.detail}
                    for e in ChangeEvent.objects.select_related('company').order_by('date', 'id')],
    }
