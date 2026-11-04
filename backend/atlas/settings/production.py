"""Production settings — used on Railway via DJANGO_SETTINGS_MODULE."""
from .base import *  # noqa: F401, F403

import hashlib
import logging
import os
import secrets

DEBUG = False

if SECRET_KEY.startswith('django-insecure'):  # noqa: F405
    # No SECRET_KEY variable: derive a stable key from the database credentials so every
    # gunicorn worker (and every restart) signs logins with the same key. Set SECRET_KEY in
    # Railway to replace it.
    _seed = os.environ.get('DATABASE_URL') or os.environ.get('RAILWAY_SERVICE_ID') or ''  # noqa: F405
    SECRET_KEY = hashlib.sha256(f'venture-gp-atlas:{_seed}'.encode()).hexdigest() if _seed else secrets.token_hex(32)
    logging.getLogger('apps').warning('SECRET_KEY is not set; using a key derived from DATABASE_URL.')
if not DATABASE_URL_SET:  # noqa: F405
    logging.getLogger('apps').warning('DATABASE_URL is not set; using temporary SQLite (data and users reset on every deploy).')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['.railway.app', 'localhost', '127.0.0.1'])  # noqa: F405

# Railway terminates TLS at the edge; redirecting here would break its internal healthcheck.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
