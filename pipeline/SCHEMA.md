# VC/Growth GP Tracker — data schema (as of 2026-11-03)

Write TWO JSON files per batch: `firms_<batch>.json` (array of firm objects) and `companies_<batch>.json` (array of company objects).
Valid JSON only (no comments, no trailing commas). Numbers are numbers (USD billions for valuations/raises/revenue unless stated), null when unknown.
Every quantitative datapoint carries a confidence label: "HARD" (company/GP disclosure, filing, or press release), "REPORTED" (credible press: Bloomberg, The Information, WSJ, FT, Reuters, Forbes, TechCrunch, PitchBook news), "ESTIMATE" (third-party estimate / extrapolation).
Source of truth order: GP's own website/portfolio page > company press release / SEC filing > PitchBook / Preqin / Crunchbase / Forbes / Bloomberg / The Information / Reuters > other.
Be non-promotional. Prefer the most recent datapoint you can verify (2026 where possible). Never invent numbers — use null and add a note.

## Firm object
{
  "id": "a16z",                       // short slug, lowercase, no spaces
  "name": "Andreessen Horowitz (a16z)",
  "website": "https://a16z.com",
  "portfolio_url": "https://a16z.com/portfolio/",
  "hq": "Menlo Park, CA, USA",
  "other_offices": ["San Francisco", "New York", "London"],
  "founded": 2009,
  "type": "Multi-stage VC",          // e.g. Seed specialist / Deep tech VC / Multi-stage VC / Growth equity / Crossover hedge fund / Life-sciences
  "aum_usd_bn": 90, "aum_label": "REPORTED", "aum_date": "2026",
  "overview": "3-5 sentences: history, strategy, differentiation, recent developments (2025-26).",
  "recent_funds": [ {"name": "a16z AI Infrastructure Fund", "size_usd_bn": 1.7, "vintage": 2026, "label": "HARD"} ],   // last 3-6 funds incl. 2024-26 raises
  "check_size": "Seed $1-5m; A/B $10-50m; growth $50-500m+",
  "stages": ["Seed","Series A","Series B","Series C","Growth","Pre-IPO"],   // subset of: Pre-seed, Seed, Series A, Series B, Series C, Growth, Pre-IPO, Public/crossover
  "focus_areas": ["LLMs / foundation models","AI infra","Application software", ...],  // from canonical list below
  "key_people": [ {"name":"Marc Andreessen","title":"Co-founder & GP","focus":"..."} ],   // 4-10 people
  "team_size": "~600 total; ~100 investment pros", "team_label": "REPORTED",
  "performance": "Text: known fund-level net IRR/TVPI/DPI (cite public pension disclosures e.g. CalPERS, UTIMCO, Washington State, Florida SBA, Oregon PERS where available), notable fund multiples, exit record. Say 'not publicly disclosed' if so.",
  "performance_label": "HARD|REPORTED|ESTIMATE|N/A",
  "best_performers": ["Coinbase","Databricks","..."],        // 5-10 best-performing / defining investments
  "notable_exits": ["Coinbase (IPO 2021)", "..."],
  "recent_activity": "2-3 sentences on 2025-26 deal pace, themes, notable leads.",
  "watch_items": "1-2 sentences: key risks / LP considerations (key-person, style drift, concentration, mark-up risk, DPI drought).",
  "sources": ["https://...", "..."],
  "last_verified": "2026-11-03"
}

## Company object (one per company; if the same company is backed by multiple of your firms, ONE object with multiple gp_positions)
{
  "id": "anthropic",                 // slug
  "name": "Anthropic",
  "website": "https://anthropic.com",
  "hq": "San Francisco, CA, USA",
  "founded": 2021,
  "description": "1-2 sentences, what it does.",
  "sector": "AI",                    // top-level: AI, Software, Fintech, Deep tech, Biotech/Health, Defense/Gov, Consumer, Mobility, Space, Energy/Climate, Crypto, Semis/Hardware, Industrial, Other
  "focus_tags": ["LLMs / foundation models"],   // from canonical list
  "status": "Private",               // Private | Public (TICKER) | Acquired (by X, year) | Shut down
  "latest_valuation_usd_bn": 183, "valuation_date": "2025-09", "valuation_label": "HARD",   // for public cos use current market cap and date
  "valuation_history": [ {"date":"2023-05","round":"Series C","post_money_usd_bn":4.1,"lead":"Spark Capital"} ],   // chronological, as many rounds as you can verify
  "total_raised_usd_bn": 27,
  "revenue_metric": "ARR",           // ARR | Revenue | Run-rate revenue | null
  "revenue_usd_bn": 5.0, "revenue_date": "2025-08", "revenue_label": "REPORTED",
  "growth": "e.g. ~5x YoY",          // text, null if unknown
  "profitability": "e.g. Loss-making; gross margin ~60% (REPORTED)",   // text, null if unknown
  "employees": 2000,
  "ceo": "Dario Amodei",
  "other_investors": ["Google","Amazon","ICONIQ","Lightspeed","..."],   // notable investors overall, incl. non-tracked
  "gp_positions": [ {"firm_id":"spark","first_invest_year":2021,"entry_round":"Series A","fund":"Spark Capital VI (if known)","lead":true} ],
  "notes": "anything material: recent news, secondary-market marks, down rounds, IPO plans.",
  "sources": ["https://..."],
  "last_verified": "2026-11-03"
}

## Canonical focus-area vocabulary (use exactly these strings)
"LLMs / foundation models", "AI infra", "AI applications", "World models / embodied AI", "Robotics", "Autonomous vehicles", "Quantum", "Semiconductors", "Space", "Defense", "Biotech / therapeutics", "Healthcare / medtech", "Climate / energy", "Fusion / nuclear", "Fintech", "Crypto / web3", "Cybersecurity", "Developer tools", "Enterprise SaaS", "Data infrastructure", "Consumer", "Marketplaces / commerce", "Industrial / manufacturing", "Gov tech", "Edtech", "Media / entertainment", "Materials / chemistry", "Agtech / food", "Proptech", "Hardware / devices"
