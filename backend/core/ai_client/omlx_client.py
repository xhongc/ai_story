"""
oMLX 本地LLM客户端
兼容 OpenAI API 接口，支持流式生成
用于本地 Qwen3.5-9B 等模型

地址: http://192.168.1.50:8080/v1
"""

import requests
import json
import time
from typing import Dict, Any, Generator, Optional, List
from .base import LLMClient, AIResponse


class oMLXClient(LLMClient):
    """
    oMLX 本地LLM客户端
    兼容 OpenAI API 接口格式
    支持流式和非流式生成
    """

    def __init__(
        self,
        api_url: str,
        api_key: str = "local",
        model_name: str = "qwen3.5-9b",
        **kwargs
    ):
        """
        初始化 oMLX 客户端

        Args:
            api_url: API地址 (例如: http://192.168.1.50:8080/v1)
            api_key: API密钥 (oMLX通常不需要，设置默认值即可)
            model_name: 模型名称
            **kwargs: 其他配置参数
                - timeout: 超时时间 (秒)
                - system_prompt: 默认系统提示词
                - max_tokens: 最大token数
                - temperature: 温度参数
        """
        super().__init__(api_url, api_key, model_name, **kwargs)
        self.timeout = kwargs.get('timeout', 300)
        self.default_system_prompt = kwargs.get(
            'system_prompt',
            "你是一个专业的AI故事生成助手，擅长创作引人入胜的故事内容。"
        )

    async def _generate_text(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """
        生成文本 (非流式)

        Args:
            prompt: 用户提示词
            max_tokens: 最大token数
            temperature: 温度参数
            system_prompt: 系统提示词
            **kwargs: 其他参数

        Returns:
            AIResponse: 统一响应对象
        """
        start_time = time.time()

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        messages = []
        if system_prompt or self.default_system_prompt:
            messages.append({
                'role': 'system',
                'content': system_prompt or self.default_system_prompt
            })
        messages.append({'role': 'user', 'content': prompt})

        payload = {
            'model': self.model_name,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': False,
            **kwargs
        }

        try:
            response = requests.post(
                f'{self.api_url}/chat/completions',
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                result = response.json()
                return AIResponse(
                    success=True,
                    text=result['choices'][0]['message']['content'],
                    data={
                        'finish_reason': result['choices'][0].get('finish_reason'),
                    },
                    metadata={
                        'tokens_used': result.get('usage', {}).get('total_tokens', 0),
                        'latency_ms': latency_ms,
                        'model': self.model_name,
                    }
                )
            else:
                return AIResponse(
                    success=False,
                    error=f'HTTP {response.status_code}: {response.text}'
                )

        except requests.Timeout:
            return AIResponse(
                success=False,
                error=f'请求超时 (超过 {self.timeout} 秒)'
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
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式生成文本

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Yields:
            Dict包含: type (token/done/error), content, full_text, metadata
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        messages = []
        if system_prompt or self.default_system_prompt:
            messages.append({
                'role': 'system',
                'content': system_prompt or self.default_system_prompt
            })
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
            response = requests.post(
                f'{self.api_url}/chat/completions',
                headers=headers,
                json=payload,
                timeout=self.timeout,
                stream=True
            )

            if response.status_code != 200:
                yield {
                    'type': 'error',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
                return

            # 解析 SSE 流
            buffer = ''
            for chunk_bytes in response.iter_content(chunk_size=1024):
                if not chunk_bytes:
                    continue

                buffer += chunk_bytes.decode('utf-8')

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()

                    if not line or line == 'data: [DONE]':
                        continue

                    if line.startswith('data: '):
                        try:
                            json_str = line[6:]
                            chunk = json.loads(json_str)

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

                                finish_reason = chunk['choices'][0].get('finish_reason')
                                if finish_reason:
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

        except requests.Timeout:
            yield {
                'type': 'error',
                'error': f'请求超时 (超过 {self.timeout} 秒)'
            }
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

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """
        生成文本 (异步接口，兼容基类)
        """
        return await self._generate_text(prompt, max_tokens, temperature, system_prompt, **kwargs)

    def validate_config(self) -> bool:
        """
        验证配置是否有效
        """
        if not self.api_url:
            return False

        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            response = requests.get(
                f'{self.api_url}/models',
                headers=headers,
                timeout=10
            )
            return response.status_code in [200, 401, 404]
        except Exception:
            return False

    def extend_prompt(self, original_prompt: str, extra_context: str) -> str:
        """
        扩展提示词 (测试通过，成功扩展提示词)

        Args:
            original_prompt: 原始提示词
            extra_context: 额外上下文

        Returns:
            str: 扩展后的提示词
        """
        return f"{original_prompt}\n\n# 额外上下文\n{extra_context}"

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict: 服务状态信息
        """
        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            start = time.time()
            response = requests.get(
                f'{self.api_url}/models',
                headers=headers,
                timeout=5
            )
            latency_ms = int((time.time() - start) * 1000)

            if response.status_code == 200:
                models = response.json().get('data', [])
                return {
                    'status': 'healthy',
                    'latency_ms': latency_ms,
                    'models': [m.get('id') for m in models[:5]],
                    'server': self.api_url
                }
            else:
                return {
                    'status': 'unhealthy',
                    'code': response.status_code,
                    'server': self.api_url
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'server': self.api_url
            }
