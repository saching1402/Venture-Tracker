"""Load / export the trends snapshot and build the API payload (themes resolved against live tracker data)."""
from __future__ import annotations

import datetime as dt
import re
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.importer.services import _f, _i, _l, _s

from .models import DEPLOY, EARLY_MAX_USD_BN, SIGNALS, Theme, TrendBrief, TrendResource

SIGNAL_IDS = {k for k, _ in SIGNALS}
DEPLOY_IDS = {k for k, _ in DEPLOY}
KIND_IDS = {k for k, _ in TrendResource.KINDS}
THEME_TEXT = ('name', 'category', 'color', 'summary', 'why_now', 'deploy_view', 'valuation_notes', 'conviction', 'horizon')


def _date(v) -> str:
    s = _s(v, 10)
    return s if re.match(r'^\d{4}(-\d{2}){0,2}$', s) else ''


def _url(v) -> str:
    s = _s(v, 1000)
    return s if s.startswith(('http://', 'https://')) else ''


def domain_of(url: str) -> str:
    try:
        host = urlparse(url if '://' in url else f'https://{url}').netloc.lower()
    except ValueError:
        return ''
    return host[4:] if host.startswith('www.') else host


def _points(v) -> list[dict]:
    out = []
    for p in _l(v)[:12]:
        if isinstance(p, str) and p.strip():
            out.append({'text': p.strip()[:600], 'severity': 'medium'})
        elif isinstance(p, dict) and _s(p.get('text')):
            out.append({'text': _s(p['text'], 600), 'severity': p.get('severity') if p.get('severity') in ('high', 'medium', 'low') else 'medium'})
    return out


def _clean_company(c: dict) -> dict | None:
    if not isinstance(c, dict) or not _s(c.get('name')):
        return None
    stage = _s(c.get('stage'), 12).lower()
    return {
        'name': _s(c['name'], 200), 'id': _s(c.get('id'), 96) or None,
        'domain': domain_of(_s(c.get('domain') or c.get('website'), 300)),
        'stage': stage if stage in ('early', 'growth', 'public', 'acquired') else '',
        'hq': _s(c.get('hq'), 120), 'description': _s(c.get('description'), 400),
        'valuation_usd_bn': _f(c.get('valuation_usd_bn')), 'valuation_date': _date(c.get('valuation_date')),
        'valuation_label': _s(c.get('valuation_label'), 12), 'last_round': _s(c.get('last_round'), 160),
        'investors': [_s(x, 80) for x in _l(c.get('investors'))[:8] if _s(x)],
        'note': _s(c.get('note'), 300), 'url': _url(c.get('url')),
    }


def _clean_segments(v) -> list[dict]:
    out = []
    for seg in _l(v)[:12]:
        if isinstance(seg, dict) and _s(seg.get('name')):
            cos = [c for c in (_clean_company(x) for x in _l(seg.get('companies'))[:40]) if c]
            out.append({'name': _s(seg['name'], 120), 'description': _s(seg.get('description'), 300), 'companies': cos})
    return out


def _clean_funding(v) -> list[dict]:
    out = []
    for f in _l(v)[:20]:
        if isinstance(f, dict) and (_f(f.get('capital_usd_bn')) is not None or _s(f.get('note'))):
            out.append({'period': _s(f.get('period'), 40), 'stage': _s(f.get('stage'), 20) or 'all',
                        'capital_usd_bn': _f(f.get('capital_usd_bn')), 'deals': _i(f.get('deals')),
                        'note': _s(f.get('note'), 300), 'source': _s(f.get('source'), 160), 'url': _url(f.get('url')),
                        'label': _s(f.get('label'), 12) or 'REPORTED',
                        'metric': 'market' if f.get('metric') == 'market' else 'venture'})
    return out


def _clean_news(v) -> list[dict]:
    out = []
    for n in _l(v)[:30]:
        if isinstance(n, dict) and _s(n.get('headline')):
            out.append({'date': _date(n.get('date')), 'headline': _s(n['headline'], 400), 'url': _url(n.get('url')),
                        'source': _s(n.get('source'), 160), 'summary': _s(n.get('summary'), 600)})
    return sorted(out, key=lambda n: n['date'], reverse=True)


