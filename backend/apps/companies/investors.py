"""
Investor sweep: merge sourced investor lists into companies.

- Names that match one of the tracked managers (the 51 Atlas GPs) become `Position` rows (via="investor sweep"),
  so the company shows the GP and the GP shows the company.
- Every other investor (funds, corporates, angels) is added to `Company.other_investors`.
- Additive only: nothing is ever removed, existing positions are only enriched (lead flag, entry round / year when blank).
"""
from __future__ import annotations

import re

from django.db import transaction
from django.utils import timezone

from apps.managers.models import Manager

from .models import Company, Position

GENERIC = {'ventures', 'venture', 'partners', 'capital', 'management', 'investment', 'investments', 'group', 'funds',
           'fund', 'vc', 'llc', 'lp', 'inc', 'the', 'and', 'co', 'growth'}
# names that would collide with a different firm once generic words are stripped
NO_SHORT = {'baincapital', 'insight', 'index', 'spark', 'sound', 'true', 'founders', 'general', 'radical', 'battery'}
BAD_KEYS = {'us', 'usa', 'europe', 'solo', 'sologp', 'china', 'india', 'global', 'strategic', 'strategicpartners'}
ALIASES = {
    'a16z': 'Andreessen Horowitz', 'andreessen': 'Andreessen Horowitz', 'andreessenhorowitz': 'Andreessen Horowitz',
    'nea': 'New Enterprise Associates', 'newenterpriseassociates': 'New Enterprise Associates',
    'kpcb': 'Kleiner Perkins', 'kleinerperkinscaufieldbyers': 'Kleiner Perkins', 'kleiner': 'Kleiner Perkins',
    'bvp': 'Bessemer Venture Partners', 'bessemer': 'Bessemer Venture Partners',
    'gc': 'General Catalyst', 'generalcatalystpartners': 'General Catalyst',
    'usv': 'Union Square Ventures', 'ivp': 'IVP', 'institutionalventurepartners': 'IVP',
    'tcv': 'TCV', 'technologycrossoverventures': 'TCV', 'bcv': 'Bain Capital Ventures',
    'iconiq': 'ICONIQ', 'iconiqgrowth': 'ICONIQ', 'iconiqcapital': 'ICONIQ',
    'dcvc': 'DCVC', 'datacollective': 'DCVC', 'eclipseventures': 'Eclipse', 'eclipse': 'Eclipse',
    'sequoia': 'Sequoia Capital', 'sequoiacapital': 'Sequoia Capital', 'sequoiacapitalus': 'Sequoia Capital',
    'dragoneer': 'Dragoneer', 'greenoaks': 'Greenoaks', 'eladgil': 'Elad Gil', 'conviction': 'Conviction',
    'convictionpartners': 'Conviction', 'tigerglobal': 'Tiger Global', 'coatue': 'Coatue', 'hytcapital': 'HyT Capital',
    'monolith': 'Monolith', 'monolithcapital': 'Monolith', 'monolithmanagement': 'Monolith',
    'lightspeed': 'Lightspeed', 'lsvp': 'Lightspeed', 'thrive': 'Thrive Capital', 'felicisventures': 'Felicis',
    'khosla': 'Khosla Ventures', 'menlo': 'Menlo Ventures', 'greylock': 'Greylock', 'redpoint': 'Redpoint',
    'ribbit': 'Ribbit Capital', 'playground': 'Playground Global', 'lux': 'Lux Capital', 'deerfield': 'Deerfield',
    'jmi': 'JMI Equity', 'alleycorp': 'AlleyCorp', 'atomico': 'Atomico', 'balderton': 'Balderton', 'inovia': 'Inovia',
    'factorial': 'Factorial Funds', '8vc': '8VC', 'sosv': 'SOSV', 'benchmark': 'Benchmark', 'benchmarkcapital': 'Benchmark',
    'accel': 'Accel', 'accelpartners': 'Accel', 'waldencatalyst': 'Walden Catalyst', 'foundersfund': 'Founders Fund',
}


def norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def _words(s: str) -> list[str]:
    return [w for w in re.split(r'[^a-z0-9]+', (s or '').lower()) if w]


def _keys(name: str) -> set[str]:
    """Match keys for a manager name: the full name, each parenthetical alias, and the name with trailing generic words removed."""
    out = set()
    parts = [re.sub(r'\(.*?\)', '', name)] + re.findall(r'\((.*?)\)', name)
    for p in parts:
        for chunk in re.split(r'/', p):
            w = _words(chunk)
            if not w:
                continue
            out.add(''.join(w))
            while len(w) > 1 and w[-1] in GENERIC:
                w = w[:-1]
                out.add(''.join(w))
    full = norm(name)
    return {k for k in out if k == full or (len(k) >= 3 and k not in NO_SHORT and k not in BAD_KEYS)}


