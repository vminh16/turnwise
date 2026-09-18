# Build from the repository root: docker build -f collector/Dockerfile -t turnwise-collector .
# The root is the build context because the role-play scripts live in roleplay/.

# --- build: resolve and install dependencies into /srv/collector/.venv ----------------------
FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /bin/

# Use the base image's Python (same path in the runtime stage), copy files instead of
# hard-linking out of uv's cache, and precompile bytecode so the first request is not slow.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /srv/collector
COPY collector/pyproject.toml collector/uv.lock collector/.python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# --- runtime: no uv, no build cache, only the venv, the app and the scripts -----------------
FROM python:3.12-slim

WORKDIR /srv/collector
COPY --from=build /srv/collector/.venv ./.venv
COPY collector/app ./app
COPY roleplay /srv/roleplay

ENV PATH="/srv/collector/.venv/bin:$PATH" \
    COLLECTOR_ROLEPLAY_DIR=/srv/roleplay \
    COLLECTOR_DATA_DIR=/data \
    COLLECTOR_REQUIRE_VOLUME=1 \
    PYTHONUNBUFFERED=1

COPY --chmod=755 collector/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN useradd --create-home --uid 10001 collector && mkdir -p /data && chown collector /data
EXPOSE 8000

# The entrypoint gives /data to uid 10001 and drops root before the app starts.
# Render and Railway inject PORT. The app refuses to start unless COLLECTOR_ADMIN_TOKEN is set
# and /data is a mounted volume: run with -v <name>:/data, or attach a disk at /data.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sh", "-c", "uvicorn app.main:app_factory --factory --host 0.0.0.0 --port ${PORT:-8000}"]
