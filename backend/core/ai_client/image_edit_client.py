"""
图片编辑客户端实现
支持 OpenAI 兼容的 images/edits 或自定义 JSON 图片编辑接口
"""

import time
from urllib.parse import urlparse

import requests

from .base import ImageEditClient as BaseImageEditClient, AIResponse
from .text2image_client import Text2ImageClient


class ImageEditClient(BaseImageEditClient):
    """图片编辑客户端实现"""

    def _is_images_edits_endpoint(self, api_url: str) -> bool:
        path = urlparse(api_url).path.rstrip('/')
        return path.endswith('/images/edits')

    def _edit_image(
        self,
        image_url: str,
        prompt: str = "",
        mask_url: str = "",
        strength: float = 0.35,
        width: int = 1024,
        height: int = 1024,
        **kwargs
    ) -> AIResponse:
        request_url = self.api_url
        timeout = self.config.get('timeout', 300)
        start_time = time.time()

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        payload = {
            'model': self.model_name,
            'image_url': image_url,
            'prompt': prompt,
            'mask_url': mask_url,
            'strength': strength,
            'size': f'{width}x{height}',
            'width': width,
            'height': height,
            **kwargs,
        }

        try:
            response = requests.post(
                request_url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            if response.status_code != 200:
                return AIResponse(
                    success=False,
                    error=f'API请求失败: {response.status_code} - {response.text}'
                )

            result = response.json()
            latency_ms = int((time.time() - start_time) * 1000)

            data = result.get('data') or []
            if not isinstance(data, list):
                data = [data] if data else []

            if not data:
                content = ''
                choices = result.get('choices') or []
                if choices:
                    content = choices[0].get('message', {}).get('content', '')
                if not content:
                    return AIResponse(
                        success=False,
                        error='响应格式错误: 未从返回结果中解析到图片数据',
                    )

                fallback_config = {**self.config, 'timeout': timeout}
                fallback_client = Text2ImageClient(
                    api_url=request_url,
                    api_key=self.api_key,
                    model_name=self.model_name,
                    **fallback_config,
                )
                fallback_response = fallback_client._generate_image(
                    prompt=content,
                    width=width,
                    height=height,
                    steps=kwargs.get('steps', 20),
                )
                if fallback_response.success:
                    fallback_response.metadata = {
                        **(fallback_response.metadata or {}),
                        'source_image_url': image_url,
                        'strength': strength,
                    }
                return fallback_response

            localized_data = []
            localizer_config = {**self.config, 'timeout': timeout}
            localizer = Text2ImageClient(
                api_url=request_url,
                api_key=self.api_key,
                model_name=self.model_name,
                **localizer_config,
            )
            for item in data:
                if not isinstance(item, dict):
                    continue
                if not item.get('url') and not item.get('b64_json'):
                    continue
                localized_item = localizer._localize_image_item(item, width, height, timeout)
                localized_item['source_image_url'] = image_url
                localized_data.append(localized_item)

            if not localized_data:
                return AIResponse(
                    success=False,
                    error='响应格式错误: 未从data中解析到有效图片结果',
                )

            return AIResponse(
                success=True,
                text='\n'.join(item.get('url', '') for item in localized_data if item.get('url')),
                data=localized_data,
                metadata={
                    'latency_ms': latency_ms,
                    'model': self.model_name,
                    'request_url': request_url,
                    'source_image_url': image_url,
                    'strength': strength,
                    'usage': result.get('usage', {}),
                },
            )
        except requests.exceptions.RequestException as exc:
            return AIResponse(success=False, error=f'网络请求错误: {str(exc)}')
        except ValueError as exc:
            return AIResponse(success=False, error=f'响应解析错误: {str(exc)}')
        except Exception as exc:
            return AIResponse(success=False, error=f'未知错误: {str(exc)}')

    def validate_config(self) -> bool:
        return bool(self.api_url and self.api_key and self.model_name)
