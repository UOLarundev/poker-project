"""Exact percentile latency stats from recorded request timings.

percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) is a real Postgres
aggregate: it computes the 95th percentile over the actual rows in
request_metrics, not an estimate interpolated from fixed buckets the way a
Prometheus-style histogram would. That only matters because there's
something to contrast it with conceptually — see docs/latency.md.

Grouped by (route, method) as well as overall: a single blended number would
hide the real story here, since different endpoints have very different
latency profiles (creating a game vs. an action that triggers several bot
decisions in one request).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

_PERCENTILE_COLUMNS = """
    count(*) AS count,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) AS p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_ms,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY duration_ms) AS p99_ms
"""


def get_metrics_summary(db: Session) -> dict:
    overall = db.execute(text(f"SELECT {_PERCENTILE_COLUMNS} FROM request_metrics")).one()

    by_route = db.execute(
        text(f"""
            SELECT route, method, {_PERCENTILE_COLUMNS}
            FROM request_metrics
            GROUP BY route, method
            ORDER BY p95_ms DESC NULLS LAST
        """)
    ).all()

    return {
        "overall": {
            "count": overall.count,
            "p50_ms": overall.p50_ms,
            "p95_ms": overall.p95_ms,
            "p99_ms": overall.p99_ms,
        },
        "by_route": [
            {
                "route": r.route,
                "method": r.method,
                "count": r.count,
                "p50_ms": r.p50_ms,
                "p95_ms": r.p95_ms,
                "p99_ms": r.p99_ms,
            }
            for r in by_route
        ],
    }
