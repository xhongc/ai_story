"""
开发环境配置
"""

from .base import *

DEBUG = False
ALLOWED_HOSTS = ['*']

# CORS配置 - 开发环境允许所有源
CORS_ALLOW_ALL_ORIGINS = True

# 数据库 - 开发环境使用SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}