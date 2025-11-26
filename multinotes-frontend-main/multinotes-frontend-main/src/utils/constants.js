// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws';

// App Configuration
export const APP_NAME = 'Multinotes.ai';
export const APP_VERSION = '1.0.0';

// Pagination
export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

// File Upload
export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
export const ALLOWED_FILE_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
];

// Token Limits
export const LOW_TOKEN_WARNING = 1000;
export const CRITICAL_TOKEN_WARNING = 100;

// AI Configuration
export const MAX_PROMPT_LENGTH = 4000;
export const MAX_CONVERSATION_HISTORY = 50;

// UI Configuration
export const TOAST_DURATION = 3000;
export const DEBOUNCE_DELAY = 300;
export const ANIMATION_DURATION = 300;

// Routes
export const PUBLIC_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email'];
export const PROTECTED_ROUTES = ['/dashboard', '/ai', '/documents', '/settings', '/tokens'];

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME: 'multinotes-theme',
  SIDEBAR_STATE: 'multinotes-sidebar',
  RECENT_MODELS: 'multinotes-recent-models',
  RECENT_SEARCHES: 'multinotes-recent-searches',
};

// Keyboard Shortcuts
export const KEYBOARD_SHORTCUTS = {
  COMMAND_PALETTE: 'mod+k',
  NEW_CHAT: 'mod+n',
  SEARCH: 'mod+/',
  SETTINGS: 'mod+,',
};
