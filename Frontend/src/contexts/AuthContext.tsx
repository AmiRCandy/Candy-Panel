import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiService } from '@/services/api';
import { API_CONFIG } from '@/config/api';

export interface LoginCredentials {
  action:string,
  username: string;
  password: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  login: (credentials: LoginCredentials) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  isFirstTime: boolean;
  completeSetup: () => void;
  setBackendUrl: (url: string) => void;
  checkSystemStatus: () => Promise<'admin' | 'install'>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFirstTime, setIsFirstTime] = useState(false);

  // Check system status on startup
  const checkSystemStatus = async (): Promise<'admin' | 'install'> => {
    try {
      // Change to apiService.get as /check is a GET endpoint
      const response = await apiService.get<any>(API_CONFIG.ENDPOINTS.CHECK_INSTALLATION);
      // Directly check the 'installed' property from the response data
      if (response.success && response.data?.installed === false) {
        return 'install';
      }
      return 'admin';
    } catch (error) {
      console.error('Failed to check system status:', error);
      return 'admin'; // Default to admin if check fails
    }
  };

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Load saved backend URL
        const savedBackendUrl = localStorage.getItem('candy-panel-backend-url');
        if (savedBackendUrl) {
          apiService.setBaseURL(savedBackendUrl);
        }

        // Check system status
        const systemStatus = await checkSystemStatus();
        
        if (systemStatus === 'install') {
          setIsFirstTime(true);
          setIsLoading(false);
          return;
        }

        // Check if user is authenticated
        const token = localStorage.getItem('candy-panel-token');
        const userData = localStorage.getItem('candy-panel-user');
        
        if (token && userData) {
          try {
            const parsedUser = JSON.parse(userData);
            setUser(parsedUser);
          } catch (error) {
            console.error('Failed to parse user data:', error);
            localStorage.removeItem('candy-panel-token');
            localStorage.removeItem('candy-panel-user');
          }
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (credentials: LoginCredentials): Promise<boolean> => {
    try {
      const response = await apiService.post(API_CONFIG.ENDPOINTS.LOGIN_AUTH, credentials);
      
      if (response.success && response.data?.access_token) {
        // Store token
        localStorage.setItem('candy-panel-token', response.data.access_token);
        
        // Create user object (since your backend doesn't return user details in login)
        const userData = {
          id: '1',
          username: credentials.username,
          email: `${credentials.username}@candypanel.com`,
          role: 'admin'
        };
        
        localStorage.setItem('candy-panel-user', JSON.stringify(userData));
        setUser(userData);
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const logout = async () => {
    try {
      // Clear local storage
      localStorage.removeItem('candy-panel-token');
      localStorage.removeItem('candy-panel-user');
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const completeSetup = () => {
    setIsFirstTime(false);
    // After installation, user should login normally
  };

  const setBackendUrl = (url: string) => {
    apiService.setBaseURL(url);
    localStorage.setItem('candy-panel-backend-url', url);
  };

  return (
    <AuthContext.Provider value={{
      user,
      login,
      logout,
      isAuthenticated: !!user,
      isLoading,
      isFirstTime,
      completeSetup,
      setBackendUrl,
      checkSystemStatus
    }}>
      {children}
    </AuthContext.Provider>
  );
};
