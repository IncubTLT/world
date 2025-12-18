# World (Django/DRF + Next.js)

Mac/Linux–friendly стек для «Мир Странствий»: бэкенд на Django/DRF, фронт на Next.js, окружение в Docker. Минимум ручной настройки — `app.py` поднимает всё, остальное работает локально для удобного дебага.

## Что делает приложение
- **Places + GeoHub**: справочник мест, типы местности и точки покрытия с радиусами; привязка координат и медиа к любым моделям.
- **Trips**: маршруты и точки (treebeard), клонирование маршрутов, права по владельцу.
- **Reviews**: оценки 1–5, текст, до 3 медиа; сортировка по дате, средний рейтинг в карточке места; редактируют только авторы, модераторы могут скрывать.
- **Social**: подписки и лента событий (маршруты, отзывы), сортировка по дате.
- **Complaints**: жалобы на любой объект через Generic FK, роли админ/модератор/пользователь.
- **FileHub**: загрузки в S3-совместимое хранилище, привязки медиа.
- **AI**: WebSocket-чат (apps/ai).
- **Документация API**: `/api/docs` (swagger) и `/api/schema/` (OpenAPI).

## Требования
- Docker + Docker Compose
- Python 3.12+
- Node/Bun не нужны локально, если фронт гоняется в контейнере

> Команды ниже — из корня репозитория.

## Быстрый старт
1) Заполни `.env` (скопируй из `.env.example` или запусти `python3 generate_env.py` и вставь вывод). Ключевые пары: `POSTGRES_*`, `REDIS_*`, `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, `DOMAIN`, `MINIO_*`.

2) Пропиши локальные домены (Mac/Linux):
```bash
./infra/infra/debug/add_hosts.sh
```

3) Выбери сценарий запуска:

### Запуск для фронтенда (Next.js)
- Поднимаем всю инфраструктуру + фронт (hot reload внутри контейнера):
```bash
./app.py debug --mode full
```
- Доступ: фронт `http://www.localhost` (или `http://localhost:3000`), MinIO консоль `http://console.localhost`.
- API: запусти бэкенд рядом (см. ниже) или используй контейнерный, если включён.

### Запуск для бэкенда (Django/DRF локально)
1. Подними инфраструктуру без фронта (PostgreSQL, Redis, MinIO):
   ```bash
   ./app.py debug
   ```
2. Заведи venv и зависимости:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Прогони миграции (когда `./app.py debug` уже запущен):
   ```bash
   python manage.py migrate
   ```
4. Запусти сервер разработчика:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
- API: `http://localhost:8000` (Swagger `/api/docs`, OpenAPI `/api/schema/`).

### Остановка
Аккуратно гасим инфраструктуру и чистим временные данные:
```bash
./app.py stop --clean
```

### Тесты
```bash
cd backend
source .venv/bin/activate
pytest
```

## Структура
- `backend/` — Django/DRF (apps: users, filehub, geohub, places, trips, reviews, social, complaints, ai)
- `frontend/` — Next.js
- `infra/` — Docker/compose и вспомогательные скрипты
- `app.py` — единая утилита для запуска/остановки окружения

## Роли и права
- Пользователи: `user`, `moderator`, `admin` (задаются в `apps/users/models.py`).
- Владелец объекта редактирует свои сущности (места, маршруты, точки, отзывы).
- Админы/модераторы могут модерировать отзывы, жалобы и др. через API/админку.

## Полезные ссылки
- API Swagger: `http://localhost:8000/api/docs/`
- OpenAPI: `http://localhost:8000/api/schema/`
- Админка: `http://localhost:8000/admin/`

Удачной разработки! Backend и frontend комфортно работают на Mac/Linux; Windows не поддерживаем целевым образом.
