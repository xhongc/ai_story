"""URL routes for the Mock API endpoints."""

from django.urls import path

from .views import (
    MockAPIRootView,
    MockLLMGenerateView,
    MockText2ImageGenerateView,
    MockImage2VideoGenerateView,
)

app_name = 'mock_api'

urlpatterns = [
    path('', MockAPIRootView.as_view(), name='root'),
    path('llm/', MockLLMGenerateView.as_view(), name='llm_generate'),
    path('text2image/', MockText2ImageGenerateView.as_view(), name='text2image_generate'),
    path('image2video/', MockImage2VideoGenerateView.as_view(), name='image2video_generate'),
]
