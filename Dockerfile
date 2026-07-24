FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest \
    /uv /uvx /bin/

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock .python-version ./

RUN uv sync --locked --no-dev

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]