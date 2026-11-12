# CLAUDE.md — Venture GP Atlas

Context for AI assistants working on this repo. Keep it current.

**What it is:** a tracker of venture/growth managers (GPs) and their portfolio companies for an institutional LP (Mindari suite). Same stack and Railway deployment pattern as the Dynamo repo (`saching1402/dynamo`).

**Look:** white background, navy ink, gold accents, red for alerts/declines; fonts Bricolage Grotesque (display), IBM Plex Sans (body), IBM Plex Mono (numbers) — tokens in `frontend/src/index.css` `:root`.

**Stack:** Django 5 + DRF + SimpleJWT + PostgreSQL (`backend/`), React 18 + TS + Vite + Tailwind + Zustand + React Query + Recharts (`frontend/`), deployed as ONE Railway service from the repo root (root `Dockerfile` builds the React app and copies it into Django as `frontend_dist`, served by WhiteNoise + `spa_index`) + Railway Postgres. `backend/` and `frontend/` Dockerfiles remain for a two-service setup.

## Data model
- `Manager` (slug id, AUM, stages, focus_areas, performance text + label, funds, key people)
- `Company` (slug id, valuation + label/date/basis, revenue/ARR + metric/date/label, growth, profitability, `legacy`, `valuation_stale`, derived `step_up_x`, `ev_rev_x`, `first_mark_*`)
- `ValuationRound` (date `YYYY-MM`, round, post-money $bn, lead)
- `Position` (manager ↔ company; first year, entry round, lead; derived entry mark + markup)
- `Snapshot`, `ChangeEvent`, `WatchItem` (per user)

All money is **USD billions** (float). Dates are `YYYY-MM` or `YYYY-MM-DD` strings as sourced.

## Data rules
- Source precedence: GP website → company release/filing → PitchBook/Preqin/Forbes/Bloomberg/Reuters/The Information → other. Labels: HARD / REPORTED / ESTIMATE. Never invent figures; leave null.
- `legacy` = pre-2010 holding (or founded < 2005) that has listed/sold with last recorded round < 2017 (Apple, Amazon…). Hidden by default, excluded from totals.
- `valuation_stale` = only an old mark exists (pre-2024, or a non-private company with no current mark). Excluded from totals.
- `apps/importer/services.py::_derive` recomputes step-up, val/revenue (quarterly revenue ×4; >1000x dropped as unit error) and entry marks; keep it in sync with `pipeline/merge.py`.
- Import is a full snapshot: companies absent from it are removed (logged). Snapshots < 70% of live company count are rejected unless `force=1`.
- Investor sweep (`apps/companies/investors.py`): `POST /api/v1/companies/investors/` (X-Import-Token or staff) {companies:[{id, investors:[{name, lead?, round?, year?} | "name"], sources:[url]}]}. Names matching a tracked manager (`ManagerIndex`: full name, parenthetical aliases, trailing generic words stripped, `ALIASES`; `NO_SHORT` blocks collisions such as "Bain Capital" → BCV, "Index", "Insight") become `Position(via='investor sweep')` + a `new_position` ChangeEvent; others append to `other_investors`. Additive only; stores `investor_sources`, `investors_updated_at`.

