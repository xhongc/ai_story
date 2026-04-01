from django.urls import path

from .views import (
    AgentSessionInitView,
    AgentSessionMessageView,
    AgentSessionStreamView,
    AgentSessionUiResultView,
    AgentSessionAbortView,
)


urlpatterns = [
    path('session/init/', AgentSessionInitView.as_view(), name='agent-session-init'),
    path('session/<str:scope_key>/message/', AgentSessionMessageView.as_view(), name='agent-session-message'),
    path('session/<str:scope_key>/stream/', AgentSessionStreamView.as_view(), name='agent-session-stream'),
    path('session/<str:scope_key>/ui-result/', AgentSessionUiResultView.as_view(), name='agent-session-ui-result'),
    path('session/<str:scope_key>/abort/', AgentSessionAbortView.as_view(), name='agent-session-abort'),
]
