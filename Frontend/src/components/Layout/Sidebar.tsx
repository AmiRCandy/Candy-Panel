import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, Users, Server, Settings, FileText, Shield, Zap, LogOut, X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Clients', href: '/clients', icon: Users },
  { name: 'Server', href: '/server', icon: Server },
  { name: 'Configs', href: '/configs', icon: FileText },
  { name: 'API', href: '/api', icon: Zap },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onToggle }) => {
  const location = useLocation();
  const { logout } = useAuth();

  return (
    <div className="h-full w-64 bg-black border-r border-gray-800 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-800">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-black" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">Candy Panel</h1>
            <p className="text-xs text-gray-400">WireGuard Manager</p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="lg:hidden p-2 rounded-lg hover:bg-gray-800 transition-colors"
        >
          <X className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                isActive
                  ? 'bg-gray-800 text-white border border-gray-700'
                  : 'text-gray-400 hover:text-white hover:bg-gray-900'
              }`}
              onClick={() => window.innerWidth < 1024 && onToggle()}
            >
              <item.icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-gray-400 group-hover:text-white'}`} />
              <span className="font-medium">{item.name}</span>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-white" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <button
          onClick={logout}
          className="flex items-center space-x-3 w-full px-3 py-2.5 text-gray-400 hover:text-white hover:bg-gray-900 rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span>Logout</span>
        </button>
        <div className="mt-4 text-center text-xs text-gray-500">
          Built with 💜 for WireGuard Enthusiasts
        </div>
      </div>
    </div>
  );
};