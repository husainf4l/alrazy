'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';

interface DashboardHeaderProps {
  title: string;
  searchPlaceholder?: string;
  showSearch?: boolean;
  showAlerts?: boolean;
  showSecurityStatus?: boolean;
}

export default function DashboardHeader({ 
  title, 
  searchPlaceholder = "Search threats, logs...",
  showSearch = true,
  showAlerts = true,
  showSecurityStatus = true
}: DashboardHeaderProps) {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  return (
    <header className="h-16 bg-white/95 backdrop-blur-xl border-b border-gray-200/50 flex items-center justify-between px-6 shadow-sm sticky top-0 z-30">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 capitalize tracking-tight">
          {title}
        </h1>
      </div>
      
      <div className="flex items-center space-x-4">
        {/* Search */}
        {showSearch && (
          <div className="relative">
            <input
              type="text"
              placeholder={searchPlaceholder}
              className="w-72 h-9 pl-10 pr-4 text-sm bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 focus:bg-white transition-all duration-200 placeholder-gray-400"
            />
            <svg
              className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        )}

        {/* Threat Alerts */}
        {showAlerts && (
          <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-all duration-200">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
          </button>
        )}

        {/* Security Status */}
        {showSecurityStatus && (
          <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-sm font-medium">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span>Secure</span>
          </div>
        )}

        {/* Profile */}
        <div className="relative group">
          <button className="flex items-center space-x-2 p-1.5 hover:bg-gray-100 rounded-lg transition-all duration-200">
            <div className="w-8 h-8 bg-gradient-to-br from-red-400 via-orange-500 to-yellow-600 rounded-xl flex items-center justify-center text-white text-xs font-semibold shadow-lg">
              {user?.firstName && user?.lastName 
                ? `${user.firstName[0]}${user.lastName[0]}`.toUpperCase() 
                : user?.username?.substring(0, 2).toUpperCase() || 'U'}
            </div>
            <div className="hidden md:block text-left">
              <div className="text-sm font-medium text-gray-900">
                {user?.firstName && user?.lastName 
                  ? `${user.firstName} ${user.lastName}` 
                  : user?.username}
              </div>
              <div className="text-xs text-gray-500">{user?.email}</div>
            </div>
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {/* Dropdown Menu */}
          <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-xl shadow-lg border border-gray-200 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
            <div className="px-4 py-3 border-b border-gray-100">
              <div className="font-medium text-gray-900">
                {user?.firstName && user?.lastName 
                  ? `${user.firstName} ${user.lastName}` 
                  : user?.username}
              </div>
              <div className="text-sm text-gray-500">{user?.email}</div>
            </div>
            
            <button 
              onClick={() => router.push('/change-password')}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-200"
            >
              Change Password
            </button>
            
            <button 
              onClick={() => router.push('/two-factor-setup')}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-200"
            >
              Setup 2FA
            </button>
            
            <div className="border-t border-gray-100 mt-2 pt-2">
              <button 
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors duration-200"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
