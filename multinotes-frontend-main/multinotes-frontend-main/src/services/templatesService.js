import api from './api';

/**
 * Templates Service
 *
 * Handles prompt templates and categories API calls.
 * Backend: /api/user/... (coreapp) and /api/ticket/... (ticketandcategory)
 */
const templatesService = {
  /**
   * Get prompt library (all prompts/templates)
   */
  getTemplates: async (params = {}) => {
    const response = await api.get('/user/prompt_library/', { params });
    return response.data;
  },

  /**
   * Get single prompt template
   */
  getTemplate: async (templateId) => {
    const response = await api.get(`/user/prompt/${templateId}/`);
    return response.data;
  },

  /**
   * Get categories
   */
  getCategories: async () => {
    const response = await api.get('/ticket/get-categories/');
    return response.data;
  },

  /**
   * Get main categories
   */
  getMainCategories: async () => {
    const response = await api.get('/ticket/get_main_categories/');
    return response.data;
  },

  /**
   * Get main categories for user
   */
  getMainCategoriesForUser: async () => {
    const response = await api.get('/ticket/get_main_category_for_user/');
    return response.data;
  },

  /**
   * Get prompt library folders
   */
  getTemplateFolders: async () => {
    const response = await api.get('/user/prompt_library_folders/');
    return response.data;
  },

  /**
   * Get user's saved prompts
   */
  getUserTemplates: async () => {
    const response = await api.get('/user/prompt_library/', {
      params: { saved: true },
    });
    return response.data;
  },

  /**
   * Create a new prompt
   */
  createTemplate: async (data) => {
    const response = await api.post('/user/prompt/', data);
    return response.data;
  },

  /**
   * Update an existing prompt
   */
  updateTemplate: async (templateId, data) => {
    const response = await api.put(`/user/update_prompt/${templateId}/`, data);
    return response.data;
  },

  /**
   * Delete a prompt
   */
  deleteTemplate: async (templateId) => {
    await api.delete(`/user/prompt/${templateId}/`);
  },

  /**
   * Save/unsave a prompt (toggle)
   */
  toggleFavorite: async (templateId, isSaved) => {
    const response = await api.put(`/user/update_prompt/${templateId}/`, {
      is_saved: !isSaved,
    });
    return response.data;
  },

  /**
   * Use a template to generate content
   */
  useTemplate: async (templateId, variables = {}) => {
    // Get the template first
    const template = await api.get(`/user/prompt/${templateId}/`);
    // Then use it with the AI generator
    const response = await api.post('/user/text_ai_generator/', {
      prompt_text: template.data.prompt_text,
      ...variables,
    });
    return response.data;
  },

  /**
   * Create prompt folder
   */
  createFolder: async (data) => {
    const response = await api.post('/user/prompt_folder/', data);
    return response.data;
  },

  /**
   * Get prompt single details
   */
  getPromptSingle: async (params = {}) => {
    const response = await api.get('/user/prompt_single/', { params });
    return response.data;
  },

  /**
   * Get document for a prompt
   */
  getPromptDocument: async (promptId) => {
    const response = await api.get(`/user/document/${promptId}/`);
    return response.data;
  },

  /**
   * Create document for prompt
   */
  createPromptDocument: async (data) => {
    const response = await api.post('/user/document/', data);
    return response.data;
  },

  /**
   * Get FAQs
   */
  getFAQs: async () => {
    const response = await api.get('/ticket/get_faqs/');
    return response.data;
  },
};

export default templatesService;
