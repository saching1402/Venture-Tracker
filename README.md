# Venture GP Atlas

A living tracker of ~50 venture and growth managers (a16z, Sequoia, Founders Fund, Lux, DCVC, ICONIQ, Thrive, Coatue, Tiger…) and the ~900 portfolio companies they back: fund sizes, AUM, key people, disclosed performance, focus areas, and for every company its valuation history, ARR/revenue, growth, margins and full cap table of tracked managers.

Same stack and Railway layout as the Mindari / Dynamo portfolio suite:

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite, Tailwind, Zustand, React Query, Recharts (Mindari navy/gold design) |
| Backend | Django 5 + Django REST Framework + SimpleJWT |
| Database | PostgreSQL (Railway add-on) |
| Hosting | Railway: one Docker service (frontend built into Django) + Postgres |

## Repository layout

```
Dockerfile          single-service build: React app compiled, then served by Django
railway.toml        Railway config for the root build
backend/            Django API
  atlas/            project settings, urls, wsgi
  apps/users        email login, roles (admin / analyst / viewer)
  apps/managers     Manager, Fund, KeyPerson
  apps/companies    Company, ValuationRound, Position (manager ↔ company)
  apps/tracking     Snapshot (refresh log), ChangeEvent, WatchItem (per user)
  apps/importer     tracker.json import/export, management command, token-protected API
  data/tracker.json seed snapshot, loaded automatically on first deploy
frontend/           React SPA (also deployable on its own via frontend/Dockerfile)
pipeline/           weekly refresh tooling: merge.py (builds tracker.json), SCHEMA.md, push_snapshot.py
```

## API (all under `/api/v1/`, JWT required unless noted)

| Endpoint | Purpose |
|---|---|
| `POST auth/token/`, `auth/token/refresh/` | Sign in with email + password (rate-limited) |
| `GET meta/` | Header figures, refresh history |
| `GET managers/`, `managers/<id>/` | Manager list; profile with funds, people and holdings |
| `GET companies/`, `companies/<id>/` | Company list (filters: `sector`, `manager`, `status`, `min_valuation`, `legacy`, `search`); detail with rounds and positions |
| `GET companies/rounds/recent/?since=YYYY-MM` | Recent priced rounds |
| `GET changes/` | Detected valuation / revenue / status / cap-table changes |
| `GET, POST watchlist/` | Per-user starred managers and companies |
| `POST import/`, `GET export/` | Snapshot in/out for the refresh job: `X-Import-Token` header or staff login |
| `GET /health/` | Railway healthcheck (public) |

## Deploy on Railway (one service)

The repo root has a `Dockerfile` and `railway.toml`, so Railway builds it with no extra settings: the React app is compiled and served by Django from the same address, with the API under `/api/v1/`.

1. On the project canvas, **+ Create → GitHub Repo → Venture-Tracker**. Leave Root Directory empty.
2. **+ Create → Database → PostgreSQL**.
3. Open the Venture-Tracker service → **Variables** → **Raw Editor**, paste and edit:
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   DJANGO_SUPERUSER_EMAIL=you@example.com
   DJANGO_SUPERUSER_PASSWORD=at-least-12-characters
   SECRET_KEY=<openssl rand -hex 32>
   IMPORT_TOKEN=<openssl rand -hex 24>
   ANTHROPIC_API_KEY=<key from console.anthropic.com>
   ```
   Only the first three are required. Without `SECRET_KEY` a stable key is derived from the database URL; without `IMPORT_TOKEN` the weekly refresh cannot push data; without `ANTHROPIC_API_KEY` the Add manager / Add company buttons are disabled.
4. **Settings → Networking → Generate Domain** (port 8000 if asked).
5. Open the domain and sign in with the superuser email and password. First boot takes 1–2 minutes: it migrates, creates the admin and loads `backend/data/tracker.json`. Add colleagues at `/admin/` → Users.

`FORCE_REIMPORT=1` for one deploy reloads `backend/data/tracker.json` over the live data. `ALLOWED_HOSTS` defaults to `.railway.app`; add your own domain there if you attach one.

**Two-service alternative:** `backend/` and `frontend/` each still have their own Dockerfile and Railway config. Set Root Directory to `/backend` and `/frontend` on two services, set `VITE_API_URL=https://<backend>/api/v1` on the frontend and `CORS_ALLOWED_ORIGINS=https://<frontend>` on the backend.

## Adding managers and companies

Analysts and admins see **+ Add manager** and **+ Add company**. The entry appears at once; a background worker (started by `start.sh`) asks Claude with web search for the same fields as the rest of the tracker and writes them in:

- **Manager:** overview, AUM, funds, check sizes, stages, focus areas, key people, team, disclosed performance, best performers, exits, LP watch items, then its portfolio (up to `RESEARCH_MAX_PORTFOLIO` new companies). Companies already tracked are linked immediately; new ones are queued and researched one by one.
- **Company:** valuation history by round, latest valuation, ARR/revenue, growth, margins, headcount, CEO, all notable investors, and positions for every tracked manager on its cap table.

