from django.apps import AppConfig


class MockApiConfig(AppConfig):
    """App config for the mock API endpoints."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.mock_api'
    verbose_name = 'Mock API'
