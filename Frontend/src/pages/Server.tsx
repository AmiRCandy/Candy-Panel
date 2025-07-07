import React from 'react';
import { motion } from 'framer-motion';
import { Server as ServerIcon, Settings, Shield, Loader } from 'lucide-react';
import { useApi, useMutation } from '@/hooks/useApi';
import { serverService } from '@/services/serverService';

export const Server: React.FC = () => {
  // Fetch all settings
  const { data: settings = {}, loading: settingsLoading, refetch: refetchSettings } = useApi(
    () => serverService.getSettings(),
    {
      onSuccess: (data) => console.log('✅ Settings loaded:', Object.keys(data).length),
      onError: (error) => console.error('❌ Failed to load settings:', error)
    }
  );

  // Update setting mutation
  const { mutate: updateSetting, loading: updating } = useMutation(
    ({ key, value }: { key: string; value: string }) => serverService.updateSetting(key, value),
    {
      onSuccess: () => {
        console.log('✅ Setting updated successfully');
        refetchSettings();
      },
      onError: (error) => console.error('❌ Failed to update setting:', error)
    }
  );

  // Trigger sync mutation
  const { mutate: triggerSync, loading: syncing } = useMutation(
    () => serverService.triggerSync(),
    {
      onSuccess: () => {
        console.log('✅ Sync triggered successfully');
      },
      onError: (error) => console.error('❌ Failed to trigger sync:', error)
    }
  );

  const handleUpdateSetting = async (key: string, value: string) => {
    try {
      await updateSetting({ key, value });
    } catch (error) {
      console.error('Failed to update setting:', error);
    }
  };

  const handleTriggerSync = async () => {
    try {
      await triggerSync();
    } catch (error) {
      console.error('Failed to trigger sync:', error);
    }
  };

  if (settingsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader className="w-8 h-8 animate-spin text-blue-400 mx-auto mb-4" />
          <p className="text-gray-400">Loading server settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <h1 className="text-3xl font-bold text-white">Server Configuration</h1>
          <p className="text-gray-300 mt-2">Manage your WireGuard server settings</p>
        </motion.div>
        
        <motion.button
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          onClick={handleTriggerSync}
          disabled={syncing}
          className="flex items-center space-x-2 px-4 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all mt-4 sm:mt-0 transform hover:scale-105 disabled:opacity-50"
        >
          {syncing ? (
            <>
              <Loader className="w-5 h-5 animate-spin" />
              <span>Syncing...</span>
            </>
          ) : (
            <>
              <Shield className="w-5 h-5" />
              <span>Trigger Sync</span>
            </>
          )}
        </motion.button>
      </div>

      {/* Server Settings */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-6 border border-blue-500/20"
      >
        <h3 className="text-xl font-semibold text-white mb-6 flex items-center">
          <ServerIcon className="w-6 h-6 mr-3 text-blue-400" />
          Server Settings
        </h3>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Basic Settings */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Server IP
              </label>
              <input
                type="text"
                value={settings.server_ip || ''}
                onChange={(e) => handleUpdateSetting('server_ip', e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
                disabled={updating}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                DNS Servers
              </label>
              <input
                type="text"
                value={settings.dns || ''}
                onChange={(e) => handleUpdateSetting('dns', e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
                disabled={updating}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                MTU
              </label>
              <input
                type="number"
                value={settings.mtu || ''}
                onChange={(e) => handleUpdateSetting('mtu', e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
                disabled={updating}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Reset Time (hours)
              </label>
              <input
                type="number"
                value={settings.reset_time || ''}
                onChange={(e) => handleUpdateSetting('reset_time', e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
                placeholder="0 = disabled"
                disabled={updating}
              />
            </div>
          </div>

          {/* Status and Toggles */}
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10">
              <div>
                <p className="text-white font-medium">Server Status</p>
                <p className="text-sm text-gray-400">Enable/disable server</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.status === '1'}
                  onChange={(e) => handleUpdateSetting('status', e.target.checked ? '1' : '0')}
                  className="sr-only peer"
                  disabled={updating}
                />
                <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 peer-disabled:opacity-50"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10">
              <div>
                <p className="text-white font-medium">Auto Backup</p>
                <p className="text-sm text-gray-400">Automatically backup configurations</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.auto_backup === '1'}
                  onChange={(e) => handleUpdateSetting('auto_backup', e.target.checked ? '1' : '0')}
                  className="sr-only peer"
                  disabled={updating}
                />
                <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 peer-disabled:opacity-50"></div>
              </label>
            </div>

            {/* Server Statistics */}
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <h4 className="text-white font-medium mb-3">Server Statistics</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-400">Total Bandwidth</p>
                  <p className="text-white font-medium">{formatBytes(settings.bandwidth || '0')}</p>
                </div>
                <div>
                  <p className="text-gray-400">Uptime</p>
                  <p className="text-white font-medium">{formatUptime(settings.uptime || '0')}</p>
                </div>
              </div>
            </div>

            {/* Alert Messages */}
            {settings.alert && (
              <div className="bg-blue-500/20 border border-blue-500/30 rounded-xl p-4">
                <h4 className="text-blue-300 font-medium mb-2">System Alerts</h4>
                <div className="space-y-1">
                  {JSON.parse(settings.alert).map((alert: string, index: number) => (
                    <p key={index} className="text-sm text-gray-300">{alert}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

// Helper functions
const formatBytes = (bytes: string): string => {
  const b = parseInt(bytes);
  if (b >= 1024 * 1024 * 1024) return `${(b / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (b >= 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(1)} MB`;
  if (b >= 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${b} B`;
};

const formatUptime = (seconds: string): string => {
  const sec = parseInt(seconds);
  const days = Math.floor(sec / 86400);
  const hours = Math.floor((sec % 86400) / 3600);
  const minutes = Math.floor((sec % 3600) / 60);
  
  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};