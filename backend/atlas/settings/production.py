"""Production settings — used on Railway via DJANGO_SETTINGS_MODULE."""
from .base import *  # noqa: F401, F403

DEBUG = False
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
