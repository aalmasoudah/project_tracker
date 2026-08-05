FROM ghcr.io/astral-sh/uv:0.11.12@sha256:3a59a3cdd5f7c217faa36e32dbc7fddbb0412889c2a0a5229f6d790e5a019dd7 AS uv

FROM python:3.13-slim-bookworm@sha256:67a1e1f215ccda113cfc024e8639049257e88f273898f595b61476d128d387e8 AS builder

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update \
    && apt-get install --yes --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN DJANGO_SETTINGS_MODULE=config.settings.build \
    DATABASE_URL=postgresql://build:build@127.0.0.1:5432/build \
    python manage.py compilemessages \
    && DJANGO_SETTINGS_MODULE=config.settings.build \
    DATABASE_URL=postgresql://build:build@127.0.0.1:5432/build \
    python manage.py collectstatic --clear --noinput

FROM python:3.13-slim-bookworm@sha256:67a1e1f215ccda113cfc024e8639049257e88f273898f595b61476d128d387e8 AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEPLOYMENT_PROCESS_ROLE=web \
    DJANGO_SETTINGS_MODULE=config.settings.production

RUN groupadd --system insight \
    && useradd --system --gid insight --home-dir /app --shell /usr/sbin/nologin insight

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=insight:insight /app /app

USER insight
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=3).read()"]

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
