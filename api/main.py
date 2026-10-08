from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.db import get_db
from api.middleware.timing import timing_middleware
from api.routes import actions, games, history, metrics

app = FastAPI(title="Poker API")
app.middleware("http")(timing_middleware)

# /api/* and FastAPI's own built-in routes (/docs, /openapi.json — added by
# FastAPI() above, before any of this runs) always take priority: Starlette
# matches routes in registration order, so these have to be included BEFORE
# the catch-all static mount below. Mounting it first would shadow every
# API route with "does this path exist as a file" instead.
app.include_router(games.router)
app.include_router(actions.router)
app.include_router(history.router)
app.include_router(metrics.router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Used as the deploy platform's health-check target (see render.yaml
    and fly.toml). Deliberately
    touches the database with a trivial query rather than just returning
    200 unconditionally — "the process is running" and "the configured
    DATABASE_URL actually works" are different claims, and the second one
    is exactly what's most likely to be wrong on a fresh deploy pointed at
    a new database."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

# Only present inside the built Docker image (see Dockerfile's frontend
# build stage) — absent when running the API bare-metal against a
# separately-running Vite dev server, which is how local frontend
# development actually happens. Checking first means that workflow keeps
# working without this crashing on a missing directory.
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend_dist"
if _frontend_dist.is_dir():
    # html=True: serves index.html for "/" (and would for any directory
    # path) — sufficient because this SPA has exactly one real URL and
    # toggles screens via React state, not client-side routing, so there's
    # no need for a "fall back to index.html for any unmatched path" rule.
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
