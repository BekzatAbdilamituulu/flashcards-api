# Flashcards Learning API

Backend service for a flashcards learning application with spaced
repetition, per-user progress tracking, and JWT authentication.

Built with FastAPI as a production-style backend project.

------------------------------------------------------------------------

## Features

-   User registration & login (JWT Bearer)
-   Languages and words **owned by the current user** (no global data)
-   Per-user study progress
-   Smart review queue (`/study/next`)
-   Study statistics
-   Words & languages management
-   REST API with OpenAPI/Swagger
-   Automated tests with pytest
-   SQLite for development
-   Dockerized setup

------------------------------------------------------------------------

## Tech Stack

-   Python
-   FastAPI
-   SQLAlchemy
-   SQLite
-   JWT (python-jose)
-   Passlib / bcrypt
-   Pytest
-   Docker

------------------------------------------------------------------------

## Architecture

The project follows layered architecture:

    routers → services → crud → models → database

Auth is implemented via dependency injection using `get_current_user`.

Passwords are hashed. Plain text passwords are never stored.

------------------------------------------------------------------------

# 🚀 Quick Start (Docker)

The easiest way to run the project:

``` bash
docker compose up --build
```

API:

    http://127.0.0.1:8000

Swagger:

    http://127.0.0.1:8000/docs

------------------------------------------------------------------------

## Run locally without Docker

### 1. Clone repository

``` bash
git clone https://github.com/BekzatAbdilamituulu/flashcards-api.git
cd flashcards-api
```

### 2. Create virtual environment

``` bash
python -m venv venv
source venv/bin/activate  # linux/mac
venv\Scripts\activate     # windows
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

### 4. Run server

``` bash
uvicorn app.main:app --reload
```

------------------------------------------------------------------------

## Environment Variables

Create `.env` file based on `.env.example`.

Example:

    SECRET_KEY=supersecretkey
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    DATABASE_URL = "sqlite:////app/data/app.db"

------------------------------------------------------------------------

## Authentication Flow

### Register

``` http
POST /auth/register
```

``` json
{
  "username": "user1",
  "password": "12345678"
}
```

### Login

``` http
POST /auth/login
```

(form data)

Response:

``` json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

## Main Endpoints

### Languages (user-owned)
- `GET /languages` — list my languages
- `POST /languages` — create language

> Planned next: `PATCH /languages/{id}`, `DELETE /languages/{id}`

### Words (user-owned)
- `GET /words?language_id=<id>` — list words in a language
- `POST /words` — create word
- `PUT /words/{word_id}` — update word
- `DELETE /words/{word_id}` — delete word

### Study
- `GET /study/next?language_id=<id>&limit=5&random_top=3` — get next review candidate
- `POST /study/{word_id}` — submit answer and update progress  
  Body: `{"correct": true}`  
  (also supports `?correct=true/false`)

> Note: there are legacy endpoints in `study.py` marked “backward-compatible”. They should be removed or fixed (they currently reference an undefined `user_id`).

### Progress (current user)
- `GET /users/me/progress?language_id=<id>` — progress list for language
- `GET /users/me/progress/stats?language_id=<id>` — summary stats
- `DELETE /users/me/progress?language_id=<id>` — reset progress for language

## Example Study Flow

1. Register / login
2. Create language
3. Create words
4. `GET /study/next`
5. `POST /study/{word_id}` with `{"correct": true/false}`
6. View progress and stats

## Running tests

```bash
pytest
```

## Changelog

### 2026-02-09
- Refactor direction: **thin routers**, move DB logic into `crud`/`services`
- Study: unify review logic via a helper (removes duplication)
- Tests: align login tests with OAuth2 **form data** requirements
- Multi-user goal reinforced: languages/words must be **scoped to current user** (no global resources)

### 2026-02-10 — Deck system upgrade
- Added Adaptive /deck endpoint that selects study items for the authenticated user. Learning Algorithm Improvements
Introduced overdue-first selection.
Words are considered overdue based on last_review and success history.
Review intervals:
0 correct → 10 minutes
1 correct → 1 day
2 correct → 3 days
mastered (≥3) → 14 days
Overdue items are prioritized before new content.

### 2026-02-11 — Added Spaced Repetition (SM-2)
- Study answers now dynamically calculate the next appearance of a card. Difficult words return sooner, easy words move further away.
- CSV,JSON Import. Accepts UTF-8 CSV with headers:

### 2026-02-13 — Words are now created inside decks, and each deck defines a language pair.
- Words are now linked via deck_id. Source and target languages are inferred from the deck.
- Auto Translation (MyMemory). Cards can automatically receive translations.

## Author

Bekzat