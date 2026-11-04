"""Research prompts. Output formats match pipeline/SCHEMA.md so researched rows look like snapshot rows."""
from __future__ import annotations

import datetime as dt

FOCUS = ('"LLMs / foundation models", "AI infra", "AI applications", "World models / embodied AI", "Robotics", '
         '"Autonomous vehicles", "Quantum", "Semiconductors", "Space", "Defense", "Biotech / therapeutics", '
         '"Healthcare / medtech", "Climate / energy", "Fusion / nuclear", "Fintech", "Crypto / web3", "Cybersecurity", '
         '"Developer tools", "Enterprise SaaS", "Data infrastructure", "Consumer", "Marketplaces / commerce", '
         '"Industrial / manufacturing", "Gov tech", "Edtech", "Media / entertainment", "Materials / chemistry", '
         '"Agtech / food", "Proptech", "Hardware / devices"')
SECTORS = ('AI, Software, Fintech, Deep tech, Biotech/Health, Defense/Gov, Consumer, Mobility, Space, Energy/Climate, '
           'Crypto, Semis/Hardware, Industrial, Other')
STAGES = 'Pre-seed, Seed, Series A, Series B, Series C, Growth, Pre-IPO, Public/crossover'

RULES = f"""You are a venture-capital research analyst building an institutional LP tracker. Today is {{today}}.
Rules:
- Use web search. Source of truth order: the firm's / company's own website and press releases, SEC filings,
  then PitchBook / Preqin news, Crunchbase, Forbes, Bloomberg, Reuters, The Information, WSJ, FT, TechCrunch.
- Prefer the most recent figures (this year where possible). Never invent numbers: use null when you cannot verify.
- Label every quantitative datapoint "HARD" (company/GP disclosure, filing, press release), "REPORTED" (credible
  press) or "ESTIMATE" (third-party estimate).
- Money is USD billions as plain numbers (e.g. 0.25 for $250m). Dates are "YYYY-MM" (or "YYYY").
- Be non-promotional and factual.
- focus tags must come from: {FOCUS}
- sector must be one of: {SECTORS}
- stages must come from: {STAGES}
- Your FINAL message must be a single ```json fenced block and nothing else after it."""

MANAGER = """Research the venture / growth investment manager: "{name}"{website}.

Return JSON:
{{
  "firm": {{
    "name": "official name", "website": "https://...", "portfolio_url": "https://...",
    "hq": "City, State/Country", "other_offices": ["..."], "founded": 2009,
    "type": "Seed specialist | Deep tech VC | Multi-stage VC | Growth equity | Crossover hedge fund | Life-sciences | Corporate VC | Solo GP",
    "aum_usd_bn": 12.5, "aum_label": "REPORTED", "aum_date": "2026",
    "overview": "3-5 sentences: history, strategy, differentiation, 2025-26 developments",
    "recent_funds": [{{"name": "Fund V", "size_usd_bn": 1.2, "vintage": 2025, "label": "HARD"}}],
    "check_size": "Seed $1-3m; A $10-20m ...", "stages": ["Seed", "Series A"], "focus_areas": ["..."],
    "key_people": [{{"name": "...", "title": "...", "focus": "..."}}],
    "team_size": "~40 total; ~15 investors", "team_label": "REPORTED",
    "performance": "Known fund-level net IRR / TVPI / DPI (cite public pension disclosures e.g. CalPERS, UTIMCO, Washington State), notable fund multiples, exit record; or 'Not publicly disclosed'.",
    "performance_label": "HARD | REPORTED | ESTIMATE | N/A",
    "best_performers": ["..."], "notable_exits": ["Company (IPO 2021)"],
    "recent_activity": "2-3 sentences on 2025-26 deal pace and themes",
    "watch_items": "1-2 sentences: key LP risks (key-person, style drift, concentration, mark-up risk, DPI)",
    "sources": ["https://..."]
  }},
  "portfolio": [
    {{"name": "Company", "website": "https://...", "first_invest_year": 2021, "entry_round": "Series A", "lead": true}}
  ]
}}
List up to {max_portfolio} portfolio companies in "portfolio", prioritising the largest current valuations, best
performers, defining exits and the newest 2025-26 deals. Use the firm's own portfolio page where possible."""

COMPANY = """Research the company: "{name}"{website}.{context}

The LP tracks these managers (id: name). If any of them invested in the company, list them in "tracked_investors":
{managers}

Return JSON:
{{
  "name": "official name", "website": "https://...", "hq": "City, Country", "founded": 2019,
  "description": "1-2 sentences, what it does", "sector": "...", "focus_tags": ["..."],
  "status": "Private | Public (TICKER) | Acquired (by X, YYYY) | Shut down",
  "latest_valuation_usd_bn": 4.0, "valuation_date": "2026-03", "valuation_label": "REPORTED",
  "valuation_basis": "Latest round / tender | Market cap",
  "valuation_history": [{{"date": "2023-05", "round": "Series B", "post_money_usd_bn": 1.1, "lead": "Lead investor"}}],
  "total_raised_usd_bn": 0.6,
  "revenue_metric": "ARR | Revenue | Run-rate revenue", "revenue_usd_bn": 0.12, "revenue_date": "2026-01",
  "revenue_label": "REPORTED", "growth": "e.g. ~3x YoY", "profitability": "e.g. Loss-making; gross margin ~70%",
  "employees": 350, "ceo": "...",
  "other_investors": ["all notable investors"],
  "tracked_investors": [{{"id": "manager id from the list", "first_invest_year": 2022, "entry_round": "Series A", "lead": false}}],
  "notes": "anything material: recent news, secondary marks, down rounds, IPO plans",
  "sources": ["https://..."]
}}
For a public company use the current market cap as latest_valuation_usd_bn with valuation_basis "Market cap"."""


def manager_prompt(name: str, website: str, max_portfolio: int) -> tuple[str, str]:
    system = RULES.format(today=dt.date.today().isoformat())
    user = MANAGER.format(name=name, website=f' ({website})' if website else '', max_portfolio=max_portfolio)
    return system, user


def company_prompt(name: str, website: str, managers: list[tuple[str, str]], via: str | None) -> tuple[str, str]:
    system = RULES.format(today=dt.date.today().isoformat())
    context = f' It is a portfolio company of {via}.' if via else ''
    roster = '\n'.join(f'- {i}: {n}' for i, n in managers)
    user = COMPANY.format(name=name, website=f' ({website})' if website else '', context=context, managers=roster)
    return system, user
