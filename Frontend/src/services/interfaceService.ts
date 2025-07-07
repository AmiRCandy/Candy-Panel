import { apiService } from './api';
import { API_CONFIG } from '@/config/api';
import { Interface } from '@/types';

class InterfaceService {
  async getInterfaces(): Promise<Interface[]> {
    const response = await apiService.get<any>(API_CONFIG.ENDPOINTS.GET_ALL_DATA);
    return response.data?.interfaces || [];
  }

  async createInterface(interfaceData: {
    address_range: string;
    port: number;
  }): Promise<void> {
    const response = await apiService.post<any>(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'interface',
        action: 'create',
        address_range: interfaceData.address_range,
        port: interfaceData.port
      }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to create interface');
    }
  }

  async updateInterface(name: string, interfaceData: {
    address?: string;
    port?: number;
    status?: boolean;
  }): Promise<void> {
    const response = await apiService.post<any>(
      API_CONFIG.ENDPOINTS.MANAGE,
      {
        resource: 'interface',
        action: 'update',
        name,
        ...interfaceData
      }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to update interface');
    }
  }
}

export const interfaceService = new InterfaceService();