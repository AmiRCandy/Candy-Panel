import React from 'react';
import { motion } from 'framer-motion';
import { Smartphone, Monitor, Tablet, Wifi, WifiOff } from 'lucide-react';
import { Client } from '@/types';

interface ClientsTableProps {
  clients: Client[];
  loading?: boolean;
}

const getDeviceIcon = (name: string) => {
  if (name.toLowerCase().includes('phone') || name.toLowerCase().includes('mobile')) {
    return Smartphone;
  } else if (name.toLowerCase().includes('tablet') || name.toLowerCase().includes('ipad')) {
    return Tablet;
  }
  return Monitor;
};

export const ClientsTable: React.FC<ClientsTableProps> = ({ clients, loading = false }) => {
  if (loading) {
    return (
      <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Recent Clients</h3>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700 animate-pulse">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gray-700 rounded-lg"></div>
                <div>
                  <div className="w-24 h-4 bg-gray-700 rounded mb-1"></div>
                  <div className="w-32 h-3 bg-gray-700 rounded"></div>
                </div>
              </div>
              <div className="w-16 h-6 bg-gray-700 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Recent Clients</h3>
      <div className="space-y-3">
        {clients.slice(0, 5).map((client, index) => {
          const DeviceIcon = getDeviceIcon(client.name);
          const isOnline = client.connected_now;
          
          return (
            <motion.div
              key={client.name}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700"
            >
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-gray-700 rounded-lg">
                  <DeviceIcon className="w-4 h-4 text-gray-400" />
                </div>
                <div>
                  <p className="text-white font-medium">{client.name}</p>
                  <p className="text-sm text-gray-400">{client.address}</p>
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <p className="text-sm text-gray-400">
                    {(client.used_trafic.download / 1024 / 1024).toFixed(1)} MB
                  </p>
                  <p className="text-xs text-gray-500">Downloaded</p>
                </div>
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
              </div>
            </motion.div>
          );
        })}
        
        {clients.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-400">No clients found</p>
            <p className="text-sm text-gray-500 mt-1">Add your first client to get started</p>
          </div>
        )}
      </div>
    </div>
  );
};