Progress, errors and the actual cost of each job are under **Research** in the header (failed jobs can be retried); every profile has a **Re-research** button with its own model picker.

**Models and cost.** The Add dialog lets you pick the model for the manager profile, the model for its portfolio companies, and how many new companies to research, and shows a live estimate. Defaults: Sonnet 5.5 for a manager profile, Haiku 5.5 for the portfolio fan-out, Sonnet 5.5 for a single added company. Typical cost per run (tokens + $10 per 1,000 web searches):

| Model | Manager profile | Company |
|---|---|---|
| Haiku 5.5 | ~$0.12 | ~$0.06 |
| Sonnet 5.5 | ~$0.49 | ~$0.21 |
| Opus 5.5 | ~$0.88 | ~$0.37 |

So a manager with 25 new portfolio companies is about $2 on the defaults. Change the defaults with `RESEARCH_MODEL`, `RESEARCH_PORTFOLIO_MODEL` and `RESEARCH_COMPANY_MODEL`; the menu and its prices live in `RESEARCH_MODELS` in `backend/atlas/settings/base.py`. Actual cost is computed per API request (including Haiku's higher rate above 100K-token prompts) and stored on each job.

Rows added this way are marked `added_via=user` and are never removed by a weekly snapshot import. Viewer accounts cannot add (set the role in `/admin/`).

## Track Record tab (your own investments)

A record of where you have invested, for marketing sheets and IC packs:

- **Direct, SPV, co-investment and secondary positions:** company (pick a tracked company to fill description, sector, round, lead investors and co-investors), vehicle, round, investment date, amount, entry post-money, ownership, current value and basis, realised proceeds, follow-on / distribution cash flows, fees and carry, available capacity, status.
- **Fund commitments (L1 / L2):** GP (linked to the Managers tab), fund, vintage, commitment, called, distributed, NAV and GP-reported net TVPI / IRR / DPI.
- **Metrics** (calculated on the server, `apps/trackrecord/metrics.py`): gross and net MOIC, IRR (XIRR on dated cash flows; *n.m.* under one year), DPI, RVPI, unfunded, implied mark versus the company's latest tracked valuation; pooled across the book and by section. Net is estimated from the stated fee and carry unless GP-reported figures are entered.
- **Your view:** thesis, pros / cons / risks with high / medium / low severity, and a dated comment log on each investment. Managers get the same **Your view** panel on their profile, with your commitments to their funds.
- **View and filters:** switch between *All investments*, *Directs & co-investments* and *Funds*, then narrow by search (name, GP, lead or co-investor), structure, status and sector. The summary figures recalculate on the server for what is shown, and in the Funds view they are the fund-programme figures. The view is remembered per browser.
- **Download PDF** always produces what is on screen (same view and filters). The three sheets are: *Full track record* (All view), *Direct & co-investments* (Directs view) and *Fund programme* (Funds view) (commitments, paid-in and % called, distributed, NAV, net TVPI / DPI / RVPI / IRR, unfunded; by-vintage chart and tables, by-strategy table, fund-by-fund table, and with commentary your view on each fund and its GP). Programme, vintage and strategy IRRs are paid-in-weighted averages of fund net IRRs. Each is a navy / gold A4 landscape sheet (`apps/trackrecord/pdf.py`): summary strip, both tables, highlights, disclaimer. Tick *Include commentary* to add thesis, pros, cons, risks and comments; leave it off for external use. Title, subtitle, contact and disclaimer are under **Sheet settings**; each investment has an *Include on the marketing sheet* switch.

Everyone signed in can view and download; admins and analysts can edit. Companies and managers referenced by the track record are never removed by snapshot imports.

## Weekly refresh

A scheduled job researches new rounds, marks, market caps and manager news, then:

```bash
export ATLAS_API=https://<backend-domain>/api/v1 ATLAS_IMPORT_TOKEN=...
python3 pipeline/push_snapshot.py export data/tracker_prev.json   # what is live now
# … research writes batch files, then:
python3 pipeline/merge.py --prev data/tracker_prev.json --out site/tracker.json
python3 pipeline/push_snapshot.py import site/tracker.json        # upsert + change log
```

The importer refuses a snapshot with fewer than 70% of the live companies (pass `?force=1` to override), recomputes step-ups, valuation/revenue and entry-mark markups, and records every change in the Change Log.

## Local development

```bash
cd backend && cp .env.example .env   # set DATABASE_URL (sqlite:///db.sqlite3 works for dev), DEBUG=True
pip install -r requirements.txt
python manage.py migrate && python manage.py import_tracker data/tracker.json
python manage.py createsuperuser && python manage.py runserver
pytest -q

cd ../frontend && npm install
npm run dev   # Vite proxies /api to the Django server on :8000
```

Data notes: figures carry HARD / REPORTED / ESTIMATE labels; nulls mean unverified. Not investment advice.
