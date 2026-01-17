"""
主URL配置
遵循REST API最佳实践
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/projects/', include('apps.projects.urls')),
    path('api/v1/prompts/', include('apps.prompts.urls')),
    path('api/v1/models/', include('apps.models.urls')),
    path('api/v1/content/', include('apps.content.urls')),
    path('api/v1/users/', include('apps.users.urls')),
    path('api/mock/', include('apps.mock_api.urls')),
]

# 开发环境下提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
