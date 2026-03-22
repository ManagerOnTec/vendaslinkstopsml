#!/bin/bash
set -e

echo "🔄 Executando migrations..."
python manage.py migrate --no-input

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --no-input

echo "🚀 Iniciando Gunicorn..."
exec gunicorn vendaslinkstopsml.wsgi:application --bind 0.0.0.0:8080