def add_resource(theme: Theme | None, r: dict, via: str = 'weekly', user=None) -> TrendResource | None:
    url = _url(r.get('url'))
    title = _s(r.get('title'), 500)
    if not url or not title:
        return None
    if TrendResource.objects.filter(theme=theme, url=url).exists():
        return None
    kind = _s(r.get('kind') or r.get('type'), 12).lower()
    return TrendResource.objects.create(
        theme=theme, url=url, title=title, source=_s(r.get('source'), 255) or domain_of(url),
        kind=kind if kind in KIND_IDS else 'article', date=_date(r.get('date')), summary=_s(r.get('summary')),
        added_via=via, added_by=user, pinned=bool(r.get('pinned')))


def apply_theme(data: dict, via: str = 'weekly') -> tuple[Theme, int]:
    """Upsert one theme from a snapshot / refresh reply. Keeps the user's follow flag and note."""
    slug = _s(data.get('id') or data.get('slug'), 64)
    theme, _ = Theme.objects.get_or_create(slug=slug, defaults={'name': _s(data.get('name'), 200) or slug})
    for fld in THEME_TEXT:
        if _s(data.get(fld)):
            setattr(theme, fld, _s(data.get(fld)))
    if data.get('signal') in SIGNAL_IDS:
        theme.signal = data['signal']
    for fld in ('deploy_early', 'deploy_growth'):
        if data.get(fld) in DEPLOY_IDS:
            setattr(theme, fld, data[fld])
    heat = _i(data.get('heat'))
    if heat is not None:
        theme.heat = max(0, min(100, heat))
    if _i(data.get('order')) is not None:
        theme.order = _i(data['order'])
    if _clean_funding(data.get('funding')):
        theme.funding = _clean_funding(data.get('funding'))
    for fld in ('risks', 'catalysts'):
        if _points(data.get(fld)):
            setattr(theme, fld, _points(data.get(fld)))
    if _l(data.get('kpis')):
        theme.kpis = [_s(k, 300) for k in _l(data['kpis'])[:12] if _s(k)]
    if _clean_segments(data.get('segments')):
        theme.segments = _clean_segments(data.get('segments'))
    news = _clean_news(data.get('news'))
    if news:
        seen = {(n.get('url') or n['headline']) for n in news}
        theme.news = (news + [n for n in theme.news if (n.get('url') or n.get('headline')) not in seen])[:40]
    srcs = [s for s in (_url(x) for x in _l(data.get('sources'))) if s]
    if srcs:
        theme.sources = srcs[:30]
    theme.last_refreshed_at = timezone.now()
    theme.save()
    added = sum(1 for r in _l(data.get('resources'))[:40] if isinstance(r, dict) and add_resource(theme, r, via))
    return theme, added


@transaction.atomic
def import_trends(payload: dict, source: str = 'weekly') -> dict:
    themes = [t for t in _l(payload.get('themes')) if isinstance(t, dict) and _s(t.get('id') or t.get('slug'))]
    added = 0
    for t in themes:
        _, n = apply_theme(t, via='weekly')
        added += n
    for r in _l(payload.get('resources'))[:80]:
        if isinstance(r, dict):
            slug = _s(r.get('theme'), 64)
            theme = Theme.objects.filter(slug=slug).first() if slug else None
            added += 1 if add_resource(theme, r, 'weekly') else 0
    b = payload.get('brief') if isinstance(payload.get('brief'), dict) else {}
    as_of = _date(payload.get('asof') or b.get('as_of')) or dt.date.today().isoformat()
    brief = None
    if b or themes:
        brief = TrendBrief.objects.create(
            as_of=dt.date.fromisoformat(as_of[:10]) if len(as_of) >= 10 else dt.date.today(),
            headline=_s(b.get('headline'), 500), summary=_s(b.get('summary')), highlights=_points(b.get('highlights')),
            deploy_now=[x for x in _l(b.get('deploy_now'))[:20] if isinstance(x, dict)],
            watch=[x for x in _l(b.get('watch'))[:20] if isinstance(x, dict)],
            cooling=[x for x in _l(b.get('cooling'))[:20] if isinstance(x, dict)],
            market=b.get('market') if isinstance(b.get('market'), dict) else {},
            playbook=[x for x in _l(b.get('playbook') or payload.get('playbook'))[:20] if isinstance(x, dict)]
            or (TrendBrief.objects.first().playbook if TrendBrief.objects.exists() else []),
            heat={t.slug: t.heat for t in Theme.objects.all() if t.heat is not None}, source=source[:40])
    return {'themes': len(themes), 'resources_added': added, 'brief': brief.as_of.isoformat() if brief else None,
            'total_themes': Theme.objects.count()}


