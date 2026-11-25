"""秘塔 MiniMax H3 直连视频接口。"""

import requests

from core.ai_client.image2video_client import VideoGeneratorClient


class MetasoH3Client(VideoGeneratorClient):
    def create_video_task(self, prompt, model='MiniMax-H3', duration_seconds=5,
                          aspect_ratio='16:9', resolution=None, image_uri=None,
                          image_uris=None, image_base64=None, image_base64s=None,
                          image_mime_type='image/jpeg', negative_prompt=None, generate_audio=True,
                          camera_movement_description=None, **kwargs):
        quality = (resolution or '768P').upper()
        if quality not in {'480P', '768P', '1080P', '2K'}:
            raise ValueError('秘塔 H3 分辨率须为 480P、768P、1080P 或 2K')
        if not 4 <= duration_seconds <= (15 if quality == '2K' else 30):
            raise ValueError('秘塔 H3 视频时长超出该分辨率的支持范围')

        images = list(image_uris or [])
        if image_uri:
            images.insert(0, image_uri)
        encoded_images = list(image_base64s or [])
        if image_base64:
            encoded_images.insert(0, image_base64)
        image_inputs = self._build_image_inputs_for_openai_videos(images, encoded_images, image_mime_type)
        if len(image_inputs) != 1:
            raise ValueError('秘塔 H3 图生视频需要一张参考图片')

        payload = {
            'model': model,
            'content': [
                {'type': 'text', 'text': self._build_prompt_text(prompt, negative_prompt, camera_movement_description)},
                {'type': 'image_url', 'image_url': {'url': image_inputs[0]}, 'role': 'first_frame'},
            ],
            'resolution': quality,
            'duration': duration_seconds,
            'ratio': 'adaptive',
            'fast_mode': False,
        }
        if not generate_audio:
            payload['generate_audio'] = False
        response = requests.post(self.base_url, json=payload, headers=self.headers, timeout=kwargs.get('timeout', self.timeout))
        response.raise_for_status()
        return response.json()

    def _build_image_inputs_for_openai_videos(self, image_uris, resolved_image_base64s, image_mime_type):
        images = super()._build_image_inputs_for_openai_videos(image_uris, resolved_image_base64s, image_mime_type)
        for item in image_uris or []:
            url = item.get('url') if isinstance(item, dict) else item
            if url and url.startswith('/api/v1/content/storage/image/'):
                encoded = self._read_storage_image_as_base64(url)
                images.append(f'data:{image_mime_type};base64,{encoded}')
        return images

    def _build_task_status_url(self, task_id):
        return f'{self.base_url.rsplit("/", 1)[0]}/query/video_generation/{task_id}'

    def get_task_status(self, task_id):
        response = requests.get(self._build_task_status_url(task_id), headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        task = response.json().get('task')
        if not isinstance(task, dict) or not task.get('status'):
            raise ValueError('秘塔 H3 查询响应缺少 task.status')
        return task

    def _extract_video_data_from_task_result(self, task_result, task_id):
        url = (task_result.get('content') or {}).get('url')
        if not url:
            raise ValueError('秘塔 H3 任务已完成，但响应中缺少 content.url')
        return [{'url': url}]
