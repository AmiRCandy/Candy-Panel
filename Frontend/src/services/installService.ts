import { apiService } from './api';
import { API_CONFIG } from '@/config/api';
import { InstallationData } from '@/types';

class InstallService {
  async performInstallation(installData: InstallationData): Promise<void> {
    const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH, {
      action: 'install',
      server_ip: installData.server_ip,
      wg_port: installData.wg_port,
      wg_address_range: installData.wg_address_range,
      wg_dns: installData.wg_dns,
      admin_user: installData.admin_user,
      admin_password: installData.admin_password
    });
    
    if (!response.success) {
      throw new Error(response.message || 'Installation failed');
    }
  }
}

export const installService = new InstallService();