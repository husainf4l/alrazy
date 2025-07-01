'use client';

import { useState, useEffect } from 'react';
import { User, CameraAccessLevel } from '../types/user';
import { authService } from '../services/auth';
import { Icon } from '../components';

interface UsersComponentProps {
  companyId: number;
}

const UsersComponent = ({ companyId }: UsersComponentProps) => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const companyUsers = await authService.getCompanyUsers(companyId);
        setUsers(companyUsers);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch users');
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, [companyId]);

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'SUPER_ADMIN': return 'bg-purple-100 text-purple-800';
      case 'COMPANY_ADMIN': return 'bg-blue-100 text-blue-800';
      case 'USER': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getAccessLevelBadgeColor = (level: CameraAccessLevel) => {
    switch (level) {
      case 'ADMIN': return 'bg-red-100 text-red-800';
      case 'OPERATOR': return 'bg-orange-100 text-orange-800';
      case 'VIEWER': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
      <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200/50">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
          <Icon name="users" className="w-5 h-5 text-blue-600" />
          <span>Company Users ({users.length})</span>
        </h3>
        <p className="text-sm text-gray-600 mt-1">Manage user access and permissions</p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Role
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Camera Access
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Login
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.map((userData) => (
              <tr key={userData.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-10 w-10">
                      <div className="h-10 w-10 rounded-full bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
                        <span className="text-white font-medium">
                          {userData.firstName?.[0]}{userData.lastName?.[0]}
                        </span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">
                        {userData.firstName} {userData.lastName}
                      </div>
                      <div className="text-sm text-gray-500">
                        {userData.email}
                      </div>
                      <div className="text-xs text-gray-400">
                        @{userData.username}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRoleBadgeColor(userData.role)}`}>
                    {userData.role.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="space-y-1">
                    {userData.cameraAccess && userData.cameraAccess.length > 0 ? (
                      userData.cameraAccess.slice(0, 3).map((access) => (
                        <div key={access.id} className="flex items-center space-x-2">
                          <span className="text-sm text-gray-700 truncate max-w-24">
                            {access.camera?.name}
                          </span>
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getAccessLevelBadgeColor(access.accessLevel)}`}>
                            {access.accessLevel}
                          </span>
                        </div>
                      ))
                    ) : (
                      <span className="text-sm text-gray-400">No camera access</span>
                    )}
                    {userData.cameraAccess && userData.cameraAccess.length > 3 && (
                      <div className="text-xs text-gray-500">
                        +{userData.cameraAccess.length - 3} more
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {userData.lastLoginAt ? (
                    <div>
                      <div>{new Date(userData.lastLoginAt).toLocaleDateString()}</div>
                      <div className="text-xs text-gray-400">
                        {new Date(userData.lastLoginAt).toLocaleTimeString()}
                      </div>
                    </div>
                  ) : (
                    'Never'
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    userData.isActive 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {userData.isActive ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div className="flex space-x-2">
                    <button className="text-blue-600 hover:text-blue-900 hover:bg-blue-50 p-1 rounded">
                      <Icon name="settings" className="w-4 h-4" />
                    </button>
                    <button className="text-green-600 hover:text-green-900 hover:bg-green-50 p-1 rounded">
                      <Icon name="camera" className="w-4 h-4" />
                    </button>
                    <button className="text-red-600 hover:text-red-900 hover:bg-red-50 p-1 rounded">
                      <Icon name="users" className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default UsersComponent;
