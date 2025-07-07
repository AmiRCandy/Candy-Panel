import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Calendar, FileText, Smartphone, Loader } from 'lucide-react';
import { Client } from '@/types';

interface ClientFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (client: Omit<Client, 'id' | 'createdAt'>) => void;
  client?: Client;
  loading?: boolean;
}

export const ClientForm: React.FC<ClientFormProps> = ({ isOpen, onClose, onSave, client, loading = false }) => {
  const [formData, setFormData] = useState({
    name: client?.name || '',
    traffic: client ? (parseInt(client.traffic) / (1024 * 1024 * 1024)).toString() : '0',
    // Modified line: Add a more robust check for client?.expires
    endTime: client?.expires && !isNaN(new Date(client.expires).getTime())
      ? new Date(client.expires).toISOString().slice(0, 16)
      : '', // Fallback to empty string if expires is null/undefined or invalid date
    notes: client?.note || '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    
    onSave({
      ...formData,
      public_key: client?.public_key || '',
      private_key: client?.private_key || '',
      address: client?.address || '',
      wg: client?.wg || 0,
      created_at: client?.created_at || new Date().toISOString(),
      expires: formData.endTime || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      note: formData.notes,
      used_trafic: client?.used_trafic || { download: 0, upload: 0 },
      connected_now: client?.connected_now || false,
      status: client?.status !== undefined ? client.status : true,
    });
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
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Smartphone className="w-4 h-4 inline mr-2" />
              Client Name
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              placeholder="e.g., iPhone, Laptop"
              disabled={loading}
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
              <Calendar className="w-4 h-4 inline mr-2" />
              End Time
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
              <FileText className="w-4 h-4 inline mr-2" />
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
              className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50 flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <span>{client ? 'Update' : 'Create'} Client</span>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
};