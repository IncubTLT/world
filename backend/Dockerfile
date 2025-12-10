# ──────────────────────────────────────────────
# 1-й ЭТАП: собираем зависимости Python
# ──────────────────────────────────────────────
FROM python:3.12-bookworm AS builder

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential libxml2-dev libxslt1-dev zlib1g-dev \
      libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev \
      ca-certificates curl wget gnupg lsb-release && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Компилируем рядом (*.pyc) и удаляем исходники .py,
# оставляем только tasks, taskiq_app, manage.py, __init__.py, entrypoints и management/commands
RUN set -eu; \
    python -m compileall -q -j0 -b .; \
    find . -type f -name '*.py' \
      ! -name 'manage.py' \
      ! -name '__init__.py' \
      ! -name '*tasks.py' \
      ! -name 'taskiq_app.py' \
      ! -path './*/management/commands/*' \
      ! -path './*/entrypoints/*' \
      -print -delete; \
    leftover="$(find . -type f -name '*.py' \
      ! -name 'manage.py' \
      ! -name '__init__.py' \
      ! -name '*tasks.py' \
      ! -name 'taskiq_app.py' \
      ! -path './*/management/commands/*' \
      ! -path './*/entrypoints/*' \
      -print -quit)"; \
    test -z "$leftover"; \
    # убедимся, что байткод вообще есть
    test -n "$(find . -type f -name '*.pyc' -print -quit)"


# ──────────────────────────────────────────────
# 2-й ЭТАП: финальный рантайм
# ──────────────────────────────────────────────
FROM python:3.12-bookworm

# 1) переменные окружения
ENV PATH="/usr/lib/postgresql/17/bin:/root/.cargo/bin:${PATH}" \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=1 PYTHONINSPECT=0

WORKDIR /app

# 2) копируем site-packages, бинарники и код из builder
COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app             /app
COPY --from=builder /root/.cargo     /root/.cargo

# 3) системные зависимости + клиент PostgreSQL 17
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      wget gnupg lsb-release ca-certificates && \
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list && \
    wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      | gpg --dearmor -o /etc/apt/trusted.gpg.d/pgdg.gpg && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      postgresql-client-17 libpq5 \
      libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi8 \
      libjpeg62-turbo libpng16-16 shared-mime-info && \
    \
    # --- Ключевой фикс: кладём libpq.so.5 в PGDG-каталог (универсально для всех архитектур) ---
    ARCH=$(dpkg-architecture -q DEB_HOST_MULTIARCH) && \
    mkdir -p /usr/lib/postgresql/17/lib && \
    (cp /lib/${ARCH}/libpq.so.5* /usr/lib/postgresql/17/lib/ 2>/dev/null || \
     find /lib -name "libpq.so.5*" -type f -exec cp {} /usr/lib/postgresql/17/lib/ \;) && \
    (cd /usr/lib/postgresql/17/lib && \
     LIBPQ_VER=$(ls libpq.so.5.* | head -1 | sed 's/libpq.so.5\.//') && \
     ln -sf libpq.so.5.${LIBPQ_VER} libpq.so.5) && \
    \
    echo "/usr/lib/postgresql/17/lib" > /etc/ld.so.conf.d/pgdg.conf && \
    echo "/lib/${ARCH}" >> /etc/ld.so.conf.d/pgdg.conf && \
    ldconfig && \
    \
    # Чистим систему
    apt-get purge -y wget gnupg lsb-release && \
    rm -rf /var/lib/apt/lists/*

# 4) непривилегированный пользователь
RUN groupadd -r app-group && \
    useradd -r -g app-group --home-dir /home/app-user app-user && \
    mkdir -p /home/app-user/.cache && \
    chown -R app-user:app-group /app /home/app-user
USER app-user