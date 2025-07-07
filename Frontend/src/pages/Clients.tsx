import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Search, Filter, Users, Smartphone, Monitor, Tablet, Wifi, WifiOff, Edit, Trash2, Download, ToggleLeft as Toggle, MoreVertical } from 'lucide-react';
import { Client } from '@/types';
import { useApi, useMutation } from '@/hooks/useApi';
import { clientService } from '@/services/clientService';

export const Clients: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | undefined>();
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch clients
  const { data: clients = [], loading, error, refetch } = useApi(
    () => clientService.getClients(),
    {
      onSuccess: (data) => console.log('✅ Clients loaded:', data.length),
      onError: (error) => console.error('❌ Failed to load clients:', error)
    }
  );

  // Create client mutation
  const { mutate: createClient, loading: creating } = useMutation(
    (clientData: {
      name: string;
      expires: string;
      traffic: string;
      wg_id?: number;
      note?: string;
    }) => clientService.createClient(clientData),
    {
      onSuccess: () => {
        console.log('✅ Client created successfully');
        refetch();
      },
      onError: (error) => console.error('❌ Failed to create client:', error)
    }
  );

  // Update client mutation
  const { mutate: updateClient, loading: updating } = useMutation(
    ({ name, data }: { name: string; data: any }) => clientService.updateClient(name, data),
    {
      onSuccess: () => {
        console.log('✅ Client updated successfully');
        refetch();
      },
      onError: (error) => console.error('❌ Failed to update client:', error)
    }
  );

  // Delete client mutation
  const { mutate: deleteClient, loading: deleting } = useMutation(
    (name: string) => clientService.deleteClient(name),
    {
      onSuccess: () => {
        console.log('✅ Client deleted successfully');
        refetch();
      },
      onError: (error) => console.error('❌ Failed to delete client:', error)
    }
  );

  // Toggle client mutation
  const { mutate: toggleClient, loading: toggling } = useMutation(
    ({ name, enabled }: { name: string; enabled: boolean }) => clientService.toggleClient(name, enabled),
    {
      onSuccess: () => {
        console.log('✅ Client toggled successfully');
        refetch();
      },
      onError: (error) => console.error('❌ Failed to toggle client:', error)
    }
  );

  const handleAddClient = () => {
    setEditingClient(undefined);
    setShowForm(true);
  };

  const handleEditClient = (client: Client) => {
    setEditingClient(client);
    setShowForm(true);
  };

  const handleSaveClient = async (clientData: any) => {
    try {
      if (editingClient) {
        await updateClient({ name: editingClient.name, data: clientData });
      } else {
        // Convert traffic from GB to bytes for backend
        const trafficInBytes = clientData.traffic ? (parseFloat(clientData.traffic) * 1024 * 1024 * 1024).toString() : '0';
        await createClient({
          name: clientData.name,
          expires: clientData.endTime || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
          traffic: trafficInBytes,
          wg_id: 0,
          note: clientData.notes || ''
        });
      }
      setShowForm(false);
      setEditingClient(undefined);
    } catch (error) {
      console.error('Failed to save client:', error);
    }
  };

  const handleDeleteClient = async (name: string) => {
    if (window.confirm('Are you sure you want to delete this client?')) {
      try {
        await deleteClient(name);
      } catch (error) {
        console.error('Failed to delete client:', error);
      }
    }
  };

  const handleToggleClient = async (name: string, enabled: boolean) => {
    try {
      await toggleClient({ name, enabled });
    } catch (error) {
      console.error('Failed to toggle client:', error);
    }
  };

  const handleDownloadConfig = async (name: string) => {
    try {
      await clientService.downloadClientConfig(name);
    } catch (error) {
      console.error('Failed to download config:', error);
    }
  };

  const filteredClients = clients.filter(client =>
    client.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    client.address.includes(searchTerm)
  );

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="text-red-400 mb-4">❌ Failed to load clients</div>
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
          <h1 className="text-2xl font-bold text-white">Clients</h1>
          <p className="text-gray-400 mt-1">Manage WireGuard client connections</p>
        </motion.div>
        
        <motion.button
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          onClick={handleAddClient}
          disabled={creating}
          className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all mt-4 sm:mt-0 disabled:opacity-50"
        >
          <Plus className="w-5 h-5" />
          <span>{creating ? 'Creating...' : 'Add Client'}</span>
        </motion.button>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search clients..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <button className="flex items-center space-x-2 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-300 hover:bg-gray-700 transition-colors">
          <Filter className="w-4 h-4" />
          <span>Filter</span>
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl p-6 animate-pulse">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-gray-700 rounded-lg"></div>
                  <div>
                    <div className="w-24 h-4 bg-gray-700 rounded mb-2"></div>
                    <div className="w-32 h-3 bg-gray-700 rounded"></div>
                  </div>
                </div>
              </div>
              <div className="space-y-3">
                <div className="w-full h-16 bg-gray-700 rounded"></div>
                <div className="w-full h-4 bg-gray-700 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {filteredClients.map((client) => (
            <ClientCard
              key={client.name}
              client={client}
              onEdit={handleEditClient}
              onDelete={() => handleDeleteClient(client.name)}
              onToggle={(enabled) => handleToggleClient(client.name, enabled)}
              onDownload={() => handleDownloadConfig(client.name)}
              disabled={deleting || toggling}
            />
          ))}
        </div>
      )}

      {!loading && filteredClients.length === 0 && (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <Users className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">No clients found</h3>
          <p className="text-gray-400 mb-4">
            {searchTerm ? 'No clients match your search criteria' : 'Get started by adding your first client'}
          </p>
          {!searchTerm && (
            <button
              onClick={handleAddClient}
              disabled={creating}
              className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Add First Client'}
            </button>
          )}
        </div>
      )}

      {showForm && (
        <ClientForm
          isOpen={showForm}
          onClose={() => {
            setShowForm(false);
            setEditingClient(undefined);
          }}
          onSave={handleSaveClient}
          client={editingClient}
          loading={creating || updating}
        />
      )}
    </div>
  );
};

