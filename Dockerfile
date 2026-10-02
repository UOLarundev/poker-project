# ---- Stage 1: build the frontend ----
# A completely different toolchain (Node) just to produce a handful of
# static HTML/CSS/JS files. Multi-stage exists exactly for this: this
# stage's base image, and everything installed into it, never appears in
# the final image below — only the compiled output (frontend/dist) does.
FROM node:22-slim AS frontend-build
WORKDIR /frontend

# Unlike the Python side below, this split genuinely works: package.json
# is a real, standalone dependency manifest that doesn't need the actual
# source tree present to resolve — so copying just the manifests first
# means `npm ci` gets its own cached layer, and only changes when a
# dependency changes, not on every source edit.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build
# Nothing API-specific baked in at build time: the frontend only ever
# calls relative /api/* paths (see frontend/src/api.ts), so there's no
# build-time environment variable to inject here for where the backend is.

# ---- Stage 2: the API, serving the built frontend alongside it ----
# Pinned to a well-supported version independent of whatever's on the dev
# laptop — what matters is that this and CI (.github/workflows/ci.yml) agree,
# since those are what actually ship. 3.12 (not the newer 3.14 used locally)
# because every dependency here already has prebuilt wheels for it.
FROM python:3.12-slim
WORKDIR /app

# Selective, not `COPY . .`: pyproject.toml's setuptools package discovery
# still needs real source directories present (same reason as before — no
# clean dependency/source cache split on the Python side), but there's no
# reason to also drag tests/, docs/, .github/, or the frontend's SOURCE
# into the production image. interface/ is included deliberately even
# though it's not in pyproject.toml's package list at all: bot_service.py
# imports from it at runtime (`from interface.cli import choose_bot_action`),
# resolved only because it's a plain directory on disk next to api/ and
# poker_engine/ at the working directory — not because it's ever installed
# as part of the distribution. Forgetting it here would ship a container
# that works until the first bot has to act.
COPY pyproject.toml alembic.ini ./
COPY api ./api
COPY poker_engine ./poker_engine
COPY interface ./interface
COPY migrations ./migrations
RUN pip install --no-cache-dir . && rm -rf build poker_engine.egg-info

# The other half of the single-container shape: the built static assets
# from stage 1, copied in — nothing from that stage's Node toolchain comes
# with them.
COPY --from=frontend-build /frontend/dist ./frontend_dist

# Runs as an unprivileged user: if the app is ever compromised, it isn't
# root inside its own container.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Migrations are NOT run here. Baking `alembic upgrade head` into container
# startup means every replica races to migrate on boot — a real failure mode
# once this runs as more than one instance. Migration is a separate,
# explicit step: `docker compose run api alembic upgrade head`. This CMD
# only ever starts the API. Binding 0.0.0.0 (not 127.0.0.1) is required —
# a container's loopback interface is invisible outside the container even
# with a port published.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
