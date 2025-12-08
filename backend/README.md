# Backend (Django/DRF)

Skeleton для серверной части «Мир Странствий»:

- `config/` — базовые настройки Django/DRF + URL/WSGI/ASGI заготовки.
- `apps/` — доменные приложения по ТЗ: `users`, `places`, `trips`, `reviews`, `messaging`, `social`, `complaints`.
- `requirements.txt` — минимальные зависимости (Django, DRF, psycopg, pillow).

## Требования

- Python 3.12+ (рекомендуется использовать `pyenv` или системный Python 3.x).
- PostgreSQL (рабочая БД проекта).
- Redis (для кеша/очередей, если используется).
- `virtualenv` или другой менеджер окружений.

## Структура проекта

Минимальная структура:

- `backend/`
  - `config/` — настройки Django:
    - `settings.py` — базовые настройки (DATABASES, DJANGO_ALLOWED_HOSTS, STATIC/MEDIA, DRF и т.д.).
    - `urls.py` — корневой роутинг проекта.
    - `wsgi.py` / `asgi.py` — точки входа для WSGI/ASGI.
  - `apps/`
    - `users/` — пользователи, регистрация/аутентификация, профили.
    - `places/` — места, достопримечательности, точки интереса.
    - `trips/` — маршруты, поездки, планирование путешествий.
    - `reviews/` — отзывы, оценки, комментарии к местам/поездкам.
    - `messaging/` — личные сообщения/чаты (если предусмотрено ТЗ).
    - `social/` — соц. активность, подписки, лайки, лента.
    - `complaints/` — жалобы, модерация контента.
- `manage.py` — стандартный entrypoint Django.
- `requirements.txt` — список зависимостей.
- `generate_env.py` — скрипт генерации секретных ключей для `.env`.

## Быстрый старт (dev)

### 1. Клонирование и виртуальное окружение

```bash
git clone https://github.com/IncubTLT/world.git
cd world

python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts activate
pip install -r backend/requirements.txt
```

### 2. Настройка переменных окружения

Проект ожидает `.env` в корне репозитория (там же, где лежит `manage.py` / `backend/` и `generate_env.py`).

Создайте файл `.env`:

```bash
touch .env
```

Пример содержимого `.env` (минимально необходимый набор):

```bash
PYTHONPATH=./backend

DJANGO_ALLOWED_HOSTS='localhost 127.0.0.1 192.168.0.100 dev.domain.ru'
# DOMAIN='127.0.0.1'
DOMAIN='dev.domain.ru'

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=...  # будет сгенерирован

# PostgreSQL
POSTGRES_DB=word_db
POSTGRES_USER=word_user
POSTGRES_PASSWORD=...      # будет сгенерирован или задан вручную
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

DJANGO_SECRET_KEY=...
SALT_KEY=...
CERT_PASSPHRASE=...

# MINIO
USE_S3=0
AWS_S3_USE_SSL=1
# VK_AWS
AWS_S3_REGION_NAME=ru-msk
AWS_S3_DOMAIN=hb.ru-msk.vkcloud-storage.ru
AWS_ACCESS_KEY_ID='...'
AWS_SECRET_ACCESS_KEY='...'

# email
EMAIL_HOST_USER='info@mail.ru'
EMAIL_HOST_PASSWORD='...'

```

#### Генерация секретов через `generate_env.py`

В репозитории есть скрипт `generate_env.py`, который генерирует:

- `DJANGO_SECRET_KEY`
- `SALT_KEY`
- `CERT_PASSPHRASE`
- `REDIS_PASSWORD`
- `DB_PASSWORD` (опционально, если хотите сгенерировать сложный пароль БД)

Запуск из корня проекта:

```bash
python3 ./generate_env.py
```

Скрипт выведет строки формата:

```bash
DJANGO_SECRET_KEY=...
SALT_KEY=...
CERT_PASSPHRASE=...
REDIS_PASSWORD=...
POSTGRES_PASSWORD=...
```

Дальше есть два варианта:

1. **Скопировать вручную**:  
   Скопируйте вывод в ваш `.env`, подставив вместо `...`.

