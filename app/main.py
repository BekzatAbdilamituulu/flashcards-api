from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base
from .routers import words, languages, users, study, deck, auth, stats, import_export, plan, focus
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Flashcards API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(languages.router)
app.include_router(words.router)
app.include_router(users.router)
app.include_router(study.router)
app.include_router(deck.router)
app.include_router(stats.router)
app.include_router(import_export.router)
app.include_router(plan.router)
app.include_router(focus.router)
