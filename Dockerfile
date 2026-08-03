FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.1 \
    /uv /uvx /bin/

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock .python-version ./

RUN uv sync --locked --no-dev

COPY . .

EXPOSE 5000

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-180} app:app"]

