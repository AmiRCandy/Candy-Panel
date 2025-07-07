import { apiService } from './api';
import { API_CONFIG } from '@/config/api';
import { InstallationData } from '@/types';

class InstallService {
  async performInstallation(installData: InstallationData): Promise<void> {
    const response = await apiService.post(API_CONFIG.ENDPOINTS.INSTALL, installData);
    
    if (!response.success) {
      throw new Error(response.message || 'Installation failed');
    }
  }
}

export const installService = new InstallService();