'use client';

import { useState, useEffect } from 'react';
import { User, Camera, CameraUserAccess, CameraAccessLevel } from '../types/user';
import { authService } from '../services/auth';
import { Icon } from '../components';

interface CameraAccessManagementProps {
  companyId: number;
}

const CameraAccessManagement = ({ companyId }: CameraAccessManagementProps) => {
  const [users, setUsers] = useState<User[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [assignLoading, setAssignLoading] = useState(false);
  const [selectedUser, setSelectedUser] = useState<number | null>(null);
  const [selectedCamera, setSelectedCamera] = useState<number | null>(null);
  const [selectedAccessLevel, setSelectedAccessLevel] = useState<CameraAccessLevel>(CameraAccessLevel.VIEWER);

  const accessLevels: CameraAccessLevel[] = [CameraAccessLevel.VIEWER, CameraAccessLevel.OPERATOR, CameraAccessLevel.MANAGER, CameraAccessLevel.ADMIN];

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [companyUsers, companyCameras] = await Promise.all([
          authService.getCompanyUsers(companyId),
          authService.getCompanyCameras ? authService.getCompanyCameras(companyId) : authService.getCameras()
        ]);
        setUsers(companyUsers);
        setCameras(Array.isArray(companyCameras) ? companyCameras : []);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [companyId]);

  const handleAssignAccess = async () => {
    if (!selectedUser || !selectedCamera || !selectedAccessLevel) {
      setError('Please select a user, camera, and access level');
      return;
    }

    setAssignLoading(true);
    setError('');

    try {
      await authService.assignCameraAccess(selectedCamera, [selectedUser], selectedAccessLevel);
      
      // Refresh users data to show updated camera access
      const updatedUsers = await authService.getCompanyUsers(companyId);
      setUsers(updatedUsers);
      
      // Reset form
      setSelectedUser(null);
      setSelectedCamera(null);
      setSelectedAccessLevel(CameraAccessLevel.VIEWER);
      
      alert('Camera access assigned successfully!');
    } catch (err: any) {
      setError(err.message || 'Failed to assign camera access');
    } finally {
      setAssignLoading(false);
    }
  };

  const handleRevokeAccess = async (cameraId: number, userId: number) => {
    if (!confirm('Are you sure you want to revoke this camera access?')) {
      return;
    }

    try {
      await authService.revokeCameraAccess(cameraId, userId);
      
      // Refresh users data
      const updatedUsers = await authService.getCompanyUsers(companyId);
      setUsers(updatedUsers);
      
      alert('Camera access revoked successfully!');
    } catch (err: any) {
      setError(err.message || 'Failed to revoke camera access');
    }
  };

  const getAccessLevelColor = (level: CameraAccessLevel) => {
    switch (level) {
      case 'ADMIN': return 'bg-red-100 text-red-800';
      case 'OPERATOR': return 'bg-orange-100 text-orange-800';
      case 'VIEWER': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 p-6">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Camera Access Assignment Form */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
        <div className="px-6 py-4 bg-gradient-to-r from-green-50 to-emerald-50 border-b border-gray-200/50">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
            <Icon name="camera" className="w-5 h-5 text-green-600" />
            <span>Assign Camera Access</span>
          </h3>
          <p className="text-sm text-gray-600 mt-1">Grant users access to specific cameras with defined permission levels</p>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* User Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select User
              </label>
              <select
                value={selectedUser || ''}
                onChange={(e) => setSelectedUser(Number(e.target.value) || null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              >
                <option value="">Choose a user...</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.firstName} {user.lastName} ({user.username})
                  </option>
                ))}
              </select>
            </div>

            {/* Camera Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Camera
              </label>
              <select
                value={selectedCamera || ''}
                onChange={(e) => setSelectedCamera(Number(e.target.value) || null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              >
                <option value="">Choose a camera...</option>
                {cameras.map((camera) => (
                  <option key={camera.id} value={camera.id}>
                    {camera.name} - {camera.location}
                  </option>
                ))}
              </select>
            </div>

            {/* Access Level Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Access Level
              </label>
              <select
                value={selectedAccessLevel}
                onChange={(e) => setSelectedAccessLevel(e.target.value as CameraAccessLevel)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              >
                {accessLevels.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </div>

            {/* Assign Button */}
            <div className="flex items-end">
              <button
                onClick={handleAssignAccess}
                disabled={assignLoading || !selectedUser || !selectedCamera}
                className="w-full px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white text-sm font-semibold rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                {assignLoading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <>
                    <Icon name="users" className="w-4 h-4" />
                    <span>Assign Access</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Access Level Descriptions */}
          <div className="mt-4 grid grid-cols-3 gap-4 text-xs">
            <div className="p-3 bg-blue-50 rounded-lg">
              <div className="font-medium text-blue-800">VIEWER</div>
              <div className="text-blue-600">Can view camera feeds only</div>
            </div>
            <div className="p-3 bg-orange-50 rounded-lg">
              <div className="font-medium text-orange-800">OPERATOR</div>
              <div className="text-orange-600">Can view and control camera settings</div>
            </div>
            <div className="p-3 bg-red-50 rounded-lg">
              <div className="font-medium text-red-800">ADMIN</div>
              <div className="text-red-600">Full control including user management</div>
            </div>
          </div>
        </div>
      </div>

      {/* Current Camera Access Overview */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
        <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200/50">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
            <Icon name="users" className="w-5 h-5 text-blue-600" />
            <span>Current Camera Access</span>
          </h3>
          <p className="text-sm text-gray-600 mt-1">Overview of all user camera access permissions</p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Camera Access
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-8 w-8">
                        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
                          <span className="text-white text-xs font-medium">
                            {user.firstName?.[0]}{user.lastName?.[0]}
                          </span>
                        </div>
                      </div>
                      <div className="ml-3">
                        <div className="text-sm font-medium text-gray-900">
                          {user.firstName} {user.lastName}
                        </div>
                        <div className="text-xs text-gray-500">@{user.username}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="space-y-2">
                      {user.cameraAccess && user.cameraAccess.length > 0 ? (
                        user.cameraAccess.map((access) => (
                          <div key={access.id} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                            <div className="flex items-center space-x-2">
                              <Icon name="camera" className="w-4 h-4 text-gray-500" />
                              <span className="text-sm text-gray-700">
                                {access.camera?.name}
                              </span>
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getAccessLevelColor(access.accessLevel)}`}>
                                {access.accessLevel}
                              </span>
                            </div>
                            <button
                              onClick={() => handleRevokeAccess(access.cameraId, access.userId)}
                              className="text-red-600 hover:text-red-800 p-1 rounded hover:bg-red-50"
                              title="Revoke access"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </div>
                        ))
                      ) : (
                        <span className="text-sm text-gray-400">No camera access</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button 
                      onClick={() => setSelectedUser(user.id)}
                      className="text-green-600 hover:text-green-900 hover:bg-green-50 p-1 rounded"
                      title="Assign camera access"
                    >
                      <Icon name="camera" className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CameraAccessManagement;
