import { ApiResponse, AuthData, AllData, Client, Server } from '../types';

const API_BASE_URL = `http://127.0.0.1:3446`; // Central panel API base URL

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

  // New: Get all registered servers
  async getServers(): Promise<ApiResponse<{ servers: Server[] }>> {
    return this.request<{ servers: Server[] }>('/api/servers');
  }

  // New: Add a server
  async addServer(data: {
    name: string;
    ip_address: string;
    agent_port: number;
    api_key: string;
    description?: string;
  }): Promise<ApiResponse<{ server_id: number }>> {
    return this.request<{ server_id: number }>('/api/servers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // New: Update a server
  async updateServer(serverId: number, data: Partial<Server>): Promise<ApiResponse> {
    return this.request(`/api/servers/${serverId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // New: Delete a server
  async deleteServer(serverId: number): Promise<ApiResponse> {
    return this.request(`/api/servers/${serverId}`, {
      method: 'DELETE',
    });
  }

  // Modified: Fetch data for a specific server
  async getServerData(serverId: number): Promise<ApiResponse<AllData>> {
    return this.request<AllData>(`/api/data/server/${serverId}`);
  }

  async getClientDetails(name: string, public_key: string): Promise<ApiResponse<Client>> {
    // This public endpoint will call the server's public-facing client-details
    // which will handle finding the client across servers.
    return this.request<Client>(`/client-details/${name}/${public_key}`);
  }

  async createClient(serverId: number, data: {
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
        server_id: serverId, // Pass serverId
        ...data,
      }),
    });
  }

  async updateClient(serverId: number, data: {
    name: string;
    expires?: string;
    traffic?: string;
    status?: boolean;
    note?: string;
  }): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'client',
        action: 'update',
        server_id: serverId, // Pass serverId
        ...data,
      }),
    });
  }

  async deleteClient(serverId: number, name: string): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'client',
        action: 'delete',
        server_id: serverId, // Pass serverId
        name,
      }),
    });
  }

  async getClientConfig(serverId: number, name: string): Promise<ApiResponse<{ config: string }>> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'client',
        action: 'get_config',
        server_id: serverId, // Pass serverId
        name,
      }),
    });
  }

  async createInterface(serverId: number, data: {
    address_range: string;
    port: number;
  }): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'interface',
        action: 'create',
        server_id: serverId, // Pass serverId
        ...data,
      }),
    });
  }

  async updateInterface(serverId: number, name: string, data: {
    address?: string;
    port?: number;
    status?: boolean;
  }): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'interface',
        action: 'update',
        server_id: serverId, // Pass serverId
        name,
        ...data,
      }),
    });
  }

  async deleteInterface(serverId: number, wg_id: number): Promise<ApiResponse> {
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'interface',
        action: 'delete',
        server_id: serverId, // Pass serverId
        wg_id,
      }),
    });
  }

  async updateSetting(key: string, value: string): Promise<ApiResponse> {
    // Note: Settings are currently central, not per-server. server_id is not passed here.
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

  async sync(serverId: number): Promise<ApiResponse> { // Now takes serverId
    return this.request('/api/manage', {
      method: 'POST',
      body: JSON.stringify({
        resource: 'sync',
        action: 'trigger',
        server_id: serverId, // Pass serverId
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