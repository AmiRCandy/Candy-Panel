import React from 'react';
import { motion } from 'framer-motion';
import { Users, Server, Activity, Download, Globe, Loader } from 'lucide-react';
import { StatsCard } from '@/components/Dashboard/StatsCard';
import { BandwidthChart } from '@/components/Dashboard/BandwidthChart';
import { serverService } from '@/services/serverService';
import { useApi } from '@/hooks/useApi'; // Import useApi

export const Dashboard: React.FC = () => {
  // Fetch server stats using the useApi hook
  const { data: stats, loading: statsLoading, error, refetch } = useApi(
    () => serverService.getDashboardStats(),
    {
      onSuccess: (data) => console.log('✅ Dashboard stats loaded:', data),
      onError: (err) => console.error('❌ Failed to load dashboard stats:', err),
    }
  );

  const formatUptime = (seconds: string): string => {
    const sec = parseInt(seconds);
    const days = Math.floor(sec / 86400);
    const hours = Math.floor((sec % 86400) / 3600);
    const minutes = Math.floor((sec % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatBandwidth = (bytes: string): string => {
    const b = parseInt(bytes);
    if (isNaN(b)) return '0 B'; // Handle cases where bytes might be invalid
    if (b >= 1024 * 1024 * 1024) return `${(b / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    if (b >= 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(1)} MB`;
    if (b >= 1024) return `${(b / 1024).toFixed(1)} KB`;
    return `${b} B`;
  };

  // Default stats values to prevent errors if data is null during loading
  const defaultStats = {
    cpu: '0%',
    mem: { usage: '0%' },
    clients_count: 0,
    bandwidth: '0',
    uptime: '0',
    net: { download: '0 KB/s', upload: '0 KB/s' },
    status: '0', // Default to '0' (stopped)
    alert: [],
  };

  const currentStats = stats || defaultStats;

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="text-red-400 mb-4">❌ Failed to load dashboard data</div>
          <p className="text-gray-400 mb-4">{error}</p>
          <button
            onClick={refetch}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Retry
          </button>
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
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 mt-1">Monitor your WireGuard server and clients</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center space-x-2 mt-4 sm:mt-0"
        >
          <div className={`w-3 h-3 rounded-full ${currentStats.status === '1' ? 'bg-green-400' : 'bg-red-400'} ${statsLoading ? 'animate-pulse' : ''}`} />
          <span className="text-sm text-gray-400">
            Server {statsLoading ? 'Loading...' : currentStats.status === '1' ? 'Running' : 'Stopped'}
          </span>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        <StatsCard
          title="Active Clients"
          value={statsLoading ? '...' : currentStats.clients_count.toString()}
          change="+2 from last week"
          icon={Users}
          color="blue"
        />
        <StatsCard
          title="Total Bandwidth"
          value={statsLoading ? '...' : formatBandwidth(currentStats.bandwidth)}
          change="+12% from last month"
          icon={Globe}
          color="purple"
        />
        <StatsCard
          title="CPU Usage"
          value={statsLoading ? '...' : currentStats.cpu}
          change="Normal"
          icon={Activity}
          color="green"
        />
        <StatsCard
          title="Server Uptime"
          value={statsLoading ? '...' : formatUptime(currentStats.uptime)}
          change="Excellent"
          icon={Server}
          color="blue"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <BandwidthChart />
      </div>

      <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <button className="p-4 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg transition-colors text-left">
            <Users className="w-6 h-6 text-blue-400 mb-2" />
            <p className="text-white font-medium">Add Client</p>
            <p className="text-sm text-gray-400">Create new connection</p>
          </button>
          <button className="p-4 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 rounded-lg transition-colors text-left">
            <Server className="w-6 h-6 text-purple-400 mb-2" />
            <p className="text-white font-medium">Server Config</p>
            <p className="text-sm text-gray-400">Manage server settings</p>
          </button>
          <button className="p-4 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded-lg transition-colors text-left">
            <Download className="w-6 h-6 text-green-400 mb-2" />
            <p className="text-white font-medium">Export Configs</p>
            <p className="text-sm text-gray-400">Download all configs</p>
          </button>
          <button className="p-4 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-lg transition-colors text-left">
            <Activity className="w-6 h-6 text-red-400 mb-2" />
            <p className="text-white font-medium">View Logs</p>
            <p className="text-sm text-gray-400">Check server logs</p>
          </button>
        </div>
      </div>
    </div>
  );
};
