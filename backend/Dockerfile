ARG PYTHON_IMAGE=python:3.13-slim

FROM ${PYTHON_IMAGE} AS builder

LABEL maintainer="Voyage contributors" \
      version="0.10.0" \
      description="Voyage — the ultimate self-hosted travel companion." \
      org.opencontainers.image.title="Voyage" \
      org.opencontainers.image.description="Voyage helps you plan, track, and share your adventures." \
      org.opencontainers.image.version="0.10.0" \
      org.opencontainers.image.authors="Voyage contributors" \
      org.opencontainers.image.source="https://github.com/Alex-Wiesner/voyage" \
      org.opencontainers.image.vendor="Voyage contributors" \
      org.opencontainers.image.licenses="GPL-3.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    VIRTUAL_ENV=/opt/venv

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libgdal-dev \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ./server/requirements.txt /tmp/requirements.txt

RUN python -m venv "$VIRTUAL_ENV" \
    && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
    && "$VIRTUAL_ENV/bin/pip" install --no-cache-dir --no-compile --prefer-binary -r /tmp/requirements.txt \
    && find "$VIRTUAL_ENV" \( -type d -name '__pycache__' -o -type d -name 'tests' \) -prune -exec rm -rf '{}' + \
    && find "$VIRTUAL_ENV" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    VIRTUAL_ENV=/opt/venv

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
      libgdal36 \
      nginx \
      memcached \
      supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY ./server /code/
COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY ./entrypoint.sh /code/entrypoint.sh

RUN chmod +x /code/entrypoint.sh \
    && mkdir -p /code/static /code/media

RUN "$VIRTUAL_ENV/bin/python" manage.py collectstatic --noinput --verbosity 2

EXPOSE 80 8000

ENTRYPOINT ["/code/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