2. **Автоматически дописать в `.env`** (если файл ещё пустой и вы уверены, что нет дублей ключей):

   ```bash
   python3 ./generate_env.py >> .env
   ```

> Важно: если вы уже прописали `DJANGO_SECRET_KEY`/`POSTGRES_PASSWORD`/и т.п. вручную, не дублируйте ключи. Убедитесь, что в `.env` каждая переменная определена один раз.

### 3. Проверка настроек Django

Перед запуском сервера проверьте значения в `config/settings.py`:

- `DATABASES` — должны использовать значения из `.env` (`DB_NAME`, `DB_USER`, и т.д.).
- `DJANGO_ALLOWED_HOSTS` — должны включать домены/хосты из `.env` (`DJANGO_ALLOWED_HOSTS`, `DOMAIN`).
- `STATIC_ROOT` / `MEDIA_ROOT` — корректные пути для статики и медиа в dev/prod.

### 4. Миграции и создание суперпользователя

```bash
export DJANGO_SETTINGS_MODULE=config.settings  # или через .env/pycharm
python manage.py migrate
python manage.py createsuperuser
```

Следуйте подсказкам (email/логин/пароль).

### 5. Запуск dev-сервера

```bash
./app.py debug

python manage.py runserver
```



По умолчанию сервер будет доступен по адресу:

- http://127.0.0.1:8000/

Админка Django — `/admin/` (после создания суперпользователя).

## Запуск через PYTHONPATH

Если используется явный `PYTHONPATH`:

```bash
export PYTHONPATH=./backend
export DJANGO_SETTINGS_MODULE=config.settings

./app.py debug
python manage.py migrate
python manage.py runserver
```

Убедитесь, что IDE / инструменты (например, pytest, линтеры) тоже знают о `PYTHONPATH`.

## Тесты (заготовка)

*(для заполнения)*

Рекомендуемый раздел:

```text
- tests/ или apps/*/tests.py
- как запускать тесты: pytest / manage.py test
```

Пример базовой команды (если используете pytest):

```bash
pytest ./backend
```

## Стиль кода и линтеры (заготовка)

*(для заполнения)*

Здесь стоит описать:

- Какие инструменты используются: `isort`, `flake8`
- Команды для автоформатирования и проверки:

```bash
# пример:
isort .
flake8 .
```

## API и документация (заготовка)

*(для заполнения)*

Рекомендуется описать:

- Где лежит OpenAPI/Swagger (`/api/schema/`, `/api/docs/` и т.п.).
- Базовый префикс API (например, `/api/v1/`).
- Примеры аутентификации (JWT/Session/Token).

Пример раздела:

```text
- /api/v1/auth/ — аутентификация и управление пользователями
- /api/v1/places/ — места, фильтрация, поиск, детальные карточки
- /api/v1/trips/ — маршруты, построение и сохранение поездок
- /api/v1/reviews/ — отзывы, рейтинги
```

## Доменные приложения (обзор — для будущего наполнения)

### `users`

- Регистрация, логин/логаут, восстановление пароля.
- Профиль пользователя, аватар, базовая информация.
- Социальные привязки (если есть).

### `places`

- Описание мест, фотографии, геоданные.
- Категории мест (достопримечательности, рестораны, парки и т.д.).
- Поиск/фильтрация по городу, типу, тегам.

### `trips`

- Создание и редактирование маршрутов.
- Список поездок пользователя.
- Подбор мест по маршруту.

### `reviews`

- Добавление/редактирование отзывов.
- Рейтинг мест/поездок.
- Модерация отзывов.

### `messaging`

- Личные сообщения между пользователями.
- Уведомления (опционально).

### `social`

- Подписки, лента активности.
- Лайки, сохранения, избранное.

### `complaints`

- Жалобы на контент/пользователей.
- Инструменты модерации и статусы жалоб.

> Все описания выше — заготовки: по мере развития проекта их можно детализировать под реальное ТЗ.

## Продакшн и деплой (черновик)

*(для заполнения)*

Здесь в будущем можно описать:

- Как запускать проект под gunicorn/uvicorn + nginx.
- Как подключать внешнюю БД PostgreSQL и Redis.
- Как организован сбор статики (`collectstatic`).
- Любые дополнительные сервисы (очереди, кэш, background-таски).
