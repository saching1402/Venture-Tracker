"""
Return metrics for the track record. Pure functions: no database access except via the objects passed in.

Conventions
- Cash flows from the LP's point of view: negative = invested, positive = returned.
- Gross = before vehicle fees and carry. Net = after the stated annual fee and carry
  (an estimate), unless the GP-reported net MOIC / IRR is entered, which then wins.
- IRR is an XIRR on actual dated flows, with the unrealised value as a terminal flow.
"""
from __future__ import annotations

import datetime as dt
from collections.abc import Iterable

Flow = tuple[dt.date, float]


def xirr(flows: Iterable[Flow]) -> float | None:
    """Annualised IRR for dated flows (decimal, e.g. 0.25 = 25%). None when undefined."""
    fl = sorted((d, a) for d, a in flows if a)
    if len(fl) < 2 or not any(a < 0 for _, a in fl) or not any(a > 0 for _, a in fl):
        return None
    t0 = fl[0][0]
    ts = [((d - t0).days / 365.25, a) for d, a in fl]
    if ts[-1][0] <= 0:
        return None

    def npv(r: float) -> float:
        return sum(a / (1 + r) ** t for t, a in ts)

    lo, hi = -0.9999, 1.0
    f_lo = npv(lo)
    while npv(hi) * f_lo > 0 and hi < 1e6:   # widen until the root is bracketed
        hi *= 4
    if npv(hi) * f_lo > 0:
        return None
    for _ in range(200):                        # bisection: slow but never diverges
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-9 or hi - lo < 1e-10:
            break
        if f_mid * f_lo < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def _r(v: float | None, n: int = 4) -> float | None:
    return None if v is None else round(v, n)


def compute(inv, today: dt.date | None = None, latest_company_valuation: float | None = None) -> dict:
    """Metrics for one investment (`inv` is an Investment with prefetched cashflows)."""
    today = today or dt.date.today()
    end = inv.value_date or today
    cfs = list(inv.cashflows.all())
    follow_ons = -sum(c.amount_usd_m for c in cfs if c.amount_usd_m < 0)
    dists = sum(c.amount_usd_m for c in cfs if c.amount_usd_m > 0)
    invested = (inv.invested_usd_m or 0) + follow_ons
    realised = (inv.realised_usd_m or 0) + dists
    current = 0.0 if inv.status in ('realised', 'written_off') and inv.current_value_usd_m is None else (inv.current_value_usd_m or 0)
    if inv.status == 'written_off':
        current = 0.0
    gross_total = realised + current

    flows: list[Flow] = [(inv.invest_date, -(inv.invested_usd_m or 0))]
    flows += [(c.date, c.amount_usd_m) for c in cfs]
    if inv.realised_usd_m:
        flows.append((end, inv.realised_usd_m))
    if current:
        flows.append((end, current))

    years = max(0.0, (end - inv.invest_date).days / 365.25)
    fees = invested * (inv.mgmt_fee_pct or 0) / 100 * years
    gain = gross_total - invested - fees
    carry = max(0.0, gain) * (inv.carry_pct or 0) / 100
    net_total = gross_total - fees - carry
    scale = net_total / gross_total if gross_total > 0 else 0.0
    net_flows = [(d, a * scale if a > 0 else a) for d, a in flows]

    gross_moic = gross_total / invested if invested else None
    short = years < 1  # IRR is not annualised for holds under a year (shown as n.m.)
    gross_irr = None if short else xirr(flows)
    has_fees = bool(inv.mgmt_fee_pct or inv.carry_pct)
    net_moic = inv.net_moic_reported if inv.net_moic_reported is not None else (net_total / invested if invested else None)
    net_irr = (inv.net_irr_reported / 100) if inv.net_irr_reported is not None else (None if short else xirr(net_flows))
    net_basis = ('reported' if inv.net_moic_reported is not None or inv.net_irr_reported is not None or inv.dpi_reported is not None
                 else 'estimate' if has_fees else 'no fees')

    implied_markup = (latest_company_valuation / inv.entry_valuation_usd_bn
                      if latest_company_valuation and inv.entry_valuation_usd_bn else None)
    ownership = inv.ownership_pct
    if ownership is None and inv.entry_valuation_usd_bn and inv.structure in ('direct', 'spv', 'coinvest'):
        ownership = (inv.invested_usd_m or 0) / (inv.entry_valuation_usd_bn * 1000) * 100
    return {
        'invested_usd_m': _r(invested, 3),
        'realised_usd_m': _r(realised, 3),
        'current_usd_m': _r(current, 3),
        'total_value_usd_m': _r(gross_total, 3),
        'gain_usd_m': _r(gross_total - invested, 3),
        'gross_moic': _r(gross_moic, 3),
        'gross_irr': _r(gross_irr),
        'dpi': _r(realised / invested if invested else None, 3),
        'rvpi': _r(current / invested if invested else None, 3),
        'net_moic': _r(net_moic, 3),
        'net_irr': _r(net_irr),
        'net_dpi': _r(inv.dpi_reported if inv.dpi_reported is not None else ((realised * scale) / invested if invested else None), 3),
        'net_basis': net_basis,
        'fees_usd_m': _r(fees, 3),
        'carry_usd_m': _r(carry, 3),
        'holding_years': _r(years, 2),
        'irr_nm': short and inv.net_irr_reported is None,
        'unfunded_usd_m': _r(max(0.0, inv.commitment_usd_m - invested), 3) if inv.commitment_usd_m else None,
        'ownership_pct': _r(ownership, 5),
        'implied_markup_x': _r(implied_markup, 2),
        'suggested_value_usd_m': _r((inv.invested_usd_m or 0) * implied_markup, 3) if implied_markup else None,
        '_flows': flows,
        '_net_flows': net_flows,
        '_net_total': net_total,
    }


