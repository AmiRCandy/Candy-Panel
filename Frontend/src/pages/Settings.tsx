import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings as SettingsIcon, User, Shield, Bell, Palette, Download, Upload } from 'lucide-react';
import { BackendConfig } from '@/components/Settings/BackendConfig';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState({
    username: 'admin',
    email: 'admin@candypanel.com',
    notifications: true,
    darkMode: true,
    autoBackup: true,
    backupInterval: 24,
    maxClients: 100,
    sessionTimeout: 30
  });

  const handleSave = () => {
    console.log('Saving settings:', settings);
  };

  const handleExportConfig = () => {
    const config = {
      server: {
        publicIP: '192.168.1.100',
        port: 51820,
        dns: '1.1.1.1'
      },
      clients: []
    };
    
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'candy-panel-config.json';
    a.click();
  };

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
      >
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-300 mt-2">Manage your Candy Panel configuration</p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Backend Configuration */}
        <BackendConfig />

        {/* User Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-6 border border-purple-500/20"
        >
          <h3 className="text-xl font-semibold text-white mb-6 flex items-center">
            <User className="w-6 h-6 mr-3 text-purple-400" />
            User Profile
          </h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Username
              </label>
              <input
                type="text"
                value={settings.username}
                onChange={(e) => setSettings({ ...settings, username: e.target.value })}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email
              </label>
              <input
                type="email"
                value={settings.email}
                onChange={(e) => setSettings({ ...settings, email: e.target.value })}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                New Password
              </label>
              <input
                type="password"
                placeholder="Leave blank to keep current password"
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none backdrop-blur-sm"
              />
            </div>
          </div>
        </motion.div>

        {/* Security Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass rounded-2xl p-6 border border-green-500/20"
        >
          <h3 className="text-xl font-semibold text-white mb-6 flex items-center">
            <Shield className="w-6 h-6 mr-3 text-green-400" />
            Security
          </h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Session Timeout (minutes)
              </label>
              <input
                type="number"
                value={settings.sessionTimeout}
                onChange={(e) => setSettings({ ...settings, sessionTimeout: Number(e.target.value) })}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Maximum Clients
              </label>
              <input
                type="number"
                value={settings.maxClients}
                onChange={(e) => setSettings({ ...settings, maxClients: Number(e.target.value) })}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
              />
            </div>

            <div className="bg-yellow-500/20 border border-yellow-500/30 rounded-xl p-4">
              <h4 className="text-yellow-300 font-medium mb-2">Two-Factor Authentication</h4>
              <p className="text-sm text-gray-300 mb-3">Add an extra layer of security to your account</p>
              <button className="px-4 py-2 bg-yellow-500/20 text-yellow-300 rounded-lg hover:bg-yellow-500/30 transition-colors">
                Enable 2FA
              </button>
            </div>
          </div>
        </motion.div>

        {/* System Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass rounded-2xl p-6 border border-orange-500/20"
        >
          <h3 className="text-xl font-semibold text-white mb-6 flex items-center">
            <SettingsIcon className="w-6 h-6 mr-3 text-orange-400" />
            System
          </h3>
          
          <div className="space-y-6">
            <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10">
              <div>
                <p className="text-white font-medium">Notifications</p>
                <p className="text-sm text-gray-400">Receive system alerts and updates</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.notifications}
                  onChange={(e) => setSettings({ ...settings, notifications: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
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
                  checked={settings.autoBackup}
                  onChange={(e) => setSettings({ ...settings, autoBackup: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {settings.autoBackup && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Backup Interval (hours)
                </label>
                <input
                  type="number"
                  value={settings.backupInterval}
                  onChange={(e) => setSettings({ ...settings, backupInterval: Number(e.target.value) })}
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
                />
              </div>
            )}

            <div className="space-y-4">
              <button
                onClick={handleExportConfig}
                className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-500/20 text-blue-300 rounded-xl hover:bg-blue-500/30 transition-colors border border-blue-500/30"
              >
                <Download className="w-5 h-5" />
                <span>Export Configuration</span>
              </button>

              <button className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-green-500/20 text-green-300 rounded-xl hover:bg-green-500/30 transition-colors border border-green-500/30">
                <Upload className="w-5 h-5" />
                <span>Import Configuration</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all font-medium transform hover:scale-105"
        >
          Save Settings
        </button>
      </div>
    </div>
  );
};