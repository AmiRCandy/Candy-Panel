import { apiService } from './api';
import { API_CONFIG } from '@/config/api';
import { ServerStats } from '@/types';

class ServerService {
  async getDashboardStats(): Promise<ServerStats> {
    const response = await apiService.get<ServerStats>(API_CONFIG.ENDPOINTS.DASHBOARD);
    
    if (response.success && response.data) {
      return response.data;
    }
    
    throw new Error(response.message || 'Failed to get dashboard stats');
  }

  async getSettings(): Promise<Record<string, string>> {
    const response = await apiService.get<Record<string, string>>(API_CONFIG.ENDPOINTS.SETTINGS);
    
    if (response.success && response.data) {
      return response.data;
    }
    
    throw new Error(response.message || 'Failed to get settings');
  }

  async updateSetting(key: string, value: string): Promise<void> {
    const response = await apiService.put(
      API_CONFIG.ENDPOINTS.SETTING_BY_KEY,
      { value },
      { key }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to update setting');
    }
  }

  async triggerSync(): Promise<void> {
    const response = await apiService.post(API_CONFIG.ENDPOINTS.SYNC);
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to trigger sync');
    }
  }
}

export const serverService = new ServerService();