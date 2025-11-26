import api from './api';

const chatService = {
  getConversations: async (params = {}) => {
    const response = await api.get('/coreapp/conversations/', { params });
    return response.data;
  },

  getConversation: async (conversationId) => {
    const response = await api.get(`/coreapp/conversations/${conversationId}/`);
    return response.data;
  },

  createConversation: async (data) => {
    const response = await api.post('/coreapp/conversations/', data);
    return response.data;
  },

  deleteConversation: async (conversationId) => {
    await api.delete(`/coreapp/conversations/${conversationId}/`);
  },

  getModels: async () => {
    const response = await api.get('/coreapp/llms/');
    return response.data;
  },

  getModelRecommendation: async (promptType) => {
    const response = await api.get('/coreapp/llms/recommend/', {
      params: { prompt_type: promptType },
    });
    return response.data;
  },

  sendMessage: async (data) => {
    const response = await api.post('/coreapp/generate/', data);
    return response.data;
  },

  streamMessage: (data, onChunk, onComplete, onError) => {
    const controller = new AbortController();

    fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/coreapp/generate/stream/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
      },
      body: JSON.stringify(data),
      signal: controller.signal,
    })
      .then(async (response) => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n').filter((line) => line.trim());

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') {
                onComplete();
              } else {
                try {
                  const parsed = JSON.parse(data);
                  onChunk(parsed);
                } catch (e) {
                  onChunk({ content: data });
                }
              }
            }
          }
        }
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          onError(error);
        }
      });

    return controller;
  },

  rateResponse: async (responseId, rating) => {
    const response = await api.post(`/coreapp/responses/${responseId}/rate/`, {
      rating,
    });
    return response.data;
  },

  regenerateResponse: async (responseId) => {
    const response = await api.post(`/coreapp/responses/${responseId}/regenerate/`);
    return response.data;
  },

  compareModels: async (data) => {
    const response = await api.post('/coreapp/compare/', data);
    return response.data;
  },

  getConversationSummary: async (conversationId) => {
    const response = await api.get(`/coreapp/conversations/${conversationId}/summary/`);
    return response.data;
  },

  exportConversation: async (conversationId, format = 'markdown') => {
    const response = await api.get(`/coreapp/conversations/${conversationId}/export/`, {
      params: { format },
      responseType: format === 'pdf' ? 'blob' : 'json',
    });
    return response.data;
  },
};

export default chatService;
