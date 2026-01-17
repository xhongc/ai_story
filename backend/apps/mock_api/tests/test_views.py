from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class MockAPITestCase(APITestCase):
    """Integration-style tests for the mock API HTTP endpoints."""

    def test_root_endpoint_lists_available_services(self):
        response = self.client.get(reverse('mock_api:root'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('endpoints', response.data)
        self.assertIn('llm', response.data['endpoints'])

    def test_root_endpoint_allows_post(self):
        response = self.client.post(reverse('mock_api:root'), {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('service', response.data)

    def test_llm_endpoint_returns_mock_text(self):
        response = self.client.post(
            reverse('mock_api:llm_generate'),
            {'prompt': '请改写这个故事'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertGreater(len(response.data['text']), 0)
        self.assertTrue(response.data['metadata'].get('is_mock'))

    def test_llm_endpoint_streaming_mode(self):
        response = self.client.post(
            reverse('mock_api:llm_generate'),
            {'prompt': '请改写这个故事', 'stream': True},
            format='json',
            HTTP_ACCEPT='text/event-stream',
            stream=True,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = b''.join(response.streaming_content)
        response.close()
        self.assertIn(b'data: {', content)
        self.assertIn(b'[DONE]', content)

    def test_text2image_endpoint_returns_urls(self):
        response = self.client.post(
            reverse('mock_api:text2image_generate'),
            {'prompt': 'A cute cat', 'sample_count': 2},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']['urls']), 2)
        self.assertTrue(response.data['metadata'].get('is_mock'))

    def test_image2video_endpoint_returns_video_payload(self):
        response = self.client.post(
            reverse('mock_api:image2video_generate'),
            {'image_url': 'https://example.com/sample.png'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('url', response.data['data'])
        self.assertTrue(response.data['metadata'].get('is_mock'))

    def test_missing_prompt_returns_validation_error(self):
        response = self.client.post(
            reverse('mock_api:llm_generate'),
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('error', response.data)
