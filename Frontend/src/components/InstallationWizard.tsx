import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Server, Network, Users, CheckCircle, ArrowRight, ArrowLeft, Loader } from 'lucide-react';
import { installService } from '@/services/installService';
import { InstallationData } from '@/types';

interface InstallationStep {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<any>;
  component: React.ComponentType<any>;
}

const steps: InstallationStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to Candy Panel',
    description: 'Let\'s set up your WireGuard management system',
    icon: Shield,
    component: WelcomeStep
  },
  {
    id: 'server',
    title: 'Server Configuration',
    description: 'Configure your server settings',
    icon: Server,
    component: ServerStep
  },
  {
    id: 'network',
    title: 'Network Setup',
    description: 'Set up network and security options',
    icon: Network,
    component: NetworkStep
  },
  {
    id: 'admin',
    title: 'Admin Account',
    description: 'Create your administrator account',
    icon: Users,
    component: AdminStep
  },
  {
    id: 'installation',
    title: 'Installing',
    description: 'Setting up your Candy Panel',
    icon: Loader,
    component: InstallationStep
  },
  {
    id: 'complete',
    title: 'Installation Complete',
    description: 'Your Candy Panel is ready to use',
    icon: CheckCircle,
    component: CompleteStep
  }
];

interface InstallationWizardProps {
  onComplete: () => void;
}

