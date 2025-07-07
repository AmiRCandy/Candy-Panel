import { apiService } from './api';
import { API_CONFIG } from '@/config/api';
import { Client } from '@/types';

class ClientService {
  async getClients(): Promise<Client[]> {
    const response = await apiService.get<Client[]>(API_CONFIG.ENDPOINTS.CLIENTS);
    return response.data || [];
  }

  async createClient(clientData: {
    name: string;
    expires: string;
    traffic: string;
    wg_id?: number;
    note?: string;
  }): Promise<Client> {
    const response = await apiService.post<any>(
      API_CONFIG.ENDPOINTS.CLIENTS,
      {
        name: clientData.name,
        expires: clientData.expires,
        traffic: clientData.traffic,
        wg_id: clientData.wg_id || 0,
        note: clientData.note || ''
      }
    );
    
    if (response.success) {
      return response.data;
    }
    
    throw new Error(response.message || 'Failed to create client');
  }

  async updateClient(name: string, clientData: {
    expires?: string;
    traffic?: string;
    status?: boolean;
    note?: string;
  }): Promise<Client> {
    const response = await apiService.put<any>(
      API_CONFIG.ENDPOINTS.CLIENT_BY_NAME,
      clientData,
      { name }
    );
    
    if (response.success) {
      return response.data;
    }
    
    throw new Error(response.message || 'Failed to update client');
  }

  async deleteClient(name: string): Promise<void> {
    const response = await apiService.delete(
      API_CONFIG.ENDPOINTS.CLIENT_BY_NAME,
      { name }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to delete client');
    }
  }

  async toggleClient(name: string, enabled: boolean): Promise<void> {
    const response = await apiService.put(
      API_CONFIG.ENDPOINTS.CLIENT_BY_NAME,
      { status: enabled },
      { name }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to toggle client');
    }
  }

  async getClientConfig(name: string): Promise<string> {
    const response = await apiService.get<{ config: string }>(
      API_CONFIG.ENDPOINTS.CLIENT_CONFIG,
      { name }
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