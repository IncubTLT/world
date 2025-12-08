#!/bin/bash

cd /app

echo "🚀 Старт entrypoint.sh"

# === Параллельная сборка статики ===
echo "🎨 Запускаем collectstatic в фоне..."
(
  attempt=1
  until python3 manage.py collectstatic --no-input; do
    if [ "$attempt" -ge 5 ]; then
      echo "❌ Превышено количество попыток collectstatic"
      break
    fi
    echo "🔄 Попытка $attempt/5: collectstatic неудачно, пробуем снова..."
    attempt=$((attempt + 1))
    sleep 5
  done
  echo "✅ Статика собрана"
) &

# === Ожидание PostgreSQL ===
# echo "⏳ Проверка готовности PostgreSQL..."
# until pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER"; do
#   echo "🔁 Ждём PostgreSQL..."
#   sleep 2
# done
# echo "✅ PostgreSQL готов"

# === Применение миграций ===
echo "🗃️ Применяем миграции Django..."
attempt=1
until python3 manage.py migrate; do
  if [ "$attempt" -ge 10 ]; then
    echo "❌ Превышено количество попыток migrate"
    exit 1
  fi
  echo "🔄 Попытка $attempt/10: база ещё не готова, пробуем снова..."
  attempt=$((attempt + 1))
  sleep 5
done
echo "✅ Миграции успешно применены"

# === Запуск Gunicorn ===
echo "🚦 Запуск Gunicorn..."
exec gunicorn -c config/entrypoints/server/prod.py config.asgi:application
