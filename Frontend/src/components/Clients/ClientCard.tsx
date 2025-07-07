import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Smartphone, Monitor, Tablet, Wifi, WifiOff, Edit, Trash2, Download, ToggleLeft as Toggle, MoreVertical } from 'lucide-react';
import { Client } from '@/types';

interface ClientCardProps {
  client: Client;
  onEdit: (client: Client) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
  disabled?: boolean;
}

const getDeviceIcon = (name: string) => {
  if (name.toLowerCase().includes('phone') || name.toLowerCase().includes('mobile')) {
    return Smartphone;
  } else if (name.toLowerCase().includes('tablet') || name.toLowerCase().includes('ipad')) {
    return Tablet;
  }
  return Monitor;
};

export const ClientCard: React.FC<ClientCardProps> = ({ client, onEdit, onDelete, onToggle, disabled = false }) => {
  const [showMenu, setShowMenu] = useState(false);
  const DeviceIcon = getDeviceIcon(client.name);
  
  const isOnline = client.connected_now;
  const trafficUsedGB = (client.used_trafic.download + client.used_trafic.upload) / (1024 * 1024 * 1024);
  const trafficLimitGB = parseInt(client.traffic) / (1024 * 1024 * 1024);
  const trafficPercent = trafficLimitGB > 0 ? (trafficUsedGB / trafficLimitGB) * 100 : 0;

  const handleDownloadConfig = async () => {
    try {
      console.log('📥 Downloading config for client:', client.name);
      // This would be handled by the parent component
    } catch (error) {
      console.error('Failed to download config:', error);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-all ${disabled ? 'opacity-50' : ''}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`p-3 rounded-lg ${client.status ? 'bg-blue-500/20' : 'bg-gray-500/20'}`}>
            <DeviceIcon className={`w-5 h-5 ${client.status ? 'text-blue-400' : 'text-gray-400'}`} />
          </div>
          <div>
            <h3 className="text-white font-semibold">{client.name}</h3>
            <p className="text-sm text-gray-400">{client.address}</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2">
            {isOnline ? (
              <Wifi className="w-4 h-4 text-green-400" />
            ) : (
              <WifiOff className="w-4 h-4 text-gray-500" />
            )}
            <span className={`text-xs px-2 py-1 rounded-full ${
              isOnline 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-gray-500/20 text-gray-400'
            }`}>
              {isOnline ? 'Online' : 'Offline'}
            </span>
          </div>
          
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              disabled={disabled}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
            >
              <MoreVertical className="w-4 h-4 text-gray-400" />
            </button>
            
            {showMenu && !disabled && (
              <div className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-10">
                <button
                  onClick={() => {
                    onEdit(client);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-gray-300 hover:bg-gray-700 flex items-center space-x-2"
                >
                  <Edit className="w-4 h-4" />
                  <span>Edit</span>
                </button>
                <button
                  onClick={() => {
                    onToggle(client.name, !client.status);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-gray-300 hover:bg-gray-700 flex items-center space-x-2"
                >
                  <Toggle className="w-4 h-4" />
                  <span>{client.status ? 'Disable' : 'Enable'}</span>
                </button>
                <button 
                  onClick={() => {
                    handleDownloadConfig();
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-gray-300 hover:bg-gray-700 flex items-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>Download Config</span>
                </button>
                <button
                  onClick={() => {
                    onDelete(client.name);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-red-400 hover:bg-gray-700 flex items-center space-x-2"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Delete</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-400">Upload</p>
            <p className="text-white font-medium">{(client.used_trafic.upload / 1024 / 1024).toFixed(1)} MB</p>
          </div>
          <div>
            <p className="text-gray-400">Download</p>
            <p className="text-white font-medium">{(client.used_trafic.download / 1024 / 1024).toFixed(1)} MB</p>
          </div>
        </div>

        {trafficLimitGB > 0 && (
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-400">Traffic Usage</span>
              <span className="text-white">{trafficPercent.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${trafficPercent > 80 ? 'bg-red-500' : trafficPercent > 60 ? 'bg-yellow-500' : 'bg-blue-500'}`}
                style={{ width: `${Math.min(trafficPercent, 100)}%` }}
              />
            </div>
          </div>
        )}

        <div className="text-sm">
          <p className="text-gray-400">Expires</p>
          <p className="text-white">{new Date(client.expires).toLocaleDateString()}</p>
        </div>
      </div>
    </motion.div>
  );
};