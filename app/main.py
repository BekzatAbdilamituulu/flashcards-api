from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    auth,
    users,
    admin_languages,
    languages,
    decks,
    study,
)

app = FastAPI(title="Flashcards API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin_languages.router)
app.include_router(users.router)
app.include_router(languages.router)
app.include_router(decks.router)
app.include_router(study.router)


