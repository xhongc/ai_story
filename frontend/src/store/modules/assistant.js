import agentService from '@/services/pageAgent/agentService';
import { generateLocalAssistantResponse } from '@/services/pageAgent/localAssistant';
import { pageAgentActionRegistry } from '@/services/pageAgent/actionRegistry';

const createMessage = (role, content, extra = {}) => ({
  id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
  role,
  content,
  createdAt: Date.now(),
  suggestions: [],
  ...extra,
});

const createInitialAssistantMessage = (context) => createMessage(
  'assistant',
  context?.summary || '我已经准备好读取当前页面上下文。',
  { suggestions: [] }
);

const syncSession = (state) => {
  const scopeKey = state.activeScopeKey;
  if (!scopeKey) {
    return;
  }
  state.sessions = {
    ...state.sessions,
    [scopeKey]: {
      messages: [...state.messages],
    },
  };
};

const state = {
  visible: false,
  streaming: false,
  draft: '',
  currentContext: null,
  activeScopeKey: '',
  messages: [],
  sessions: {},
  initializedScopes: {},
  requestController: null,
};

const getters = {
  visible: (state) => state.visible,
  streaming: (state) => state.streaming,
  draft: (state) => state.draft,
  currentContext: (state) => state.currentContext,
  messages: (state) => state.messages,
};

const mutations = {
  SET_VISIBLE(state, value) {
    state.visible = value;
  },
  SET_STREAMING(state, value) {
    state.streaming = value;
  },
  SET_DRAFT(state, value) {
    state.draft = value;
  },
  UPDATE_CONTEXT(state, context) {
    state.currentContext = context;
    state.activeScopeKey = context?.scopeKey || '';
  },
  SET_CONTEXT(state, context) {
    const nextScopeKey = context?.scopeKey || '';
    state.currentContext = context;
    state.activeScopeKey = nextScopeKey;

    const existingSession = nextScopeKey ? state.sessions[nextScopeKey] : null;
    if (existingSession?.messages?.length) {
      state.messages = [...existingSession.messages];
      return;
    }

    state.messages = context ? [createInitialAssistantMessage(context)] : [];
    syncSession(state);
  },
  ADD_MESSAGE(state, message) {
    state.messages = [...state.messages, message];
    syncSession(state);
  },
  REPLACE_LAST_MESSAGE(state, message) {
    if (!state.messages.length) {
      state.messages = [message];
    } else {
      state.messages = [...state.messages.slice(0, -1), message];
    }
    syncSession(state);
  },
  SET_SCOPE_INITIALIZED(state, scopeKey) {
    state.initializedScopes = {
      ...state.initializedScopes,
      [scopeKey]: true,
    };
  },
  SET_REQUEST_CONTROLLER(state, controller) {
    state.requestController = controller;
  },
};

const buildRouteParams = (context) => {
  if (context?.pageType === 'project_detail' && context?.entities?.projectId) {
    return { id: context.entities.projectId };
  }
  return {};
};

const buildUiContext = (context) => ({
  page_type: context?.pageType || 'generic',
  allowed_ui_actions: context?.capabilities || [],
  selected_storyboard_id: context?.entities?.firstStoryboardId || null,
  visible_stage: context?.entities?.processingStage || context?.entities?.failedStage || '',
  opened_panel: 'assistant',
});

const createSuggestionFromIntent = (event) => ({
  id: event.action_id || `${event.intent}-${Date.now()}`,
  action: event.intent,
  label: event.label,
  params: event.params || {},
  description: event.description || '',
  requiresConfirmation: Boolean(event.requires_confirmation),
});

