from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    admin_languages,
    auth,
    auto,
    decks,
    health,
    inbox,
    languages,
    library,
    progress,
    study,
    users,
)

app = FastAPI(title="Flashcards API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_V1_PREFIX)
app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(admin_languages.router, prefix=API_V1_PREFIX)
app.include_router(users.router, prefix=API_V1_PREFIX)
app.include_router(languages.router, prefix=API_V1_PREFIX)
app.include_router(inbox.router, prefix=API_V1_PREFIX)
app.include_router(decks.router, prefix=API_V1_PREFIX)
app.include_router(study.router, prefix=API_V1_PREFIX)
app.include_router(progress.router, prefix=API_V1_PREFIX)
app.include_router(library.router, prefix=API_V1_PREFIX)
app.include_router(auto.router, prefix=API_V1_PREFIX)
