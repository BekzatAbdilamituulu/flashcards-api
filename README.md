# Flashcards Learning API

Backend service for a flashcards learning application with spaced
repetition, per-user progress tracking, and JWT authentication.

Built with FastAPI as a production-style backend project.

------------------------------------------------------------------------

## Features

-   User registration & login
-   JWT authentication (Bearer tokens)
-   Per-user study progress
-   Smart review queue
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

### Use token

Send header:

    Authorization: Bearer <token>

------------------------------------------------------------------------

## Example Study Flow

1.  Create language\
2.  Create words\
3.  Get review queue\
4.  Submit answer\
5.  Track progress & statistics

All operations are user-scoped via JWT.

------------------------------------------------------------------------

## Running tests

``` bash
pytest
```

Tests use a separate database and override dependencies.

------------------------------------------------------------------------

## Future Improvements

-   Refresh tokens
-   Deck sharing
-   Multiplayer rooms
-   Advanced spaced repetition algorithms
-   Background tasks
-   Caching

------------------------------------------------------------------------

## Project Goal

This project is part of my backend engineering portfolio.\
The focus is on:

-   clean architecture
-   authentication & security
-   correct data ownership
-   realistic API design
-   testability

------------------------------------------------------------------------

## Author

Bekzat
