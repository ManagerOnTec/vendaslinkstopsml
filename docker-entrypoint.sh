#!/bin/bash
set -e

echo "🔄 Executando migrations..."
python manage.py migrate --no-input

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --no-input

# Debug: Verificar configuração de ALLOWED_HOSTS
echo "🔍 Configuração de ALLOWED_HOSTS:"
if [ -z "$ALLOWED_HOSTS" ]; then
    echo "   ⚠️ ALLOWED_HOSTS não definido!"
    echo "   Valor padrão será usado (vazio em produção, wildcard em DEBUG)"
else
    echo "   ✅ ALLOWED_HOSTS = $ALLOWED_HOSTS"
fi

echo "https://DEBUG configurado para: $DEBUG"
echo ""
echo "🚀 Iniciando Gunicorn..."
exec gunicorn vendaslinkstopsml.wsgi:application --bind 0.0.0.0:8080
