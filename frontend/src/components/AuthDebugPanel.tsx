'use client';

import { useAuth } from '../contexts/AuthContext';
import { authService } from '../services/auth';
import { useEffect, useState } from 'react';

interface DebugInfo {
  cookies: string;
  localStorage: string;
  hasTokens: boolean;
  user: any;
}

export default function AuthDebugPanel() {
  const { user, loading } = useAuth();
  const [debugInfo, setDebugInfo] = useState<DebugInfo>({
    cookies: '',
    localStorage: '',
    hasTokens: false,
    user: null
  });

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const updateDebugInfo = () => {
        setDebugInfo({
          cookies: document.cookie,
          localStorage: localStorage.getItem('user_data') || 'null',
          hasTokens: authService.isAuthenticated(),
          user: user
        });
      };

      updateDebugInfo();
      
      // Update every 2 seconds to show real-time changes
      const interval = setInterval(updateDebugInfo, 2000);
      
      return () => clearInterval(interval);
    }
  }, [user]);

  const clearAllData = () => {
    if (typeof window !== 'undefined') {
      // Clear localStorage
      localStorage.removeItem('user_data');
      
      // Clear cookies
      document.cookie.split(";").forEach(function(c) { 
        document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
      });
      
      console.log('🗑️ All auth data cleared');
      
      // Refresh the debug info
      setTimeout(() => {
        setDebugInfo({
          cookies: document.cookie,
          localStorage: localStorage.getItem('user_data') || 'null',
          hasTokens: authService.isAuthenticated(),
          user: user
        });
      }, 100);
    }
  };

  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 w-96 bg-gray-900 text-white p-4 rounded-lg shadow-2xl z-50 text-xs font-mono max-h-96 overflow-y-auto">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-bold text-yellow-400">🔍 Auth Debug Panel</h3>
        <button 
          onClick={clearAllData}
          className="bg-red-600 hover:bg-red-700 px-2 py-1 rounded text-xs"
        >
          Clear All
        </button>
      </div>
      
      <div className="space-y-3">
        {/* Loading State */}
        <div>
          <span className="text-blue-400">Loading:</span> 
          <span className={loading ? "text-yellow-400" : "text-green-400"}>
            {loading ? "⏳ Yes" : "✅ No"}
          </span>
        </div>

        {/* Auth Service Token Check */}
        <div>
          <span className="text-blue-400">Has Tokens:</span> 
          <span className={debugInfo.hasTokens ? "text-green-400" : "text-red-400"}>
            {debugInfo.hasTokens ? "✅ Yes" : "❌ No"}
          </span>
        </div>

        {/* User State */}
        <div>
          <span className="text-blue-400">User:</span> 
          <span className={debugInfo.user ? "text-green-400" : "text-red-400"}>
            {debugInfo.user ? `✅ ${debugInfo.user.email}` : "❌ null"}
          </span>
        </div>

        {/* Company ID */}
        {debugInfo.user && (
          <div>
            <span className="text-blue-400">Company ID:</span> 
            <span className="text-green-400">
              {debugInfo.user.companyId || "❌ Missing"}
            </span>
          </div>
        )}

        {/* Cookies */}
        <div>
          <span className="text-blue-400">Cookies:</span>
          <div className="bg-gray-800 p-2 rounded mt-1 max-h-20 overflow-y-auto">
            {debugInfo.cookies || "❌ No cookies"}
          </div>
        </div>

        {/* LocalStorage */}
        <div>
          <span className="text-blue-400">LocalStorage:</span>
          <div className="bg-gray-800 p-2 rounded mt-1 max-h-20 overflow-y-auto break-all">
            {debugInfo.localStorage}
          </div>
        </div>

        {/* Refresh Test */}
        <div className="pt-2 border-t border-gray-700">
          <button 
            onClick={() => window.location.reload()}
            className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-xs mr-2"
          >
            🔄 Test Refresh
          </button>
          <button 
            onClick={() => console.log('Current auth state:', { user, loading, hasTokens: debugInfo.hasTokens })}
            className="bg-purple-600 hover:bg-purple-700 px-3 py-1 rounded text-xs"
          >
            📝 Log State
          </button>
        </div>
      </div>
    </div>
  );
}
