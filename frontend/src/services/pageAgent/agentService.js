import agentApi from '@/api/agent';


const parseSSEStream = async (response, onEvent) => {
  if (!response.ok || !response.body) {
    throw new Error('页面助手流连接失败');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let finished = false;

  while (!finished) {
    const { value, done } = await reader.read();
    if (done) {
      finished = true;
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop() || '';

    chunks.forEach((chunk) => {
      const line = chunk.split('\n').find((item) => item.startsWith('data: '));
      if (!line) {
        return;
      }
      try {
        onEvent(JSON.parse(line.slice(6)));
      } catch (error) {
        console.error('Failed to parse page agent event:', error);
      }
    });
  }
};


export default {
  initSession(payload) {
    return agentApi.initSession(payload);
  },

  sendMessage(scopeKey, payload) {
    return agentApi.sendMessage(scopeKey, payload);
  },

  sendUiResult(scopeKey, payload) {
    return agentApi.sendUiResult(scopeKey, payload);
  },

  abort(scopeKey) {
    return agentApi.abort(scopeKey);
  },

  async consumeStream({ scopeKey, streamToken, accessToken, signal, onEvent }) {
    const response = await fetch(agentApi.buildStreamUrl(scopeKey, streamToken, accessToken), {
      method: 'GET',
      credentials: 'include',
      signal,
    });
    await parseSSEStream(response, onEvent);
  },
};
