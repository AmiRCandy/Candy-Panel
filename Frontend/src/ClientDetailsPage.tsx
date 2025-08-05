// Frontend/src/ClientDetailsPage.tsx
import React, { useState, useEffect } from 'react';
import {
  Download,
  QrCode,
  Clock,
  Calendar,
  Activity,
  Upload,
  HardDrive,
  User,
  Shield,
  Wifi,
  ChevronDown,
  ChevronUp,
  AlertCircle, // Added for error display
} from 'lucide-react';
import { useParams } from 'react-router-dom'; // Import useParams
import { apiClient } from './utils/api'; // Import apiClient
import { Client } from './types'; // Import Client interface

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (dateString: string): string => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return 'Invalid Date';
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatUptime = (seconds: number): string => { // Reusing function from main App.tsx
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};


const getTrafficPercentage = (used: number, total: number): number => {
  if (total === 0) return 0;
  return Math.min((used / total) * 100, 100);
};

function ClientDetailsPage() { // Renamed from App to ClientDetailsPage
  const { clientname, clientpubkey } = useParams<{ clientname: string; clientpubkey: string }>(); // Get params from URL
  const [clientData, setClientData] = useState<Client | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showQR, setShowQR] = useState(false);

  useEffect(() => {
    const fetchClient = async () => {
      setLoading(true);
      setError(null);
      if (!clientname || !clientpubkey) {
        setError("Client name or public key missing from URL.");
        setLoading(false);
        return;
      }
      try {
        const response = await apiClient.getClientDetails(clientname, clientpubkey);
        if (response.success && response.data) {
          setClientData(response.data);
        } else {
          setError(response.message || 'Failed to load client data.');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Network error while fetching client data.');
        console.error("Error fetching client data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchClient();
  }, [clientname, clientpubkey]); // Re-fetch if clientname or public key changes

  const handleDownload = async () => {
    if (!clientData) return;
    setIsDownloading(true);
    try {
      // Reconstruct the config using live data
      const config = `# WARNING: This configuration does not contain your private key for security.
# For the full config, please ask your administrator.
[Interface]
PrivateKey = <YOUR_CLIENT_PRIVATE_KEY_HERE>
Address = ${clientData.address}/32
DNS = ${clientData.server_dns}
MTU = ${clientData.server_mtu}

[Peer]
PublicKey = ${clientData.interface_public_key}
Endpoint = ${clientData.server_endpoint_ip}:${clientData.interface_port}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25`;

      const blob = new Blob([config], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${clientData.name.replace(/\s+/g, '_')}.conf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Error downloading config:", e);
      // Optionally show an error message
    } finally {
      setIsDownloading(false);
    }
  };

  const handleShowQR = () => {
    setShowQR(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="text-center text-white">
          <Shield className="w-16 h-16 text-blue-600 animate-pulse mx-auto mb-4" />
          <p className="text-xl font-semibold">Loading Client Details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="bg-red-900/50 border border-red-700 rounded-2xl shadow-2xl p-8 w-full max-w-lg text-red-300 text-center animate-fade-in">
          <AlertCircle className="w-12 h-12 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Error</h1>
          <p>{error}</p>
          <p className="text-sm mt-4">Please check the URL or contact support.</p>
        </div>
      </div>
    );
  }

  if (!clientData) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="bg-gray-800 rounded-2xl shadow-2xl p-8 w-full max-w-lg text-gray-400 text-center animate-fade-in">
          <Shield className="w-12 h-12 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Client Not Found</h1>
          <p>The client details could not be loaded. It might not exist, or the link is incorrect.</p>
        </div>
      </div>
    );
  }

  const totalUsedTraffic = clientData.used_trafic.download + clientData.used_trafic.upload;
  const trafficLimit = parseInt(clientData.traffic) || 0; // Ensure traffic is parsed as number
  const trafficPercentage = getTrafficPercentage(totalUsedTraffic, trafficLimit);

  return (
    <div className="min-h-screen bg-gray-900 p-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl mx-auto mb-4 flex items-center justify-center animate-pulse">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Candy Panel Wiregaurd Client</h1>
          <p className="text-gray-400">Configuration Details</p>
        </div>

        {/* Main Client Card */}
        <div className="bg-gray-800 rounded-2xl shadow-2xl border border-gray-700 overflow-hidden">
          {/* Client Header */}
          <div className="p-6 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center">
                  <User className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">{clientData.name}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <div className={`w-2 h-2 rounded-full ${clientData.status ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
                    <span className="text-sm text-gray-400 capitalize">{clientData.status ? 'Active' : 'Inactive'}</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-400">IP Address</p>
                <p className="text-white font-mono">{clientData.address}</p>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Created At */}
            <div className="bg-gray-700/50 rounded-xl p-4 hover:bg-gray-700 transition-all duration-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-600/20 rounded-lg flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Created</p>
                  <p className="text-white font-medium">{formatDate(clientData.created_at)}</p>
                </div>
              </div>
            </div>

            {/* Expires */}
            <div className="bg-gray-700/50 rounded-xl p-4 hover:bg-gray-700 transition-all duration-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-orange-600/20 rounded-lg flex items-center justify-center">
                  <Clock className="w-5 h-5 text-orange-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Expires</p>
                  <p className="text-white font-medium">{formatDate(clientData.expires)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Traffic Usage */}
          <div className="p-6 border-t border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-400" />
              Traffic Usage
            </h3>
            
            {/* Progress Bar */}
            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-400 mb-2">
                <span>Used: {formatBytes(totalUsedTraffic)}</span>
                <span>Limit: {formatBytes(trafficLimit)}</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-3">
                <div
                  className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${trafficPercentage}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1 text-center">{trafficPercentage.toFixed(1)}% used</p>
            </div>

            {/* Download/Upload Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-gray-700/50 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-600/20 rounded-lg flex items-center justify-center">
                    <HardDrive className="w-4 h-4 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Download</p>
                    <p className="text-white font-medium">{formatBytes(clientData.used_trafic.download)}</p>
                  </div>
                </div>
              </div>
              <div className="bg-gray-700/50 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-green-600/20 rounded-lg flex items-center justify-center">
                    <Upload className="w-4 h-4 text-green-400" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Upload</p>
                    <p className="text-white font-medium">{formatBytes(clientData.used_trafic.upload)}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="p-6 border-t border-gray-700 bg-gray-800/50">
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleDownload}
                disabled={isDownloading}
                className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white py-3 px-6 rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105"
              >
                <Download className={`w-5 h-5 ${isDownloading ? 'animate-bounce' : ''}`} />
                {isDownloading ? 'Downloading...' : 'Download Config'}
              </button>
              <button
                onClick={handleShowQR}
                className="flex-1 flex items-center justify-center gap-2 bg-purple-600 text-white py-3 px-6 rounded-xl hover:bg-purple-700 transition-all duration-200 transform hover:scale-105"
              >
                <QrCode className="w-5 h-5" />
                Show QR Code
              </button>
            </div>
          </div>

          {/* Expandable Details */}
          <div className="border-t border-gray-700">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="w-full p-4 flex items-center justify-center gap-2 text-gray-400 hover:text-white hover:bg-gray-700/30 transition-all duration-200"
            >
              <span className="text-sm">Technical Details</span>
              {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            
            {showDetails && (
              <div className="p-6 pt-0 animate-fade-in">
                <div className="bg-gray-700/30 rounded-xl p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Endpoint:</span>
                    <span className="text-white font-mono text-sm">{clientData.server_endpoint_ip}:{clientData.interface_port}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Allowed IPs:</span>
                    <span className="text-white font-mono text-sm">0.0.0.0/0, ::/0</span> {/* This is usually fixed for clients */}
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">DNS:</span>
                    <span className="text-white font-mono text-sm">{clientData.server_dns}</span>
                  </div>
                   <div className="flex justify-between">
                    <span className="text-gray-400">MTU:</span>
                    <span className="text-white font-mono text-sm">{clientData.server_mtu}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Protocol:</span>
                    <span className="text-white font-mono text-sm">WireGuard</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* QR Code Modal */}
        {showQR && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-gray-800 rounded-2xl p-6 max-w-sm w-full border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4 text-center">QR Code</h3>
              <div className="bg-white rounded-xl p-4 mb-4 flex justify-center items-center">
                <img
                    src={`/qr/${clientname}/${clientpubkey}`}
                    alt="QR Code"
                    className="max-w-full h-auto"
                />
              </div>
              <p className="text-gray-400 text-sm text-center mb-4">
                Scan this code with the WireGuard app to import the configuration.
              </p>
              <button
                onClick={() => setShowQR(false)}
                className="w-full bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-all duration-200"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ClientDetailsPage; // Export with the new name