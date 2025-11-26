import api from './api';

/**
 * Authentication Service
 *
 * Handles all authentication-related API calls.
 * Backend URLs: /api/auth/v1/... for versioned endpoints
 */
const authService = {
  /**
   * Login with email/username and password
   */
  login: async (credentials) => {
    const response = await api.post('/auth/v1/login/', {
      userNameOrEmail: credentials.email || credentials.username,
      password: credentials.password,
      deviceToken: credentials.deviceToken || null,
    });
    return response.data;
  },

  /**
   * Register a new user
   */
  register: async (userData) => {
    const response = await api.post('/auth/v1/register/', {
      email: userData.email,
      username: userData.username,
      password: userData.password,
      referr_by_code: userData.referralCode || null,
    });
    return response.data;
  },

  /**
   * Social login (Google/Facebook)
   */
  googleLogin: async (tokenData) => {
    const response = await api.post('/auth/v1/social-login/', {
      socialId: tokenData.socialId,
      socialType: 'google',
      email: tokenData.email,
      username: tokenData.name || tokenData.email.split('@')[0],
      deviceToken: tokenData.deviceToken || null,
    });
    return response.data;
  },

  facebookLogin: async (tokenData) => {
    const response = await api.post('/auth/v1/social-login/', {
      socialId: tokenData.socialId,
      socialType: 'facebook',
      email: tokenData.email,
      username: tokenData.name || tokenData.email.split('@')[0],
      deviceToken: tokenData.deviceToken || null,
    });
    return response.data;
  },

  /**
   * Logout - blacklist refresh token
   */
  logout: async (refreshToken) => {
    try {
      // Backend uses SimpleJWT blacklist
      await api.post('/token/refresh/', { refresh: refreshToken });
    } catch (error) {
      // Ignore logout errors - user is logged out locally anyway
    }
  },

  /**
   * Refresh access token
   */
  refreshToken: async (refreshToken) => {
    const response = await api.post('/token/refresh/', {
      refresh: refreshToken,
    });
    return response.data;
  },

  /**
   * Request password reset email
   */
  forgotPassword: async (email) => {
    const response = await api.post('/auth/v1/forgot-password/', { email });
    return response.data;
  },

  /**
   * Reset password with token
   */
  resetPassword: async (token, password) => {
    const response = await api.post('/auth/v1/reset-password/', {
      token,
      password,
    });
    return response.data;
  },

  /**
   * Verify email with token
   */
  verifyEmail: async (token) => {
    const response = await api.post('/auth/v1/verify-email-token/', { token });
    return response.data;
  },

  /**
   * Get user profile by ID
   */
  getProfile: async (userId) => {
    const response = await api.get(`/auth/get-user/${userId}/`);
    return response.data;
  },

  /**
   * Update user profile
   */
  updateProfile: async (userId, data) => {
    const response = await api.patch(`/auth/update-user/${userId}/`, data);
    return response.data;
  },

  /**
   * Change password (authenticated)
   */
  changePassword: async (data) => {
    const response = await api.post('/auth/change-password/', {
      old_password: data.oldPassword,
      new_password: data.newPassword,
    });
    return response.data;
  },

  /**
   * Resend verification email
   */
  resendVerificationEmail: async (userId) => {
    const response = await api.post('/auth/resend_verification/', { userId });
    return response.data;
  },

  /**
   * Generate password for social login users
   */
  generatePassword: async (password) => {
    const response = await api.post('/auth/generate_password/', { password });
    return response.data;
  },

  /**
   * Get image URL from S3
   */
  getImageUrl: async (imageKey) => {
    const response = await api.get('/auth/media/preview/', {
      params: { image: imageKey },
    });
    return response.data;
  },

  /**
   * Upload profile image
   */
  uploadImage: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/auth/uploadImage/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

export default authService;
