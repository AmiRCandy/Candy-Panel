// API Configuration
export const API_CONFIG = {
  // Backend base URL - change this to your backend address
  BASE_URL:'http://localhost:3445',
  
  // API endpoints matching your backend
  ENDPOINTS: {
    // System check and authentication
    LOGIN_AUTH: '/check',
    INSTALL_STATUS: '/login',
    
    // Installation
    INSTALL: '/install',
    
    // Dashboard
    DASHBOARD: '/dashboard',
    SYNC: '/sync',
    
    // Client management
    CLIENTS: '/clients',
    CLIENT_BY_NAME: '/clients/:name',
    CLIENT_CONFIG: '/clients/:name/config',
    
    // Interface management
    INTERFACES: '/interfaces',
    INTERFACE_BY_NAME: '/interfaces/:name',
    
    // Settings
    SETTINGS: '/settings',
    SETTING_BY_KEY: '/settings/:key',
    
    // API Tokens
    API_TOKENS: '/api-tokens',
    API_TOKEN_BY_NAME: '/api-tokens/:name',
  },
  
  // Request timeout in milliseconds
  TIMEOUT: 30000,
  
  // Default headers
  DEFAULT_HEADERS: {
    'Content-Type': 'application/json',
  },
};

// API Response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  code?: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination?: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}