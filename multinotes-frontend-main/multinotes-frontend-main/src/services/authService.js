import api from './api';

const authService = {
  login: async (credentials) => {
    const response = await api.post('/authentication/login/', credentials);
    return response.data;
  },

  register: async (userData) => {
    const response = await api.post('/authentication/register/', userData);
    return response.data;
  },

  googleLogin: async (token) => {
    const response = await api.post('/authentication/google/', { token });
    return response.data;
  },

  facebookLogin: async (token) => {
    const response = await api.post('/authentication/facebook/', { token });
    return response.data;
  },

  logout: async (refreshToken) => {
    try {
      await api.post('/authentication/logout/', { refresh: refreshToken });
    } catch (error) {
      // Ignore logout errors
    }
  },

  refreshToken: async (refreshToken) => {
    const response = await api.post('/authentication/token/refresh/', {
      refresh: refreshToken,
    });
    return response.data;
  },

  forgotPassword: async (email) => {
    const response = await api.post('/authentication/password/reset/', { email });
    return response.data;
  },

  resetPassword: async (token, password) => {
    const response = await api.post('/authentication/password/reset/confirm/', {
      token,
      password,
    });
    return response.data;
  },

  verifyEmail: async (token) => {
    const response = await api.post('/authentication/verify-email/', { token });
    return response.data;
  },

  getProfile: async () => {
    const response = await api.get('/authentication/profile/');
    return response.data;
  },

  updateProfile: async (data) => {
    const response = await api.patch('/authentication/profile/', data);
    return response.data;
  },

  changePassword: async (data) => {
    const response = await api.post('/authentication/password/change/', data);
    return response.data;
  },

  resendVerificationEmail: async () => {
    const response = await api.post('/authentication/resend-verification/');
    return response.data;
  },
};

export default authService;
