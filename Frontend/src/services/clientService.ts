import { apiService } from './api';
import { API_CONFIG } from '@/config/api';
import { Client } from '@/types';

class ClientService {
  async getClients(): Promise<Client[]> {
    const response = await apiService.get<any>(API_CONFIG.ENDPOINTS.GET_ALL_DATA);
    return response.data?.clients || [];
  }

  async createClient(clientData: {
    name: string;
    expires: string;
    traffic: string;
    wg_id?: number;
    note?: string;
  }): Promise<string> {
    const response = await apiService.post<any>(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'client',
        action: 'create',
        name: clientData.name,
        expires: clientData.expires,
        traffic: clientData.traffic,
        wg_id: clientData.wg_id || 0,
        note: clientData.note || ''
      }
    );
    
    if (response.success) {
      return response.data?.client_config || '';
    }
    
    throw new Error(response.message || 'Failed to create client');
  }

  async updateClient(name: string, clientData: {
    expires?: string;
    traffic?: string;
    status?: boolean;
    note?: string;
  }): Promise<void> {
    const response = await apiService.post<any>(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'client',
        action: 'update',
        name,
        ...clientData
      }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to update client');
    }
  }

  async deleteClient(name: string): Promise<void> {
    const response = await apiService.post(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'client',
        action: 'delete',
        name
      }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to delete client');
    }
  }

  async toggleClient(name: string, enabled: boolean): Promise<void> {
    const response = await apiService.post(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'client',
        action: 'update',
        name,
        status: enabled
      }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to toggle client');
    }
  }

  async getClientConfig(name: string): Promise<string> {
    const response = await apiService.post<{ config: string }>(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'client',
        action: 'get_config',
        name
      }
    );
    
    if (response.success && response.data) {
      return response.data.config;
    }
    
    throw new Error(response.message || 'Failed to get client config');
  }

  async downloadClientConfig(name: string): Promise<void> {
    try {
      const config = await this.getClientConfig(name);
      
      const blob = new Blob([config], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name}.conf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      throw new Error('Failed to download client config');
    }
  }
}

export const clientService = new ClientService();