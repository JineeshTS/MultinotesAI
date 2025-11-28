import api from './api';
import { store } from '../store';

/**
 * Chat Service
 *
 * Handles AI chat and conversation API calls.
 * Backend: /api/user/... (coreapp)
 */
const chatService = {
  /**
   * Get all group responses (conversations) for the user
   */
  getConversations: async (params = {}) => {
    const response = await api.get('/user/group_response/', { params });
    return response.data;
  },

  /**
   * Get a specific conversation/group history
   */
  getConversation: async (conversationId) => {
    const response = await api.get(`/user/group_history/${conversationId}/`);
    return response.data;
  },

  /**
   * Create a new conversation/group response
   */
  createConversation: async (data) => {
    const response = await api.post('/user/group_response/', data);
    return response.data;
  },

  /**
   * Delete a conversation
   */
  deleteConversation: async (conversationId) => {
    await api.delete(`/user/group_response/${conversationId}/`);
  },

  /**
   * Get available LLM models for the user
   */
  getModels: async () => {
    const response = await api.get('/user/get_models_by_user/');
    return response.data;
  },

  /**
   * Get all LLM models (admin)
   */
  getAllModels: async () => {
    const response = await api.get('/user/get_models/');
    return response.data;
  },

  /**
   * Get model details
   */
  getModel: async (modelId) => {
    const response = await api.get(`/user/get_model/${modelId}/`);
    return response.data;
  },

  /**
   * Send a text-to-text generation request
   */
  sendMessage: async (data) => {
    const response = await api.post('/user/text_ai_generator/', data);
    return response.data;
  },

  /**
   * Send a file-based generation request
   */
  sendFileMessage: async (data) => {
    const response = await api.post('/user/file_ai_generator/', data);
    return response.data;
  },

  /**
   * Dynamic LLM generator (flexible endpoint)
   */
  dynamicGenerate: async (data) => {
    const response = await api.post('/user/dynamic_llm_generator/', data);
    return response.data;
  },

  /**
   * Stream message with Server-Sent Events
   */
  streamMessage: (data, onChunk, onComplete, onError) => {
    const controller = new AbortController();
    const state = store.getState();
    const token = state.auth.accessToken;

    fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/user/text_ai_generator/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ ...data, stream: true }),
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

  /**
   * Rate an LLM model
   */
  rateModel: async (llmId, rating, review = '') => {
    const response = await api.post('/user/add_rating/', {
      llm: llmId,
      rating,
      review,
    });
    return response.data;
  },

  /**
   * Get ratings for a model
   */
  getModelRatings: async (llmId) => {
    const response = await api.get(`/user/get_ratings_by_admin/${llmId}/`);
    return response.data;
  },

  /**
   * Get prompt details
   */
  getPrompt: async (promptId) => {
    const response = await api.get(`/user/prompt/${promptId}/`);
    return response.data;
  },

  /**
   * Get prompt response details
   */
  getPromptResponse: async (responseId) => {
    const response = await api.get(`/user/prompt_response/${responseId}/`);
    return response.data;
  },

  /**
   * Get dashboard counts
   */
  getDashboardCounts: async () => {
    const response = await api.get('/user/dashboard_count/');
    return response.data;
  },

  /**
   * Text to image generation
   */
  generateImage: async (data) => {
    const response = await api.post('/user/gemini_text_to_image/', data);
    return response.data;
  },

  /**
   * Text to speech generation
   */
  generateSpeech: async (data) => {
    const response = await api.post('/user/text_to_speech_generate/', data);
    return response.data;
  },

  /**
   * Speech to text generation
   */
  transcribeSpeech: async (data) => {
    const response = await api.post('/user/speech_to_text_generate/', data);
    return response.data;
  },

  /**
   * Image to text (vision)
   */
  analyzeImage: async (data) => {
    const response = await api.post('/user/gemini_picture_to_text/', data);
    return response.data;
  },

  /**
   * Code generation
   */
  generateCode: async (data) => {
    const response = await api.post('/user/code_generate_together/', data);
    return response.data;
  },
};

export default chatService;
