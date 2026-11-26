"""视频生成节点执行逻辑。"""

import time
import uuid
from typing import Any, Dict

from apps.ai_proxy.views import _build_provider_payload, _ensure_list, _parse_int, _pick_provider
from apps.models.token_utils import create_ai_client_for_user

from .image_input_helpers import prepare_image_inputs_for_api
from .response_helpers import extract_video_url, normalize_video_result


DEFAULT_VIDEO_PROMPTS = {
    '生成视频',
    '图生视频',
}


def _resolve_video_prompt(input_payload: Dict[str, Any]) -> str:
    prompt = str(input_payload.get('prompt') or '').strip()
    text = str(input_payload.get('text') or '').strip()
    return f"{text}\n{prompt}"


def execute_video_generation(input_payload: Dict[str, Any], user_id=None) -> Dict[str, Any]:
    """执行视频生成节点，调用视频模型从图片生成视频。"""
    prompt = _resolve_video_prompt(input_payload)
    model = input_payload.get('model', '')
    image_inputs = _ensure_list(input_payload.get('image_urls') or input_payload.get('images') or input_payload.get('source_images'))
    image_input = input_payload.get('image_url') or input_payload.get('image')
    if image_input and image_input not in image_inputs:
        image_inputs.insert(0, image_input)
    image_base64 = input_payload.get('image_base64')
    image_base64s = _ensure_list(input_payload.get('image_base64s'))
    prepared_images = prepare_image_inputs_for_api(image_inputs, prefer_online_url=True)
    api_image_inputs = prepared_images['api_image_inputs']
    for prepared_base64 in prepared_images['image_base64s']:
        if prepared_base64 not in image_base64s:
            image_base64s.append(prepared_base64)

    provider = _pick_provider('image2video', model)
    if not provider:
        raise RuntimeError('没有可用的视频模型提供商')
    is_ucloud = getattr(provider, 'executor_class', '') == 'core.ai_client.ucloud_h3_client.UCloudH3Client'
    if not prompt.strip() and not (
        is_ucloud and (input_payload.get('content') or image_inputs or image_base64 or image_base64s)
    ):
        raise RuntimeError('prompt 不能为空')
    if not image_inputs and not image_base64 and not image_base64s and not (
        is_ucloud and (input_payload.get('content') or prompt.strip())
    ):
        raise RuntimeError('缺少可用于生成视频的图片输入')

    client = create_ai_client_for_user(provider, user_id=user_id)
    raw_result = client._generate_video(
        prompt=prompt,
        model=provider.model_name,
        image_uri=api_image_inputs[0] if api_image_inputs else '',
        image_uris=api_image_inputs,
        image_base64=image_base64,
        image_base64s=image_base64s,
        image_mime_type=input_payload.get('image_mime_type') or prepared_images['image_mime_type'] or 'image/jpeg',
        duration_seconds=_parse_int(input_payload.get('duration_seconds'), _parse_int(input_payload.get('duration'), 5)) or 5,
        sample_count=_parse_int(input_payload.get('sample_count'), _parse_int(input_payload.get('n'), 1)) or 1,
        aspect_ratio=input_payload.get('aspect_ratio') or input_payload.get('ratio') or '16:9',
        resolution=input_payload.get('resolution'),
        seed=_parse_int(input_payload.get('seed')),
        negative_prompt=input_payload.get('negative_prompt'),
        generate_audio=input_payload.get('generate_audio', True),
        camera_movement_description=(
            input_payload.get('camera_movement_description')
            or input_payload.get('cameraMovementDescription')
            or ''
        ),
        **{key: input_payload[key] for key in (
            'content', 'callback_url', 'callback_token', 'use_context_ir',
            'skill_id', 'mute_audio', 'aigc_watermark', 'idempotency_key',
        ) if key in input_payload},
    )
    result = normalize_video_result(raw_result)
    if not result['success']:
        raise RuntimeError(result['error'] or '视频生成失败')

    output_payload = {
        'id': f'vidgen-{uuid.uuid4().hex[:8]}',
        'object': 'list',
        'created': int(time.time()),
        'model': provider.model_name,
        'provider': _build_provider_payload(provider),
        'data': result['data'],
        'metadata': result['metadata'],
    }
    video_url = extract_video_url(output_payload)
    if not video_url:
        raise RuntimeError('模型未返回可用视频地址')
    delivered_resolution = result['data'][0].get('resolution') if isinstance(result['data'][0], dict) else None

    normalized_output = {
        'videoUrl': video_url,
        'video_url': video_url,
        'prompt': prompt,
        'model': model or provider.model_name,
        'duration': input_payload.get('duration') or '5s',
        'aspectRatio': input_payload.get('aspect_ratio') or input_payload.get('aspectRatio') or '16:9',
        'resolution': delivered_resolution or input_payload.get('resolution') or '720p',
        'image_urls': prepared_images['original_urls'],
        'text': input_payload.get('text') or '',
    }
    return {
        'output_payload': output_payload,
        'normalized_output': normalized_output,
    }