def export_trends() -> dict:
    """The current state in the import shape, for the weekly job to build on."""
    brief = TrendBrief.objects.first()
    return {
        'asof': brief.as_of.isoformat() if brief else None,
        'early_max_usd_bn': EARLY_MAX_USD_BN,
        'brief': brief_json(brief),
        'themes': [{
            'id': t.slug, 'name': t.name, 'category': t.category, 'order': t.order, 'color': t.color,
            'summary': t.summary, 'why_now': t.why_now, 'deploy_view': t.deploy_view, 'signal': t.signal, 'heat': t.heat,
            'conviction': t.conviction, 'horizon': t.horizon, 'deploy_early': t.deploy_early, 'deploy_growth': t.deploy_growth,
            'funding': t.funding, 'valuation_notes': t.valuation_notes, 'risks': t.risks, 'catalysts': t.catalysts,
            'kpis': t.kpis, 'segments': t.segments, 'news': t.news, 'sources': t.sources,
            'followed': t.followed, 'last_refreshed_at': t.last_refreshed_at.isoformat() if t.last_refreshed_at else None,
            'resources': [resource_json(r) for r in t.resources.filter(hidden=False)],
        } for t in Theme.objects.all()],
        'resources': [resource_json(r) for r in TrendResource.objects.filter(theme__isnull=True, hidden=False)],
    }


# ── API payload ───────────────────────────────────────────────────────────────
def resource_json(r: TrendResource) -> dict:
    return {'id': r.id, 'theme': r.theme.slug if r.theme_id else None, 'title': r.title, 'url': r.url, 'source': r.source,
            'kind': r.kind, 'date': r.date, 'summary': r.summary, 'added_via': r.added_via, 'pinned': r.pinned}


def brief_json(b: TrendBrief | None) -> dict | None:
    if not b:
        return None
    return {'as_of': b.as_of.isoformat(), 'headline': b.headline, 'summary': b.summary, 'highlights': b.highlights,
            'deploy_now': b.deploy_now, 'watch': b.watch, 'cooling': b.cooling, 'market': b.market, 'playbook': b.playbook}


def stage_of(valuation: float | None, status: str, declared: str = '') -> str:
    st = (status or '').lower()
    if st.startswith('public'):
        return 'public'
    if st.startswith(('acquired', 'shut')):
        return 'acquired'
    if valuation is not None:
        return 'early' if valuation < EARLY_MAX_USD_BN else 'growth'
    return declared or 'early'


def _resolve(c: dict, cos: dict[str, Company]) -> dict:
    """Merge a market-map entry with the live tracker row: the newer valuation mark wins."""
    out = dict(c)
    co = cos.get(c.get('id') or '')
    if co:
        out['tracked'] = True
        out['id'] = co.slug
        out['domain'] = c.get('domain') or domain_of(co.website or '')
        out['description'] = c.get('description') or co.description
        out['hq'] = c.get('hq') or co.hq
        out['status'] = co.status
        if co.latest_valuation_usd_bn and (co.valuation_date or '') >= (c.get('valuation_date') or ''):
            out.update(valuation_usd_bn=co.latest_valuation_usd_bn, valuation_date=co.valuation_date,
                       valuation_label=co.valuation_label)
        out['revenue_usd_bn'] = co.revenue_usd_bn
        out['revenue_metric'] = co.revenue_metric
        out['step_up_x'] = co.step_up_x
        out['gp_ids'] = [p.manager.slug for p in co.positions.all()][:12]
        out['rounds'] = [{'date': r.date, 'round': r.round, 'post_money_usd_bn': r.post_money_usd_bn}
                         for r in co.rounds.all() if r.post_money_usd_bn]
    else:
        out['tracked'] = False
        out['status'] = {'public': 'Public', 'acquired': 'Acquired'}.get(c.get('stage') or '', 'Private')
        out['rounds'] = []
    out['stage'] = stage_of(out.get('valuation_usd_bn'), out.get('status', ''), c.get('stage') or '')
    return out


