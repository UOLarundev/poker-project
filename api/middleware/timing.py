"""Server-side request timing — the foundation of the p95 depth point.

This is NOT about fixing bot speed (explicitly out of scope — the bot AI
stays untouched). It's purely measurement: how long does this server
actually take to answer a request, recorded as a real row per request so
an exact percentile_cont(0.95) can be computed later, not an estimate.
"""

from __future__ import annotations

import time

from starlette.background import BackgroundTask
from starlette.requests import Request

from api.db import SessionLocal
from api.models import RequestMetric


async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    # Only /api/* — serving a JS/CSS file or /docs isn't part of the
    # latency story this project is telling, and recording every static
    # asset request would just dilute the table with uninteresting noise.
    if request.url.path.startswith("/api/"):
        # scope["route"] is set by Starlette's router during call_next, on
        # the same scope dict this Request wraps — so by the time call_next
        # returns, it's populated. Using the matched route TEMPLATE
        # ("/api/hands/{hand_id}/actions"), not the raw path with a real
        # UUID in it, is what makes aggregating across many different
        # hands/games into one percentile meaningful.
        route = request.scope.get("route")
        route_path = route.path if route is not None else request.url.path
        method = request.method
        status = response.status_code

        def record() -> None:
            # Deliberately NOT written before returning the response: that
            # would make the act of measuring latency itself add latency
            # to the very request being measured. BackgroundTask runs this
            # after the response has already been sent to the client.
            with SessionLocal() as db:
                db.add(RequestMetric(route=route_path, method=method, status=status, duration_ms=duration_ms))
                db.commit()

        response.background = BackgroundTask(record)

    return response