def summarise(rows: list[tuple]) -> dict:
    """Pooled metrics across (investment, metrics) pairs."""
    if not rows:
        return {'count': 0}
    inv_sum = sum(m['invested_usd_m'] or 0 for _, m in rows)
    real_sum = sum(m['realised_usd_m'] or 0 for _, m in rows)
    cur_sum = sum(m['current_usd_m'] or 0 for _, m in rows)
    net_sum = sum(m['_net_total'] for _, m in rows)
    flows = [f for _, m in rows for f in m['_flows']]
    net_flows = [f for _, m in rows for f in m['_net_flows']]
    by_structure: dict[str, dict] = {}
    for inv, m in rows:
        s = by_structure.setdefault(inv.get_structure_display(), {'count': 0, 'invested_usd_m': 0.0, 'total_value_usd_m': 0.0})
        s['count'] += 1
        s['invested_usd_m'] += m['invested_usd_m'] or 0
        s['total_value_usd_m'] += m['total_value_usd_m'] or 0
    for s in by_structure.values():
        s['gross_moic'] = round(s['total_value_usd_m'] / s['invested_usd_m'], 3) if s['invested_usd_m'] else None
    best = max(rows, key=lambda r: r[1]['gross_moic'] or 0)
    return {
        'count': len(rows),
        'active': sum(1 for i, _ in rows if i.status in ('active', 'partial')),
        'realised_count': sum(1 for i, _ in rows if i.status in ('realised', 'partial')),
        'invested_usd_m': round(inv_sum, 3),
        'realised_usd_m': round(real_sum, 3),
        'current_usd_m': round(cur_sum, 3),
        'total_value_usd_m': round(real_sum + cur_sum, 3),
        'gross_moic': round((real_sum + cur_sum) / inv_sum, 3) if inv_sum else None,
        'net_moic': round(net_sum / inv_sum, 3) if inv_sum else None,
        'dpi': round(real_sum / inv_sum, 3) if inv_sum else None,
        'gross_irr': _r(xirr(flows)),
        'net_irr': _r(xirr(net_flows)),
        'capacity_usd_m': round(sum(i.capacity_usd_m or 0 for i, _ in rows), 3),
        'unfunded_usd_m': round(sum(m['unfunded_usd_m'] or 0 for _, m in rows), 3),
        'by_structure': by_structure,
        'best': {'name': best[0].name, 'gross_moic': best[1]['gross_moic']},
    }


def _bucket(rows: list[tuple]) -> dict:
    com = sum(i.commitment_usd_m or 0 for i, _ in rows)
    called = sum(m['invested_usd_m'] or 0 for _, m in rows)
    dist = sum(m['realised_usd_m'] or 0 for _, m in rows)
    nav = sum(m['current_usd_m'] or 0 for _, m in rows)
    # Paid-in-weighted average of each fund's net IRR (GP-reported where entered), so buckets reconcile with fund rows
    w = [(m['invested_usd_m'] or 0, m['net_irr']) for _, m in rows if m['net_irr'] is not None and m['invested_usd_m']]
    wsum = sum(a for a, _ in w)
    return {
        'count': len(rows),
        'commitment_usd_m': round(com, 3), 'called_usd_m': round(called, 3), 'distributed_usd_m': round(dist, 3),
        'nav_usd_m': round(nav, 3), 'total_value_usd_m': round(dist + nav, 3),
        'unfunded_usd_m': round(sum(m['unfunded_usd_m'] or 0 for _, m in rows), 3),
        'pct_called': round(called / com, 4) if com else None,
        'tvpi': round((dist + nav) / called, 3) if called else None,
        'dpi': round(dist / called, 3) if called else None,
        'rvpi': round(nav / called, 3) if called else None,
        'net_irr': _r(sum(a * r for a, r in w) / wsum) if wsum else None,
        'irr_coverage': round(wsum / called, 3) if called else None,
    }


def fund_programme(rows: list[tuple]) -> dict:
    """LP fund-programme view: totals, by vintage, by strategy. NAV is taken as net (GP-reported)."""
    funds = [r for r in rows if r[0].is_fund]
    if not funds:
        return {'count': 0, 'by_vintage': [], 'by_strategy': []}
    total = _bucket(funds)
    total['gps'] = len({i.manager_id or i.name for i, _ in funds})
    total['capacity_usd_m'] = round(sum(i.capacity_usd_m or 0 for i, _ in funds), 3)
    vint: dict[int, list] = {}
    strat: dict[str, list] = {}
    for inv, m in funds:
        vint.setdefault(inv.vintage or inv.invest_date.year, []).append((inv, m))
        label = (inv.manager.type if inv.manager_id and inv.manager.type else '') or inv.get_structure_display()
        strat.setdefault(label, []).append((inv, m))
    total['by_vintage'] = [dict(_bucket(v), vintage=k) for k, v in sorted(vint.items())]
    total['by_strategy'] = sorted((dict(_bucket(v), strategy=k) for k, v in strat.items()),
                                  key=lambda b: -b['commitment_usd_m'])
    return total