## Auto-research (apps/research)
- `POST /api/v1/research/` {kind, name, website?, include_portfolio?} or {kind, id} creates the row (`added_via='user'`, `research_status='queued'`) and a `ResearchJob`; `research_worker` (started in start.sh, `RESEARCH_CONCURRENCY` threads) claims jobs with `select_for_update(skip_locked)`.
- `engine.ask_claude` uses the Messages API with `web_search_20250305`, follows `pause_turn`, and expects a final ```json block in the SCHEMA shape (prompts in `prompts.py`). Manager jobs spawn child company jobs; `recompute()` re-derives marks after linking.
- Needs `ANTHROPIC_API_KEY`. Model is chosen per job (Add dialog / Re-research) from `settings.RESEARCH_MODELS`, which also holds per-model prices; defaults `RESEARCH_MODEL` (manager, Sonnet), `RESEARCH_PORTFOLIO_MODEL` (fan-out, Haiku), `RESEARCH_COMPANY_MODEL` (Sonnet). Unknown model ids fall back to the default. `engine.request_cost` prices each API request; `ResearchJob.cost` accumulates it. Only admin/analyst/staff can create jobs.
- Snapshot imports never delete `added_via='user'` rows; `pipeline/merge.py` keeps firm ids it hasn't seen in its CANON list.
- Business profiles (`apps/research/profiles.py`): `Company.profile` / `Manager.profile` JSON (company: summary, products, customers, business_model, financials, value_chain.chain[layer, examples, current], competition, competitive_position, moat, industry.market/trends, risks, sources; GP: summary, strategy, funds, team, track_record, differentiation, platform, peers, current_themes, lp_considerations, sources) + `profile_updated_at` + `profile_status`. Jobs `coprofile` / `gpprofile` use `profile_status` (not `research_status`), fill missing headline revenue / description only, and are claimed after user-initiated jobs (`claim_next` orders bulk last). API `/api/v1/research/profiles/`: GET stats + per-model `est_profile`, POST {kind, scope missing|all|shortlist, ids?, limit?, model?} (default model = portfolio/Haiku), DELETE cancels queued; accepts a signed-in admin/analyst or X-Import-Token. UI: `components/Profile.tsx` (drawer views, Generate/Refresh, bulk dialog on Companies / Managers). Snapshot imports never touch profiles.

## Track record (apps/trackrecord)
- `Investment` (amounts USD **millions**, valuations USD billions), `CashFlow` (negative = in, positive = out to LP), `InvestmentComment`, `SheetSettings` singleton, `ManagerAssessment` + `ManagerComment` (GP view).
- Structures: direct / spv / coinvest / secondary (company rows) and l1 / l2 (fund rows, `manager` FK, vintage, commitment). `is_fund` drives which section and columns.
- `metrics.compute` is the single source for UI and PDF: gross MOIC/IRR/DPI, net after fee + carry (scaled positive flows) unless `net_*_reported` / `dpi_reported` set; IRR suppressed (`irr_nm`) under one year.
- API under `/api/v1/track-record/`: `investments/` (list returns investments + summaries + settings + can_edit; `POST {id}/comments/`), `settings/`, `prefill/?company=`, `pdf/?commentary=1&ids=`, `managers/<slug>/assessment/`, `managers/<slug>/comments/`.
- Points lists are `[{text, severity: high|medium|low}]` (`serializers.clean_points`).
- `views.apply_filters` (view=all|direct|funds, structure, status, sector, q) is shared by `investments/` and `pdf/`; the list also returns `facets` from the unfiltered book. PDF kinds: `pdf/?kind=all|direct|funds` (or `view=`). `metrics.fund_programme` builds the fund sheet (totals, `by_vintage`, `by_strategy` via manager.type); bucket net IRR = paid-in-weighted average of fund net IRRs so it reconciles with fund rows.

## Shortlist (apps/shortlist)
- `ShortlistItem` (kind company|fund, FK company or manager, `my_priority` / `claude_priority` L1-L3 with `*_since`, `claude_rationale`, thesis, rounds_plan, target_allocation_usd_m, and refresh outputs: brief, momentum, performance, next_round, catalysts/risks points, sources), `PriorityChange` (track mine|claude, old→new, note, who, when; every change logged), `NewsItem` (de-duplicated by url/headline; `hidden` = dismissed, never re-added), `ShortlistMark` (one row per refresh: valuation/revenue or AUM).
- Refresh = `ResearchJob(kind='shortlist', slug=<item id>)` on the shared research worker → `shortlist.engine.run_refresh`: writes newer valuation/revenue/rounds/status back to `Company` (or AUM/funds/performance to `Manager`), lifts a stale headline valuation to a newer priced round, logs ChangeEvents, adds news, sets Claude's priority (logged when it moves).
- Adding an untracked name creates the company/manager row + a profile ResearchJob; `research.engine.run_job` then calls `after_profile` to queue the first refresh.
- API `/api/v1/shortlist/`: GET (items + can_edit + model menu), POST add, `<id>/` PATCH (my_priority + note, thesis, rounds_plan, target) / DELETE, `<id>/refresh/`, `refresh/` (kind, priority, ids), `news/<id>/` DELETE (dismiss). Edits need admin/analyst.
- Migration `0002_seed_shortlist` seeds Anthropic, OpenAI, Anduril, Physical Intelligence, Baseten, Fireworks (my priority L1; Claude's initial view) and queues a first refresh when ANTHROPIC_API_KEY is set. Snapshot imports never delete shortlisted companies/managers.
- Frontend: `pages/Shortlist.tsx` (tab `#shortlist`, drawer `#sl-<id>`).

