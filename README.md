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
   ```
   Only the first three are required. Without `SECRET_KEY` a stable key is derived from the database URL; without `IMPORT_TOKEN` the weekly refresh cannot push data.
4. **Settings → Networking → Generate Domain** (port 8000 if asked).
5. Open the domain and sign in with the superuser email and password. First boot takes 1–2 minutes: it migrates, creates the admin and loads `backend/data/tracker.json`. Add colleagues at `/admin/` → Users.

`FORCE_REIMPORT=1` for one deploy reloads `backend/data/tracker.json` over the live data. `ALLOWED_HOSTS` defaults to `.railway.app`; add your own domain there if you attach one.

**Two-service alternative:** `backend/` and `frontend/` each still have their own Dockerfile and Railway config. Set Root Directory to `/backend` and `/frontend` on two services, set `VITE_API_URL=https://<backend>/api/v1` on the frontend and `CORS_ALLOWED_ORIGINS=https://<frontend>` on the backend.

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
