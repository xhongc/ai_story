"""提示词管理URL路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PromptTemplateSetViewSet, PromptTemplateViewSet, GlobalVariableViewSet

router = DefaultRouter()
router.register(r'sets', PromptTemplateSetViewSet, basename='prompttemplateset')
router.register(r'templates', PromptTemplateViewSet, basename='prompttemplate')
router.register(r'variables', GlobalVariableViewSet, basename='globalvariable')

urlpatterns = [
    path('', include(router.urls)),
]
