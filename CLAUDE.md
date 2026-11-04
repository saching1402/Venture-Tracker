# CLAUDE.md — Venture GP Atlas

Context for AI assistants working on this repo. Keep it current.

**What it is:** a tracker of venture/growth managers (GPs) and their portfolio companies for an institutional LP (Mindari suite). Same stack and Railway deployment pattern as the Dynamo repo (`saching1402/dynamo`).

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

## Conventions
- All data endpoints require JWT (`IsAuthenticated`). Import/export require `X-Import-Token` or staff.
- Frontend loads the full manager + company lists once into Zustand; detail drawers fetch via React Query. Hash routes: `#managers`, `#companies`, `#gp-<id>`, `#co-<id>`.
- Frontend calls the API same-origin at `/api/v1` unless `VITE_API_URL` is set at build time.
- Without `SECRET_KEY`, production derives a stable key from `DATABASE_URL` (all gunicorn workers must share one key).
- Commit format: `type(scope): message`.
