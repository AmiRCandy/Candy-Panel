import { apiService } from './api';
import { API_CONFIG } from '@/config/api';
import { ServerStats } from '@/types';

class ServerService {
  async getDashboardStats(): Promise<ServerStats> {
    const response = await apiService.get<any>(API_CONFIG.ENDPOINTS.GET_ALL_DATA);
    
    if (response.success && response.data) {
      return response.data.dashboard;
    }
    
    throw new Error(response.message || 'Failed to get dashboard stats');
  }

  async getSettings(): Promise<Record<string, string>> {
    const response = await apiService.get<any>(API_CONFIG.ENDPOINTS.GET_ALL_DATA);
    
    if (response.success && response.data) {
      return response.data.settings;
    }
    
    throw new Error(response.message || 'Failed to get settings');
  }

  async updateSetting(key: string, value: string): Promise<void> {
    const response = await apiService.post(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'setting',
        action: 'update',
        key,
        value
      }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to update setting');
    }
  }

  async triggerSync(): Promise<void> {
    const response = await apiService.post(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'sync',
        action: 'trigger'
      }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to trigger sync');
    }
  }

  async addApiToken(name: string, token: string): Promise<void> {
    const response = await apiService.post(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'api_token',
        action: 'create_or_update',
        name,
        token
      }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to add API token');
    }
  }

  async deleteApiToken(name: string): Promise<void> {
    const response = await apiService.post(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'api_token',
        action: 'delete',
        name
      }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to delete API token');
    }
  }
}

export const serverService = new ServerService();