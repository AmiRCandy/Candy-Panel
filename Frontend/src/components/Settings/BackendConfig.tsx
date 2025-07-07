import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Server, Check, AlertCircle, Loader } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { apiService } from '@/services/api';

export const BackendConfig: React.FC = () => {
  const { setBackendUrl } = useAuth();
  const [url, setUrl] = useState('');
  const [testing, setTesting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    // Load saved backend URL
    const savedUrl = localStorage.getItem('candy-panel-backend-url') || 'http://localhost:8080/api';
    setUrl(savedUrl);
  }, []);

  const testConnection = async () => {
    if (!url.trim()) {
      setErrorMessage('Please enter a backend URL');
      setConnectionStatus('error');
      return;
    }

    setTesting(true);
    setConnectionStatus('idle');
    setErrorMessage('');

    try {
      // Temporarily set the URL for testing
      const originalBaseURL = apiService['baseURL'];
      apiService.setBaseURL(url);

      // Test connection with a simple health check
      const response = await fetch(`${url}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(10000), // 10 second timeout
      });

      if (response.ok) {
        setConnectionStatus('success');
        setBackendUrl(url);
      } else {
        throw new Error(`Server responded with status ${response.status}`);
      }
    } catch (error) {
      setConnectionStatus('error');
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          setErrorMessage('Connection timeout - please check if the server is running');
        } else {
          setErrorMessage(error.message);
        }
      } else {
        setErrorMessage('Failed to connect to backend server');
      }
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    if (connectionStatus === 'success') {
      setBackendUrl(url);
      localStorage.setItem('candy-panel-backend-url', url);
    } else {
      testConnection();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl p-6 border border-blue-500/20"
    >
      <h3 className="text-xl font-semibold text-white mb-6 flex items-center">
        <Server className="w-6 h-6 mr-3 text-blue-400" />
        Backend Configuration
      </h3>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Backend Server URL
          </label>
          <div className="flex space-x-3">
            <input
              type="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setConnectionStatus('idle');
                setErrorMessage('');
              }}
              placeholder="http://localhost:8080/api"
              className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none backdrop-blur-sm"
            />
            <button
              onClick={testConnection}
              disabled={testing}
              className="px-6 py-3 bg-blue-500/20 text-blue-300 rounded-xl hover:bg-blue-500/30 transition-colors border border-blue-500/30 disabled:opacity-50"
            >
              {testing ? (
                <Loader className="w-5 h-5 animate-spin" />
              ) : (
                'Test'
              )}
            </button>
          </div>
        </div>

        {/* Connection Status */}
        {connectionStatus !== 'idle' && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className={`p-4 rounded-xl border ${
              connectionStatus === 'success'
                ? 'bg-green-500/20 border-green-500/30'
                : 'bg-red-500/20 border-red-500/30'
            }`}
          >
            <div className="flex items-center space-x-2">
              {connectionStatus === 'success' ? (
                <Check className="w-5 h-5 text-green-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-400" />
              )}
              <span className={`font-medium ${
                connectionStatus === 'success' ? 'text-green-300' : 'text-red-300'
              }`}>
                {connectionStatus === 'success' ? 'Connection Successful' : 'Connection Failed'}
              </span>
            </div>
            {errorMessage && (
              <p className="text-red-300 text-sm mt-2">{errorMessage}</p>
            )}
          </motion.div>
        )}

        {/* API Endpoints Info */}
        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
          <h4 className="text-white font-medium mb-3">Expected API Endpoints</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
            <div className="text-gray-300">
              <span className="text-green-400">GET</span> /health
            </div>
            <div className="text-gray-300">
              <span className="text-blue-400">POST</span> /auth/login
            </div>
            <div className="text-gray-300">
              <span className="text-blue-400">GET</span> /server/status
            </div>
            <div className="text-gray-300">
              <span className="text-blue-400">GET</span> /clients
            </div>
            <div className="text-gray-300">
              <span className="text-blue-400">GET</span> /interfaces
            </div>
            <div className="text-gray-300">
              <span className="text-blue-400">GET</span> /stats/bandwidth
            </div>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={testing}
          className="w-full px-4 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50"
        >
          {connectionStatus === 'success' ? 'Save Configuration' : 'Test & Save'}
        </button>
      </div>
    </motion.div>
  );
};