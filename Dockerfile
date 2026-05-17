FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies first (cached unless pyproject.toml / uv.lock changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY main.py glossary.json README.md ./
COPY src/       src/
COPY static/    static/
COPY templates/ templates/

# Install the project package itself
RUN uv sync --frozen --no-dev

ENV PORT=9999

EXPOSE ${PORT}

# On Docker Desktop (macOS/Windows) host.docker.internal resolves to the host.
# On Linux pass --add-host=host.docker.internal:host-gateway to docker run,
# or override with -e OLLAMA_HOST=http://<host-ip>:11434.
ENV OLLAMA_HOST=http://host.docker.internal:11434
# Set ROOT_PATH when running behind a reverse proxy at a sub-path, e.g. ROOT_PATH=/comlab
ENV ROOT_PATH=""

# Mount the data directory to persist the DuckDB file:
#   docker run -v ./data:/app/data ...
RUN mkdir -p /app/data
CMD uv run uvicorn main:app --host 0.0.0.0 --port "${PORT}"