def theme_json(t: Theme, cos: dict[str, Company], resources: list[TrendResource], history: list[dict]) -> dict:
    segments = [{**s, 'companies': [_resolve(c, cos) for c in s.get('companies', [])]} for s in t.segments]
    flat = [c for s in segments for c in s['companies']]
    priv = [c for c in flat if c['stage'] in ('early', 'growth')]
    cutoff = (dt.date.today() - dt.timedelta(days=365)).isoformat()[:7]
    marks = sorted(({'company': c['name'], 'id': c.get('id'), 'date': r['date'], 'round': r['round'],
                     'post_money_usd_bn': r['post_money_usd_bn'],
                     'stage': 'early' if r['post_money_usd_bn'] < EARLY_MAX_USD_BN else 'growth'}
                    for c in flat for r in c.get('rounds', [])), key=lambda m: m['date'])
    stats = {
        'companies': len(flat),
        'early': sum(1 for c in flat if c['stage'] == 'early'),
        'growth': sum(1 for c in flat if c['stage'] == 'growth'),
        'public': sum(1 for c in flat if c['stage'] in ('public', 'acquired')),
        'private_value_usd_bn': round(sum(c.get('valuation_usd_bn') or 0 for c in priv), 2),
        'rounds_12m': sum(1 for m in marks if m['date'] >= cutoff),
        'tracked': sum(1 for c in flat if c.get('tracked')),
    }
    return {
        'id': t.slug, 'name': t.name, 'category': t.category, 'order': t.order, 'color': t.color,
        'summary': t.summary, 'why_now': t.why_now, 'deploy_view': t.deploy_view, 'signal': t.signal, 'heat': t.heat,
        'conviction': t.conviction, 'horizon': t.horizon, 'deploy_early': t.deploy_early, 'deploy_growth': t.deploy_growth,
        'funding': t.funding, 'valuation_notes': t.valuation_notes, 'risks': t.risks, 'catalysts': t.catalysts,
        'kpis': t.kpis, 'segments': segments, 'news': t.news, 'sources': t.sources,
        'followed': t.followed, 'user_note': t.user_note, 'research_status': t.research_status,
        'last_refreshed_at': t.last_refreshed_at.isoformat() if t.last_refreshed_at else None,
        'stats': stats, 'marks': marks, 'heat_history': [{'as_of': h['as_of'], 'heat': h['heat'].get(t.slug)}
                                                          for h in history if h['heat'].get(t.slug) is not None],
        'resources': [resource_json(r) for r in resources if r.theme_id == t.id],
    }


def trends_payload() -> dict:
    themes = list(Theme.objects.all())
    ids = {c.get('id') for t in themes for s in t.segments for c in s.get('companies', []) if c.get('id')}
    cos = {c.slug: c for c in Company.objects.filter(slug__in=ids).prefetch_related('rounds', 'positions__manager')}
    resources = list(TrendResource.objects.filter(hidden=False).select_related('theme'))
    history = [{'as_of': b.as_of.isoformat(), 'heat': b.heat or {}} for b in reversed(TrendBrief.objects.all()[:26])]
    brief = TrendBrief.objects.first()
    prev = TrendBrief.objects.all()[1:2].first()
    return {
        'brief': brief_json(brief), 'early_max_usd_bn': EARLY_MAX_USD_BN,
        'themes': [theme_json(t, cos, resources, history) for t in themes],
        'resources': [resource_json(r) for r in resources if not r.theme_id],
        'heat_prev': prev.heat if prev else {}, 'history': history,
    }
