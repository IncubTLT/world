# Backend (Django/DRF)

Skeleton для серверной части «Мир Странствий»:

- `config/` — базовые настройки Django/DRF + URL/WSGI/ASGI заготовки.
- `apps/` — доменные приложения по ТЗ: users, places, trips, reviews, messaging, social, complaints.
- `requirements.txt` — минимальные зависимости (Django, DRF, psycopg, pillow).

Быстрый старт (dev):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Проверьте DATABASES/ALLOWED_HOSTS/STATIC_ROOT/MEDIA_ROOT в `config/settings.py` перед запуском.
