"""
Django基础配置
遵循SOLID原则,使用分层设置
"""

import os
from datetime import timedelta
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 安全配置
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = True
ALLOWED_HOSTS = []

# 应用定义
INSTALLED_APPS = [

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 第三方应用
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_celery_beat',

    # 本地应用
    'apps.projects',
    'apps.prompts',
    'apps.models',
    'apps.content',
    'apps.users',
    'apps.mock_api',
    'apps.agent',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('SQLITE_DB_PATH', str(BASE_DIR / 'data' / 'ai_story.db')),
    }
}

# 密码验证
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 国际化
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# 静态文件
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 媒体文件
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Storage文件 (用于存储生成的图片、视频等)
STORAGE_URL = 'storage/'
STORAGE_ROOT = BASE_DIR.parent / 'storage'  # 仓库根目录的storage文件夹

# 默认主键字段
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Redis配置 - 使用不同的数据库避免冲突
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Celery配置
BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'  # 数据库0: Celery任务队列
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'  # 数据库0: Celery任务队列
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'  # 数据库1: Celery结果存储
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_VISIBILITY_TIMEOUT = int(os.getenv('CELERY_BROKER_VISIBILITY_TIMEOUT', 3600 * 3))  # 3小时，需大于最长任务执行时间

# Redis Pub/Sub配置 (用于实时流式推送)
REDIS_PUBSUB_URL = os.getenv('REDIS_PUBSUB_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/2')  # 数据库2: Pub/Sub专用

# CORS配置
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = ["http://127.0.0.1:3000"]

AGENT_SERVER_BASE_URL = os.getenv('AGENT_SERVER_BASE_URL', 'http://127.0.0.1:9002').strip()
AGENT_SERVER_USERNAME = os.getenv('AGENT_SERVER_USERNAME', 'opencode').strip()
AGENT_SERVER_PASSWORD = os.getenv('AGENT_SERVER_PASSWORD', '').strip()
AGENT_MODEL_PROVIDER_ID = os.getenv('AGENT_MODEL_PROVIDER_ID', 'opencode').strip()
AGENT_MODEL_ID = os.getenv('AGENT_MODEL_ID', 'big-pickle').strip()
AGENT_MODEL_VARIANT = os.getenv('AGENT_MODEL_VARIANT', '').strip()
AGENT_REMOTE_AGENT_NAME = os.getenv('AGENT_REMOTE_AGENT_NAME', 'build').strip()
AGENT_SHOW_FREE_MODELS = os.getenv('AGENT_SHOW_FREE_MODELS', 'false').strip()
OPENCODE_CONFIG_FILE = os.getenv('OPENCODE_CONFIG_FILE', str(Path.home() / '.config' / 'opencode' / 'opencode.json')).strip()
OPENCODE_MANAGED_PROVIDER_PREFIX = os.getenv('OPENCODE_MANAGED_PROVIDER_PREFIX', 'ai_story').strip()
OPENCODE_DEFAULT_PROVIDER_NPM = os.getenv('OPENCODE_DEFAULT_PROVIDER_NPM', '@ai-sdk/openai-compatible').strip()

# JWT配置
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',
}

# 缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/4',  # 数据库4: Django缓存
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
