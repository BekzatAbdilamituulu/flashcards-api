# DeepLex (Backend + Frontend)

Monorepo for a reading-centered language learning app.

DeepLex helps users save words from books and texts, organize them by source, and review them through contextual study.

- `backend/`: FastAPI API + PostgreSQL + Alembic
- `frontend/`: React + Vite client

This README reflects the current project after the latest source/study/dashboard refactor pass.

## Repository Structure

- `backend/`
  - `app/` FastAPI app, routers, services, models
  - `alembic/` migrations
  - `tests/` pytest suite
  - `.github/workflows/tests.yml` backend CI workflow
- `frontend/`
  - `src/` React app (auth, onboarding, dashboard, sources, study, progress, library)

## Current Product Direction

DeepLex is no longer just a generic flashcards app.

Current architecture direction:
- **Deck** = study container
- **Source** = reading context
- **Card** = stored in a deck, optionally linked to a reading source

### Current intended model
- `main` deck = user study/review container
- `users` deck = optional personal storage/custom collection
- `library` deck = curated import source
- reading source = book/article/text context

### Important rule
Creating a **source** does **not** create a deck.

A word saved from a book should typically:
- go into the user’s `main` deck
- keep `reading_source_id` pointing to the current source

## Current Features

### Backend (FastAPI)

- JWT auth with refresh tokens:
  - register
  - login
  - Google sign-in via verified Google ID token -> DeepLex JWT exchange
  - refresh rotation
  - logout
- User profile and learning pair management:
  - default languages
  - list/add learning pairs
  - set default pair
  - update daily goals
- Language management:
  - user read-only language list
  - admin create/update/delete languages
- Deck system:
  - deck types: `main`, `users`, `library`
  - list/create/update/delete user decks (`users` decks)
  - cards CRUD + progress reset per card
- Reading sources:
  - create source
  - list sources
  - get source
  - get source cards
  - get source detail payload
  - source stats scoped to main deck cards
- Study flow:
  - get next batch
  - get deck status
  - submit answer
  - restricted to `main` decks
  - optional source-scoped study with `reading_source_id`
- Progress endpoints:
  - summary
  - daily range
  - month view
  - streak
  - today-added
  - reset my progress for a deck
- Inbox:
  - quick add word
  - bulk import with dry-run and duplicate handling
- Auto preview:
  - preview translation/example suggestions without saving
- Library marketplace:
  - list library decks/cards
  - import single or selected library cards into user main deck
  - admin create library deck
- Health endpoint

### Frontend (React + Vite)

- Auth screens (welcome/login/register) with token-based guards
- Onboarding flow for first learning pair
- Add pair flow for existing users
- Dashboard with:
  - active pair summary
  - current source widget
  - source picker modal on dashboard
  - quick add word modal with auto preview
  - all-word list with memory strength
  - incomplete reading notes section
- Sources UI:
  - `/app/sources`
  - `/app/sources/:sourceId`
  - old `/app/decks` routes redirected for compatibility
- Source detail page:
  - backend-driven source detail payload
  - source-linked word list
  - source-specific review button
  - save/edit/delete entries in source context
  - backend-provided `memory_strength` on source cards
- Study pages:
  - `/app/study`
  - `/app/study/:deckId`
  - supports source-specific study through query param filter
  - simplified 2-button review actions:
    - `I don't know`
    - `I know`
- Progress page with charting (`recharts`)
- Library UI:
  - `/app/library`
  - `/app/library/:deckId`

## Recent Fixes and Improvements

### Architecture / product cleanup
- Separated **source** and **deck** concepts more clearly
- Source routes renamed in frontend from `/app/decks` to `/app/sources`
- Added compatibility redirects from old deck routes
- Source creation confirmed to be independent from deck creation
- Source stats now count only cards in the `main` deck

### Dashboard fixes
- Fixed dashboard reading section scope issues
- Word list now shows all loaded words instead of fake `x/10` preview wording
- Current source card list behavior no longer incorrectly limits dashboard words to current source
- Current source actions simplified to:
  - Change source
  - Clear
- Change source now uses in-place modal selection instead of redirecting away
- Incomplete notes `Complete now` now opens the correct source edit flow

### Source detail fixes
- Source detail page now reads from backend source endpoints instead of frontend deck-side filtering
- Added one backend source detail payload:
  - `GET /api/v1/reading-sources/{source_id}/detail`
- Source detail review button now starts review for current source vocabulary
- Removed source detail status filter UI
- Source detail cards now include backend-computed `memory_strength`

### Study fixes
- Added source-specific study filter while still using main deck as review container
- Simplified study action buttons to two choices:
  - `I don't know`
  - `I know`

## Tech Stack

### Backend
- Python 3.11
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic v2
- python-jose + passlib/bcrypt
- httpx
- pytest

### Frontend
- React 19
- React Router
- Vite
- Tailwind CSS v4
- Axios
- Recharts

## API Base Path

All API routes are under:

`/api/v1`

## Key API Routes

### Auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/login-json`
- `POST /api/v1/auth/google`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`

### Users & Pairs
- `GET /api/v1/users/me`
- `PUT /api/v1/users/me/languages`
- `GET /api/v1/users/me/learning-pairs`
- `POST /api/v1/users/me/learning-pairs`
- `PUT /api/v1/users/me/learning-pairs/{pair_id}/default`
- `GET /api/v1/users/me/default-learning-pair`
- `PUT /api/v1/users/me/goals`

### Languages
- `GET /api/v1/languages`
- `POST /api/v1/admin/languages` (admin)
- `PATCH /api/v1/admin/languages/{language_id}` (admin)
- `DELETE /api/v1/admin/languages/{language_id}` (admin)

### Decks & Cards
- `GET /api/v1/decks`
- `POST /api/v1/decks`
- `GET /api/v1/decks/{deck_id}`
- `PATCH /api/v1/decks/{deck_id}`
- `DELETE /api/v1/decks/{deck_id}`
- `GET /api/v1/decks/{deck_id}/cards`
- `POST /api/v1/decks/{deck_id}/cards`
- `PATCH /api/v1/decks/{deck_id}/cards/{card_id}`
- `POST /api/v1/decks/{deck_id}/cards/{card_id}/reset`
- `DELETE /api/v1/decks/{deck_id}/cards/{card_id}`

### Reading Sources
- `GET /api/v1/reading-sources`
- `POST /api/v1/reading-sources`
- `GET /api/v1/reading-sources/{source_id}`
- `GET /api/v1/reading-sources/{source_id}/detail`
- `GET /api/v1/reading-sources/{source_id}/cards`

### Study & Progress
- `GET /api/v1/study/decks/{deck_id}/next`
- `GET /api/v1/study/decks/{deck_id}/status`
- `POST /api/v1/study/{card_id}`
- `GET /api/v1/progress/summary`
- `GET /api/v1/progress/daily`
- `GET /api/v1/progress/month`
- `GET /api/v1/progress/streak`
- `GET /api/v1/progress/today-added`
- `DELETE /api/v1/progress/me/progress`

### Inbox / Auto / Library
- `POST /api/v1/inbox/word`
- `POST /api/v1/inbox/bulk`
- `POST /api/v1/auto/preview`
- `GET /api/v1/library/decks`
- `GET /api/v1/library/decks/{deck_id}/cards`
- `POST /api/v1/library/cards/{card_id}/import`
- `POST /api/v1/library/decks/{deck_id}/import-selected`
- `POST /api/v1/library/admin/decks` (admin)

### Health
- `GET /api/v1/health`

## Run Locally

### 1) Backend

```bash
docker compose up -d postgres
cd backend
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Default local backend database:
- `postgresql://postgres:postgres@localhost:5432/deeplex`

The bundled Docker Compose setup also creates:
- `deeplex_test` for the backend test suite

Required backend auth env:
- `GOOGLE_CLIENT_ID` for Google sign-in

### 2) Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Typical frontend URL:
- `http://127.0.0.1:5173`

Required frontend auth env:
- `VITE_GOOGLE_CLIENT_ID` must match the Google web client configured for the frontend origin

### Google Auth API

`POST /api/v1/auth/google`

Request body:

```json
{
  "id_token": "google-id-token"
}
```

Response body matches the existing auth token payload:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

Failure cases:
- invalid or mismatched Google token
- unverified Google email
- existing DeepLex account with the same email but no Google link
- missing `GOOGLE_CLIENT_ID` server configuration

## Tests

Run backend tests:

```bash
docker compose up -d postgres
cd backend
pytest
```

## Notes

- Admin access is username-based via `ADMIN_USERNAMES` environment variable.
- The current repo is a monorepo, so CI/test workflows should run with the correct working directory instead of assuming repo root files exist.

## Deploy On Render

This repo is set up for a split Render deployment:

- backend: Render web service from `backend/`
- frontend: Render static site from `frontend/`
- database: Render Postgres, connected through `DATABASE_URL`

The repo root includes a [`render.yaml`](/home/bekzat/Desktop/cortex/render.yaml) blueprint for the backend and frontend services. It intentionally leaves secrets and environment-specific values unsynced so they can be entered in Render.

### Backend service

Root directory:
- `backend`

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
./entrypoint.sh
```

Behavior:
- binds to Render's `PORT`
- runs `alembic upgrade head` on start when `RUN_MIGRATIONS_ON_START=1`
- uses PostgreSQL through `DATABASE_URL` in every environment

Required backend env vars:
- `APP_ENV=production`
- `DEBUG=false`
- `DATABASE_URL` = Render Postgres connection string
- `SECRET_KEY` = strong random value, minimum 32 characters
- `REFRESH_SECRET_KEY` = strong random value, minimum 32 characters
- `BACKEND_CORS_ORIGINS` = frontend origin, for example `https://your-frontend.onrender.com`
- `ALLOWED_HOSTS` = backend hostnames, for example `your-api.onrender.com`
- `GOOGLE_CLIENT_ID` = Google OAuth web client ID used by the frontend

Optional backend env vars:
- `RUN_MIGRATIONS_ON_START=1`
- `MYMEMORY_DE_EMAIL`
- `ADMIN_USERNAMES`

### Frontend service

Use a Render static site.

Root directory:
- `frontend`

Build command:

```bash
npm ci && npm run build
```

Publish directory:

```bash
dist
```

Required frontend env vars:
- `VITE_API_BASE_URL` = backend public URL, for example `https://your-api.onrender.com`
- `VITE_GOOGLE_CLIENT_ID` = same Google OAuth web client ID as the backend

The static site needs an SPA rewrite from `/*` to `/index.html`. That is already included in [`render.yaml`](/home/bekzat/Desktop/cortex/render.yaml).

### Render Postgres

The included [`render.yaml`](/home/bekzat/Desktop/cortex/render.yaml) provisions a Render Postgres database and wires the backend `DATABASE_URL` from that service automatically.

The backend normalizes legacy `postgres://...` URLs to `postgresql://...` for SQLAlchemy compatibility.

### Google OAuth

To keep Google sign-in working after deployment, update the Google Cloud OAuth client configuration with:

- authorized JavaScript origin: frontend public URL
- if needed for your Google setup, the backend public URL as an allowed origin as well

Then set both:

- backend `GOOGLE_CLIENT_ID`
- frontend `VITE_GOOGLE_CLIENT_ID`

to that same web client ID.
