import api from './api';

const templatesService = {
  getTemplates: async (params = {}) => {
    const response = await api.get('/coreapp/templates/', { params });
    return response.data;
  },

  getTemplate: async (templateId) => {
    const response = await api.get(`/coreapp/templates/${templateId}/`);
    return response.data;
  },

  getCategories: async () => {
    const response = await api.get('/coreapp/categories/');
    return response.data;
  },

  getFavorites: async () => {
    const response = await api.get('/coreapp/templates/favorites/');
    return response.data;
  },

  getTrending: async () => {
    const response = await api.get('/coreapp/templates/trending/');
    return response.data;
  },

  getUserTemplates: async () => {
    const response = await api.get('/coreapp/templates/my/');
    return response.data;
  },

  createTemplate: async (data) => {
    const response = await api.post('/coreapp/templates/', data);
    return response.data;
  },

  updateTemplate: async (templateId, data) => {
    const response = await api.patch(`/coreapp/templates/${templateId}/`, data);
    return response.data;
  },

  deleteTemplate: async (templateId) => {
    await api.delete(`/coreapp/templates/${templateId}/`);
  },

  toggleFavorite: async (templateId) => {
    const response = await api.post(`/coreapp/templates/${templateId}/favorite/`);
    return response.data;
  },

  useTemplate: async (templateId, variables = {}) => {
    const response = await api.post(`/coreapp/templates/${templateId}/use/`, {
      variables,
    });
    return response.data;
  },

  shareTemplate: async (templateId) => {
    const response = await api.post(`/coreapp/templates/${templateId}/share/`);
    return response.data;
  },

  searchTemplates: async (query, category = null) => {
    const params = { q: query };
    if (category) {
      params.category = category;
    }
    const response = await api.get('/coreapp/templates/search/', { params });
    return response.data;
  },
};

export default templatesService;
