"""
生产环境配置
"""

from .base import *

DEBUG = False
ALLOWED_HOSTS = ['*']

# CORS配置 - 按需放开来源
CORS_ALLOW_ALL_ORIGINS = True

# 数据库 - 生产环境默认使用SQLite，可通过环境变量覆盖路径
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('SQLITE_DB_PATH', str(BASE_DIR / 'data' / 'ai_story.db')),
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
        'level': 'INFO',
    },
}
