FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY data/ data/

# Install dependencies
RUN uv sync --no-dev

ENV PYTHONPATH=/app/src
ENV PROFILES_PATH=/app/data/profiles
ENV HOOKS_PATH=/app/data/hooks.jsonl

EXPOSE 8000

CMD ["/bin/sh", "-c", "uv run uvicorn writer_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
