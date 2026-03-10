"""项目管理URL路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SeriesViewSet, ProjectViewSet, ProjectStageViewSet, ProjectModelConfigViewSet
from .sse_views import (
    ProjectStageSSEView,
    ProjectAllStagesSSEView,
)

router = DefaultRouter()
router.register(r'series', SeriesViewSet, basename='series')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'stages', ProjectStageViewSet, basename='stage')
router.register(r'model-configs', ProjectModelConfigViewSet, basename='model-config')

urlpatterns = [
    path('', include(router.urls)),
    path('sse/projects/<str:project_id>/stages/<str:stage_name>/',
         ProjectStageSSEView.as_view(),
         name='project-stage-sse'),
    path('sse/projects/<str:project_id>/',
         ProjectAllStagesSSEView.as_view(),
         name='project-all-stages-sse'),
]
