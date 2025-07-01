'use client';

import { useRouter } from 'next/navigation';
import { Sidebar, Icon } from '../../../components';
import { useAuth } from '../../../contexts/AuthContext';
import CameraManagement from '../../../components/CameraManagement';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleItemClick = (itemId: string) => {
    if (itemId === 'dashboard') {
      router.push('/dashboard');
    } else if (itemId === 'users') {
      router.push('/dashboard/users');
    } else if (itemId === 'analytics') {
      router.push('/dashboard/analytics');
    } else if (itemId === 'projects') {
      router.push('/dashboard/projects');
    } else if (itemId === 'messages') {
      router.push('/dashboard/messages');
    } else if (itemId === 'calendar') {
      router.push('/dashboard/calendar');
    } else if (itemId === 'settings') {
      // Already on settings page
      return;
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50 font-sans antialiased">
      {/* Sidebar */}
      <Sidebar activeItem="settings" onItemClick={handleItemClick} />

      {/* Main Content */}
      <div className="ml-14 flex flex-col min-h-screen">
        {/* Header */}
        <header className="h-16 bg-white/95 backdrop-blur-xl border-b border-gray-200/50 flex items-center justify-between px-6 shadow-sm sticky top-0 z-30">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 capitalize tracking-tight">
              Security Settings
            </h1>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Search */}
            <div className="relative">
              <input
                type="text"
                placeholder="Search settings..."
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

            {/* Threat Alerts */}
            <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-all duration-200">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
            </button>

            {/* Security Status */}
            <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-sm font-medium">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>Secure</span>
            </div>

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

        {/* Main Content Area */}
        <main className="flex-1 bg-gradient-to-br from-gray-50 to-gray-100/50">
          <div className="max-w-7xl mx-auto">
            {/* Settings Page */}
            <div className="p-8 space-y-8">
              {/* Settings Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Security Settings</h2>
                  <p className="text-gray-600 mt-1">Manage your AI security cameras and system configuration</p>
                </div>
              </div>

              {/* Camera Management Component */}
    
              {user?.companyId ? (
                <CameraManagement companyId={user.companyId} />
              ) : (
                <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 p-8 text-center">
                  <div className="text-gray-500">
                    <Icon name="camera" className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Camera Management</h3>
                    <p className="text-sm text-gray-600 mb-4">
                      {user ? 'Your account is not associated with a company. Please contact support.' : 'Please log in to manage your security cameras'}
                    </p>
                    <button 
                      onClick={() => router.push('/login')}
                      className="px-4 py-2 bg-gradient-to-r from-red-600 to-orange-600 text-white text-sm font-semibold rounded-lg hover:from-red-700 hover:to-orange-700 transition-all duration-200"
                    >
                      {user ? 'Contact Support' : 'Login to Continue'}
                    </button>
                  </div>
                </div>
              )}

              {/* AI Detection Settings */}
              <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
                <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-gray-200/50">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                    <Icon name="analytics" className="w-5 h-5 text-blue-600" />
                    <span>AI Detection Settings</span>
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">Configure motion detection and security alerts</p>
                </div>

                <div className="p-6 space-y-6">
                  {/* Detection Sensitivity */}
                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-gray-700">Motion Detection Sensitivity</label>
                    <div className="flex items-center space-x-4">
                      <span className="text-sm text-gray-500">Low</span>
                      <div className="flex-1 h-2 bg-gray-200 rounded-full">
                        <div className="h-2 bg-gradient-to-r from-red-500 to-orange-500 rounded-full" style={{width: '75%'}}></div>
                      </div>
                      <span className="text-sm text-gray-500">High</span>
                    </div>
                  </div>

                  {/* Alert Settings */}
                  <div className="grid grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <h4 className="font-medium text-gray-900">Alert Notifications</h4>
                      <div className="space-y-3">
                        {['Email Alerts', 'SMS Notifications', 'Push Notifications', 'Webhook Integration'].map((option) => (
                          <label key={option} className="flex items-center space-x-3">
                            <input type="checkbox" className="rounded border-gray-300 text-red-600 focus:ring-red-500" defaultChecked />
                            <span className="text-sm text-gray-700">{option}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-4">
                      <h4 className="font-medium text-gray-900">Detection Zones</h4>
                      <div className="space-y-3">
                        {['Entrance Areas', 'Cash Register Zone', 'Storage Areas', 'Customer Areas'].map((zone) => (
                          <label key={zone} className="flex items-center space-x-3">
                            <input type="checkbox" className="rounded border-gray-300 text-red-600 focus:ring-red-500" defaultChecked />
                            <span className="text-sm text-gray-700">{zone}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Save Button */}
                  <div className="pt-4 border-t border-gray-200">
                    <button className="px-6 py-2 bg-gradient-to-r from-red-600 to-orange-600 text-white text-sm font-semibold rounded-xl hover:from-red-700 hover:to-orange-700 transition-all duration-200 shadow-lg hover:shadow-xl">
                      Save Settings
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
