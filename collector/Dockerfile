# Build from the repository root: docker build -f collector/Dockerfile -t turnwise-collector .
# The root is the build context because the role-play scripts live in roleplay/.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

WORKDIR /srv/collector
COPY collector/pyproject.toml collector/uv.lock collector/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY collector/app ./app
COPY roleplay /srv/roleplay

ENV PATH="/srv/collector/.venv/bin:$PATH" \
    COLLECTOR_ROLEPLAY_DIR=/srv/roleplay \
    COLLECTOR_DATA_DIR=/data \
    COLLECTOR_REQUIRE_VOLUME=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 collector && mkdir -p /data && chown collector /data
USER collector
EXPOSE 8000

# Railway and Render inject PORT. The app refuses to start unless COLLECTOR_ADMIN_TOKEN is set
# and /data is a mounted volume: run with -v <name>:/data, or attach a volume at /data.
CMD ["sh", "-c", "uvicorn app.main:app_factory --factory --host 0.0.0.0 --port ${PORT:-8000}"]
