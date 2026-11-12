"""
Theme heat: a transparent, measured 0-100 score (not an opinion), plus a rule-based signal.

HEAT = weighted average of five sub-scores, each 0-100:

  1. Capital momentum      30%  venture $ into the theme, latest period vs the prior comparable period
                                (input `capital_growth_x`, sourced each week).  score = 50 + 25 x log2(growth)
                                → 0.5x = 25, flat = 50, 2x = 75, 4x+ = 100
  2. Round velocity        20%  share of the theme's mapped private companies (with a dated round) that raised or were
                                re-marked in the last 12 months (tracker + sourced marks + dated round notes).
                                score = share x 125, capped at 100; not scored if under half the companies are dated
  3. Valuation momentum    15%  median step-up of each company's latest mark vs its previous one (latest within
                                24 months).  score = 50 + 25 x log2(median step-up) → 1x = 50, 2x = 75, 4x = 100
  4. Exits & liquidity     15%  IPOs, M&A and large secondaries in the last 12 months (input `exits_12m`, plus
                                `mega_exit` for a $25bn+ event).  0 → 15, 1 → 40, 2-3 → 65, 4+ → 85; mega +15
  5. Smart-money breadth   20%  distinct Atlas GPs (of 51) holding at least one mapped company (tracker positions).
                                score = GPs / 20 x 100, capped at 100

A missing input scores a neutral 50 and is flagged, so it neither inflates nor sinks a theme.

SIGNAL (derived, in this order):
  Cooling       capital growth below 0.9x, or heat down 5+ points vs 4 weeks ago
  Hot           heat 80+
  Accelerating  heat 65-79 and (capital growth 1.5x+ or heat up 5+ vs 4 weeks ago)
  Emerging      heat below 65 and capital growth 1.2x+
  Steady        everything else

Heat measures momentum, not attractiveness. The deploy view (overweight / selective / watch / avoid, per stage)
is a separate judgement: see DEPLOY_RUBRIC.
"""
from __future__ import annotations

import datetime as dt
import math
import re
import statistics

WEIGHTS = {'capital': 0.30, 'velocity': 0.20, 'valuation': 0.15, 'exits': 0.15, 'conviction': 0.20}
LABELS = {'capital': 'Capital momentum', 'velocity': 'Round velocity', 'valuation': 'Valuation momentum',
          'exits': 'Exits & liquidity', 'conviction': 'Smart-money breadth'}
NEW_ENTRY_SINCE_YEARS = 2
CONVICTION_FULL = 20

DEPLOY_RUBRIC = [
    {'id': 'overweight', 'label': 'Overweight', 'rule': 'Deploy now. Passes all four tests at this stage: (1) momentum: heat 65+ or a clear '
     'structural tailwind; (2) entry price: valuations still leave room for 3x+ (early) or 2x+ (growth) net; (3) access: '
     'allocation is realistically obtainable via our GPs, co-invests or secondaries; (4) liquidity fits a 7-10 year fund life.'},
    {'id': 'selective', 'label': 'Selective', 'rule': 'Attractive theme but fails one test, usually entry price or crowding. '
     'Back only category leaders or clearly mispriced names, sized smaller.'},
    {'id': 'watch', 'label': 'Watch', 'rule': 'Thesis not yet proven at this stage, or two tests fail (e.g. timelines beyond fund life, '
     'labs or incumbents likely to capture the value). Track the signals to watch; revisit when one flips.'},
    {'id': 'avoid', 'label': 'Avoid', 'rule': 'Risk/return is structurally unattractive at this stage, e.g. "early" rounds priced like '
     'growth, binary science risk at growth prices, or no realistic access.'},
]
STAGE_RULE = 'Early = latest post-money below $1bn. Growth = private at $1bn or more. Public and exited companies are shown but not scored.'


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def _log_score(x: float | None) -> float | None:
    return None if not x or x <= 0 else _clamp(50 + 25 * math.log2(x))


def _marks(c: dict) -> list[tuple[str, float]]:
    """Dated valuation marks for one company: tracker rounds plus a newer sourced mark from the theme map."""
    pts = [((r.get('date') or '')[:7], r['post_money_usd_bn']) for r in c.get('rounds', []) if r.get('post_money_usd_bn')]
    v, d = c.get('valuation_usd_bn'), (c.get('valuation_date') or '')[:7]
    if v and d and (not pts or d > max(p[0] for p in pts)):
        pts.append((d, v))
    return sorted(p for p in pts if p[0])


MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def text_dates(text: str) -> list[str]:
    """'YYYY-MM' dates written in free text: 'Mar 2026', 'Q3 2026', 'H1 2026', '2026-05'."""
    out = []
    t = (text or '').lower()
    for m, y in re.findall(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(20\d\d)', t):
        out.append(f'{y}-{MONTHS[m]:02d}')
    for q, y in re.findall(r'\bq([1-4])\s+(20\d\d)', t):
        out.append(f'{y}-{int(q) * 3:02d}')
    for h, y in re.findall(r'\bh([12])\s+(20\d\d)', t):
        out.append(f'{y}-{int(h) * 6:02d}')
    out += re.findall(r'\b(20\d\d-[01]\d)\b', t)
    return out


def latest_date(c: dict) -> str:
    ds = [d for d, _ in _marks(c)] + text_dates(f"{c.get('last_round') or ''} {c.get('description') or ''}")
    return max(ds) if ds else ''


def compute(companies: list[dict], inputs: dict, heat_4w_ago: int | None, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    cut12 = (today - dt.timedelta(days=365)).isoformat()[:7]
    cut24 = (today - dt.timedelta(days=730)).isoformat()[:7]
    since_year = today.year - NEW_ENTRY_SINCE_YEARS
    priv = [c for c in companies if c.get('stage') in ('early', 'growth')]
    comps: dict[str, dict] = {}

    g = inputs.get('capital_growth_x')
    s = _log_score(g)
    comps['capital'] = {'score': s, 'value': f'{g:.2f}x' if g else None,
                        'evidence': inputs.get('capital_note') or ('Not yet sourced' if not g else '')}

    dated = [c for c in priv if latest_date(c)]
    fresh = [c for c in dated if latest_date(c) >= cut12]
    enough = len(dated) >= max(2, len(priv) / 2)
    share = len(fresh) / len(dated) if enough else None
    comps['velocity'] = {'score': _clamp(share * 125) if share is not None else None,
                         'value': f'{len(fresh)} of {len(dated)}' if enough else None,
                         'evidence': (f'{len(fresh)} of {len(dated)} mapped private companies with a dated round raised or were re-marked since {cut12}'
                                      if enough else f'Only {len(dated)} of {len(priv)} mapped private companies have a dated round: not scored')}

    steps = []
    for c in priv:
        m = _marks(c)
        if len(m) >= 2 and m[-1][0] >= cut24 and m[-2][1] > 0:
            steps.append((m[-1][1] / m[-2][1], c['name']))
    med = statistics.median(x for x, _ in steps) if len(steps) >= 2 else None
    top = sorted(steps, reverse=True)[:3]
    comps['valuation'] = {'score': _log_score(med), 'value': f'{med:.2f}x' if med else None,
                          'evidence': (f'Median step-up {med:.2f}x across {len(steps)} companies (top: '
                                       + ', '.join(f'{n} {x:.1f}x' for x, n in top) + ')') if med else 'Fewer than 2 companies with recent marks'}

    n = inputs.get('exits_12m')
    if n is None:
        es = None
    else:
        es = 15 if n <= 0 else 40 if n == 1 else 65 if n <= 3 else 85
        es = min(100, es + (15 if inputs.get('mega_exit') else 0))
    comps['exits'] = {'score': es, 'value': None if n is None else f'{n}{" incl. mega" if inputs.get("mega_exit") else ""}',
                      'evidence': inputs.get('exits_note') or ('Not yet sourced' if n is None else '')}

    gps = sorted({g for c in companies for g, _ in (c.get('gp_entries') or [])})
    recent = sorted({g for c in companies for g, yr in (c.get('gp_entries') or []) if yr and yr >= since_year})
    comps['conviction'] = {'score': _clamp(len(gps) / CONVICTION_FULL * 100), 'value': f'{len(gps)} GPs',
                           'evidence': f'{len(gps)} of the 51 Atlas GPs hold a mapped company ({len(recent)} entered since {since_year})'}

    total = 0.0
    for k, w in WEIGHTS.items():
        c = comps[k]
        c.update(weight=w, label=LABELS[k], scored=c['score'] is not None)
        sc = c['score'] if c['score'] is not None else 50.0
        c['score'] = round(sc)
        c['points'] = round(sc * w, 1)
        total += sc * w
    heat = round(total)

    delta = heat - heat_4w_ago if heat_4w_ago is not None else 0
    if (g is not None and g < 0.9) or delta <= -5:
        signal = 'cooling'
    elif heat >= 80:
        signal = 'hot'
    elif heat >= 65 and ((g or 0) >= 1.5 or delta >= 5):
        signal = 'accelerating'
    elif heat < 65 and (g or 0) >= 1.2:
        signal = 'emerging'
    else:
        signal = 'steady'
    return {'heat': heat, 'signal': signal, 'components': [{'id': k, **comps[k]} for k in WEIGHTS],
            'delta_4w': delta if heat_4w_ago is not None else None}


FRAMEWORK = {
    'heat': {'summary': 'Heat measures momentum (how much capital, conviction and price action is flowing into a theme), '
                        'not whether to invest. It is calculated, not judged: five measured inputs, weighted.',
             'components': [
                 {'id': 'capital', 'label': LABELS['capital'], 'weight': WEIGHTS['capital'], 'how': 'Venture $ into the theme, latest period vs the prior comparable period (Crunchbase, PitchBook, Seraphim, FIA…). Score = 50 + 25 × log2(growth): 0.5x → 25, flat → 50, 2x → 75, 4x+ → 100.'},
                 {'id': 'velocity', 'label': LABELS['velocity'], 'weight': WEIGHTS['velocity'], 'how': 'Share of the theme\'s mapped private companies (with a dated round) that raised or were re-marked in the last 12 months (Atlas tracker, sourced marks and dated round notes). Score = share × 125, capped at 100. Not scored if under half the companies have a dated round.'},
                 {'id': 'valuation', 'label': LABELS['valuation'], 'weight': WEIGHTS['valuation'], 'how': 'Median step-up of each company\'s latest mark vs its previous one (latest within 24 months). Score = 50 + 25 × log2(step-up): 1x → 50, 2x → 75, 4x → 100.'},
                 {'id': 'exits', 'label': LABELS['exits'], 'weight': WEIGHTS['exits'], 'how': 'IPOs, M&A and large secondaries in the last 12 months: 0 → 15, 1 → 40, 2-3 → 65, 4+ → 85; +15 for a $25bn+ event.'},
                 {'id': 'conviction', 'label': LABELS['conviction'], 'weight': WEIGHTS['conviction'], 'how': f'Distinct Atlas GPs (of the 51 tracked) holding at least one of the theme\'s mapped companies; shows how broadly top managers are positioned. Score = GPs ÷ {CONVICTION_FULL} × 100, capped at 100.'},
             ],
             'missing': 'A missing input scores a neutral 50 and is flagged, so it neither inflates nor sinks a theme.'},
    'signal': [
        {'id': 'cooling', 'rule': 'Capital growth below 0.9x, or heat down 5+ points vs 4 weeks ago (checked first).'},
        {'id': 'hot', 'rule': 'Heat 80 or more.'},
        {'id': 'accelerating', 'rule': 'Heat 65-79 and capital growth 1.5x+ (or heat up 5+ points in 4 weeks).'},
        {'id': 'emerging', 'rule': 'Heat below 65 but capital growing 1.2x+: early momentum from a small base.'},
        {'id': 'steady', 'rule': 'Everything else.'},
    ],
    'deploy': {'summary': 'The deploy view is a separate, per-stage judgement of attractiveness at today\'s entry prices. '
                          'A hot theme can be "Avoid" at early stage (e.g. frontier labs, where "seed" rounds price like growth) '
                          'and a cooler theme can be "Overweight" if prices are reasonable and access is available.',
               'tests': ['Momentum: heat 65+ or a clear structural tailwind', 'Entry price: room for 3x+ net (early) or 2x+ net (growth)',
                         'Access: allocation obtainable via our GPs, co-invest or secondaries', 'Liquidity: realistic exit within a 7-10 year fund life'],
               'levels': DEPLOY_RUBRIC},
    'stage': STAGE_RULE,
    'cadence': 'Inputs refresh every Friday (Venture GP Atlas Weekly) and whenever a theme is refreshed; tracker-based inputs update live as rounds are added.',
}
