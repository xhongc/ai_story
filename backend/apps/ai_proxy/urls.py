from django.urls import path

from .views import (
    AIModelsView,
    ChatCompletionsProxyView,
    FileUploadView,
    ImagesGenerationsProxyView,
    VideosGenerationsProxyView,
)

urlpatterns = [
    path('models', AIModelsView.as_view(), name='ai-models'),
    path('chat/completions', ChatCompletionsProxyView.as_view(), name='ai-chat-completions'),
    path('images/generations', ImagesGenerationsProxyView.as_view(), name='ai-images-generations'),
    path('videos/generations', VideosGenerationsProxyView.as_view(), name='ai-videos-generations'),
    path('files/upload', FileUploadView.as_view(), name='ai-file-upload'),
]
