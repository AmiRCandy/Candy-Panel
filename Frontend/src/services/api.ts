import { API_CONFIG, FlaskResponse } from '@/config/api';

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

  // Generic request method
  private async request<T>(
    method: string,
    endpoint: string,
    options: {
      data?: any;
      headers?: Record<string, string>;
      timeout?: number;
      requireAuth?: boolean;
    } = {}
  ): Promise<FlaskResponse<T>> {
    const { data, headers = {}, timeout = this.timeout, requireAuth = false } = options;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const url = `${this.baseURL}${endpoint}`;
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
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      // Handle Flask response format
      return {
        success: result.success || false,
        message: result.message || 'Request successful',
        data: result.data
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
  async get<T>(endpoint: string): Promise<FlaskResponse<T>> {
    return this.request<T>('GET', endpoint, { requireAuth: true });
  }

  async post<T>(endpoint: string, data?: any): Promise<FlaskResponse<T>> {
    return this.request<T>('POST', endpoint, { data });
  }

  async put<T>(endpoint: string, data?: any): Promise<FlaskResponse<T>> {
    return this.request<T>('PUT', endpoint, { data, requireAuth: true });
  }

  async delete<T>(endpoint: string): Promise<FlaskResponse<T>> {
    return this.request<T>('DELETE', endpoint, { requireAuth: true });
  }
}

export const apiService = new ApiService();