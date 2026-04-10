"""提示词模板 Client 参数解析与合并。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from .client_param_specs import get_stage_client_param_specs, get_stage_client_param_spec_map


def validate_stage_client_params(stage_type: str, client_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """校验并归一化模板级 Client 参数。"""
    if client_params in (None, ''):
        return {}
    if not isinstance(client_params, dict):
        raise ValueError('常量参数必须是对象格式')

    spec_map = get_stage_client_param_spec_map(stage_type)
    normalized: Dict[str, Any] = {}

    for key, raw_value in client_params.items():
        spec = spec_map.get(key)
        if not spec:
            raise ValueError(f'阶段 {stage_type} 不支持参数 "{key}"')
        normalized[key] = _coerce_value(spec, raw_value, key)

    return normalized


def resolve_stage_client_params(
    stage_type: str,
    template=None,
    provider=None,
    runtime_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """按优先级合并阶段 Client 参数。"""
    resolved: Dict[str, Any] = {}

    for spec in get_stage_client_param_specs(stage_type):
        default = spec.get('default')
        if default not in (None, ''):
            resolved[spec['key']] = deepcopy(default)

    provider_config = getattr(provider, 'extra_config', None) or {}
    _apply_known_values(resolved, stage_type, provider_config)

    template_params = getattr(template, 'client_params', None) or {}
    _apply_known_values(resolved, stage_type, template_params)

    _apply_known_values(resolved, stage_type, runtime_overrides or {})
    return resolved


def serialize_stage_client_param_schema(stage_type: str, provider=None) -> list:
    """返回前端可消费的 schema，包含 provider 默认值提示。"""
    provider_config = getattr(provider, 'extra_config', None) or {}
    schema = []

    for spec in get_stage_client_param_specs(stage_type):
        item = deepcopy(spec)
        provider_default = provider_config.get(item['key'])
        if provider_default is None and item['key'] == 'ratio':
            provider_default = provider_config.get('default_ratio') or provider_config.get('ratio')
        if provider_default is None and item['key'] == 'resolution':
            provider_default = provider_config.get('default_resolution') or provider_config.get('resolution')
        item['provider_default'] = provider_default
        schema.append(item)

    return schema


def _apply_known_values(target: Dict[str, Any], stage_type: str, values: Dict[str, Any]) -> None:
    spec_map = get_stage_client_param_spec_map(stage_type)
    for key, raw_value in values.items():
        spec = spec_map.get(key)
        if not spec or raw_value is None:
            continue
        target[key] = _coerce_value(spec, raw_value, key)

    if 'ratio' in spec_map and target.get('ratio') in (None, ''):
        ratio_alias = values.get('default_ratio') or values.get('ratio')
        if ratio_alias not in (None, ''):
            target['ratio'] = _coerce_value(spec_map['ratio'], ratio_alias, 'ratio')

    if 'resolution' in spec_map and target.get('resolution') in (None, ''):
        resolution_alias = values.get('default_resolution') or values.get('resolution')
        if resolution_alias not in (None, ''):
            target['resolution'] = _coerce_value(spec_map['resolution'], resolution_alias, 'resolution')


def _coerce_value(spec: Dict[str, Any], value: Any, key: str) -> Any:
    value_type = spec['type']

    if value_type == 'string':
        normalized = str(value)
    elif value_type == 'integer':
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'参数 "{key}" 必须是整数') from exc
    elif value_type == 'number':
        try:
            normalized = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'参数 "{key}" 必须是数字') from exc
    elif value_type == 'boolean':
        if isinstance(value, bool):
            normalized = value
        elif isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {'true', '1', 'yes', 'on'}:
                normalized = True
            elif lowered in {'false', '0', 'no', 'off'}:
                normalized = False
            else:
                raise ValueError(f'参数 "{key}" 必须是布尔值')
        else:
            normalized = bool(value)
    elif value_type == 'json':
        if not isinstance(value, dict):
            raise ValueError(f'参数 "{key}" 必须是对象')
        normalized = value
    else:
        raise ValueError(f'参数 "{key}" 的类型定义无效')

    min_value = spec.get('min')
    if min_value is not None and normalized < min_value:
        raise ValueError(f'参数 "{key}" 不能小于 {min_value}')

    max_value = spec.get('max')
    if max_value is not None and normalized > max_value:
        raise ValueError(f'参数 "{key}" 不能大于 {max_value}')

    return normalized

