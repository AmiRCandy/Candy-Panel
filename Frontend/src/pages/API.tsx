import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, Key, Copy, Plus, Trash2, Eye, EyeOff, Loader } from 'lucide-react';
import { useApi, useMutation } from '@/hooks/useApi';
import { serverService } from '@/services/serverService';

export const API: React.FC = () => {
  const [showTokens, setShowTokens] = useState<{ [key: string]: boolean }>({});
  const [newTokenName, setNewTokenName] = useState('');
  const [newTokenValue, setNewTokenValue] = useState('');
  const [showNewTokenForm, setShowNewTokenForm] = useState(false);

  // Fetch API tokens from settings
  const { data: settings = {}, loading, error, refetch } = useApi(
    () => serverService.getSettings(),
    {
      onSuccess: (data) => console.log('✅ Settings loaded for API tokens'),
      onError: (error) => console.error('❌ Failed to load settings:', error)
    }
  );

  // Create token mutation
  const { mutate: createToken, loading: creating } = useMutation(
    (tokenData: { name: string; token: string }) => 
      serverService.addApiToken(tokenData.name, tokenData.token),
    {
      onSuccess: () => {
        console.log('✅ API token created successfully');
        refetch();
      },
      onError: (error) => console.error('❌ Failed to create API token:', error)
    }
  );

  // Delete token mutation
  const { mutate: deleteToken, loading: deleting } = useMutation(
    (name: string) => serverService.deleteApiToken(name),
    {
      onSuccess: () => {
        console.log('✅ API token deleted successfully');
        refetch();
      },
      onError: (error) => console.error('❌ Failed to delete API token:', error)
    }
  );

  const generateToken = async () => {
    if (!newTokenName.trim() || !newTokenValue.trim()) return;
    
    try {
      await createToken({
        name: newTokenName,
        token: newTokenValue
      });
      setNewTokenName('');
      setNewTokenValue('');
      setShowNewTokenForm(false);
    } catch (error) {
      console.error('Failed to create token:', error);
    }
  };

  const handleDeleteToken = async (name: string) => {
    if (window.confirm('Are you sure you want to delete this API token?')) {
      try {
        await deleteToken(name);
      } catch (error) {
        console.error('Failed to delete token:', error);
      }
    }
  };

  const toggleTokenVisibility = (name: string) => {
    setShowTokens(prev => ({ ...prev, [name]: !prev[name] }));
  };

  const copyToken = (token: string) => {
    navigator.clipboard.writeText(token);
    console.log('📋 Token copied to clipboard');
  };

  // Parse API tokens from settings
  const apiTokens = settings.api_tokens ? JSON.parse(settings.api_tokens) : {};
  const tokenEntries = Object.entries(apiTokens);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="text-red-400 mb-4">❌ Failed to load API tokens</div>
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
          <h1 className="text-3xl font-bold text-white">API Management</h1>
          <p className="text-gray-300 mt-2">Manage API tokens and integrations</p>
        </motion.div>
        
        <motion.button
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          onClick={() => setShowNewTokenForm(true)}
          disabled={creating}
          className="flex items-center space-x-2 px-4 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all mt-4 sm:mt-0 transform hover:scale-105 disabled:opacity-50"
        >
          <Plus className="w-5 h-5" />
          <span>{creating ? 'Creating...' : 'Generate Token'}</span>
        </motion.button>
      </div>

      {/* API Documentation */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-6 border border-blue-500/20"
      >
        <h3 className="text-xl font-semibold text-white mb-4 flex items-center">
          <Zap className="w-6 h-6 mr-3 text-blue-400" />
          API Endpoints
        </h3>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-green-400 font-mono text-sm">POST</span>
                <span className="text-gray-400 text-sm">/api/manage</span>
              </div>
              <p className="text-gray-300 text-sm">Create/Update/Delete clients</p>
              <p className="text-gray-500 text-xs">resource: client, action: create/update/delete</p>
            </div>
            
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-blue-400 font-mono text-sm">GET</span>
                <span className="text-gray-400 text-sm">/api/data</span>
              </div>
              <p className="text-gray-300 text-sm">Get all dashboard data</p>
              <p className="text-gray-500 text-xs">Returns clients, interfaces, settings</p>
            </div>
            
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-yellow-400 font-mono text-sm">POST</span>
                <span className="text-gray-400 text-sm">/api/manage</span>
              </div>
              <p className="text-gray-300 text-sm">Manage interfaces</p>
              <p className="text-gray-500 text-xs">resource: interface, action: create/update</p>
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-purple-400 font-mono text-sm">POST</span>
                <span className="text-gray-400 text-sm">/api/manage</span>
              </div>
              <p className="text-gray-300 text-sm">Update settings</p>
              <p className="text-gray-500 text-xs">resource: setting, action: update</p>
            </div>
            
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-green-400 font-mono text-sm">POST</span>
                <span className="text-gray-400 text-sm">/api/manage</span>
              </div>
              <p className="text-gray-300 text-sm">Get client config</p>
              <p className="text-gray-500 text-xs">resource: client, action: get_config</p>
            </div>
            
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-orange-400 font-mono text-sm">POST</span>
                <span className="text-gray-400 text-sm">/api/manage</span>
              </div>
              <p className="text-gray-300 text-sm">Trigger sync</p>
              <p className="text-gray-500 text-xs">resource: sync, action: trigger</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Token Management */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-6 border border-purple-500/20"
      >
        <h3 className="text-xl font-semibold text-white mb-6 flex items-center">
          <Key className="w-6 h-6 mr-3 text-purple-400" />
          API Tokens
        </h3>
        
        {showNewTokenForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mb-6 p-4 bg-white/5 rounded-xl border border-white/10"
          >
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Token Name
                </label>
                <input
                  type="text"
                  value={newTokenName}
                  onChange={(e) => setNewTokenName(e.target.value)}
                  placeholder="Token name (e.g., Mobile App)"
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none backdrop-blur-sm"
                  disabled={creating}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Token Value
                </label>
                <input
                  type="text"
                  value={newTokenValue}
                  onChange={(e) => setNewTokenValue(e.target.value)}
                  placeholder="Enter token value"
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none backdrop-blur-sm"
                  disabled={creating}
                />
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={generateToken}
                  disabled={!newTokenName.trim() || !newTokenValue.trim() || creating}
                  className="px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center space-x-2"
                >
                  {creating ? (
                    <>
                      <Loader className="w-4 h-4 animate-spin" />
                      <span>Creating...</span>
                    </>
                  ) : (
                    <span>Create Token</span>
                  )}
                </button>
                <button
                  onClick={() => setShowNewTokenForm(false)}
                  disabled={creating}
                  className="px-4 py-2 bg-gray-600 text-white rounded-xl hover:bg-gray-700 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </motion.div>
        )}
        
        {loading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="p-4 bg-white/5 rounded-xl border border-white/10 animate-pulse">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="w-32 h-4 bg-gray-700 rounded mb-2"></div>
                    <div className="w-24 h-3 bg-gray-700 rounded"></div>
                  </div>
                  <div className="w-16 h-6 bg-gray-700 rounded"></div>
                </div>
                <div className="w-full h-10 bg-gray-700 rounded mb-3"></div>
                <div className="flex space-x-2">
                  <div className="w-20 h-6 bg-gray-700 rounded"></div>
                  <div className="w-20 h-6 bg-gray-700 rounded"></div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {tokenEntries.map(([name, token]) => (
              <motion.div
                key={name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="p-4 bg-white/5 rounded-xl border border-white/10"
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="text-white font-medium">{name}</h4>
                    <p className="text-gray-400 text-sm">API Token</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleDeleteToken(name)}
                      disabled={deleting}
                      className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {deleting ? <Loader className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 mb-3">
                  <code className="flex-1 px-3 py-2 bg-black/30 rounded-lg text-gray-300 font-mono text-sm">
                    {showTokens[name] ? token : '••••••••••••••••••••'}
                  </code>
                  <button
                    onClick={() => toggleTokenVisibility(name)}
                    className="p-2 text-gray-400 hover:text-white transition-colors"
                  >
                    {showTokens[name] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => copyToken(token as string)}
                    className="p-2 text-gray-400 hover:text-white transition-colors"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))}
            
            {tokenEntries.length === 0 && !loading && (
              <div className="text-center py-8">
                <Key className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">No API tokens</h3>
                <p className="text-gray-400 mb-4">Create your first API token to get started</p>
                <button
                  onClick={() => setShowNewTokenForm(true)}
                  className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all"
                >
                  Generate First Token
                </button>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
};