// API Configuration for Flask Backend
export const API_CONFIG = {
  // Backend base URL - change this to your Flask backend address
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3446',
  
  // API endpoints matching your Flask backend
  ENDPOINTS: {
    // System check and authentication
    CHECK_INSTALLATION: '/check',
    AUTH: '/api/auth',
    
    // Unified data endpoint
    GET_ALL_DATA: '/api/data',
    
    // Unified management endpoint
    MANAGE: '/api/manage',
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

export interface FlaskResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}

export interface AllDataResponse {
  dashboard: any;
  clients: any[];
  interfaces: any[];
  settings: Record<string, string>;
}