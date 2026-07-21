# Production image for the Tender Monitor backend.
#
# Includes Playwright + Chromium (needed for Tier 2/3 fetch) baked in, so the
# container is self-sufficient — no "uv run playwright install" step at deploy
# time. Built with the project's real dependency manager (uv), from the same
# pyproject.toml / uv.lock used in development — no drift between dev and prod.

FROM python:3.12-slim

# Build tools for C-extension deps (argon2-cffi, lxml) + curl to fetch uv.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# Install Python deps first (separate layer — cached unless pyproject/lock change).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Playwright needs its OS-level libraries (fonts, libnss3, etc.) — --with-deps
# installs them via apt automatically for the currently-locked Playwright version.
RUN uv run playwright install --with-deps chromium

# Now the actual application code, and finish the sync (installs the project itself).
COPY . .
RUN uv sync --frozen

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# No --reload in prod. Workers=1: a single MongoDB AsyncMongoClient connection
# pool is shared correctly within one process; scale via multiple containers
# behind a proxy later if needed, not via --workers (would need per-worker Mongo
# pools and APScheduler job-store locking, out of scope tonight).
#
# Shell form so ${PORT} is expanded: PaaS hosts (Render, Railway…) inject the
# port to listen on and health-check it. Defaults to 8000 elsewhere.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
