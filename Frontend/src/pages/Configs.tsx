import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Eye, EyeOff, Plus, Edit, Trash2, Loader } from 'lucide-react';
import { useApi, useMutation } from '@/hooks/useApi';
import { interfaceService } from '@/services/interfaceService';
import { Interface } from '@/types';

export const Configs: React.FC = () => {
  const [editingInterface, setEditingInterface] = useState<Interface | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [visibleKeys, setVisibleKeys] = useState<{ [key: string]: boolean }>({});

  // Fetch interfaces
  const { data: interfaces = [], loading, error, refetch } = useApi(
    () => interfaceService.getInterfaces(),
    {
      onSuccess: (data) => console.log('✅ Interfaces loaded:', data.length),
      onError: (error) => console.error('❌ Failed to load interfaces:', error)
    }
  );

  // Create interface mutation
  const { mutate: createInterface, loading: creating } = useMutation(
    (interfaceData: { address_range: string; port: number }) => 
      interfaceService.createInterface(interfaceData),
    {
      onSuccess: () => {
        console.log('✅ Interface created successfully');
        refetch();
      },
      onError: (error) => console.error('❌ Failed to create interface:', error)
    }
  );

  // Update interface mutation
  const { mutate: updateInterface, loading: updating } = useMutation(
    ({ name, data }: { name: string; data: any }) => 
      interfaceService.updateInterface(name, data),
    {
      onSuccess: () => {
        console.log('✅ Interface updated successfully');
        refetch();
      },
      onError: (error) => console.error('❌ Failed to update interface:', error)
    }
  );

  const toggleKeyVisibility = (id: string) => {
    setVisibleKeys(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSaveInterface = async (interfaceData: { address_range: string; port: number }) => {
    try {
      if (editingInterface) {
        await updateInterface({ 
          name: `wg${editingInterface.wg}`, 
          data: {
            address: interfaceData.address_range,
            port: interfaceData.port
          }
        });
      } else {
        await createInterface(interfaceData);
      }
      setEditingInterface(null);
      setShowForm(false);
    } catch (error) {
      console.error('Failed to save interface:', error);
    }
  };

  const downloadConfig = (iface: Interface) => {
    console.log('📥 Downloading config for interface:', `wg${iface.wg}`);
    const config = `[Interface]
PrivateKey = ${iface.private_key}
Address = ${iface.address_range}
ListenPort = ${iface.port}
SaveConfig = true
PostUp = ufw allow ${iface.port}/udp
PostDown = ufw delete allow ${iface.port}/udp`;

    const blob = new Blob([config], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `wg${iface.wg}.conf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="text-red-400 mb-4">❌ Failed to load interfaces</div>
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
          <h1 className="text-3xl font-bold text-white">Interface Configurations</h1>
          <p className="text-gray-300 mt-2">Manage WireGuard interface settings (wg0, wg1, etc.)</p>
        </motion.div>
        
        <motion.button
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          onClick={() => {
            setEditingInterface(null);
            setShowForm(true);
          }}
          disabled={creating}
          className="flex items-center space-x-2 px-4 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all mt-4 sm:mt-0 transform hover:scale-105 disabled:opacity-50"
        >
          <Plus className="w-5 h-5" />
          <span>{creating ? 'Creating...' : 'Add Interface'}</span>
        </motion.button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-6">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="glass rounded-2xl p-6 border border-gray-800 animate-pulse">
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gray-700 rounded-xl"></div>
                  <div>
                    <div className="w-24 h-6 bg-gray-700 rounded mb-2"></div>
                    <div className="w-32 h-4 bg-gray-700 rounded"></div>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <div className="w-16 h-6 bg-gray-700 rounded"></div>
                  <div className="w-8 h-8 bg-gray-700 rounded"></div>
                </div>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="space-y-4">
                  {[...Array(3)].map((_, j) => (
                    <div key={j} className="w-full h-16 bg-gray-700 rounded"></div>
                  ))}
                </div>
                <div className="space-y-4">
                  {[...Array(2)].map((_, j) => (
                    <div key={j} className="w-full h-20 bg-gray-700 rounded"></div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {interfaces.map((iface, index) => (
            <motion.div
              key={iface.wg}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="glass rounded-2xl p-6 border border-gray-800 hover:border-gray-700 transition-all"
            >
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center space-x-4">
                  <div className={`p-3 rounded-xl ${iface.status ? 'bg-green-500/20' : 'bg-gray-500/20'}`}>
                    <FileText className={`w-6 h-6 ${iface.status ? 'text-green-400' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">wg{iface.wg}</h3>
                    <p className="text-gray-400">{iface.address_range}</p>
                    <p className="text-gray-500 text-sm">Port: {iface.port}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    iface.status 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-gray-500/20 text-gray-400'
                  }`}>
                    {iface.status ? 'Active' : 'Inactive'}
                  </span>
                  
                  <button
                    onClick={() => {
                      setEditingInterface(iface);
                      setShowForm(true);
                    }}
                    disabled={updating}
                    className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                    title="Edit interface"
                  >
                    {updating ? <Loader className="w-4 h-4 animate-spin text-gray-400" /> : <Edit className="w-4 h-4 text-gray-400" />}
                  </button>
                  
                  <button
                    onClick={() => downloadConfig(iface)}
                    className="p-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg transition-colors"
                    title="Download config"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <h4 className="text-white font-medium mb-2">Network Settings</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Address Range:</span>
                        <span className="text-white">{iface.address_range}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Port:</span>
                        <span className="text-white">{iface.port}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Status:</span>
                        <span className={iface.status ? 'text-green-400' : 'text-red-400'}>
                          {iface.status ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-white font-medium mb-2">Keys</h4>
                    <div className="space-y-2">
                      <div>
                        <p className="text-gray-400 text-sm mb-1">Private Key:</p>
                        <div className="flex items-center space-x-2">
                          <code className="flex-1 px-3 py-2 bg-black/30 rounded-lg text-gray-300 font-mono text-xs">
                            {visibleKeys[`wg${iface.wg}`] ? iface.private_key : '••••••••••••••••••••••••••••••••••••••••••••••'}
                          </code>
                          <button
                            onClick={() => toggleKeyVisibility(`wg${iface.wg}`)}
                            className="p-2 text-gray-400 hover:text-white transition-colors"
                          >
                            {visibleKeys[`wg${iface.wg}`] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>
                      <div>
                        <p className="text-gray-400 text-sm mb-1">Public Key:</p>
                        <code className="block px-3 py-2 bg-black/30 rounded-lg text-gray-300 font-mono text-xs">
                          {iface.public_key}
                        </code>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
          
          {interfaces.length === 0 && !loading && (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-white mb-2">No interfaces found</h3>
              <p className="text-gray-400 mb-4">Create your first WireGuard interface to get started</p>
              <button
                onClick={() => setShowForm(true)}
                className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all"
              >
                Create First Interface
              </button>
            </div>
          )}
        </div>
      )}

      {/* Interface Form Modal */}
      {showForm && (
        <InterfaceForm
          interface={editingInterface}
          onSave={handleSaveInterface}
          onCancel={() => setShowForm(false)}
          loading={creating || updating}
        />
      )}
    </div>
  );
};

// Interface Form Component
interface InterfaceFormProps {
  interface: Interface | null;
  onSave: (data: { address_range: string; port: number }) => void;
  onCancel: () => void;
  loading?: boolean;
}

const InterfaceForm: React.FC<InterfaceFormProps> = ({ interface: iface, onSave, onCancel, loading = false }) => {
  const [formData, setFormData] = useState({
    address_range: iface?.address_range || '10.0.0.1/24',
    port: iface?.port || 51820,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    onSave(formData);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">
            {iface ? 'Edit Interface' : 'Add New Interface'}
          </h2>
          <button
            onClick={onCancel}
            disabled={loading}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
          >
            <Plus className="w-5 h-5 text-gray-400 rotate-45" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Address Range (CIDR)
            </label>
            <input
              type="text"
              required
              value={formData.address_range}
              onChange={(e) => setFormData({ ...formData, address_range: e.target.value })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              placeholder="10.0.0.1/24"
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Listen Port
            </label>
            <input
              type="number"
              required
              value={formData.port}
              onChange={(e) => setFormData({ ...formData, port: Number(e.target.value) })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              disabled={loading}
            />
          </div>

          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50 flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <span>{iface ? 'Update' : 'Create'} Interface</span>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
};