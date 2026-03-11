"""项目资产上下文工具。"""

from typing import Any, Dict, List


def build_project_asset_context(project) -> Dict[str, Any]:
    """
    构建项目模板渲染所需的资产上下文。

    返回结构:
    - 顶层仍保留全局变量键，兼容现有模板
    - 额外补充 `project_assets` 与 `asset_bindings` 供画布流程和模板显式引用
    """
    from apps.prompts.models import GlobalVariable

    global_vars = GlobalVariable.get_variables_for_user(
        user=project.user,
        include_system=True,
    )

    bound_assets: List[Dict[str, Any]] = []
    project_assets: Dict[str, Any] = {}

    bindings = project.asset_bindings.select_related('asset').all()
    for binding in bindings:
        asset = binding.asset
        if not asset or not asset.is_active:
            continue

        typed_value = asset.get_typed_value()
        project_assets[asset.key] = typed_value
        bound_assets.append({
            'id': str(binding.id),
            'asset_id': str(asset.id),
            'key': asset.key,
            'group': asset.group,
            'description': asset.description,
            'variable_type': asset.variable_type,
            'scope': asset.scope,
            'typed_value': typed_value,
        })

    return {
        **global_vars,
        **project_assets,
        'project_assets': project_assets,
        'asset_bindings': bound_assets,
    }
