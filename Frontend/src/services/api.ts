import { API_CONFIG, ApiResponse } from '@/config/api';

class ApiService {
  private baseURL: string;
  private timeout: number;
  private defaultHeaders: Record<string, string>;

  constructor() {
    this.baseURL = API_CONFIG.BASE_URL;
    this.timeout = API_CONFIG.TIMEOUT;
    this.defaultHeaders = API_CONFIG.DEFAULT_HEADERS;
  }

  // Set backend URL dynamically
  setBaseURL(url: string) {
    this.baseURL = url;
    console.log(`🔄 API Backend URL set to: ${url}`);
  }

  // Get auth token from localStorage
  private getAuthToken(): string | null {
    return localStorage.getItem('candy-panel-token');
  }

  // Build headers with auth token
  private buildHeaders(customHeaders: Record<string, string> = {}): Record<string, string> {
    const headers = { ...this.defaultHeaders, ...customHeaders };
    const token = this.getAuthToken();
    
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    
    return headers;
  }

  // Build full URL
  private buildURL(endpoint: string, params?: Record<string, string>): string {
    let url = `${this.baseURL}${endpoint}`;
    
    // Replace URL parameters
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url = url.replace(`:${key}`, value);
      });
    }
    
    return url;
  }

  // Generic request method
  private async request<T>(
    method: string,
    endpoint: string,
    options: {
      data?: any;
      params?: Record<string, string>;
      headers?: Record<string, string>;
      timeout?: number;
    } = {}
  ): Promise<ApiResponse<T>> {
    const { data, params, headers = {}, timeout = this.timeout } = options;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const url = this.buildURL(endpoint, params);
      const requestHeaders = this.buildHeaders(headers);
      
      console.log(`🌐 API Request: ${method} ${url}`);
      
      const config: RequestInit = {
        method,
        headers: requestHeaders,
        signal: controller.signal,
      };
      
      if (data && method !== 'GET') {
        config.body = JSON.stringify(data);
      }
      
      const response = await fetch(url, config);
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      // Handle your backend's response format
      if (result.success !== undefined) {
        return {
          success: result.success,
          data: result.data || result,
          message: result.message
        };
      }
      
      // For endpoints that return data directly
      return {
        success: true,
        data: result,
        message: 'Request successful'
      };
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error('Request timeout');
        }
        throw error;
      }
      
      throw new Error('Unknown error occurred');
    }
  }

  // HTTP methods
  async get<T>(endpoint: string, params?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('GET', endpoint, { params });
  }

  async post<T>(endpoint: string, data?: any, params?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, { data, params });
  }

  async put<T>(endpoint: string, data?: any, params?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', endpoint, { data, params });
  }

  async delete<T>(endpoint: string, params?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', endpoint, { params });
  }

  async patch<T>(endpoint: string, data?: any, params?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('PATCH', endpoint, { data, params });
  }
}

export const apiService = new ApiService();