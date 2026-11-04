#!/bin/sh
# Railway startup script — same flow as Dynamo:
#   1. migrate  2. ensure superuser  3. gunicorn in background (healthcheck passes)
#   4. seed from data/tracker.json when the database is empty (or FORCE_REIMPORT=1)
#   5. wait on gunicorn

echo "=== Venture GP Atlas backend starting ==="
if [ -z "$SECRET_KEY" ] && [ -z "$DATABASE_URL" ] && [ -z "$RAILWAY_SERVICE_ID" ]; then
    # share one temporary key across all gunicorn workers in this container
    export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
fi
python -u manage.py migrate --noinput 2>&1 || echo "!!! migrate failed"

python -u manage.py shell 2>&1 << 'PYEOF'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
email, pw = os.environ.get('DJANGO_SUPERUSER_EMAIL', ''), os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
if email and pw:
    if not User.objects.filter(email=email).exists():
        User.objects.create_superuser(email=email, password=pw, full_name=os.environ.get('DJANGO_SUPERUSER_FULL_NAME', 'Admin'))
        print(f'Superuser created: {email}')
    else:
        print(f'Superuser already exists: {email}')
else:
    print('DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD not set — skipping superuser')
PYEOF

gunicorn atlas.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --threads 4 --timeout 180 \
    --access-logfile - --error-logfile - --log-level info &
GUNICORN_PID=$!
sleep 3

COUNT=$(python -u -c "
import django, os
django.setup()
from apps.companies.models import Company
print(Company.objects.count())
" 2>/dev/null || echo "0")
echo "Companies in database: $COUNT | FORCE_REIMPORT=${FORCE_REIMPORT:-0}"
if [ "$COUNT" = "0" ] || [ "${FORCE_REIMPORT:-0}" = "1" ]; then
    python -u manage.py import_tracker /app/data/tracker.json --force 2>&1 || echo "!!! seed import failed"
else
    echo "Data present — skipping seed import."
fi

wait $GUNICORN_PID