class ManagerIndex:
    def __init__(self):
        self.by_key: dict[str, Manager] = {}
        mgrs = list(Manager.objects.filter(is_stub=False))
        for m in mgrs:
            slug = norm(m.slug)
            for k in _keys(m.name) | ({slug} if slug not in NO_SHORT and len(slug) >= 3 else set()):
                self.by_key.setdefault(k, m)
        for alias, target in ALIASES.items():
            m = self.by_key.get(norm(target)) or next((x for x in mgrs if norm(target) in _keys(x.name)), None)
            if m:
                self.by_key[alias] = m

    def match(self, name: str) -> Manager | None:
        n = norm(name)
        if n in self.by_key:
            return self.by_key[n]
        if n in NO_SHORT:  # e.g. "Bain Capital" (the buyout firm) must not become Bain Capital Ventures
            return None
        w = _words(re.sub(r'\(.*?\)', '', name))
        while len(w) > 1 and w[-1] in GENERIC:
            w = w[:-1]
            k = ''.join(w)
            if k in self.by_key and k not in NO_SHORT:
                return self.by_key[k]
        return None


def _year(v) -> int | None:
    try:
        y = int(str(v)[:4])
    except (TypeError, ValueError):
        return None
    return y if 1990 <= y <= 2100 else None


@transaction.atomic
def merge_investors(payload: dict, source: str = 'investor sweep') -> dict:
    from apps.research.engine import recompute
    from apps.tracking.models import ChangeEvent

    idx = ManagerIndex()
    today = timezone.localdate()
    stats = {'companies': 0, 'unknown_companies': [], 'positions_added': 0, 'positions_enriched': 0, 'others_added': 0}
    for row in payload.get('companies') or []:
        if not isinstance(row, dict):
            continue
        co = Company.objects.filter(slug=str(row.get('id') or '')).first()
        if not co:
            stats['unknown_companies'].append(str(row.get('id'))[:96])
            continue
        stats['companies'] += 1
        others = list(co.other_investors or [])
        seen = {norm(x) for x in others}
        existing = {p.manager_id: p for p in co.positions.all()}
        touched = False
        for inv in row.get('investors') or []:
            if isinstance(inv, str):
                inv = {'name': inv}
            if not isinstance(inv, dict):
                continue
            name = str(inv.get('name') or '').strip()[:200]
            if not name or len(name) < 2:
                continue
            m = idx.match(name)
            if m:
                p = existing.get(m.id)
                if not p:
                    p = Position.objects.create(company=co, manager=m, lead=bool(inv.get('lead')), via=source[:64],
                                                entry_round=str(inv.get('round') or '')[:255], first_invest_year=_year(inv.get('year')))
                    existing[m.id] = p
                    stats['positions_added'] += 1
                    touched = True
                    ChangeEvent.objects.create(date=today, company=co, company_name=co.name, manager=m, type='new_position',
                                               detail=f'{m.name} added as investor in {co.name} ({source})')
                else:
                    changed = []
                    if inv.get('lead') and not p.lead:
                        p.lead = True
                        changed.append('lead')
                    if not p.entry_round and inv.get('round'):
                        p.entry_round = str(inv['round'])[:255]
                        changed.append('entry_round')
                    if not p.first_invest_year and _year(inv.get('year')):
                        p.first_invest_year = _year(inv.get('year'))
                        changed.append('first_invest_year')
                    if changed:
                        p.save(update_fields=changed)
                        stats['positions_enriched'] += 1
                        touched = True
                seen.add(norm(name))
                continue
            if norm(name) not in seen:
                others.append(name)
                seen.add(norm(name))
                stats['others_added'] += 1
        srcs = [s for s in (str(x)[:1000] for x in (row.get('sources') or [])) if s.startswith('http')]
        if others != (co.other_investors or []) or srcs:
            co.other_investors = others[:120]
            if srcs:
                co.investor_sources = list(dict.fromkeys((co.investor_sources or []) + srcs))[:30]
            co.investors_updated_at = timezone.now()
            co.save(update_fields=['other_investors', 'investor_sources', 'investors_updated_at'])
        elif touched:
            co.investors_updated_at = timezone.now()
            co.save(update_fields=['investors_updated_at'])
        if touched:
            recompute(co)
    return stats