export const InstallationWizard: React.FC<InstallationWizardProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [installationData, setInstallationData] = useState<InstallationData>({
    server_ip: '',
    wg_port: '51820',
    wg_address_range: '10.0.0.1/24',
    wg_dns: '8.8.8.8',
    admin_user: 'admin',
    admin_password: ''
  });

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const updateData = (data: Partial<InstallationData>) => {
    setInstallationData({ ...installationData, ...data });
  };

  const CurrentStepComponent = steps[currentStep].component;

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {steps.map((step, index) => {
              const Icon = step.icon;
              const isActive = index === currentStep;
              const isCompleted = index < currentStep;
              
              return (
                <div key={step.id} className="flex items-center">
                  <div className={`flex items-center justify-center w-12 h-12 rounded-full border-2 transition-all ${
                    isCompleted 
                      ? 'bg-green-500 border-green-500 text-white' 
                      : isActive 
                        ? 'bg-blue-500 border-blue-500 text-white' 
                        : 'bg-gray-800 border-gray-700 text-gray-400'
                  }`}>
                    {isCompleted ? (
                      <CheckCircle className="w-6 h-6" />
                    ) : (
                      <Icon className="w-6 h-6" />
                    )}
                  </div>
                  {index < steps.length - 1 && (
                    <div className={`w-16 h-0.5 mx-4 transition-all ${
                      isCompleted ? 'bg-green-500' : 'bg-gray-700'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
          <div className="text-center">
            <h2 className="text-2xl font-bold text-white">{steps[currentStep].title}</h2>
            <p className="text-gray-400 mt-1">{steps[currentStep].description}</p>
          </div>
        </div>

        {/* Step Content */}
        <div className="glass rounded-2xl p-8 border border-gray-800 min-h-[400px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <CurrentStepComponent
                data={installationData}
                updateData={updateData}
                onNext={nextStep}
                onPrev={prevStep}
                onComplete={onComplete}
                isFirst={currentStep === 0}
                isLast={currentStep === steps.length - 1}
              />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

// Step Components
function WelcomeStep({ onNext }: any) {
  return (
    <div className="text-center space-y-6">
      <div className="w-24 h-24 bg-gradient-to-br from-blue-400 to-purple-500 rounded-2xl flex items-center justify-center mx-auto">
        <Shield className="w-12 h-12 text-white" />
      </div>
      <div>
        <h3 className="text-3xl font-bold text-white mb-4">Welcome to Candy Panel</h3>
        <p className="text-gray-300 text-lg max-w-2xl mx-auto">
          The most advanced WireGuard management panel. We'll guide you through the setup process to get your VPN server running in minutes.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="p-6 bg-white/5 rounded-xl border border-white/10">
          <Server className="w-8 h-8 text-blue-400 mb-3" />
          <h4 className="text-white font-semibold mb-2">Easy Setup</h4>
          <p className="text-gray-400 text-sm">Automated installation and configuration</p>
        </div>
        <div className="p-6 bg-white/5 rounded-xl border border-white/10">
          <Network className="w-8 h-8 text-purple-400 mb-3" />
          <h4 className="text-white font-semibold mb-2">Secure by Default</h4>
          <p className="text-gray-400 text-sm">Industry-standard security practices</p>
        </div>
        <div className="p-6 bg-white/5 rounded-xl border border-white/10">
          <Users className="w-8 h-8 text-green-400 mb-3" />
          <h4 className="text-white font-semibold mb-2">User Management</h4>
          <p className="text-gray-400 text-sm">Comprehensive client management tools</p>
        </div>
      </div>
      <button
        onClick={onNext}
        className="flex items-center space-x-2 px-8 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all mx-auto transform hover:scale-105"
      >
        <span>Get Started</span>
        <ArrowRight className="w-5 h-5" />
      </button>
    </div>
  );
}

function ServerStep({ data, updateData, onNext, onPrev }: any) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold text-white mb-2">Server Configuration</h3>
        <p className="text-gray-400">Configure your server's basic settings</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Server IP Address
          </label>
          <input
            type="text"
            value={data.server_ip}
            onChange={(e) => updateData({ server_ip: e.target.value })}
            placeholder="192.168.1.100"
            className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none backdrop-blur-sm"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            WireGuard Port
          </label>
          <input
            type="text"
            value={data.wg_port}
            onChange={(e) => updateData({ wg_port: e.target.value })}
            className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
          />
        </div>
      </div>

      <div className="bg-blue-500/20 border border-blue-500/30 rounded-xl p-4">
        <h4 className="text-blue-300 font-medium mb-2">Auto-Detection</h4>
        <p className="text-sm text-gray-300">
          We'll automatically detect your server's public IP address. You can change this later if needed.
        </p>
      </div>

      <div className="flex justify-between pt-6">
        <button
          onClick={onPrev}
          className="flex items-center space-x-2 px-6 py-3 bg-gray-800 text-gray-300 rounded-xl hover:bg-gray-700 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back</span>
        </button>
        <button
          onClick={onNext}
          disabled={!data.server_ip}
          className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50"
        >
          <span>Continue</span>
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

function NetworkStep({ data, updateData, onNext, onPrev }: any) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold text-white mb-2">Network Setup</h3>
        <p className="text-gray-400">Configure network and DNS settings</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            VPN Network Range
          </label>
          <input
            type="text"
            value={data.wg_address_range}
            onChange={(e) => updateData({ wg_address_range: e.target.value })}
            className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            DNS Servers
          </label>
          <input
            type="text"
            value={data.wg_dns}
            onChange={(e) => updateData({ wg_dns: e.target.value })}
            className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:border-blue-500 focus:outline-none backdrop-blur-sm"
          />
        </div>
      </div>

      <div className="bg-green-500/20 border border-green-500/30 rounded-xl p-4">
        <h4 className="text-green-300 font-medium mb-2">Recommended Settings</h4>
        <p className="text-sm text-gray-300">
          We've pre-configured optimal settings for most use cases. These can be customized later in the admin panel.
        </p>
      </div>

      <div className="flex justify-between pt-6">
        <button
          onClick={onPrev}
          className="flex items-center space-x-2 px-6 py-3 bg-gray-800 text-gray-300 rounded-xl hover:bg-gray-700 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back</span>
        </button>
        <button
          onClick={onNext}
          className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all"
        >
          <span>Continue</span>
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

function AdminStep({ data, updateData, onNext, onPrev }: any) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold text-white mb-2">Create Admin Account</h3>
        <p className="text-gray-400">Set up your administrator credentials</p>
      </div>
      
      <div className="space-y-4 max-w-md mx-auto">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Username
          </label>
          <input
            type="text"
            value={data.admin_user}
            onChange={(e) => updateData({ admin_user: e.target.value })}
            placeholder="admin"
            className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none backdrop-blur-sm"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Password
          </label>
          <input
            type="password"
            value={data.admin_password}
            onChange={(e) => updateData({ admin_password: e.target.value })}
            placeholder="Enter a strong password"
            className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none backdrop-blur-sm"
          />
        </div>
      </div>

      <div className="bg-yellow-500/20 border border-yellow-500/30 rounded-xl p-4">
        <h4 className="text-yellow-300 font-medium mb-2">Security Note</h4>
        <p className="text-sm text-gray-300">
          Choose a strong password with at least 8 characters, including uppercase, lowercase, numbers, and special characters.
        </p>
      </div>

      <div className="flex justify-between pt-6">
        <button
          onClick={onPrev}
          className="flex items-center space-x-2 px-6 py-3 bg-gray-800 text-gray-300 rounded-xl hover:bg-gray-700 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back</span>
        </button>
        <button
          onClick={onNext}
          disabled={!data.admin_user || !data.admin_password}
          className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50"
        >
          <span>Start Installation</span>
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

function InstallationStep({ data, onNext }: any) {
  const [progress, setProgress] = useState(0);
  const [currentTask, setCurrentTask] = useState('Initializing...');
  const [error, setError] = useState<string | null>(null);

  const tasks = [
    'Installing WireGuard...',
    'Generating server keys...',
    'Configuring network interfaces...',
    'Setting up firewall rules...',
    'Creating database...',
    'Configuring web server...',
    'Finalizing installation...'
  ];

  React.useEffect(() => {
    const performInstallation = async () => {
      try {
        setCurrentTask('Starting installation...');
        await installService.performInstallation(data);
        
        // Simulate progress for UI
        const interval = setInterval(() => {
          setProgress(prev => {
            const newProgress = prev + 1;
            const taskIndex = Math.floor((newProgress / 100) * tasks.length);
            if (taskIndex < tasks.length) {
              setCurrentTask(tasks[taskIndex]);
            }
            
            if (newProgress >= 100) {
              clearInterval(interval);
              setTimeout(onNext, 1000);
              return 100;
            }
            return newProgress;
          });
        }, 100);
      } catch (error) {
        setError(error instanceof Error ? error.message : 'Installation failed');
      }
    };

    performInstallation();
  }, [data, onNext]);

  if (error) {
    return (
      <div className="text-center space-y-6">
        <div className="w-24 h-24 bg-red-500/20 rounded-2xl flex items-center justify-center mx-auto">
          <Shield className="w-12 h-12 text-red-400" />
        </div>
        <div>
          <h3 className="text-2xl font-bold text-white mb-4">Installation Failed</h3>
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors"
          >
            Retry Installation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="text-center space-y-8">
      <div className="w-24 h-24 bg-gradient-to-br from-blue-400 to-purple-500 rounded-2xl flex items-center justify-center mx-auto">
        <Loader className="w-12 h-12 text-white animate-spin" />
      </div>
      
      <div>
        <h3 className="text-2xl font-bold text-white mb-4">Installing Candy Panel</h3>
        <p className="text-gray-400 mb-8">Please wait while we set up your WireGuard management system...</p>
        
        <div className="max-w-md mx-auto">
          <div className="flex justify-between text-sm text-gray-400 mb-2">
            <span>{currentTask}</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function CompleteStep({ onComplete }: any) {
  return (
    <div className="text-center space-y-6">
      <div className="w-24 h-24 bg-gradient-to-br from-green-400 to-blue-500 rounded-2xl flex items-center justify-center mx-auto">
        <CheckCircle className="w-12 h-12 text-white" />
      </div>
      
      <div>
        <h3 className="text-3xl font-bold text-white mb-4">Installation Complete!</h3>
        <p className="text-gray-300 text-lg max-w-2xl mx-auto">
          Your Candy Panel has been successfully installed and configured. You can now start managing your WireGuard server.
        </p>
      </div>

      <button
        onClick={onComplete}
        className="flex items-center space-x-2 px-8 py-3 bg-gradient-to-r from-green-500 to-blue-500 text-white rounded-xl hover:from-green-600 hover:to-blue-600 transition-all mx-auto transform hover:scale-105"
      >
        <span>Enter Candy Panel</span>
        <ArrowRight className="w-5 h-5" />
      </button>
    </div>
  );
}