## Trends (apps/trends)
- `Theme` (slug, heat 0-100, signal, conviction, horizon, `deploy_early` / `deploy_growth` overweight|selective|watch|avoid, funding rows with `metric` venture|market, risks/catalysts, kpis, `segments` = market map [{name, companies:[{name, id (tracker slug), domain, stage, valuation…}]}], news, sources; user fields `followed`, `user_note`), `TrendResource` (reading list per theme or global; unique per theme+url; `hidden` = removed by user, never re-added), `TrendBrief` (one per weekly update; headline, deploy_now/watch/cooling, market stats, playbook, `heat` snapshot for history).
- Heat and signal are CALCULATED (`apps/trends/heat.py`, single source; the UI framework text comes from `heat.FRAMEWORK`): heat = 30% capital momentum (`inputs.capital_growth_x`, 50+25·log2) + 20% round velocity (share of dated mapped private companies with a mark/dated round in 12m; unscored if <½ dated) + 15% valuation momentum (median latest/previous step-up) + 15% exits (`inputs.exits_12m`, `mega_exit`) + 20% smart-money breadth (Atlas GPs holding mapped companies ÷ 20). Missing inputs score a neutral 50 and are flagged. Signal rules: cooling → hot → accelerating → emerging → steady. Imports and refresh replies supply `inputs` only; `services.rescore()` stores heat/signal (for history). `start.sh` runs `rescore_trends --seed-inputs` to backfill missing inputs. Deploy views stay a per-stage judgement against four tests (momentum, entry price, access, liquidity).
- Stage rule (`EARLY_MAX_USD_BN` = 1.0): early < $1bn post-money, growth ≥ $1bn private, public/acquired separate. `services._resolve` merges map entries with live `Company` rows; the newer valuation mark wins.
- API `/api/v1/trends/`: GET (whole tab), `themes/<slug>/` PATCH (followed, user_note), `themes/<slug>/refresh/` (ResearchJob kind `theme` → `engine.run_theme`), `resources/` POST, `resources/<id>/` PATCH/DELETE, `import/` POST + `export/` GET (X-Import-Token). Import upserts themes and keeps user fields; news merges (cap 40).
- Seed: `backend/data/trends.json` (built by `pipeline/build_trends_seed.py`), loaded by `start.sh` via `import_trends --if-empty`. Weekly updates come from the "Venture GP Atlas Weekly" scheduled task (Fridays), which exports, edits and re-imports.
- Frontend: `pages/Trends.tsx` (tab `#trends`, drawer `#th-<id>`).

## Conventions
- All data endpoints require JWT (`IsAuthenticated`). Import/export require `X-Import-Token` or staff.
- Frontend loads the full manager + company lists once into Zustand; detail drawers fetch via React Query. Hash routes: `#managers`, `#companies`, `#gp-<id>`, `#co-<id>`.
- Frontend calls the API same-origin at `/api/v1` unless `VITE_API_URL` is set at build time.
- Without `SECRET_KEY`, production derives a stable key from `DATABASE_URL` (all gunicorn workers must share one key).
- Logos: `components/Logo.tsx` (`Logo` by url/domain, `CoLogo` / `GpLogo` by tracker id via the store, `WithLogo` layout); icons come from Google's favicon service (sz=128) with an initials fallback for missing or 16px placeholder icons. Manager and company list endpoints include `website` for this. CSS class is `co-logo` (`.logo` is the site brand mark).
- Commit format: `type(scope): message`.
