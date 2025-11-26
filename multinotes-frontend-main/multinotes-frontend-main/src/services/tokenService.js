import api from './api';

const tokenService = {
  getBalance: async () => {
    const response = await api.get('/tokens/balance/');
    return response.data;
  },

  getUsageHistory: async (params = {}) => {
    const response = await api.get('/tokens/usage/history/', { params });
    return response.data;
  },

  getUsageBreakdown: async () => {
    const response = await api.get('/tokens/usage/breakdown/');
    return response.data;
  },

  getDailyUsage: async (days = 30) => {
    const response = await api.get('/tokens/usage/daily/', { params: { days } });
    return response.data;
  },

  estimateUsage: async (modelId, promptLength) => {
    const response = await api.post('/tokens/estimate/', {
      model_id: modelId,
      prompt_length: promptLength,
    });
    return response.data;
  },

  purchaseTokens: async (packageId) => {
    const response = await api.post('/tokens/purchase/', { package_id: packageId });
    return response.data;
  },

  getTokenPackages: async () => {
    const response = await api.get('/tokens/packages/');
    return response.data;
  },
};

export default tokenService;
