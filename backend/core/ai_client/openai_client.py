"""
OpenAI兼容的LLM客户端实现
支持OpenAI API和兼容接口
"""

import requests
import json
import time
from typing import Dict, Any, Generator
from .base import LLMClient, AIResponse


class OpenAIClient(LLMClient):
    """
    OpenAI客户端实现
    兼容OpenAI API和类似接口
    支持流式和非流式生成
    """

    def _generate_text(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ) -> AIResponse:
        """生成文本(非流式) 废弃"""

        start_time = time.time()

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': self.model_name,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens or self.config.get("max_tokens", 4096),
            'temperature': temperature or self.config.get("temperature", 0.7),
            **kwargs
        }

        try:
            timeout = self.config.get('timeout', 60)

            response = requests.post(
                f'{self.api_url}',
                headers=headers,
                json=payload,
                timeout=timeout
            )

            if response.status_code == 200:
                result = response.json()
                latency_ms = int((time.time() - start_time) * 1000)

                return AIResponse(
                    success=True,
                    text=result['choices'][0]['message']['content'],
                    metadata={
                        'tokens_used': result.get('usage', {}).get('total_tokens', 0),
                        'latency_ms': latency_ms,
                        'model': self.model_name,
                    }
                )
            else:
                return AIResponse(
                    success=False,
                    error=f'API请求失败: {response.status_code} - {response.text}'
                )

        except requests.RequestException as e:
            return AIResponse(
                success=False,
                error=f'网络请求错误: {str(e)}'
            )
        except Exception as e:
            return AIResponse(
                success=False,
                error=f'未知错误: {str(e)}'
            )

    def generate_stream(
        self,
        prompt: str,
        system_prompt:str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式生成文本

        Args:
            prompt: 输入提示词
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Yields:
            Dict包含: type (token/done/error), content, metadata
        """

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        payload = {
            'model': self.model_name,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': True,
            **kwargs
        }

        start_time = time.time()
        full_text = ""

        try:
            timeout = self.config.get('timeout', 300)
            api_url = self.api_url
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=timeout,
                stream=True
            )

            if response.status_code != 200:
                yield {
                    'type': 'error',
                    'error': f'API请求失败: {response.status_code} - {response.text}'
                }
                return

            # 读取SSE流
            buffer = ''
            for chunk_bytes in response.iter_content(chunk_size=1024):
                if not chunk_bytes:
                    continue

                buffer += chunk_bytes.decode('utf-8')

                # 按行分割
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()

                    if not line or line == 'data: [DONE]':
                        continue

                    if line.startswith('data: '):
                        try:
                            json_str = line[6:]  # 移除 'data: ' 前缀
                            chunk = json.loads(json_str)

                            # 提取内容
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    full_text += content
                                    yield {
                                        'type': 'token',
                                        'content': content,
                                        'full_text': full_text
                                    }

                                # 检查是否结束
                                finish_reason = chunk['choices'][0].get('finish_reason')
                                if finish_reason:
                                    # 计算延迟
                                    latency_ms = int((time.time() - start_time) * 1000)

                                    yield {
                                        'type': 'done',
                                        'full_text': full_text,
                                        'metadata': {
                                            'latency_ms': latency_ms,
                                            'model': self.model_name,
                                            'finish_reason': finish_reason
                                        }
                                    }

                        except json.JSONDecodeError:
                            continue

        except requests.RequestException as e:
            yield {
                'type': 'error',
                'error': f'网络请求错误: {str(e)}'
            }
        except Exception as e:
            yield {
                'type': 'error',
                'error': f'未知错误: {str(e)}'
            }

    def validate_config(self) -> bool:
        """验证配置"""
        if not self.api_url or not self.api_key or not self.model_name:
            return False

        # 简单的连通性测试
        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            response = requests.get(
                f'{self.api_url}/models',
                headers=headers,
                timeout=10
            )
            return response.status_code in [200, 401]  # 401表示认证问题,但API可达
        except Exception:
            return False
