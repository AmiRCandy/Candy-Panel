import { apiService } from './api';
import { API_CONFIG } from '@/config/api';
import { Interface } from '@/types';

class InterfaceService {
  async getInterfaces(): Promise<Interface[]> {
    const response = await apiService.get<Interface[]>(API_CONFIG.ENDPOINTS.INTERFACES);
    return response.data || [];
  }

  async createInterface(interfaceData: {
    address_range: string;
    port: number;
  }): Promise<Interface> {
    const response = await apiService.post<Interface>(
      API_CONFIG.ENDPOINTS.INTERFACES,
      interfaceData
    );
    
    if (response.success && response.data) {
      return response.data;
    }
    
    throw new Error(response.message || 'Failed to create interface');
  }

  async updateInterface(name: string, interfaceData: {
    address?: string;
    port?: number;
    status?: boolean;
  }): Promise<Interface> {
    const response = await apiService.put<Interface>(
      API_CONFIG.ENDPOINTS.INTERFACE_BY_NAME,
      interfaceData,
      { name }
    );
    
    if (response.success && response.data) {
      return response.data;
    }
    
    throw new Error(response.message || 'Failed to update interface');
  }

  async deleteInterface(name: string): Promise<void> {
    const response = await apiService.delete(
      API_CONFIG.ENDPOINTS.INTERFACE_BY_NAME,
      { name }
    );
    
    if (!response.success) {
      throw new Error(response.message || 'Failed to delete interface');
    }
  }
}

export const interfaceService = new InterfaceService();