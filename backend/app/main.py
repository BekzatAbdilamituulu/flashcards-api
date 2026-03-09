import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from .config import settings
from .core.exceptions import register_exception_handlers
from .core.logging_config import setup_logging
from .core.rate_limit import limiter
from .core.request_logging import log_requests
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

setup_logging(settings.debug)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting in %s mode", settings.app_env)
    yield
    logger.info("Application shutting down")


app = FastAPI(title="Flashcards API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

register_exception_handlers(app)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts_list,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(log_requests)

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