# Pinned to a well-supported version independent of whatever's on the dev
# laptop — what matters is that this and CI (.github/workflows/ci.yml) agree,
# since those are what actually ship. 3.12 (not the newer 3.14 used locally)
# because every dependency here already has prebuilt wheels for it.
FROM python:3.12-slim

WORKDIR /app

# One layer, no dependency/source split: this project resolves dependencies
# through pyproject.toml + setuptools package discovery, which needs the
# real api/ and poker_engine/ directories present to even read the package
# list. Faking the usual "copy manifest, install, then copy source" caching
# trick would mean a second, duplicated dependency list (e.g. a parallel
# requirements.txt) — worse than a slower rebuild.
COPY . .
RUN pip install --no-cache-dir .

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
