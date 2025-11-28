import api from './api';

/**
 * Token/Subscription Service
 *
 * Handles token balance, usage tracking, and subscription API calls.
 * Backend: /api/subscription/... and /api/plan/... (planandsubscription)
 */
const tokenService = {
  /**
   * Get user's subscription/storage details including token balance
   */
  getBalance: async () => {
    const response = await api.get('/user/user_storage_view/');
    return response.data;
  },

  /**
   * Get user's current subscription
   */
  getSubscription: async () => {
    const response = await api.get('/subscription/get-subscription/');
    return response.data;
  },

  /**
   * Get per day token usage history
   */
  getUsageHistory: async (params = {}) => {
    const response = await api.get('/user/per_day_used_token/', { params });
    return response.data;
  },

  /**
   * Get dashboard token usage breakdown
   */
  getUsageBreakdown: async () => {
    const response = await api.get('/user/dashboard_count/');
    return response.data;
  },

  /**
   * Get daily usage stats
   */
  getDailyUsage: async (days = 30) => {
    const response = await api.get('/user/per_day_used_token/', { params: { days } });
    return response.data;
  },

  /**
   * Get available subscription plans
   */
  getTokenPackages: async () => {
    const response = await api.get('/plan/get-plans/');
    return response.data;
  },

  /**
   * Get specific plan details
   */
  getPlan: async (planId) => {
    const response = await api.get(`/plan/get-plan/${planId}/`);
    return response.data;
  },

  /**
   * Create Razorpay order for subscription
   */
  createOrder: async (planId, couponCode = null) => {
    const data = { plan_id: planId };
    if (couponCode) {
      data.coupon_code = couponCode;
    }
    const response = await api.post('/subscription/payment/create-order/', data);
    return response.data;
  },

  /**
   * Verify Razorpay payment
   */
  verifyPayment: async (paymentData) => {
    const response = await api.post('/subscription/payment/verify/', paymentData);
    return response.data;
  },

  /**
   * Get payment status
   */
  getPaymentStatus: async (orderId) => {
    const response = await api.get(`/subscription/payment/status/${orderId}/`);
    return response.data;
  },

  /**
   * Validate coupon code
   */
  validateCoupon: async (couponCode) => {
    const response = await api.post('/subscription/payment/validate-coupon/', {
      coupon_code: couponCode,
    });
    return response.data;
  },

  /**
   * Apply coupon to get discount
   */
  applyCoupon: async (couponCode) => {
    const response = await api.post('/ticket/apply_coupon/', {
      coupon_code: couponCode,
    });
    return response.data;
  },

  /**
   * Get transaction history
   */
  getTransactions: async () => {
    const response = await api.get('/transaction/get-transaction/');
    return response.data;
  },

  /**
   * Get specific transaction
   */
  getTransaction: async (transactionId) => {
    const response = await api.get(`/transaction/get-transaction/${transactionId}/`);
    return response.data;
  },

  /**
   * Create subscription
   */
  createSubscription: async (data) => {
    const response = await api.post('/subscription/create-subscription/', data);
    return response.data;
  },

  /**
   * Update subscription
   */
  updateSubscription: async (subscriptionId, data) => {
    const response = await api.put(`/subscription/update-subscription/${subscriptionId}/`, data);
    return response.data;
  },

  /**
   * Request refund
   */
  requestRefund: async (orderId, reason) => {
    const response = await api.post('/subscription/payment/refund/', {
      order_id: orderId,
      reason,
    });
    return response.data;
  },
};

export default tokenService;