const actions = {
  open({ commit }) {
    commit('SET_VISIBLE', true);
  },
  close({ commit }) {
    commit('SET_VISIBLE', false);
  },
  toggle({ commit, state }) {
    commit('SET_VISIBLE', !state.visible);
  },
  updateDraft({ commit }, value) {
    commit('SET_DRAFT', value);
  },
  async registerContext({ commit, state }, context) {
    const scopeUnchanged = state.activeScopeKey === context?.scopeKey;
    const hadSession = Boolean(context?.scopeKey && state.sessions[context.scopeKey]);

    if (scopeUnchanged && hadSession) {
      commit('UPDATE_CONTEXT', context);
    } else {
      commit('SET_CONTEXT', context);
    }

    if (context?.scopeKey && !state.initializedScopes[context.scopeKey]) {
      try {
        await agentService.initSession({
          scope_key: context.scopeKey,
          route_name: context?.meta?.routeName || '',
          route_params: buildRouteParams(context),
          ui_context: buildUiContext(context),
        });
        commit('SET_SCOPE_INITIALIZED', context.scopeKey);
      } catch (error) {
        console.error('Failed to init agent session:', error);
      }
    }
  },
  async sendMessage({ commit, state, rootGetters }, prompt) {
    const content = String(prompt || state.draft || '').trim();
    if (!content || state.streaming) {
      return;
    }

    commit('ADD_MESSAGE', createMessage('user', content));
    commit('SET_DRAFT', '');
    commit('SET_STREAMING', true);

    const pendingMessage = createMessage('assistant', '正在整理当前页面上下文...', {
      pending: true,
    });
    commit('ADD_MESSAGE', pendingMessage);

    try {
      const response = await agentService.sendMessage(state.currentContext.scopeKey, {
        text: content,
        route_name: state.currentContext?.meta?.routeName || '',
        route_params: buildRouteParams(state.currentContext),
        ui_context: buildUiContext(state.currentContext),
      });

      const controller = new AbortController();
      commit('SET_REQUEST_CONTROLLER', controller);
      let assembledText = '';
      const suggestions = [];

      await agentService.consumeStream({
        scopeKey: state.currentContext.scopeKey,
        streamToken: response.stream_token,
        accessToken: rootGetters['auth/accessToken'],
        signal: controller.signal,
        onEvent: (event) => {
          if (event.type === 'token') {
            assembledText += event.content || '';
            commit('REPLACE_LAST_MESSAGE', createMessage('assistant', assembledText || '正在生成中...', {
              pending: true,
              suggestions: [...suggestions],
            }));
          } else if (event.type === 'message') {
            assembledText = event.content || assembledText;
            commit('REPLACE_LAST_MESSAGE', createMessage('assistant', assembledText, {
              suggestions: [...suggestions],
            }));
          } else if (event.type === 'ui_intent') {
            suggestions.push(createSuggestionFromIntent(event));
            commit('REPLACE_LAST_MESSAGE', createMessage('assistant', assembledText || '我已整理出可执行动作。', {
              suggestions: [...suggestions],
            }));
          } else if (event.type === 'error') {
            throw new Error(event.message || '页面助手处理失败');
          }
        },
      });
    } catch (error) {
      console.error('Agent request failed, fallback to local responder:', error);
      try {
        const response = await generateLocalAssistantResponse({
          context: state.currentContext,
          prompt: content,
        });

        commit('REPLACE_LAST_MESSAGE', createMessage('assistant', response.content, {
          suggestions: response.suggestions || [],
        }));
      } catch (fallbackError) {
        commit('REPLACE_LAST_MESSAGE', createMessage('assistant', fallbackError.message || '页面助手处理失败，请稍后再试。'));
      }
    } finally {
      commit('SET_STREAMING', false);
      commit('SET_REQUEST_CONTROLLER', null);
    }
  },
  async executeSuggestion({ commit, state }, suggestion) {
    if (!suggestion?.action || !state.currentContext?.scopeKey) {
      return;
    }

    try {
      const result = await pageAgentActionRegistry.execute(
        state.currentContext.scopeKey,
        suggestion.action,
        suggestion.params || {}
      );

      try {
        await agentService.sendUiResult(state.currentContext.scopeKey, {
          action_id: suggestion.id,
          intent: suggestion.action,
          success: true,
          result: result || `已执行「${suggestion.label || suggestion.action}」。`,
        });
      } catch (error) {
        console.error('Failed to send ui result:', error);
      }

      commit('ADD_MESSAGE', createMessage('assistant', result || `已执行「${suggestion.label || suggestion.action}」。`));
    } catch (error) {
      commit('ADD_MESSAGE', createMessage('assistant', error.message || '执行当前页面操作失败。'));
    }
  },
  async abort({ commit, state }) {
    try {
      state.requestController?.abort();
      if (state.activeScopeKey) {
        await agentService.abort(state.activeScopeKey);
      }
    } catch (error) {
      console.error('Failed to abort agent request:', error);
    } finally {
      commit('SET_STREAMING', false);
      commit('SET_REQUEST_CONTROLLER', null);
    }
  },
};

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
};
