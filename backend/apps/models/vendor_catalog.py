"""内置模型厂商目录与模型发现工具。"""

from typing import Any, Dict


VENDOR_CATALOG: Dict[str, Dict[str, Any]] = {
    '302ai': {
        'label': '302.AI',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://api.302.ai/v1/chat/completions',
                'models_endpoint': 'https://api.302.ai/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'recommended_patterns': ['gpt', 'claude', 'gemini', 'deepseek', 'qwen', 'grok', 'llama'],
                'configurable_api_url': True,
            },
            'text2image': {
                'provider_type': 'text2image',
                'api_url': 'https://api.302.ai/302/images/generations',
                'models_endpoint': 'https://api.302.ai/v1/models',
                'executor_class': 'core.ai_client.text2image_client.Text2ImageClient',
                'recommended_patterns': ['gpt-image', 'flux', 'sdxl', 'wanx', 'imagen'],
                'configurable_api_url': True,
            },
        },
    },
    'deepseek': {
        'label': 'DeepSeek',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://api.deepseek.com/chat/completions',
                'models_endpoint': 'https://api.deepseek.com/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'model_filter': ['deepseek'],
                'recommended_patterns': ['deepseek-chat', 'deepseek-reasoner'],
                'configurable_api_url': True,
            },
        },
    },
    'volcengine': {
        'label': '火山引擎',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
                'models_endpoint': 'https://ark.cn-beijing.volces.com/api/v3/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'recommended_patterns': ['doubao', 'deepseek', 'seed'],
                'configurable_api_url': True,
            },
            'text2image': {
                'provider_type': 'text2image',
                'api_url': 'https://ark.cn-beijing.volces.com/api/v3/images/generations',
                'models_endpoint': 'https://ark.cn-beijing.volces.com/api/v3/models',
                'executor_class': 'core.ai_client.text2image_client.Text2ImageClient',
                'recommended_patterns': ['seedream', 'doubao'],
                'configurable_api_url': True,
            },
            'image_edit': {
                'provider_type': 'image_edit',
                'api_url': 'https://ark.cn-beijing.volces.com/api/v3/images/edits',
                'models_endpoint': 'https://ark.cn-beijing.volces.com/api/v3/models',
                'executor_class': 'core.ai_client.image_edit_client.ImageEditClient',
                'model_filter': ['edit'],
                'recommended_patterns': ['edit'],
                'configurable_api_url': True,
            },
            'image2video': {
                'provider_type': 'image2video',
                'api_url': 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
                'models_endpoint': 'https://ark.cn-beijing.volces.com/api/v3/models',
                'executor_class': 'core.ai_client.volcengine_image2video_client.VolcengineImage2VideoClient',
                'model_filter': ['video', 'seedance'],
                'recommended_patterns': ['seedance', 'video'],
                'configurable_api_url': True,
            },
        },
    },
    'dashscope': {
        'label': '阿里云百炼',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
                'models_endpoint': 'https://dashscope.aliyuncs.com/compatible-mode/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'model_filter': ['qwen'],
                'recommended_patterns': ['qwen-plus', 'qwen-max', 'qwen-turbo'],
                'configurable_api_url': True,
            },
            'text2image': {
                'provider_type': 'text2image',
                'api_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/images/generations',
                'models_endpoint': 'https://dashscope.aliyuncs.com/compatible-mode/v1/models',
                'executor_class': 'core.ai_client.text2image_client.Text2ImageClient',
                'recommended_patterns': ['wanx', 'image'],
                'configurable_api_url': True,
            },
        },
    },
    'modelscope': {
        'label': 'ModelScope',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://api-inference.modelscope.cn/v1/chat/completions',
                'models_endpoint': 'https://api-inference.modelscope.cn/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'recommended_patterns': ['qwen', 'deepseek', 'glm', 'llama', 'kimi'],
                'configurable_api_url': True,
            },
        },
    },
    'newapi': {
        'label': 'New API 网关',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://your-newapi-server-address/v1/chat/completions',
                'models_endpoint': 'https://your-newapi-server-address/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'recommended_patterns': [],
                'configurable_api_url': True,
            },
            'text2image': {
                'provider_type': 'text2image',
                'api_url': 'https://your-newapi-server-address/v1/images/generations',
                'models_endpoint': 'https://your-newapi-server-address/v1/models',
                'executor_class': 'core.ai_client.text2image_client.Text2ImageClient',
                'recommended_patterns': ['flux', 'sdxl', 'wanx', 'gpt-image'],
                'configurable_api_url': True,
            },
            'image2video': {
                'provider_type': 'image2video',
                'api_url': 'https://your-newapi-server-address/v1/videos/generations',
                'models_endpoint': 'https://your-newapi-server-address/v1/models',
                'executor_class': 'core.ai_client.image2video_client.VideoGeneratorClient',
                'recommended_patterns': ['veo', 'kling', 'wan', 'seedance'],
                'configurable_api_url': True,
            },
        },
    },
    'openai': {
        'label': 'OpenAI',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://api.openai.com/v1/chat/completions',
                'models_endpoint': 'https://api.openai.com/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'model_filter': ['gpt', 'o1', 'o3', 'o4'],
                'recommended_patterns': ['gpt-4.1', 'gpt-4o', 'o3', 'o1'],
                'configurable_api_url': True,
            },
            'text2image': {
                'provider_type': 'text2image',
                'api_url': 'https://api.openai.com/v1/images/generations',
                'models_endpoint': 'https://api.openai.com/v1/models',
                'executor_class': 'core.ai_client.text2image_client.Text2ImageClient',
                'model_filter': ['gpt-image', 'dall-e'],
                'recommended_patterns': ['gpt-image-1', 'dall-e-3'],
                'configurable_api_url': True,
            },
            'image_edit': {
                'provider_type': 'image_edit',
                'api_url': 'https://api.openai.com/v1/images/edits',
                'models_endpoint': 'https://api.openai.com/v1/models',
                'executor_class': 'core.ai_client.image_edit_client.ImageEditClient',
                'model_filter': ['gpt-image', 'dall-e'],
                'recommended_patterns': ['gpt-image-1'],
                'configurable_api_url': True,
            },
        },
    },
    'gemini': {
        'label': 'Gemini',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
                'models_endpoint': 'https://generativelanguage.googleapis.com/v1beta/openai/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'model_filter': ['gemini'],
                'recommended_patterns': ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-1.5-pro'],
                'configurable_api_url': True,
            },
            'text2image': {
                'provider_type': 'text2image',
                'api_url': 'https://generativelanguage.googleapis.com/v1beta/openai/images/generations',
                'models_endpoint': 'https://generativelanguage.googleapis.com/v1beta/openai/models',
                'executor_class': 'core.ai_client.text2image_client.Text2ImageClient',
                'model_filter': ['imagen', 'gemini'],
                'recommended_patterns': ['imagen-3'],
                'configurable_api_url': True,
            },
            'image2video': {
                'provider_type': 'image2video',
                'api_url': 'https://generativelanguage.googleapis.com/v1beta/openai/videos/generations',
                'models_endpoint': 'https://generativelanguage.googleapis.com/v1beta/openai/models',
                'executor_class': 'core.ai_client.image2video_client.VideoGeneratorClient',
                'model_filter': ['veo', 'gemini'],
                'recommended_patterns': ['veo-3', 'veo-2'],
                'configurable_api_url': True,
            },
        },
    },
    'grok': {
        'label': 'Grok',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://api.x.ai/v1/chat/completions',
                'models_endpoint': 'https://api.x.ai/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'model_filter': ['grok'],
                'recommended_patterns': ['grok-2', 'grok-beta'],
                'configurable_api_url': True,
            },
        },
    },
    'minimax': {
        'label': 'MiniMax',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://api.minimax.chat/v1/text/chatcompletion_v2',
                'models_endpoint': 'https://api.minimax.chat/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'model_filter': ['minimax', 'abab'],
                'recommended_patterns': ['minimax', 'abab'],
                'configurable_api_url': True,
            },
        },
    },
    'siliconflow': {
        'label': '硅基流动',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://api.siliconflow.cn/v1/chat/completions',
                'models_endpoint': 'https://api.siliconflow.cn/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'recommended_patterns': ['deepseek', 'qwen', 'glm', 'kimi'],
                'configurable_api_url': True,
            },
        },
    },
    'openrouter': {
        'label': 'OpenRouter',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://openrouter.ai/api/v1/chat/completions',
                'models_endpoint': 'https://openrouter.ai/api/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'recommended_patterns': ['grok', 'deepseek', 'qwen', 'claude', 'gemini'],
                'configurable_api_url': True,
            },
        },
    },
    'zhipu': {
        'label': '智谱 AI',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                'models_endpoint': 'https://open.bigmodel.cn/api/paas/v4/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'model_filter': ['glm'],
                'recommended_patterns': ['glm-4', 'glm-4.5'],
                'configurable_api_url': True,
            },
        },
    },
    'moonshot': {
        'label': 'Moonshot',
        'capabilities': {
            'llm': {
                'provider_type': 'llm',
                'api_url': 'https://api.moonshot.cn/v1/chat/completions',
                'models_endpoint': 'https://api.moonshot.cn/v1/models',
                'executor_class': 'core.ai_client.openai_client.OpenAIClient',
                'model_filter': ['moonshot', 'kimi'],
                'recommended_patterns': ['moonshot-v1', 'kimi'],
                'configurable_api_url': True,
            },
        },
    },
}
