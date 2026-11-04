# Venture GP Atlas

A living tracker of ~50 venture and growth managers (a16z, Sequoia, Founders Fund, Lux, DCVC, ICONIQ, Thrive, Coatue, Tiger…) and the ~900 portfolio companies they back: fund sizes, AUM, key people, disclosed performance, focus areas, and for every company its valuation history, ARR/revenue, growth, margins and full cap table of tracked managers.

Same stack and Railway layout as the Mindari / Dynamo portfolio suite:

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite, Tailwind, Zustand, React Query, Recharts (Mindari navy/gold design) |
| Backend | Django 5 + Django REST Framework + SimpleJWT |
| Database | PostgreSQL (Railway add-on) |
| Hosting | Railway: two Docker services + Postgres |

## Repository layout

```
backend/            Django API (Railway service #1)
  atlas/            project settings, urls, wsgi
  apps/users        email login, roles (admin / analyst / viewer)
  apps/managers     Manager, Fund, KeyPerson
  apps/companies    Company, ValuationRound, Position (manager ↔ company)
  apps/tracking     Snapshot (refresh log), ChangeEvent, WatchItem (per user)
  apps/importer     tracker.json import/export, management command, token-protected API
  data/tracker.json seed snapshot, loaded automatically on first deploy
frontend/           React SPA (Railway service #2), served by a dependency-free Node server
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

## Deploy on Railway

1. **New project → Deploy from GitHub repo** → pick this repo. Create **two services** from it:
   - `backend`: Settings → Root Directory `backend` (uses `backend/railway.toml` + Dockerfile).
   - `frontend`: Settings → Root Directory `frontend` (uses `frontend/railway.json` + Dockerfile).
2. **Add PostgreSQL** (New → Database → PostgreSQL).
3. **Backend variables**
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   - `SECRET_KEY` = output of `openssl rand -hex 32`
   - `ALLOWED_HOSTS` = `.railway.app`
   - `CORS_ALLOWED_ORIGINS` = the frontend URL, e.g. `https://venture-tracker-frontend.up.railway.app`
   - `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` (≥12 chars): first admin, created on boot
   - `IMPORT_TOKEN` = output of `openssl rand -hex 32` (used by the weekly refresh)
4. **Frontend variables**: `VITE_API_URL` = `https://<backend-domain>/api/v1` (build-time; redeploy after changing).
5. Generate a public domain for each service (Settings → Networking). On first boot the backend migrates, creates the admin and loads `data/tracker.json`.
6. Sign in at the frontend URL. Add colleagues at `https://<backend-domain>/admin/` → Users.

`FORCE_REIMPORT=1` on the backend for one deploy reloads `data/tracker.json` over the live data.

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
VITE_API_URL=http://localhost:8000/api/v1 npm run dev
```

Data notes: figures carry HARD / REPORTED / ESTIMATE labels; nulls mean unverified. Not investment advice.
