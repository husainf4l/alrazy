'use client';

import { useState } from 'react';
import { authService } from '../services/auth';

const AuthDebugComponent = () => {
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const testLogin = async () => {
    setLoading(true);
    setResult('');
    
    try {
      const response = await authService.login({
        username: 'husain',
        password: 'tt55oo77'
      });
      
      setResult(`Login successful! User: ${response.user?.firstName} ${response.user?.lastName}, Role: ${response.user?.role}`);
    } catch (error: any) {
      setResult(`Login failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const testCurrentUser = async () => {
    setLoading(true);
    setResult('');
    
    try {
      const user = await authService.getCurrentUser();
      setResult(`Current user: ${user.firstName} ${user.lastName}, Email: ${user.email}`);
    } catch (error: any) {
      setResult(`Get current user failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const testAssignCameraAccess = async () => {
    setLoading(true);
    setResult('');
    
    try {
      // Test assigning user ID 3 to camera ID 1 with VIEWER access
      const result = await authService.assignCameraAccess(1, [3], 'VIEWER');
      setResult(`Camera access assigned successfully! Result: ${JSON.stringify(result)}`);
    } catch (error: any) {
      setResult(`Assign camera access failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const testCompanyUsers = async () => {
    setLoading(true);
    setResult('');
    
    try {
      const users = await authService.getCompanyUsers(1);
      setResult(`Found ${users.length} company users: ${users.map(u => u.firstName + ' ' + u.lastName).join(', ')}`);
    } catch (error: any) {
      setResult(`Get company users failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const testCreateCamera = async () => {
    setLoading(true);
    setResult('');
    
    try {
      const cameraData = {
        name: "Test Frontend Camera",
        location: "Frontend Test Location",
        rtspUrl: "rtsp://192.168.1.150:554/stream1",
        companyId: 1
      };
      const result = await authService.createCamera(cameraData);
      setResult(`Camera created successfully! ID: ${result.camera?.id}, Name: ${result.camera?.name}`);
    } catch (error: any) {
      setResult(`Create camera failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg max-w-md">
      <h3 className="text-lg font-semibold mb-4">Auth Debug</h3>
      
      <div className="space-y-3">
        <button
          onClick={testLogin}
          disabled={loading}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Test Login
        </button>
        
        <button
          onClick={testCurrentUser}
          disabled={loading}
          className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        >
          Test Get Current User
        </button>
        
        <button
          onClick={testCompanyUsers}
          disabled={loading}
          className="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
        >
          Test Get Company Users
        </button>
        
        <button
          onClick={testAssignCameraAccess}
          disabled={loading}
          className="w-full px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50"
        >
          Test Assign Camera Access
        </button>
        
        <button
          onClick={testCreateCamera}
          disabled={loading}
          className="w-full px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
        >
          Test Create Camera
        </button>

        <button
          onClick={testCreateCamera}
          disabled={loading}
          className="w-full px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
        >
          Test Create Camera
        </button>
      </div>
      
      {loading && (
        <div className="mt-4 text-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
        </div>
      )}
      
      {result && (
        <div className="mt-4 p-3 bg-gray-100 rounded text-sm">
          {result}
        </div>
      )}
    </div>
  );
};

export default AuthDebugComponent;
