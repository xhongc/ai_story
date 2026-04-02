from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import Mock, patch

import requests

from apps.agent.services.builtin_models import BuiltinAgentModelRegistry
from apps.agent.services.gateway import AgentGateway
from apps.models.models import ModelProvider
from apps.users.models import UserPreference


class BuiltinAgentModelRegistryTestCase(TestCase):
    @override_settings(AGENT_SHOW_FREE_MODELS='true')
    def test_list_models_returns_free_models_when_enabled(self):
        models = BuiltinAgentModelRegistry.list_models()

        self.assertTrue(models)
        self.assertIn('builtin:opencode/big-pickle', [item['id'] for item in models])

    @override_settings(AGENT_SHOW_FREE_MODELS='false')
    def test_list_models_returns_empty_when_disabled(self):
        self.assertEqual(BuiltinAgentModelRegistry.list_models(), [])


class AgentModelListViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='agent-user', password='secret123')
        self.client.force_authenticate(self.user)

    @override_settings(AGENT_SHOW_FREE_MODELS='true')
    def test_get_models_includes_builtin_free_models(self):
        response = self.client.get('/api/v1/agent/models/')

        self.assertEqual(response.status_code, 200)
        model_ids = [item['id'] for item in response.data['results']]
        self.assertIn('builtin:opencode/big-pickle', model_ids)
        self.assertIn('builtin:opencode/minimax-m2.5-free', model_ids)

    @override_settings(AGENT_SERVER_BASE_URL='http://opencode.local', AGENT_SHOW_FREE_MODELS='false')
    def test_get_models_marks_runtime_status_for_database_provider(self):
        provider = ModelProvider.objects.create(
            name='Runtime Ready',
            provider_type='llm',
            executor_class='core.ai_client.openai_client.OpenAIClient',
            api_url='https://example.com/v1/chat/completions',
            api_key='secret',
            model_name='gpt-ready',
            is_active=True,
        )

        runtime_target = AgentGateway()._resolve_model_target(str(provider.id))
        runtime_provider_map = {
            runtime_target['provider_id']: {
                'models': {
                    runtime_target['model_id']: {},
                },
            },
        }

        with patch.object(AgentGateway, 'fetch_runtime_provider_map_safe', return_value=runtime_provider_map):
            response = self.client.get('/api/v1/agent/models/')

        self.assertEqual(response.status_code, 200)
        model = response.data['results'][0]
        self.assertEqual(model['id'], str(provider.id))
        self.assertTrue(model['runtime_available'])
        self.assertEqual(model['runtime_status'], 'ready')

    @override_settings(AGENT_SERVER_BASE_URL='http://opencode.local', AGENT_SHOW_FREE_MODELS='false')
    def test_post_rejects_model_when_runtime_requires_restart(self):
        provider = ModelProvider.objects.create(
            name='Needs Restart',
            provider_type='llm',
            executor_class='core.ai_client.openai_client.OpenAIClient',
            api_url='https://example.com/v1/chat/completions',
            api_key='secret',
            model_name='gpt-restart',
            is_active=True,
        )

        with patch.object(AgentGateway, 'fetch_runtime_provider_map_safe', return_value={}):
            response = self.client.post(
                '/api/v1/agent/models/',
                {'selected_model_provider_id': str(provider.id)},
                format='json',
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn('重启 opencode serve', response.data['error'])

    @override_settings(AGENT_SHOW_FREE_MODELS='true')
    def test_post_accepts_builtin_model_selection(self):
        response = self.client.post(
            '/api/v1/agent/models/',
            {'selected_model_provider_id': 'builtin:opencode/qwen3.6-plus-free'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        preference = UserPreference.objects.get(user=self.user, key='assistant_model_provider_id')
        self.assertEqual(preference.value, 'builtin:opencode/qwen3.6-plus-free')

    @override_settings(AGENT_SHOW_FREE_MODELS='false')
    def test_post_rejects_builtin_model_selection_when_disabled(self):
        response = self.client.post(
            '/api/v1/agent/models/',
            {'selected_model_provider_id': 'builtin:opencode/qwen3.6-plus-free'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)


class AgentGatewayTestCase(TestCase):
    @override_settings(AGENT_SHOW_FREE_MODELS='true')
    def test_resolve_model_target_supports_builtin_model(self):
        gateway = AgentGateway()

        target = gateway._resolve_model_target('builtin:opencode/nemotron-3-super-free')

        self.assertEqual(target['provider_id'], 'opencode')
        self.assertEqual(target['model_id'], 'nemotron-3-super-free')
        self.assertEqual(target['variant'], '')

    @override_settings(AGENT_SERVER_BASE_URL='http://opencode.local')
    def test_get_runtime_model_status_returns_unknown_when_fetch_fails(self):
        gateway = AgentGateway()
        gateway._fetch_runtime_provider_map = Mock(side_effect=requests.RequestException('boom'))

        status = gateway.get_runtime_model_status('opencode', 'big-pickle')

        self.assertFalse(status['runtime_checked'])
        self.assertFalse(status['runtime_available'])
        self.assertEqual(status['runtime_status'], 'unknown')

    @override_settings(AGENT_REMOTE_AGENT_NAME='build')
    def test_submit_prompt_retries_without_agent_on_schema_validation_error(self):
        gateway = AgentGateway()
        client = Mock()

        error_response = Mock()
        error_response.json.return_value = {
            'error': {
                'message': 'Invalid JSON payload received. Unknown name "ref" at \'tools[0].function_declarations[0]\''
            }
        }
        http_error = requests.HTTPError(response=error_response)

        first_response = Mock()
        first_response.raise_for_status.side_effect = http_error
        second_response = Mock()
        second_response.raise_for_status.return_value = None
        client.post.side_effect = [first_response, second_response]

        gateway._submit_prompt(
            client,
            'session-1',
            'hello',
            {'page': 'project'},
            {'allowed_ui_actions': []},
        )

        self.assertEqual(client.post.call_count, 2)
        first_payload = client.post.call_args_list[0].kwargs['json']
        second_payload = client.post.call_args_list[1].kwargs['json']
        self.assertEqual(first_payload['agent'], 'build')
        self.assertNotIn('agent', second_payload)


    def test_iter_sse_events_parses_text_stream(self):
        gateway = AgentGateway()
        response = Mock()
        response.iter_lines.return_value = iter([
            'data: {"type":"server.connected","properties":{}}',
            '',
            'data: {"type":"session.idle","properties":{"sessionID":"ses_1"}}',
            '',
        ])

        events = list(gateway._iter_sse_events(response))

        self.assertEqual(events, [
            {'type': 'server.connected', 'properties': {}},
            {'type': 'session.idle', 'properties': {'sessionID': 'ses_1'}},
        ])

    def test_iter_sse_events_accepts_bytes_lines(self):
        gateway = AgentGateway()
        response = Mock()
        response.iter_lines.return_value = iter([
            b'data: {"type":"server.connected","properties":{}}',
            b'',
        ])

        events = list(gateway._iter_sse_events(response))

        self.assertEqual(events, [
            {'type': 'server.connected', 'properties': {}},
        ])

    def test_iter_sse_events_ignores_read_timeout_connection_error(self):
        gateway = AgentGateway()
        response = Mock()

        def line_iter():
            yield 'data: {"type":"server.connected","properties":{}}'
            yield ''
            raise requests.exceptions.ConnectionError('Read timed out.')

        response.iter_lines.side_effect = line_iter

        events = list(gateway._iter_sse_events(response))

        self.assertEqual(events, [
            {'type': 'server.connected', 'properties': {}},
        ])

    @override_settings(AGENT_REMOTE_AGENT_NAME='build')
    def test_submit_prompt_keeps_error_when_it_is_not_schema_related(self):
        gateway = AgentGateway()
        client = Mock()

        error_response = Mock()
        error_response.json.return_value = {'error': {'message': 'upstream timeout'}}
        http_error = requests.HTTPError(response=error_response)

        first_response = Mock()
        first_response.raise_for_status.side_effect = http_error
        client.post.return_value = first_response

        with self.assertRaises(requests.HTTPError):
            gateway._submit_prompt(
                client,
                'session-1',
                'hello',
                {'page': 'project'},
                {'allowed_ui_actions': []},
            )

        self.assertEqual(client.post.call_count, 1)
