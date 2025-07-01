'use client';

import { useState, useEffect } from 'react';
import { Camera } from '../types/user';
import { authService } from '../services/auth';
import { Icon } from '../components';

interface CameraManagementProps {
  companyId: number;
}

const CameraManagement = ({ companyId }: CameraManagementProps) => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [newCamera, setNewCamera] = useState({
    name: '',
    location: '',
    rtspUrl: '',
    username: '',
    password: '',
    description: ''
  });

  useEffect(() => {
    fetchCameras();
  }, [companyId]);

  const fetchCameras = async () => {
    try {
      setLoading(true);
      const companyCameras = await authService.getCompanyCameras ? 
        await authService.getCompanyCameras(companyId) : 
        await authService.getCameras();
      setCameras(Array.isArray(companyCameras) ? companyCameras : []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch cameras');
    } finally {
      setLoading(false);
    }
  };

  const handleAddCamera = async () => {
    if (!newCamera.name || !newCamera.location || !newCamera.rtspUrl) {
      setError('Please fill in all required fields (Name, Location, RTSP URL)');
      return;
    }

    // Validate RTSP URL format
    if (!newCamera.rtspUrl.startsWith('rtsp://')) {
      setError('RTSP URL must start with rtsp://');
      return;
    }

    setFormLoading(true);
    setError('');

    try {
      // Prepare camera data to match backend CreateCameraDto exactly
      const cameraData: any = {
        name: newCamera.name.trim(),
        location: newCamera.location.trim(),
        rtspUrl: newCamera.rtspUrl.trim(),
        companyId: companyId
      };

      // Add optional fields only if they have values
      if (newCamera.description && newCamera.description.trim()) {
        cameraData.description = newCamera.description.trim();
      }
      
      if (newCamera.username && newCamera.username.trim()) {
        cameraData.username = newCamera.username.trim();
      }
      
      if (newCamera.password && newCamera.password.trim()) {
        cameraData.password = newCamera.password.trim();
      }

      // Add default technical settings that match backend validation
      cameraData.resolutionWidth = 1920;
      cameraData.resolutionHeight = 1080;
      cameraData.fps = 30;
      cameraData.quality = 80;
      cameraData.enableMotionDetection = true;
      cameraData.enableRecording = true;
      cameraData.recordingDuration = 60;

      console.log('Sending camera data to backend:', cameraData);

      const response = await authService.createCamera(cameraData);
      
      if (response.camera) {
        setCameras(prev => [...prev, response.camera!]);
        setShowAddForm(false);
        setNewCamera({
          name: '',
          location: '',
          rtspUrl: '',
          username: '',
          password: '',
          description: ''
        });
        alert('Camera added successfully!');
      }
    } catch (err: any) {
      console.error('Camera creation error:', err);
      setError(err.message || 'Failed to add camera');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteCamera = async (cameraId: number) => {
    if (!confirm('Are you sure you want to delete this camera? This action cannot be undone.')) {
      return;
    }

    try {
      await authService.deleteCamera(cameraId);
      setCameras(prev => prev.filter(camera => camera.id !== cameraId));
      alert('Camera deleted successfully!');
    } catch (err: any) {
      setError(err.message || 'Failed to delete camera');
    }
  };

  const getStatusColor = (camera: Camera) => {
    if (camera.isOnline) {
      return 'bg-green-100 text-green-700';
    }
    return 'bg-red-100 text-red-700';
  };

  const getStatusText = (camera: Camera) => {
    return camera.isOnline ? 'Online' : 'Offline';
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

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
      <div className="px-6 py-4 bg-gradient-to-r from-red-50 to-orange-50 border-b border-gray-200/50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
              <Icon name="camera" className="w-5 h-5 text-red-600" />
              <span>AI Security Cameras</span>
            </h3>
            <p className="text-sm text-gray-600 mt-1">Configure and monitor your connected security cameras</p>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-4 py-2 bg-gradient-to-r from-red-600 to-orange-600 text-white text-sm font-semibold rounded-lg hover:from-red-700 hover:to-orange-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 flex items-center space-x-2"
          >
            <Icon name="camera" className="w-4 h-4" />
            <span>{showAddForm ? 'Cancel' : 'Add Camera'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* Add Camera Form */}
      {showAddForm && (
        <div className="p-6 bg-gray-50 border-b border-gray-200">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Add New Camera</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Camera Name *
              </label>
              <input
                type="text"
                value={newCamera.name}
                onChange={(e) => setNewCamera(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                placeholder="e.g., Main Entrance Camera"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Location *
              </label>
              <input
                type="text"
                value={newCamera.location}
                onChange={(e) => setNewCamera(prev => ({ ...prev, location: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                placeholder="e.g., Main Entrance, Floor 1"
              />
            </div>
            
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                RTSP URL *
              </label>
              <input
                type="text"
                value={newCamera.rtspUrl}
                onChange={(e) => setNewCamera(prev => ({ ...prev, rtspUrl: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                placeholder="rtsp://192.168.1.100:554/stream1"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Camera Username
              </label>
              <input
                type="text"
                value={newCamera.username}
                onChange={(e) => setNewCamera(prev => ({ ...prev, username: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                placeholder="Optional"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Camera Password
              </label>
              <input
                type="password"
                value={newCamera.password}
                onChange={(e) => setNewCamera(prev => ({ ...prev, password: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                placeholder="Optional"
              />
            </div>
            
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={newCamera.description}
                onChange={(e) => setNewCamera(prev => ({ ...prev, description: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                rows={3}
                placeholder="Optional description of the camera"
              />
            </div>
          </div>
          
          <div className="flex justify-end space-x-3 mt-6">
            <button
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors duration-200"
            >
              Cancel
            </button>
            <button
              onClick={handleAddCamera}
              disabled={formLoading}
              className="px-4 py-2 bg-gradient-to-r from-red-600 to-orange-600 text-white rounded-lg hover:from-red-700 hover:to-orange-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {formLoading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <>
                  <Icon name="camera" className="w-4 h-4" />
                  <span>Add Camera</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Camera List */}
      <div className="p-6">
        {cameras.length === 0 ? (
          <div className="text-center py-12">
            <Icon name="camera" className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Cameras Found</h3>
            <p className="text-gray-500 mb-4">Get started by adding your first security camera</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="px-6 py-3 bg-gradient-to-r from-red-600 to-orange-600 text-white text-sm font-semibold rounded-xl hover:from-red-700 hover:to-orange-700 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Add Your First Camera
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {cameras.map((camera) => (
              <div key={camera.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors duration-200">
                <div className="flex items-center space-x-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    camera.isOnline 
                      ? 'bg-green-100 text-green-600' 
                      : 'bg-red-100 text-red-600'
                  }`}>
                    <Icon name="camera" className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900">{camera.name}</h4>
                    <p className="text-sm text-gray-600">
                      {camera.location}
                      {camera.description && ` • ${camera.description}`}
                    </p>
                    <p className="text-xs text-gray-500">
                      {camera.lastConnectedAt ? 
                        `Last seen: ${new Date(camera.lastConnectedAt).toLocaleString()}` :
                        'Never connected'
                      }
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <div className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(camera)}`}>
                    {getStatusText(camera)}
                  </div>
                  
                  <div className="flex space-x-2">
                    <button 
                      className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all duration-200"
                      title="View camera feed"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                    <button 
                      className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-all duration-200"
                      title="Edit camera settings"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    </button>
                    <button 
                      onClick={() => handleDeleteCamera(camera.id)}
                      className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200"
                      title="Delete camera"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Camera Stats */}
      {cameras.length > 0 && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200/50">
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {cameras.filter(c => c.isOnline).length}
              </div>
              <div className="text-xs text-gray-600">Online</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {cameras.filter(c => !c.isOnline).length}
              </div>
              <div className="text-xs text-gray-600">Offline</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{cameras.length}</div>
              <div className="text-xs text-gray-600">Total</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">24/7</div>
              <div className="text-xs text-gray-600">Monitoring</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CameraManagement;
