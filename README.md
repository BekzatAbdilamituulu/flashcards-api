# Flashcards Learning API

This app is designed to help students, solo learners, and readers learn new words easily and effectively.When you are reading a book or an article and encounter an unfamiliar word, you can quickly add it to the app. From that moment, the system takes care of the learning process for you — no need to think about how often to repeat it or when to review it.

The app helps you:
- Add new words instantly while reading
- Review words using a smart repetition system
- Track your daily progress
- Build learning streaks
- See how many words you’ve learned per day or per week

For example, you can proudly say: “I learned 100 new words this week.”

The goal is simple:
Make vocabulary learning effortless, motivating, and consistent.

------------------------------------------------------------------------

## Features

- JWT Authentication
- Deck & Card Management
- Per-User Progress Tracking
- Auto-translation(MyMemory api, for example sentence Tatoeba)
- SM-2 Spaced Repetition Algorithm
- Smart Study Queue (/study/next)
- Due / New Card Prioritization
- Multi-deck architecture
- Alembic Migrations
- Dockerized Setup
- Pytest Test Suite

------------------------------------------------------------------------
## Spaced Repetition (SM-2)

Each user has independent scheduling per card:

- status (new | learning | mastered)
- stage (1..5 when learning)
- due_at (datetime)

| Stage | Delay After Correct Answer | Description                |
| ----- | -------------------------- | -------------------------- |
| 1     | ~45 seconds                | Current session repeat     |
| 2     | +5 minutes                 | Short-term reinforcement   |
| 3     | +1 hour                    | Medium reinforcement       |
| 4     | +12 hours                  | Daily memory consolidation |
| 5     | +72 hours                  | Long-term memory check     |

- After passing Stage 5, the card becomes: status = 'mastered', due_at = None(next update to 30day)
- Wrong Answer Behavior: The card drops only one stage back, not fully reset.
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
Deck Types
The system uses a unified Deck table with 3 types

| Type      | Purpose                                                               |
| --------- | --------------------------------------------------------------------- |
| `main`    | Auto-created per language pair. **Only deck allowed for study.**      |
| `users`   | User-created collection decks. Can store cards but cannot be studied. |
| `library` | Admin-created public decks (read-only for users).                     |


Learning Model

User → Learning Pair → Main Deck → Cards → Progress

Each user:

- Has one or more learning pairs (e.g. EN → RU)
- Each pair automatically has exactly one main deck
- Study and progress tracking only operate on the main deck
- Users may create additional users decks for organization

Study Rules

- Study endpoints reject any deck where deck_type != "main"
- Cards in users decks cannot be studied
- Daily progress is calculated only for the main deck
- Study updates:
- card progress
- stage
- due_at
- daily counters (Asia/Bishkek timezone)

Progress System

- Daily progress includes:
- cards_done
- reviews_done
- new_done
- streak tracking
- Timezone: Asia/Bishkek (+06)

Security Rules

- Only users decks can be updated or deleted by user
- main decks cannot be deleted
- library decks are read-only
- Study endpoints enforce deck_type == "main"

------------------------------------------------------------------------
## Database Design (Current)

Key entities:
- User
- Language
- UserLearningPair
- Deck (main | users | library)
- Card
- UserCardProgress
- DailyProgress
- DeckAccess (role-based)
- TranslationCache
- ExampleSentenceCache

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

### 2026-02-14 — Architecture is changed to User -> Deck -> Card -> Progress per card.
- Create Patch Delet languages if only admin.(User only can get languages)
- Deck all cards in deck. Deck belongs to user(can be published, draft hidden), user can share with deck with share_code. Edit deck only (owner, editor). 

### 2026-02-23 — Learning stages

### 2026-02-26 — Major Architecture Refactor
 
- Introduced main | users | library deck types
- Study restricted to main decks only
- Users decks converted to storage/collection decks
- Removed share/publish functionality
- Progress and daily tracking bound to main deck
- Cleaned study access validation
- Fixed deck update/delete restrictions
- Enforced deck_type validation across routers


## Author

Bekzat