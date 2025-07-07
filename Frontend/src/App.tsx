import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Layout } from './components/Layout/Layout';
import { InstallationWizard } from './components/InstallationWizard';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Clients } from './pages/Clients';
import { Server } from './pages/Server';
import { Configs } from './pages/Configs';
import { API } from './pages/API';
import { Settings } from './pages/Settings';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation } from 'react-router-dom';

const PageTransition: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
};

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white">Loading Candy Panel...</p>
        </div>
      </div>
    );
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const AppContent: React.FC = () => {
  const { isAuthenticated, isFirstTime, completeSetup } = useAuth();
  
  if (isFirstTime) {
    return <InstallationWizard onComplete={completeSetup} />;
  }
  
  return (
    <div className="min-h-screen bg-black">
      <Router>
        <Routes>
          <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
          <Route path="/" element={
            <ProtectedRoute>
              <Layout>
                <PageTransition>
                  <Dashboard />
                </PageTransition>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/clients" element={
            <ProtectedRoute>
              <Layout>
                <PageTransition>
                  <Clients />
                </PageTransition>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/server" element={
            <ProtectedRoute>
              <Layout>
                <PageTransition>
                  <Server />
                </PageTransition>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/configs" element={
            <ProtectedRoute>
              <Layout>
                <PageTransition>
                  <Configs />
                </PageTransition>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/api" element={
            <ProtectedRoute>
              <Layout>
                <PageTransition>
                  <API />
                </PageTransition>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/settings" element={
            <ProtectedRoute>
              <Layout>
                <PageTransition>
                  <Settings />
                </PageTransition>
              </Layout>
            </ProtectedRoute>
          } />
        </Routes>
      </Router>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
