import { ApiResponse, AuthData, AllData } from '../types';

const API_BASE_URL = import.meta.env.VITE_APP_API_URL || 'http://serverip:3445';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('candy_panel_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Request failed');
      }

      return data;
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Network error');
    }
  }

  async checkInstallation(): Promise<{ installed: boolean }> {
    const response = await fetch(`${API_BASE_URL}/check`);
    return response.json();
  }

  async login(username: string, password: string): Promise<ApiResponse<AuthData>> {
    const result = await this.request<AuthData>('/api/auth', {
      method: 'POST',
      body: JSON.stringify({
        action: 'login',
        username,
        password,
      }),
    });

    if (result.success && result.data) {
      this.token = result.data.access_token;
      localStorage.setItem('candy_panel_token', this.token);
    }

    return result;
  }

  async install(data: {
    server_ip: string;
    wg_port: string;
    wg_address_range?: string;
    wg_dns?: string;
    admin_user?: string;
    admin_password?: string;
  }): Promise<ApiResponse> {
    return this.request('/api/auth', {
      method: 'POST',
      body: JSON.stringify({
        action: 'install',
        ...data,
      }),
    });
  }

  async getAllData(): Promise<ApiResponse<AllData>> {
    return this.request<AllData>('/api/data');
  }

  async createClient(data: {
    name: string;
    expires: string;
    traffic: string;
    wg_id?: number;
    note?: string;
  }): Promise<ApiResponse<{ client_config: string }>> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'client',
        action: 'create',
        ...data,
      }),
    });
  }

  async updateClient(data: {
    name: string;
    expires?: string;
    traffic?: string;
    status?: boolean; // Added status update
    note?: string;
  }): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'client',
        action: 'update',
        ...data,
      }),
    });
  }

  async deleteClient(name: string): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'client',
        action: 'delete',
        name,
      }),
    });
  }

  async getClientConfig(name: string): Promise<ApiResponse<{ config: string }>> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'client',
        action: 'get_config',
        name,
      }),
    });
  }

  async createInterface(data: {
    address_range: string;
    port: number;
  }): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'interface',
        action: 'create',
        ...data,
      }),
    });
  }

  async updateInterface(name: string, data: {
    address?: string;
    port?: number;
    status?: boolean;
  }): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'interface',
        action: 'update',
        name,
        ...data,
      }),
    });
  }

  async deleteInterface(wg_id: number): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'interface',
        action: 'delete',
        wg_id,
      }),
    });
  }

  async updateSetting(key: string, value: string): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'setting',
        action: 'update',
        key,
        value,
      }),
    });
  }

  // New API Token methods
  async addApiToken(name: string, token: string): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'api_token',
        action: 'create_or_update',
        name,
        token,
      }),
    });
  }

  async deleteApiToken(name: string): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'api_token',
        action: 'delete',
        name,
      }),
    });
  }

  async sync(): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'sync',
        action: 'trigger',
      }),
    });
  }

  logout(): void {
    this.token = null;
    localStorage.removeItem('candy_panel_token');
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }
}

export const apiClient = new ApiClient();
