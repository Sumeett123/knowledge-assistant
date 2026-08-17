const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  UPLOAD: `${API_BASE_URL}/upload`,
  QUERY: `${API_BASE_URL}/query`,
  HEALTH: `${API_BASE_URL}/health`,
};

export const APP_CONFIG = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  ALLOWED_FILE_TYPES: ['application/pdf'],
  API_TIMEOUT: 30000,
};
