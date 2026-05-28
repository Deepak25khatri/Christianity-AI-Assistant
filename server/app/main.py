"""FastAPI entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.db import init_db
from app.routes import auth as auth_routes
from app.routes import conversations as convo_routes
from app.routes import feedback as feedback_routes
from app.routes import images as image_routes
from app.routes import messages as message_routes
from app.routes import verses as verse_routes

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
log = logging.getLogger("app")

settings = get_settings()

app = FastAPI(title="Christianity AI Assistant", version="0.1.0")

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_min}/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    log.info("db initialized at %s", settings.sqlite_path)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


app.include_router(auth_routes.router)
app.include_router(convo_routes.router)
app.include_router(message_routes.router)
app.include_router(image_routes.router)
app.include_router(verse_routes.router)
app.include_router(feedback_routes.router)