// Client Card Component
interface ClientCardProps {
  client: Client;
  onEdit: (client: Client) => void;
  onDelete: () => void;
  onToggle: (enabled: boolean) => void;
  onDownload: () => void;
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

const ClientCard: React.FC<ClientCardProps> = ({ client, onEdit, onDelete, onToggle, onDownload, disabled = false }) => {
  const [showMenu, setShowMenu] = useState(false);
  const DeviceIcon = getDeviceIcon(client.name);
  
  const isOnline = client.connected_now;
  const trafficUsedGB = (client.used_trafic.download + client.used_trafic.upload) / (1024 * 1024 * 1024);
  const trafficLimitGB = parseInt(client.traffic) / (1024 * 1024 * 1024);
  const trafficPercent = trafficLimitGB > 0 ? (trafficUsedGB / trafficLimitGB) * 100 : 0;

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
                    onToggle(!client.status);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-gray-300 hover:bg-gray-700 flex items-center space-x-2"
                >
                  <Toggle className="w-4 h-4" />
                  <span>{client.status ? 'Disable' : 'Enable'}</span>
                </button>
                <button 
                  onClick={() => {
                    onDownload();
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-gray-300 hover:bg-gray-700 flex items-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>Download Config</span>
                </button>
                <button
                  onClick={() => {
                    onDelete();
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

// Client Form Component
interface ClientFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (client: any) => void;
  client?: Client;
  loading?: boolean;
}

const ClientForm: React.FC<ClientFormProps> = ({ isOpen, onClose, onSave, client, loading = false }) => {
  const [formData, setFormData] = useState({
    name: client?.name || '',
    traffic: client ? (parseInt(client.traffic) / (1024 * 1024 * 1024)).toString() : '0',
    endTime: client?.expires ? new Date(client.expires).toISOString().slice(0, 16) : '',
    notes: client?.note || '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    onSave(formData);
  };

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">
            {client ? 'Edit Client' : 'Add New Client'}
          </h2>
          <button
            onClick={onClose}
            disabled={loading}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
          >
            <Plus className="w-5 h-5 text-gray-400 rotate-45" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Client Name
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              placeholder="e.g., iPhone, Laptop"
              disabled={loading || !!client}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Traffic Limit (GB)
            </label>
            <input
              type="number"
              value={formData.traffic}
              onChange={(e) => setFormData({ ...formData, traffic: e.target.value })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              placeholder="0 = unlimited"
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Expiration Date
            </label>
            <input
              type="datetime-local"
              value={formData.endTime}
              onChange={(e) => setFormData({ ...formData, endTime: e.target.value })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Notes
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none resize-none"
              rows={3}
              placeholder="Optional notes..."
              disabled={loading}
            />
          </div>

          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50"
            >
              {loading ? 'Saving...' : client ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
};