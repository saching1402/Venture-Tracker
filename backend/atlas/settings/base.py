"""
Base Django settings for Venture GP Atlas.
Mirrors the Dynamo backend configuration; override in production.py.
"""
import os
from pathlib import Path
from datetime import timedelta
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me-in-production-please')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
]
LOCAL_APPS = [
    'apps.users',
    'apps.managers',
    'apps.companies',
    'apps.tracking',
    'apps.importer',
    'apps.research',
    'apps.trackrecord',
    'apps.shortlist',
    'apps.trends',
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'atlas.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'atlas.wsgi.application'

# Railway: reference the Postgres add-on (DATABASE_URL=${{Postgres.DATABASE_URL}}).
# Without it the app falls back to SQLite inside the container, which is wiped on every deploy.
DATABASE_URL_SET = bool(os.environ.get('DATABASE_URL'))
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# Unlike Dynamo's open Phase-3 setting, every data endpoint requires a signed-in user.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'atlas.pagination.AtlasPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
    'DEFAULT_THROTTLE_CLASSES': ('rest_framework.throttling.ScopedRateThrottle',),
    'DEFAULT_THROTTLE_RATES': {'login': '10/min', 'import': '20/hour'},
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:5173', 'http://localhost:3000'])
CORS_ALLOW_CREDENTIALS = True

# Auto-research (Add manager / Add company): Claude API + web search
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')
# Default models: Sonnet for a manager's own profile, Haiku (≈20x cheaper) for the portfolio fan-out
RESEARCH_MODEL = env('RESEARCH_MODEL', default='claude-sonnet-5-5')
RESEARCH_PORTFOLIO_MODEL = env('RESEARCH_PORTFOLIO_MODEL', default='claude-haiku-5-5')
RESEARCH_COMPANY_MODEL = env('RESEARCH_COMPANY_MODEL', default='claude-sonnet-5-5')
# Models offered in the Add dialog. USD per million tokens: (input, output, input above 100K-token prompts, output above).
# Update when Anthropic pricing changes; any model id here can also be set as a default above.
RESEARCH_MODELS = {
    'claude-haiku-5-5': {'label': 'Haiku 5.5 · economy', 'price': (0.10, 0.50, 0.50, 2.50)},
    'claude-sonnet-5-5': {'label': 'Sonnet 5.5 · balanced', 'price': (2.0, 10.0, 2.0, 10.0)},
    'claude-opus-5-5': {'label': 'Opus 5.5 · deepest', 'price': (4.0, 20.0, 4.0, 20.0)},
}
RESEARCH_SEARCH_PRICE = 0.01  # $10 per 1,000 web searches
RESEARCH_MAX_PORTFOLIO = env.int('RESEARCH_MAX_PORTFOLIO', default=25)  # new companies researched per added manager
RESEARCH_CONCURRENCY = env.int('RESEARCH_CONCURRENCY', default=3)

# Token the weekly refresh job sends in the X-Import-Token header (empty = import API disabled)
IMPORT_TOKEN = env('IMPORT_TOKEN', default='')
DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024  # tracker.json snapshots are ~2 MB

# Built React app (copied in by the root Dockerfile); served at / by WhiteNoise + spa_index
FRONTEND_DIST = BASE_DIR / 'frontend_dist'
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dubai'
USE_I18N = True
USE_TZ = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'verbose': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
