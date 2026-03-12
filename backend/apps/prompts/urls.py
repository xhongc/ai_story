"""提示词管理URL路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PromptTemplateSetViewSet,
    PromptTemplateViewSet,
    GlobalVariableViewSet,
    PromptDebugSessionViewSet,
    PromptDebugRunViewSet,
    PromptDebugArtifactViewSet,
)

router = DefaultRouter()
router.register(r'sets', PromptTemplateSetViewSet, basename='prompttemplateset')
router.register(r'templates', PromptTemplateViewSet, basename='prompttemplate')
router.register(r'variables', GlobalVariableViewSet, basename='globalvariable')
router.register(r'debug-sessions', PromptDebugSessionViewSet, basename='promptdebugsession')
router.register(r'debug-runs', PromptDebugRunViewSet, basename='promptdebugrun')
router.register(r'debug-artifacts', PromptDebugArtifactViewSet, basename='promptdebugartifact')

urlpatterns = [
    path('', include(router.urls)),
]
