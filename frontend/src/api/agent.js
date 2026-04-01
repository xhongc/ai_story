import apiClient from '@/services/apiClient';


const buildStreamUrl = (scopeKey, streamToken, accessToken) => {
  const baseUrl = (process.env.VUE_APP_API_BASE_URL || '/api/v1').replace(/\/$/, '');
  const query = new URLSearchParams({ stream_token: streamToken });
  if (accessToken) {
    query.set('access_token', accessToken);
  }
  return `${baseUrl}/agent/session/${encodeURIComponent(scopeKey)}/stream/?${query.toString()}`;
};


export default {
  initSession(data) {
    return apiClient.post('/agent/session/init/', data);
  },

  sendMessage(scopeKey, data) {
    return apiClient.post(`/agent/session/${encodeURIComponent(scopeKey)}/message/`, data);
  },

  sendUiResult(scopeKey, data) {
    return apiClient.post(`/agent/session/${encodeURIComponent(scopeKey)}/ui-result/`, data);
  },

  abort(scopeKey) {
    return apiClient.post(`/agent/session/${encodeURIComponent(scopeKey)}/abort/`);
  },

  buildStreamUrl,
};
