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

## Auto-research (apps/research)
- `POST /api/v1/research/` {kind, name, website?, include_portfolio?} or {kind, id} creates the row (`added_via='user'`, `research_status='queued'`) and a `ResearchJob`; `research_worker` (started in start.sh, `RESEARCH_CONCURRENCY` threads) claims jobs with `select_for_update(skip_locked)`.
- `engine.ask_claude` uses the Messages API with `web_search_20250305`, follows `pause_turn`, and expects a final ```json block in the SCHEMA shape (prompts in `prompts.py`). Manager jobs spawn child company jobs; `recompute()` re-derives marks after linking.
- Needs `ANTHROPIC_API_KEY`. Model is chosen per job (Add dialog / Re-research) from `settings.RESEARCH_MODELS`, which also holds per-model prices; defaults `RESEARCH_MODEL` (manager, Sonnet), `RESEARCH_PORTFOLIO_MODEL` (fan-out, Haiku), `RESEARCH_COMPANY_MODEL` (Sonnet). Unknown model ids fall back to the default. `engine.request_cost` prices each API request; `ResearchJob.cost` accumulates it. Only admin/analyst/staff can create jobs.
- Snapshot imports never delete `added_via='user'` rows; `pipeline/merge.py` keeps firm ids it hasn't seen in its CANON list.

## Track record (apps/trackrecord)
- `Investment` (amounts USD **millions**, valuations USD billions), `CashFlow` (negative = in, positive = out to LP), `InvestmentComment`, `SheetSettings` singleton, `ManagerAssessment` + `ManagerComment` (GP view).
- Structures: direct / spv / coinvest / secondary (company rows) and l1 / l2 (fund rows, `manager` FK, vintage, commitment). `is_fund` drives which section and columns.
- `metrics.compute` is the single source for UI and PDF: gross MOIC/IRR/DPI, net after fee + carry (scaled positive flows) unless `net_*_reported` / `dpi_reported` set; IRR suppressed (`irr_nm`) under one year.
- API under `/api/v1/track-record/`: `investments/` (list returns investments + summaries + settings + can_edit; `POST {id}/comments/`), `settings/`, `prefill/?company=`, `pdf/?commentary=1&ids=`, `managers/<slug>/assessment/`, `managers/<slug>/comments/`.
- Points lists are `[{text, severity: high|medium|low}]` (`serializers.clean_points`).

## Conventions
- All data endpoints require JWT (`IsAuthenticated`). Import/export require `X-Import-Token` or staff.
- Frontend loads the full manager + company lists once into Zustand; detail drawers fetch via React Query. Hash routes: `#managers`, `#companies`, `#gp-<id>`, `#co-<id>`.
- Frontend calls the API same-origin at `/api/v1` unless `VITE_API_URL` is set at build time.
- Without `SECRET_KEY`, production derives a stable key from `DATABASE_URL` (all gunicorn workers must share one key).
- Commit format: `type(scope): message`.
