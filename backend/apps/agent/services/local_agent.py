import time


def _includes_any(text, keywords):
    return any(item in text for item in keywords)


def _build_ui_intent(intent, label, params=None, description='', requires_confirmation=False):
    return {
        'action_id': f'{intent}-{int(time.time() * 1000)}',
        'intent': intent,
        'label': label,
        'params': params or {},
        'description': description,
        'requires_confirmation': requires_confirmation,
    }


class LocalAgentResponder:
    def respond(self, *, user_message, context, ui_context=None, history=None):
        ui_context = ui_context or {}
        allowed = set(ui_context.get('allowed_ui_actions') or [])
        page_type = context.get('page_type')

        if page_type == 'project_detail':
            return self._respond_project_detail(user_message=user_message, context=context, allowed=allowed)

        return {
            'content': '当前页面还没有接入专用业务分析，我可以先帮助你理解页面结构和主要入口。',
            'ui_intents': [],
        }

    def _respond_project_detail(self, *, user_message, context, allowed):
        normalized = (user_message or '').strip()
        stats = context.get('stats') or {}
        entities = context.get('entities') or {}
        summary = context.get('summary') or '当前项目已加载。'

        progress_text = f"当前阶段完成度 {stats.get('completed_stages', 0)}/{stats.get('total_stages', 0)}，分镜 {stats.get('storyboard_count', 0)} 个"
        if stats.get('failed_stages'):
            progress_text += f"，失败阶段 {stats.get('failed_stages')} 个"
        if entities.get('processing_stage'):
            progress_text += f"，正在执行 {entities.get('processing_stage')}"

        if _includes_any(normalized, ['下一步', '建议', '怎么做']):
            if entities.get('project_status') == 'processing':
                content = '当前流程仍在执行，建议先观察处理中的阶段，避免重复触发。'
            elif stats.get('failed_stages', 0) > 0:
                content = '当前有失败阶段，建议先定位失败节点，再决定是局部重试还是继续微调。'
            elif stats.get('storyboard_count', 0) == 0:
                content = '分镜还未生成，建议优先推进到分镜阶段。'
            elif stats.get('camera_ready_count', 0) == 0:
                content = '已有分镜但运镜内容不足，可以先补一次运镜生成或进入微调。'
            else:
                content = '当前流程基础数据已经具备，可以继续推进视频生成，或先做局部内容优化。'
        elif _includes_any(normalized, ['分镜', '运镜', '修改', '微调']):
            content = f'{summary} {progress_text}。你可以先定位到相关区域，再进入节点微调。'
        elif _includes_any(normalized, ['运行', '暂停', '恢复']):
            content = f'{summary} {progress_text}。我已经根据当前状态整理出可执行动作。'
        else:
            content = f'{summary} {progress_text}。'

        intents = []
        if _includes_any(normalized, ['分镜', '定位']) and 'focus_stage' in allowed:
            intents.append(_build_ui_intent('focus_stage', '定位到分镜阶段', {'stageType': 'storyboard'}, '滚动到分镜区域。'))
        if _includes_any(normalized, ['微调', '修改', '优化', '分镜']) and entities.get('first_storyboard_id') and 'open_storyboard_chat' in allowed:
            intents.append(_build_ui_intent('open_storyboard_chat', '打开分镜微调助手', {'storyboardId': entities.get('first_storyboard_id')}, '直接打开第一个分镜的微调入口。', True))
        if _includes_any(normalized, ['运镜', '镜头']) and entities.get('first_camera_id') and entities.get('first_camera_storyboard_id') and 'open_camera_chat' in allowed:
            intents.append(_build_ui_intent('open_camera_chat', '打开运镜微调助手', {
                'cameraId': entities.get('first_camera_id'),
                'storyboardId': entities.get('first_camera_storyboard_id'),
            }, '打开首个可微调的运镜节点。', True))
        if _includes_any(normalized, ['运行', '开始', '执行']) and entities.get('project_status') != 'processing' and 'run_pipeline' in allowed:
            intents.append(_build_ui_intent('run_pipeline', '运行完整流程', {}, '触发当前分集的完整流程。', True))
        if _includes_any(normalized, ['暂停']) and entities.get('project_status') == 'processing' and 'pause_pipeline' in allowed:
            intents.append(_build_ui_intent('pause_pipeline', '暂停当前流程', {}, '暂停项目级流程执行。', True))
        if _includes_any(normalized, ['恢复', '继续']) and entities.get('project_status') == 'paused' and 'resume_pipeline' in allowed:
            intents.append(_build_ui_intent('resume_pipeline', '恢复当前流程', {}, '从暂停状态恢复项目流程。', True))

        if not intents and stats.get('storyboard_count', 0) > 0 and 'focus_stage' in allowed:
            intents.append(_build_ui_intent('focus_stage', '先看分镜区域', {'stageType': 'storyboard'}, '定位到当前分镜内容。'))

        return {
            'content': content,
            'ui_intents': intents[:3],
        }

    def stream_events(self, *, user_message, context, ui_context=None, history=None):
        response = self.respond(user_message=user_message, context=context, ui_context=ui_context, history=history)
        full_text = response.get('content') or ''
        yield {'type': 'connected'}
        if full_text:
            for chunk in self._chunk_text(full_text):
                yield {'type': 'token', 'content': chunk}
        yield {
            'type': 'message',
            'role': 'assistant',
            'content': full_text,
        }
        for intent in response.get('ui_intents') or []:
            yield {
                'type': 'ui_intent',
                **intent,
            }
        yield {'type': 'done'}

    def _chunk_text(self, text, size=18):
        return [text[index:index + size] for index in range(0, len(text), size)] or ['']
