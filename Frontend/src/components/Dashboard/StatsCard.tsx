import React from 'react';
import { motion } from 'framer-motion';
import { DivideIcon as LucideIcon } from 'lucide-react';

interface StatsCardProps {
  title: string;
  value: string;
  change?: string;
  icon: LucideIcon;
  color: 'blue' | 'purple' | 'green' | 'red';
}

const colorClasses = {
  blue: 'from-blue-500/20 to-blue-600/20 border-blue-500/30 text-blue-400',
  purple: 'from-purple-500/20 to-purple-600/20 border-purple-500/30 text-purple-400',
  green: 'from-green-500/20 to-green-600/20 border-green-500/30 text-green-400',
  red: 'from-red-500/20 to-red-600/20 border-red-500/30 text-red-400',
};

export const StatsCard: React.FC<StatsCardProps> = ({ title, value, change, icon: Icon, color }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`bg-gradient-to-br ${colorClasses[color]} border rounded-xl p-6 backdrop-blur-sm`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          {change && (
            <p className="text-sm text-gray-400 mt-1">{change}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg bg-gradient-to-br ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </motion.div>
  );
};