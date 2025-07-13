import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Server as ServerIcon, // Renamed to avoid conflict with interface Server
  Users,
  Settings,
  Activity,
  Plus,
  Edit,
  Trash2,
  Download,
  Eye,
  EyeOff,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  HardDrive,
  Cpu,
  Network,
  LogOut,
  Shield,
  Link2,
  Bot,
  Key,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { apiClient } from './utils/api';
import { Client, Interface, AllData, ApiTokens, Server, DashboardStats } from './types';

interface TabButtonProps {
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  onClick: () => void;
}
const API_BASE_URL = `${window.location.protocol}//${window.location.host}`;
const TabButton: React.FC<TabButtonProps> = ({ icon, label, isActive, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-300 transform hover:scale-105 ${
      isActive
        ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/25'
        : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
    }`}
  >
    {icon}
    <span className="hidden sm:inline">{label}</span>
  </button>
);

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatUptime = (seconds: number): string => {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [data, setData] = useState<AllData | null>(null); // Data for the selected server
  const [allServers, setAllServers] = useState<Server[]>([]); // List of all registered servers
  const [selectedServerId, setSelectedServerId] = useState<number | null>(null); // Currently selected server
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const initialLoadRef = useRef(true);

  // Auth form states
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Install form states (for central panel installation)
  const [serverIp, setServerIp] = useState('');
  const [wgPort, setWgPort] = useState('51820');
  const [wgAddressRange, setWgAddressRange] = useState('10.0.0.1/24');
  const [wgDns, setWgDns] = useState('8.8.8.8');
  const [adminUser, setAdminUser] = useState('admin');
  const [adminPassword, setAdminPassword] = useState('admin');

  // Client form states
  const [showClientForm, setShowClientForm] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [clientName, setClientName] = useState('');
  const [clientExpires, setClientExpires] = useState('');
  const [clientTraffic, setClientTraffic] = useState('');
  const [clientWgId, setClientWgId] = useState('0'); // WG interface ID on the remote server
  const [clientNote, setClientNote] = useState('');
  const [clientStatus, setClientStatus] = useState(true);

  // Interface form states
  const [showInterfaceForm, setShowInterfaceForm] = useState(false);
  const [interfaceAddressRange, setInterfaceAddressRange] = useState('');
  const [interfacePort, setInterfacePort] = useState('');
  const [showEditInterfaceForm, setShowEditInterfaceForm] = useState(false);
  const [editingInterface, setEditingInterface] = useState<Interface | null>(null);
  const [editInterfaceAddressRange, setEditInterfaceAddressRange] = useState('');
  const [editInterfacePort, setEditInterfacePort] = useState('');
  const [editInterfaceStatus, setEditInterfaceStatus] = useState(true);

  // Server management form states
  const [showAddServerForm, setShowAddServerForm] = useState(false);
  const [newServerName, setNewServerName] = useState('');
  const [newServerIp, setNewServerIp] = useState('');
  const [newAgentPort, setNewAgentPort] = useState('3447');
  const [newApiKey, setNewApiKey] = useState('');
  const [newServerDescription, setNewServerDescription] = useState('');
  const [showEditServerForm, setShowEditServerForm] = useState(false);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const [editServerName, setEditServerName] = useState('');
  const [editServerIp, setEditServerIp] = useState('');
  const [editAgentPort, setEditAgentPort] = useState('');
  const [editApiKey, setEditApiKey] = useState(''); // Allow editing API key if needed
  const [editServerDescription, setEditServerDescription] = useState('');
  const [editServerStatus, setEditServerStatus] = useState<string>('active');

  // Settings states
  const [settingsValues, setSettingsValues] = useState<Record<string, string>>({});
  const [stagedSettings, setStagedSettings] = useState<Record<string, string>>({});
  const [apiTokens, setApiTokens] = useState<ApiTokens>({});
  const [newApiTokenName, setNewApiTokenName] = useState('');
  const [newApiTokenValue, setNewApiTokenValue] = useState('');
  const [showApiTokenForm, setShowApiTokenForm] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      // Load all servers first
      loadServers();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated && selectedServerId !== null) {
      // Load data for the selected server
      loadServerData(selectedServerId, true); // Initial load for selected server
      const interval = setInterval(() => {
        if (activeTab === 'dashboard' || activeTab === 'clients') {
          loadServerData(selectedServerId, false); // Subsequent loads, don't show full loading
        }
      }, 5000); // Fetch every 5 seconds
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, selectedServerId, activeTab]);


  const checkAuth = async () => {
    try {
      const { installed } = await apiClient.checkInstallation();
      setIsInstalled(installed);

      if (installed && apiClient.isAuthenticated()) {
        setIsAuthenticated(true);
      } else {
        setLoading(false);
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      setLoading(false);
    }
  };

  const loadServers = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getServers();
      if (response.success && response.data) {
        setAllServers(response.data.servers);
        if (response.data.servers.length > 0 && selectedServerId === null) {
          // Auto-select the first server if none is selected
          setSelectedServerId(response.data.servers[0].server_id);
        } else if (response.data.servers.length === 0) {
          setSelectedServerId(null); // No servers to select
        }
      } else {
        setError(response.message || 'Failed to load servers.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load servers');
      console.error('Error loading servers:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadServerData = async (serverId: number, showFullLoading = true) => {
    if (showFullLoading || initialLoadRef.current) {
      setLoading(true);
    }
    try {
      const response = await apiClient.getServerData(serverId);
      if (response.success && response.data) {
        setData(response.data);
        setSettingsValues(response.data.settings); // Central settings
        setStagedSettings(response.data.settings); // Initialize staged settings
        try {
          const parsedApiTokens = JSON.parse(response.data.settings.api_tokens || '{}');
          setApiTokens(parsedApiTokens);
        } catch (e) {
          console.error("Failed to parse API tokens from settings:", e);
          setApiTokens({});
        }
      } else {
        if (showFullLoading) {
          setError(response.message || `Failed to load data for server ${serverId}.`);
          setData(null); // Clear data if loading fails
        }
      }
    } catch (err) {
      if (showFullLoading) {
        setError(err instanceof Error ? err.message : `Failed to load data for server ${serverId}`);
        setData(null); // Clear data if loading fails
      }
      console.error(`Error loading data for server ${serverId}:`, err);
    } finally {
      if (showFullLoading || initialLoadRef.current) {
        setLoading(false);
        initialLoadRef.current = false;
      }
    }
  };

  const showMessage = (message: string, isError = false) => {
    if (isError) {
      setError(message);
      setSuccess('');
    } else {
      setSuccess(message);
      setError('');
    }
    setTimeout(() => {
      setError('');
      setSuccess('');
    }, 4000);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const response = await apiClient.login(username, password);
      if (response.success) {
        setIsAuthenticated(true);
        showMessage('Login successful!');
        // loadServers will be called by useEffect after isAuthenticated changes
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Login failed', true);
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const response = await apiClient.install({
        server_ip: serverIp,
        wg_port: wgPort,
        wg_address_range: wgAddressRange,
        wg_dns: wgDns,
        admin_user: adminUser,
        admin_password: adminPassword,
      });
      if (response.success) {
        setIsInstalled(true);
        showMessage('Installation completed successfully!');
        // checkAuth will re-run and handle authentication after install
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Installation failed', true);
    } finally {
      setLoading(false);
    }
  };

  const handleClientSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedServerId === null) {
      showMessage('Please select a server first.', true);
      return;
    }
    try {
      setLoading(true);
      const trafficInBytes = (parseFloat(clientTraffic) * 1024 * 1024).toString();
      if (editingClient) {
        const response = await apiClient.updateClient(selectedServerId, {
          name: editingClient.name,
          expires: clientExpires,
          traffic: trafficInBytes,
          note: clientNote,
          status: clientStatus,
        });
        if (response.success) {
          showMessage('Client updated successfully!');
        }
      } else {
        const response = await apiClient.createClient(selectedServerId, {
          name: clientName,
          expires: clientExpires,
          traffic: trafficInBytes,
          wg_id: parseInt(clientWgId),
          note: clientNote,
        });
        if (response.success) {
          showMessage('Client created successfully!');
        }
      }

      resetClientForm();
      await loadServerData(selectedServerId);
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Operation failed', true);
    } finally {
      setLoading(false);
    }
  };

  const handleInterfaceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedServerId === null) {
      showMessage('Please select a server first.', true);
      return;
    }
    try {
      setLoading(true);
      const response = await apiClient.createInterface(selectedServerId, {
        address_range: interfaceAddressRange,
        port: parseInt(interfacePort),
      });
      if (response.success) {
        showMessage('Interface created successfully!');
        setShowInterfaceForm(false);
        setInterfaceAddressRange('');
        setInterfacePort('');
        await loadServerData(selectedServerId);
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Interface creation failed', true);
    } finally {
      setLoading(false);
    }
  };

  const resetClientForm = () => {
    setShowClientForm(false);
    setEditingClient(null);
    setClientName('');
    setClientExpires('');
    setClientTraffic('');
    setClientWgId('0');
    setClientNote('');
    setClientStatus(true);
  };

  const editClient = (client: Client) => {
    setEditingClient(client);
    setClientName(client.name);
    setClientExpires(client.expires.split('T')[0]);
    setClientTraffic(client.traffic);
    setClientWgId(client.wg ? client.wg.toString() : '0'); // Ensure wg_id is string
    setClientNote(client.note);
    setClientStatus(client.status);
    setShowClientForm(true);
  };

  const deleteClient = async (clientName: string) => {
    if (!confirm(`Are you sure you want to delete client "${clientName}" from server ${selectedServerId}?`)) return;
    if (selectedServerId === null) {
      showMessage('No server selected.', true);
      return;
    }

    try {
      setLoading(true);
      const response = await apiClient.deleteClient(selectedServerId, clientName);
      if (response.success) {
        showMessage('Client deleted successfully!');
        await loadServerData(selectedServerId);
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Delete failed', true);
    } finally {
      setLoading(false);
    }
  };

  const downloadConfig = async (clientName: string) => {
    if (selectedServerId === null) {
      showMessage('No server selected.', true);
      return;
    }
    try {
      const response = await apiClient.getClientConfig(selectedServerId, clientName);
      if (response.success && response.data) {
        const blob = new Blob([response.data.config], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${clientName}.conf`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Download failed', true);
    }
  };

  const shortLink = async (name: string, public_key: string) => {
    try {
      // The shortlink doesn't contain server_id directly, it relies on the backend's
      // _get_client_by_name_and_public_key to search across servers.
      window.open(`${API_BASE_URL}/client-details/${name}/${public_key}`, '_blank');
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to generate shortlink', true);
    }
  };

  const handleSync = async () => {
    if (selectedServerId === null) {
      showMessage('Please select a server to sync.', true);
      return;
    }
    setLoading(true);
    try {
      // Apply staged settings first (these are central settings)
      for (const key in stagedSettings) {
        if (stagedSettings.hasOwnProperty(key) && settingsValues[key] !== stagedSettings[key]) {
          await apiClient.updateSetting(key, stagedSettings[key]);
        }
      }
      
      const response = await apiClient.sync(selectedServerId); // Sync on selected server
      if (response.success) {
        showMessage('Sync completed successfully!');
        await loadServerData(selectedServerId); // Reload selected server data
        await loadServers(); // Reload server list to get updated statuses/caches
      } else {
        showMessage(response.message || 'Sync failed.', true);
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Sync failed', true);
    } finally {
      setLoading(false);
    }
  };

  const updateStagedSetting = (key: string, value: string) => {
    setStagedSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleAddApiToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newApiTokenName || !newApiTokenValue) {
      showMessage('Please provide both name and token.', true);
      return;
    }
    try {
      setLoading(true);
      const response = await apiClient.addApiToken(newApiTokenName, newApiTokenValue);
      if (response.success) {
        showMessage('API token added/updated successfully!');
        setNewApiTokenName('');
        setNewApiTokenValue('');
        setShowApiTokenForm(false);
        await loadServerData(selectedServerId!); // Reload to update settings display
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to add/update API token', true);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteApiToken = async (name: string) => {
    if (!confirm(`Are you sure you want to delete API token "${name}"?`)) return;
    try {
      setLoading(true);
      const response = await apiClient.deleteApiToken(name);
      if (response.success) {
        showMessage('API token deleted successfully!');
        await loadServerData(selectedServerId!); // Reload to update settings display
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to delete API token', true);
    } finally {
      setLoading(false);
    }
  };

  const editInterface = (iface: Interface) => {
    setEditingInterface(iface);
    setEditInterfaceAddressRange(iface.address_range);
    setEditInterfacePort(iface.port.toString());
    setEditInterfaceStatus(iface.status);
    setShowEditInterfaceForm(true);
  };

  const handleEditInterfaceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingInterface || selectedServerId === null) {
      showMessage('No interface or server selected.', true);
      return;
    }

    try {
      setLoading(true);
      const response = await apiClient.updateInterface(selectedServerId, `wg${editingInterface.wg}`, {
        address: editInterfaceAddressRange,
        port: parseInt(editInterfacePort),
        status: editInterfaceStatus,
      });
      if (response.success) {
        showMessage('Interface updated successfully!');
        setShowEditInterfaceForm(false);
        setEditingInterface(null);
        await loadServerData(selectedServerId);
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Interface update failed', true);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteInterface = async (wg_id: number) => {
    if (!confirm(`Are you sure you want to delete WireGuard interface wg${wg_id} and all its associated clients from server ${selectedServerId}? This action cannot be undone.`)) return;
    if (selectedServerId === null) {
      showMessage('No server selected.', true);
      return;
    }
    try {
      setLoading(true);
      const response = await apiClient.deleteInterface(selectedServerId, wg_id);
      if (response.success) {
        showMessage(`Interface wg${wg_id} deleted successfully!`);
        await loadServerData(selectedServerId);
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to delete interface', true);
    } finally {
      setLoading(false);
    }
  };

  const handleAddServerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const response = await apiClient.addServer({
        name: newServerName,
        ip_address: newServerIp,
        agent_port: parseInt(newAgentPort),
        api_key: newApiKey,
        description: newServerDescription,
      });
      if (response.success) {
        showMessage('Server added successfully!');
        setShowAddServerForm(false);
        setNewServerName('');
        setNewServerIp('');
        setNewAgentPort('3447');
        setNewApiKey('');
        setNewServerDescription('');
        await loadServers(); // Reload server list
        if (response.data && response.data.server_id && selectedServerId === null) {
          setSelectedServerId(response.data.server_id); // Auto-select newly added if no other selected
        }
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to add server', true);
    } finally {
      setLoading(false);
    }
  };

  const editServer = (server: Server) => {
    setEditingServer(server);
    setEditServerName(server.name);
    setEditServerIp(server.ip_address);
    setEditAgentPort(server.agent_port.toString());
    setEditApiKey(server.api_key || ''); // Pre-fill if exists (though usually not returned)
    setEditServerDescription(server.description);
    setEditServerStatus(server.status);
    setShowEditServerForm(true);
  };

  const handleEditServerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingServer) return;

    try {
      setLoading(true);
      const updateData: Partial<Server> = {
        name: editServerName,
        ip_address: editServerIp,
        agent_port: parseInt(editAgentPort),
        api_key: editApiKey,
        description: editServerDescription,
        status: editServerStatus,
      };
      const response = await apiClient.updateServer(editingServer.server_id, updateData);
      if (response.success) {
        showMessage('Server updated successfully!');
        setShowEditServerForm(false);
        setEditingServer(null);
        await loadServers(); // Reload server list to reflect changes
        if (selectedServerId === editingServer.server_id) {
          await loadServerData(selectedServerId); // Reload data for the selected server if it was updated
        }
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to update server', true);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteServer = async (serverId: number, serverName: string) => {
    if (!confirm(`Are you sure you want to delete server "${serverName}" (ID: ${serverId}) and all its associated clients and interfaces? This action cannot be undone.`)) return;

    try {
      setLoading(true);
      const response = await apiClient.deleteServer(serverId);
      if (response.success) {
        showMessage('Server deleted successfully!');
        await loadServers(); // Reload server list
        if (selectedServerId === serverId) {
          setSelectedServerId(null); // Deselect if the deleted server was active
          setData(null); // Clear displayed data
        }
      }
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to delete server', true);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    apiClient.logout();
    setIsAuthenticated(false);
    setData(null);
    setAllServers([]);
    setSelectedServerId(null);
    setLoading(false);
    initialLoadRef.current = true;
  };

  const currentServer = useMemo(() => {
    return allServers.find(server => server.server_id === selectedServerId);
  }, [allServers, selectedServerId]);

  // Aggregate dashboard stats from all servers for the overview dashboard tab
  const aggregatedDashboardStats: DashboardStats | null = useMemo(() => {
    if (!allServers || allServers.length === 0) return null;

    let totalClients = 0;
    let totalDownload = 0; // in KB/s
    let totalUpload = 0;   // in KB/s
    const overallStatus: string[] = [];
    const overallAlerts: string[] = [];
    let centralCpu = 'N/A';
    let centralMem = { total: 'N/A', available: 'N/A', usage: 'N/A' };
    let centralUptime = 'N/A';

    allServers.forEach(server => {
      if (server.dashboard_cache) {
        totalClients += server.dashboard_cache.clients_count || 0;
        try {
          totalDownload += parseFloat(server.dashboard_cache.net.download.replace(' KB/s', '')) || 0;
          totalUpload += parseFloat(server.dashboard_cache.net.upload.replace(' KB/s', '')) || 0;
        } catch {} // Ignore parsing errors

        overallStatus.push(server.dashboard_cache.status);
        if (server.dashboard_cache.alert && server.dashboard_cache.alert.length > 0) {
            overallAlerts.push(...server.dashboard_cache.alert);
        }

        // For central CPU/Mem/Uptime, just take from the first active server found, or keep N/A
         if (server.status === 'active' && centralCpu === 'N/A') {
          centralCpu = server.dashboard_cache?.cpu || centralCpu;
          centralMem = server.dashboard_cache?.mem || centralMem; // Fix applied here
          centralUptime = server.dashboard_cache?.uptime || centralUptime;
        }
      }
    });

    // Determine overall status
    let combinedStatus = 'Unknown';
    if (allServers.some(s => s.status === 'unreachable')) {
        combinedStatus = 'Partially Unreachable';
    } else if (allServers.some(s => s.status === 'error')) {
        combinedStatus = 'Partially Errored';
    } else if (allServers.every(s => s.status === 'active')) {
        combinedStatus = 'All Active';
    } else if (allServers.length > 0) {
        combinedStatus = 'Mixed Status';
    }


    return {
      cpu: centralCpu,
      mem: centralMem,
      clients_count: totalClients,
      status: combinedStatus,
      alert: Array.from(new Set(overallAlerts)), // Unique alerts
      bandwidth: data?.dashboard.bandwidth || '0', // This needs to be sum from all servers too, or central setting
      uptime: centralUptime,
      net: {
        download: `${totalDownload.toFixed(2)} KB/s`,
        upload: `${totalUpload.toFixed(2)} KB/s`,
      },
    };
  }, [allServers, data]); // Depend on allServers and also data (for bandwidth if it's central)


  if (!isInstalled) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="bg-gray-800 rounded-2xl shadow-2xl p-8 w-full max-w-lg border border-gray-700 animate-fade-in">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-600 rounded-2xl mx-auto mb-4 flex items-center justify-center animate-pulse-slow">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Candy Panel</h1>
            <p className="text-gray-400">Install WireGuard Server</p>
          </div>

          <form onSubmit={handleInstall} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Server IP</label>
                <input
                  type="text"
                  value={serverIp}
                  onChange={(e) => setServerIp(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                  placeholder="192.168.1.100"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">WireGuard Port</label>
                <input
                  type="number"
                  value={wgPort}
                  onChange={(e) => setWgPort(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                  placeholder="51820"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Address Range</label>
                <input
                  type="text"
                  value={wgAddressRange}
                  onChange={(e) => setWgAddressRange(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                  placeholder="10.0.0.1/24"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">DNS Server</label>
                <input
                  type="text"
                  value={wgDns}
                  onChange={(e) => setWgDns(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                  placeholder="8.8.8.8"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Admin Username</label>
                <input
                  type="text"
                  value={adminUser}
                  onChange={(e) => setAdminUser(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Admin Password</label>
                <input
                  type="password"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Installing...
                </>
              ) : (
                'Install WireGuard Server'
              )}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-300 text-sm animate-slide-in">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            </div>
          )}
          {success && (
            <div className="mt-4 p-3 bg-green-900/50 border border-green-700 rounded-lg text-green-300 text-sm animate-slide-in">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                {success}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="bg-gray-800 rounded-2xl shadow-2xl p-8 w-full max-w-md border border-gray-700 animate-fade-in">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-600 rounded-2xl mx-auto mb-4 flex items-center justify-center animate-pulse-slow">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Candy Panel</h1>
            <p className="text-gray-400">Sign in to your account</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 pr-10 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300 transition-colors duration-200"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-300 text-sm animate-slide-in">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Common UI for server selection / management
  const renderServerManagement = () => (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-xl font-bold text-white">Server Management</h2>
        <button
          onClick={() => setShowAddServerForm(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-all duration-200 transform hover:scale-105"
        >
          <Plus className="w-4 h-4" />
          Add Server
        </button>
      </div>

      {/* Add Server Form Modal */}
      {showAddServerForm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700 animate-scale-in">
            <h3 className="text-lg font-semibold mb-4 text-white">Add New Server</h3>
            <form onSubmit={handleAddServerSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Server Name</label>
                <input type="text" value={newServerName} onChange={(e) => setNewServerName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Server IP/Hostname</label>
                <input type="text" value={newServerIp} onChange={(e) => setNewServerIp(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" placeholder="192.168.1.100" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Agent Port</label>
                <input type="number" value={newAgentPort} onChange={(e) => setNewAgentPort(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" placeholder="3447" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Agent API Key</label>
                <input type="text" value={newApiKey} onChange={(e) => setNewApiKey(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Description (Optional)</label>
                <textarea value={newServerDescription} onChange={(e) => setNewServerDescription(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" rows={2} />
              </div>
              <div className="flex gap-2">
                <button type="submit" disabled={loading}
                  className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-all duration-200 transform hover:scale-105">
                  {loading ? 'Adding...' : 'Add Server'}
                </button>
                <button type="button" onClick={() => setShowAddServerForm(false)}
                  className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-all duration-200 transform hover:scale-105">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Server Form Modal */}
      {showEditServerForm && editingServer && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700 animate-scale-in">
            <h3 className="text-lg font-semibold mb-4 text-white">Edit Server: {editingServer.name}</h3>
            <form onSubmit={handleEditServerSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Server Name</label>
                <input type="text" value={editServerName} onChange={(e) => setEditServerName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Server IP/Hostname</label>
                <input type="text" value={editServerIp} onChange={(e) => setEditServerIp(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Agent Port</label>
                <input type="number" value={editAgentPort} onChange={(e) => setEditAgentPort(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Agent API Key</label>
                <input type="text" value={editApiKey} onChange={(e) => setEditApiKey(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" />
                <p className="text-xs text-gray-500 mt-1">Leave empty if not changing.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                <textarea value={editServerDescription} onChange={(e) => setEditServerDescription(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white" rows={2} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                <select
                  value={editServerStatus}
                  onChange={(e) => setEditServerStatus(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="unreachable">Unreachable</option>
                  <option value="error">Error</option>
                </select>
              </div>
              <div className="flex gap-2">
                <button type="submit" disabled={loading}
                  className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-all duration-200 transform hover:scale-105">
                  {loading ? 'Updating...' : 'Update Server'}
                </button>
                <button type="button" onClick={() => setShowEditServerForm(false)}
                  className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-all duration-200 transform hover:scale-105">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700">
        <div className="p-6 border-b border-gray-700">
          <h3 className="font-semibold text-white">Managed Servers</h3>
        </div>
        <div className="p-6">
          {allServers.length === 0 ? (
            <div className="text-center py-8">
              <ServerIcon className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No servers added yet</p>
              <p className="text-sm text-gray-500 mt-1">Add your first server to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700/50 border-b border-gray-700">
                  <tr>
                    <th className="text-left p-4 font-medium text-gray-300">Name</th>
                    <th className="text-left p-4 font-medium text-gray-300">IP:Port</th>
                    <th className="text-left p-4 font-medium text-gray-300">Status</th>
                    <th className="text-left p-4 font-medium text-gray-300">Last Synced</th>
                    <th className="text-left p-4 font-medium text-gray-300">Description</th>
                    <th className="text-left p-4 font-medium text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {allServers.map((server) => (
                    <tr key={server.server_id} className="hover:bg-gray-700/30 transition-colors duration-200">
                      <td className="p-4">
                        <p className="font-medium text-white">{server.name}</p>
                        <p className="text-xs text-gray-500">ID: {server.server_id}</p>
                      </td>
                      <td className="p-4 text-sm text-gray-300">{server.ip_address}:{server.agent_port}</td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${server.status === 'active' ? 'bg-green-500 animate-pulse' : server.status === 'unreachable' ? 'bg-red-500' : 'bg-gray-500'}`} />
                          <span className="text-sm text-gray-300 capitalize">{server.status}</span>
                        </div>
                      </td>
                      <td className="p-4 text-sm text-gray-300">
                        {server.last_synced ? new Date(server.last_synced).toLocaleString() : 'Never'}
                      </td>
                      <td className="p-4 text-sm text-gray-300">{server.description}</td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => editServer(server)}
                            className="p-2 text-gray-400 hover:bg-gray-600/20 rounded-lg transition-all duration-200 transform hover:scale-110"
                            title="Edit Server"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteServer(server.server_id, server.name)}
                            className="p-2 text-red-400 hover:bg-red-600/20 rounded-lg transition-all duration-200 transform hover:scale-110"
                            title="Delete Server"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderDashboard = () => {
    // Determine which dashboard stats to show based on selectedServerId
    let displayDashboard: DashboardStats | null = null;
    if (activeTab === 'dashboard') { // The main aggregated dashboard
        displayDashboard = aggregatedDashboardStats;
    } else if (selectedServerId !== null && data) { // Dashboard for a specific selected server
        displayDashboard = data.dashboard;
    }

    if (!displayDashboard) return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-400" />
        <span className="ml-2 text-gray-400">Loading dashboard data...</span>
      </div>
    );


    return (
      <div className="space-y-6 animate-fade-in">
        {/* Alerts */}
        {displayDashboard.alert && displayDashboard.alert.length > 0 && (
          <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4 animate-slide-in">
            <div className="flex items-center gap-2 text-blue-300">
              <AlertCircle className="w-5 h-5" />
              <span className="font-medium">System Alert</span>
            </div>
            <ul className="mt-2 text-blue-200 text-sm">
              {displayDashboard.alert.map((alert, index) => (
                <li key={index}>{alert}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700 hover:border-gray-600 transition-all duration-300 transform hover:scale-105">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600/20 rounded-lg flex items-center justify-center">
                <Cpu className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">CPU Usage</p>
                <p className="text-xl font-bold text-white">{displayDashboard.cpu}</p>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700 hover:border-gray-600 transition-all duration-300 transform hover:scale-105">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-600/20 rounded-lg flex items-center justify-center">
                <HardDrive className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">Memory</p>
                <p className="text-xl font-bold text-white">{displayDashboard.mem.usage}</p>
                <p className="text-xs text-gray-500">{displayDashboard.mem.available} available</p>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700 hover:border-gray-600 transition-all duration-300 transform hover:scale-105">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-600/20 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">Total Clients</p>
                <p className="text-xl font-bold text-white">{displayDashboard.clients_count}</p>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700 hover:border-gray-600 transition-all duration-300 transform hover:scale-105">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-orange-600/20 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">Uptime</p>
                <p className="text-xl font-bold text-white">{formatUptime(parseInt(displayDashboard.uptime))}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Network Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700 hover:border-gray-600 transition-all duration-300">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-blue-600/20 rounded-lg flex items-center justify-center">
                <Network className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="font-semibold text-white">Network Activity</h3>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Download:</span>
                <span className="text-sm font-medium text-white">{displayDashboard.net.download}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Upload:</span>
                <span className="text-sm font-medium text-white">{displayDashboard.net.upload}</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700 hover:border-gray-600 transition-all duration-300">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-green-600/20 rounded-lg flex items-center justify-center">
                <Activity className="w-5 h-5 text-green-400" />
              </div>
              <h3 className="font-semibold text-white">Total Bandwidth</h3>
            </div>
            <p className="text-2xl font-bold text-white">{formatBytes(parseInt(displayDashboard.bandwidth))}</p>
          </div>
        </div>

        {/* Recent Clients (for selected server only) */}
        {selectedServerId !== null && data && (
            <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700">
                <div className="p-6 border-b border-gray-700">
                    <h3 className="font-semibold text-white">Recent Clients on {currentServer?.name || "Selected Server"}</h3>
                </div>
                <div className="p-6">
                    {data.clients.length === 0 ? (
                    <div className="text-center py-8">
                        <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                        <p className="text-gray-400">No clients configured for this server</p>
                        <p className="text-sm text-gray-500 mt-1">Add clients to {currentServer?.name || "this server"}</p>
                    </div>
                    ) : (
                    <div className="space-y-3">
                        {data.clients.slice(0, 5).map((client) => (
                        <div key={client.name} className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-all duration-200">
                            <div className="flex items-center gap-3">
                            <div className={`w-3 h-3 rounded-full ${client.status ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
                            <div>
                                <p className="font-medium text-white">{client.name}</p>
                                <p className="text-sm text-gray-400">{client.address}</p>
                            </div>
                            </div>
                            <div className="text-right">
                            <p className="text-sm font-medium text-white">
                                {formatBytes(client.used_trafic.download + client.used_trafic.upload)}
                            </p>
                            <p className="text-xs text-gray-500">used</p>
                            </div>
                        </div>
                        ))}
                    </div>
                    )}
                </div>
            </div>
        )}
      </div>
    );
  };

  const renderClients = () => {
    if (selectedServerId === null) {
      return (
        <div className="flex items-center justify-center py-12 text-gray-400">
          <AlertCircle className="w-5 h-5 mr-2" />
          Please add and select a server to manage clients.
        </div>
      );
    }
    if (!data) return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-400" />
        <span className="ml-2 text-gray-400">Loading client data for {currentServer?.name || "selected server"}...</span>
      </div>
    );

    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h2 className="text-xl font-bold text-white">Clients on {currentServer?.name}</h2>
          <button
            onClick={() => setShowClientForm(true)}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-all duration-200 transform hover:scale-105"
          >
            <Plus className="w-4 h-4" />
            Add Client
          </button>
        </div>

        {/* Client Form Modal */}
        {showClientForm && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700 animate-scale-in">
              <h3 className="text-lg font-semibold mb-4 text-white">
                {editingClient ? 'Edit Client' : 'Add New Client'}
              </h3>
              <form onSubmit={handleClientSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
                  <input
                    type="text"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                    disabled={!!editingClient}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Expires</label>
                  <input
                    type="date"
                    value={clientExpires}
                    onChange={(e) => setClientExpires(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Traffic Limit (MB)</label>
                  <input
                    type="number"
                    value={clientTraffic}
                    onChange={(e) => setClientTraffic(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                    required
                  />
                </div>
                {!editingClient && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">WireGuard Interface ID</label>
                    <select
                      value={clientWgId}
                      onChange={(e) => setClientWgId(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                    >
                      {data?.interfaces.map((iface) => (
                        <option key={iface.wg} value={iface.wg}>
                          wg{iface.wg} - {iface.address_range}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {editingClient && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                    <label htmlFor="client-status-toggle" className="flex items-center cursor-pointer">
                      <div className="relative">
                        <input
                          type="checkbox"
                          id="client-status-toggle"
                          className="sr-only"
                          checked={clientStatus}
                          onChange={(e) => setClientStatus(e.target.checked)}
                        />
                        <div className="block bg-gray-600 w-14 h-8 rounded-full"></div>
                        <div className={`dot absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition ${clientStatus ? 'translate-x-full bg-blue-600' : ''}`}></div>
                      </div>
                      <div className="ml-3 text-gray-300 font-medium">
                        {clientStatus ? 'Active' : 'Inactive'}
                      </div>
                    </label>
                  </div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Note</label>
                  <textarea
                    value={clientNote}
                    onChange={(e) => setClientNote(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                    rows={3}
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-all duration-200 transform hover:scale-105"
                  >
                    {loading ? 'Saving...' : (editingClient ? 'Update' : 'Create')}
                  </button>
                  <button
                    type="button"
                    onClick={resetClientForm}
                    className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-all duration-200 transform hover:scale-105"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Clients List */}
        <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700">
          {data.clients.length === 0 ? (
            <div className="p-8 text-center">
              <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No clients configured</p>
              <p className="text-sm text-gray-500 mt-1">Add your first client to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700/50 border-b border-gray-700">
                  <tr>
                    <th className="text-left p-4 font-medium text-gray-300">Name</th>
                    <th className="text-left p-4 font-medium text-gray-300">Address</th>
                    <th className="text-left p-4 font-medium text-gray-300">Status</th>
                    <th className="text-left p-4 font-medium text-gray-300">Usage</th>
                    <th className="text-left p-4 font-medium text-gray-300">Expires</th>
                    <th className="text-left p-4 font-medium text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {data.clients.map((client) => (
                    <tr key={client.name} className="hover:bg-gray-700/30 transition-colors duration-200">
                      <td className="p-4">
                        <div>
                          <p className="font-medium text-white">{client.name}</p>
                          {client.note && (
                            <p className="text-sm text-gray-400">{client.note}</p>
                          )}
                        </div>
                      </td>
                      <td className="p-4 text-sm text-gray-300">{client.address}</td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${client.status ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
                          <span className="text-sm text-gray-300">
                            {client.status ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                      </td>
                      <td className="p-4 text-sm text-gray-300">
                        {formatBytes(client.used_trafic.download + client.used_trafic.upload)}
                      </td>
                      <td className="p-4 text-sm text-gray-300">
                        {new Date(client.expires).toLocaleDateString()}
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => downloadConfig(client.name)}
                            className="p-2 text-blue-400 hover:bg-blue-600/20 rounded-lg transition-all duration-200 transform hover:scale-110"
                            title="Download Config"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => shortLink(client.name,client.public_key)}
                            className="p-2 text-blue-400 hover:bg-blue-600/20 rounded-lg transition-all duration-200 transform hover:scale-110"
                            title="ShortLink"
                          >
                            <Link2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => editClient(client)}
                            className="p-2 text-gray-400 hover:bg-gray-600/20 rounded-lg transition-all duration-200 transform hover:scale-110"
                            title="Edit Client"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => deleteClient(client.name)}
                            className="p-2 text-red-400 hover:bg-red-600/20 rounded-lg transition-all duration-200 transform hover:scale-110"
                            title="Delete Client"
                            >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderSettings = () => {
    if (selectedServerId === null) {
      return (
        <div className="flex items-center justify-center py-12 text-gray-400">
          <AlertCircle className="w-5 h-5 mr-2" />
          Please add and select a server to manage its settings or interfaces.
        </div>
      );
    }
    if (!data) return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-400" />
        <span className="ml-2 text-gray-400">Loading settings data for {currentServer?.name || "selected server"}...</span>
      </div>
    );

    const commonSettings = [
      { key: 'server_ip', label: 'Server IP (Central)', type: 'text' }, // This should probably be the central panel's IP, not server specific
      { key: 'custom_endpont', label: 'Custom Endpoint (Central)', type: 'text' }, // Same as above
      { key: 'dns', label: 'DNS Server (Global for Clients)', type: 'text' },
      { key: 'mtu', label: 'MTU (Global for Clients)', type: 'number' },
      { key: 'reset_time', label: 'Reset Time (hours, Agent)', type: 'number' }, // This affects agents
      { key: 'ap_port', label: 'API + Panel Port (Central)', type: 'number' },
      { key: 'auto_backup', label: 'Auto Backup (Agent)', type: 'select', options: [{ value: '1', label: 'Enabled' }, { value: '0', label: 'Disabled' }] },
    ];
    // Note: 'reset_time' and 'auto_backup' are currently settings stored centrally but influence agent behavior.
    // In a multi-server setup, these might become per-server settings, or the central panel needs to send
    // a command to each agent to update its local settings. For simplicity now, they are central settings.


    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h2 className="text-xl font-bold text-white">Settings for {currentServer?.name}</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowInterfaceForm(true)}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-all duration-200 transform hover:scale-105"
            >
              <Plus className="w-4 h-4" />
              Add Interface
            </button>
            <button
              onClick={handleSync}
              disabled={loading}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-all duration-200 transform hover:scale-105"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Sync & Apply
            </button>
          </div>
        </div>

        {/* Add Interface Form Modal */}
        {showInterfaceForm && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700 animate-scale-in">
              <h3 className="text-lg font-semibold mb-4 text-white">Add New Interface on {currentServer?.name}</h3>
              <form onSubmit={handleInterfaceSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Address Range</label>
                  <input
                    type="text"
                    value={interfaceAddressRange}
                    onChange={(e) => setInterfaceAddressRange(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                    placeholder="10.0.1.1/24"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Port</label>
                  <input
                    type="number"
                    value={interfacePort}
                    onChange={(e) => setInterfacePort(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                    placeholder="51821"
                    required
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-all duration-200 transform hover:scale-105"
                  >
                    {loading ? 'Creating...' : 'Create Interface'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowInterfaceForm(false)}
                    className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-all duration-200 transform hover:scale-105"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit Interface Form Modal */}
        {showEditInterfaceForm && editingInterface && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700 animate-scale-in">
              <h3 className="text-lg font-semibold mb-4 text-white">Edit Interface wg{editingInterface.wg} on {currentServer?.name}</h3>
              <form onSubmit={handleEditInterfaceSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Address Range</label>
                  <input
                    type="text"
                    value={editInterfaceAddressRange}
                    onChange={(e) => setEditInterfaceAddressRange(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Port</label>
                  <input
                    type="number"
                    value={editInterfacePort}
                    onChange={(e) => setEditInterfacePort(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                  <label htmlFor="interface-status-toggle" className="flex items-center cursor-pointer">
                    <div className="relative">
                      <input
                        type="checkbox"
                        id="interface-status-toggle"
                        className="sr-only"
                        checked={editInterfaceStatus}
                        onChange={(e) => setEditInterfaceStatus(e.target.checked)}
                      />
                      <div className="block bg-gray-600 w-14 h-8 rounded-full"></div>
                      <div className={`dot absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition ${editInterfaceStatus ? 'translate-x-full bg-blue-600' : ''}`}></div>
                    </div>
                    <div className="ml-3 text-gray-300 font-medium">
                      {editInterfaceStatus ? 'Active' : 'Inactive'}
                    </div>
                  </label>
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-all duration-200 transform hover:scale-105"
                  >
                    {loading ? 'Saving...' : 'Update Interface'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowEditInterfaceForm(false)}
                    className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-all duration-200 transform hover:scale-105"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Common Settings (central settings) */}
        <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6">
          <h3 className="font-semibold text-white mb-4">General Settings (Central Panel)</h3>
          <div className="flex flex-wrap -mx-3 gap-y-6">
            {commonSettings.map((setting) => (
              <div key={setting.key} className="w-full md:w-1/2 px-3">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {setting.label}
                </label>
                {setting.type === 'select' ? (
                  <select
                    value={stagedSettings[setting.key] || ''}
                    onChange={(e) => updateStagedSetting(setting.key, e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                  >
                    {setting.options?.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={setting.type}
                    value={stagedSettings[setting.key] || ''}
                    onChange={(e) => updateStagedSetting(setting.key, e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                  />
                )}
              </div>
            ))}
          </div>
        </div>


        {/* Telegram Bot Settings (central settings) */}
        <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Bot className="w-5 h-5 text-purple-400" /> Telegram Bot Settings
             <div>
              <label htmlFor="telegram-bot-status-toggle" className="flex items-center cursor-pointer">
                <div className="relative">
                  <input
                    type="checkbox"
                    id="telegram-bot-status-toggle"
                    className="sr-only"
                    checked={stagedSettings['telegram_bot_status'] === '1'}
                    onChange={(e) => updateStagedSetting('telegram_bot_status', e.target.checked ? '1' : '0')}
                  />
                  <div className="block bg-gray-600 w-14 h-8 rounded-full"></div>
                  <div className={`dot absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition ${stagedSettings['telegram_bot_status'] === '1' ? 'translate-x-full bg-blue-600' : ''}`}></div>
                </div>
                <div className="ml-3 text-gray-300 font-medium">
                  {stagedSettings['telegram_bot_status'] === '1' ? 'Enabled' : 'Disabled'}
                </div>
              </label>
            </div>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Admin Telegram ID</label>
              <input
                type="text"
                value={stagedSettings['telegram_bot_admin_id'] || ''}
                onChange={(e) => updateStagedSetting('telegram_bot_admin_id', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                placeholder="Your Telegram User ID"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Bot Token</label>
              <input
                type="text"
                value={stagedSettings['telegram_bot_token'] || ''}
                onChange={(e) => updateStagedSetting('telegram_bot_token', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                placeholder="Your Telegram Bot Token"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">API ID</label>
              <input
                type="text"
                value={stagedSettings['telegram_api_id'] || ''}
                onChange={(e) => updateStagedSetting('telegram_api_id', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                placeholder="Your API ID"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">API HASH</label>
              <input
                type="text"
                value={stagedSettings['telegram_api_hash'] || ''}
                onChange={(e) => updateStagedSetting('telegram_api_hash', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                placeholder="Your API HASH"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Card Number</label>
              <input
                type="text"
                value={stagedSettings['admin_card_number'] || ''}
                onChange={(e) => updateStagedSetting('admin_card_number', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                placeholder="Your Card number for seller"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Prices (JSON)</label>
              <input
                value={stagedSettings['prices'] || ''}
                onChange={(e) => updateStagedSetting('prices', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-all duration-200"
                placeholder='{"1Month":75000,"1GB":4000}'
              />
              <p className="text-xs text-gray-500 mt-1">Enter as a valid JSON string, e.g., `"per_month":75000,"per_gb":4000`</p>
            </div>
          </div>
        </div>

        {/* API Tokens Management (central settings) */}
        <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6">
          <h3 className="font-semibold text-white mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Key className="w-5 h-5 text-yellow-400" /> API Tokens
            </div>
            <button
              onClick={() => setShowApiTokenForm(true)}
              className="flex items-center gap-2 bg-blue-600 text-white px-3 py-1 rounded-lg text-sm hover:bg-blue-700 transition-all duration-200"
            >
              <Plus className="w-4 h-4" /> Add Token
            </button>
          </h3>

          {showApiTokenForm && (
            <div className="bg-gray-700/50 rounded-lg p-4 mb-4 border border-gray-600 animate-fade-in">
              <form onSubmit={handleAddApiToken} className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Token Name</label>
                  <input
                    type="text"
                    value={newApiTokenName}
                    onChange={(e) => setNewApiTokenName(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                    placeholder="e.g., my_app_token"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Token Value</label>
                  <input
                    type="text"
                    value={newApiTokenValue}
                    onChange={(e) => setNewApiTokenValue(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                    placeholder="e.g., some_secret_string_123"
                    required
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-all duration-200"
                  >
                    {loading ? 'Saving...' : 'Save Token'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowApiTokenForm(false)}
                    className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-all duration-200"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {Object.keys(apiTokens).length === 0 ? (
            <div className="text-center py-4 text-gray-400">No API tokens configured.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700/50 border-b border-gray-700">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-300">Name</th>
                    <th className="text-left p-3 font-medium text-gray-300">Token</th>
                    <th className="text-left p-3 font-medium text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {Object.entries(apiTokens).map(([name, token]) => (
                    <tr key={name} className="hover:bg-gray-700/30 transition-colors duration-200">
                      <td className="p-3 text-white font-medium">{name}</td>
                      <td className="p-3 text-gray-400 font-mono text-sm break-all">{token}</td>
                      <td className="p-3">
                        <button
                          onClick={() => handleDeleteApiToken(name)}
                          className="p-2 text-red-400 hover:bg-red-600/20 rounded-lg transition-all duration-200 transform hover:scale-110"
                          title="Delete Token"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Interfaces (for selected server) */}
        <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700">
          <div className="p-6 border-b border-gray-700">
            <h3 className="font-semibold text-white">WireGuard Interfaces on {currentServer?.name}</h3>
          </div>
          <div className="p-6">
            {data.interfaces.length === 0 ? (
              <div className="text-center py-8">
                <ServerIcon className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">No interfaces configured for this server</p>
                <p className="text-sm text-gray-500 mt-1">Add your first interface to get started</p>
              </div>
            ) : (
              <div className="space-y-4">
                {data.interfaces.map((iface) => (
                  <div key={iface.wg} className="flex items-center justify-between p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-all duration-200">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${iface.status ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
                      <div>
                        <p className="font-medium text-white">wg{iface.wg}</p>
                        <p className="text-sm text-gray-400">{iface.address_range}</p>
                      </div>
                    </div>
                    <div className="text-right flex items-center gap-2">
                      <p className="text-sm font-medium text-white">Port {iface.port}</p>
                      <p className="text-xs text-gray-400">
                        {iface.status ? 'Active' : 'Inactive'}
                      </p>
                      <button
                        onClick={() => editInterface(iface)}
                        className="p-2 text-gray-400 hover:bg-gray-600/20 rounded-lg transition-all duration-200 transform hover:scale-110"
                        title="Edit Interface"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteInterface(iface.wg)}
                        className="p-2 text-red-400 hover:bg-red-600/20 rounded-lg transition-all duration-200 transform hover:scale-110"
                        title="Delete Interface"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 shadow-lg border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center animate-pulse-slow">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-xl font-bold text-white">Candy Panel</h1>
            </div>
            {isAuthenticated && (
              <div className="flex items-center gap-4">
                {/* Server Selector */}
                {allServers.length > 0 && (
                  <div className="relative">
                    <select
                      value={selectedServerId || ''}
                      onChange={(e) => setSelectedServerId(parseInt(e.target.value))}
                      className="bg-gray-700 text-white py-2 px-3 rounded-lg border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 pr-8"
                    >
                      {allServers.map((server) => (
                        <option key={server.server_id} value={server.server_id}>
                          {server.name} ({server.status})
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                  </div>
                )}
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 text-gray-400 hover:text-white px-3 py-2 rounded-lg hover:bg-gray-700 transition-all duration-200 transform hover:scale-105"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Navigation */}
      {isAuthenticated && (
        <nav className="bg-gray-800 border-b border-gray-700 sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex space-x-4 py-4 overflow-x-auto">
              <TabButton
                icon={<Activity className="w-4 h-4" />}
                label="Overview"
                isActive={activeTab === 'dashboard'}
                onClick={() => setActiveTab('dashboard')}
              />
              <TabButton
                icon={<ServerIcon className="w-4 h-4" />}
                label="Servers"
                isActive={activeTab === 'servers'}
                onClick={() => setActiveTab('servers')}
              />
              <TabButton
                icon={<Users className="w-4 h-4" />}
                label="Clients"
                isActive={activeTab === 'clients'}
                onClick={() => setActiveTab('clients')}
              />
              <TabButton
                icon={<Settings className="w-4 h-4" />}
                label="Settings"
                isActive={activeTab === 'settings'}
                onClick={() => setActiveTab('settings')}
              />
            </div>
          </div>
        </nav>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {isAuthenticated && loading && !data && allServers.length === 0 && ( // Initial load for servers
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 animate-spin text-blue-400" />
            <span className="ml-2 text-gray-400">Loading servers...</span>
          </div>
        )}
        {isAuthenticated && !loading && allServers.length === 0 && activeTab !== 'servers' && (
          <div className="flex items-center justify-center py-12 text-gray-400 flex-col">
            <AlertCircle className="w-12 h-12 mb-4 text-blue-400" />
            <p className="text-xl font-semibold mb-2">No Servers Configured</p>
            <p className="text-md">Please go to the "Servers" tab to add your first WireGuard server.</p>
          </div>
        )}
        {isAuthenticated && selectedServerId === null && allServers.length > 0 && activeTab !== 'servers' && (
             <div className="flex items-center justify-center py-12 text-gray-400 flex-col">
                <AlertCircle className="w-12 h-12 mb-4 text-blue-400" />
                <p className="text-xl font-semibold mb-2">Select a Server</p>
                <p className="text-md">Please select a server from the dropdown in the header to view its details.</p>
            </div>
        )}


        {isAuthenticated && activeTab === 'dashboard' && selectedServerId !== null && renderDashboard()}
        {isAuthenticated && activeTab === 'dashboard' && selectedServerId === null && allServers.length > 0 && renderDashboard()} {/* Show aggregated dashboard if no server selected but servers exist */}
        {isAuthenticated && activeTab === 'servers' && renderServerManagement()}
        {isAuthenticated && activeTab === 'clients' && renderClients()}
        {isAuthenticated && activeTab === 'settings' && renderSettings()}
      </main>

      {/* Messages */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-600 text-white px-4 py-3 rounded-lg shadow-lg z-50 max-w-sm animate-slide-in">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}
      {success && (
        <div className="fixed bottom-4 right-4 bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg z-50 max-w-sm animate-slide-in">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm">{success}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;