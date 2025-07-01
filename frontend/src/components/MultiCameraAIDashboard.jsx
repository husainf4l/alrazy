import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Play, 
  Pause, 
  Camera, 
  AlertTriangle, 
  Record, 
  Eye, 
  Settings,
  Maximize,
  Minimize
} from 'lucide-react';

const MultiCameraAIDashboard = () => {
  const [cameraManager, setCameraManager] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [streamingFPS, setStreamingFPS] = useState(10);
  const [aiDetectionEnabled, setAiDetectionEnabled] = useState(true);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [motionAlerts, setMotionAlerts] = useState(new Map());
  const [aiDetections, setAiDetections] = useState(new Map());
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  const frameRefs = useRef(new Map());
  const managerRef = useRef(null);

  // Initialize camera manager
  useEffect(() => {
    const initializeManager = async () => {
      try {
        // Get authentication data (replace with your auth system)
        const accessToken = localStorage.getItem('access_token');
        const companyId = parseInt(localStorage.getItem('company_id'));
        
        if (!accessToken || !companyId) {
          console.error('❌ Missing authentication data');
          return;
        }

        // Create and initialize manager
        const manager = new MultiCameraAIManager();
        
        // Set up callbacks
        manager.onCameraFrame = handleCameraFrame;
        manager.onMotionDetected = handleMotionDetected;
        manager.onCameraStatusChange = handleCameraStatusChange;
        manager.onAIDetection = handleAIDetection;

        const success = await manager.initialize(accessToken, companyId);
        
        if (success) {
          setCameraManager(manager);
          managerRef.current = manager;
          setCameras(manager.getAllCameras());
          setIsConnected(true);
          console.log('✅ Camera manager initialized successfully');
        } else {
          console.error('❌ Failed to initialize camera manager');
        }
      } catch (error) {
        console.error('❌ Error initializing camera manager:', error);
      }
    };

    initializeManager();

    // Cleanup on unmount
    return () => {
      if (managerRef.current) {
        managerRef.current.disconnect();
      }
    };
  }, []);

  // Handle camera frame updates
  const handleCameraFrame = useCallback((cameraId, frameData, timestamp) => {
    const frameRef = frameRefs.current.get(cameraId);
    if (frameRef) {
      frameRef.src = `data:image/jpeg;base64,${frameData}`;
      frameRef.dataset.timestamp = timestamp;
    }
  }, []);

  // Handle motion detection
  const handleMotionDetected = useCallback((cameraId, detected, confidence) => {
    setMotionAlerts(prev => {
      const newAlerts = new Map(prev);
      if (detected) {
        newAlerts.set(cameraId, {
          timestamp: Date.now(),
          confidence: confidence,
          active: true
        });
        
        // Auto-clear alert after 5 seconds
        setTimeout(() => {
          setMotionAlerts(current => {
            const updated = new Map(current);
            const alert = updated.get(cameraId);
            if (alert) {
              alert.active = false;
              updated.set(cameraId, alert);
            }
            return updated;
          });
        }, 5000);
      }
      return newAlerts;
    });
  }, []);

  // Handle AI detection results
  const handleAIDetection = useCallback((cameraId, detection) => {
    setAiDetections(prev => {
      const newDetections = new Map(prev);
      const existing = newDetections.get(cameraId) || [];
      
      newDetections.set(cameraId, [
        {
          ...detection,
          timestamp: Date.now(),
          id: Math.random().toString(36).substr(2, 9)
        },
        ...existing.slice(0, 4) // Keep last 5 detections
      ]);
      
      return newDetections;
    });
  }, []);

  // Handle camera status changes
  const handleCameraStatusChange = useCallback((cameraId, status) => {
    setCameras(prev => prev.map(camera => 
      camera.id === cameraId 
        ? { ...camera, streamStatus: status }
        : camera
    ));
  }, []);

  // Start recording for a camera
  const startRecording = async (cameraId, duration = 60) => {
    if (cameraManager) {
      const result = await cameraManager.startRecording(cameraId, duration);
      if (result) {
        // Show success notification
        console.log(`📹 Recording started for camera ${cameraId}`);
      }
    }
  };

  // Toggle streaming for a camera
  const toggleCameraStream = (cameraId) => {
    if (cameraManager) {
      const camera = cameraManager.getCamera(cameraId);
      if (camera?.isStreaming) {
        cameraManager.stopCameraStream(cameraId);
      } else {
        cameraManager.startCameraStream(cameraId);
      }
    }
  };

  // Update streaming FPS
  const updateStreamingFPS = (newFPS) => {
    setStreamingFPS(newFPS);
    if (cameraManager) {
      cameraManager.setStreamingFPS(newFPS);
    }
  };

  // Toggle AI detection
  const toggleAIDetection = () => {
    const newState = !aiDetectionEnabled;
    setAiDetectionEnabled(newState);
    if (cameraManager) {
      cameraManager.setAIDetection(newState);
    }
  };

  // Get status badge color
  const getStatusBadgeVariant = (status) => {
    switch (status) {
      case 'streaming': return 'default';
      case 'connected': return 'secondary';
      case 'error': return 'destructive';
      case 'stopped': return 'outline';
      default: return 'secondary';
    }
  };

  // Render camera card
  const renderCameraCard = (camera) => {
    const motionAlert = motionAlerts.get(camera.id);
    const detections = aiDetections.get(camera.id) || [];
    const isMotionActive = motionAlert?.active;

    return (
      <Card 
        key={camera.id} 
        className={`relative transition-all duration-300 ${
          isMotionActive ? 'ring-2 ring-red-500 shadow-lg' : ''
        }`}
      >
        <CardHeader className="pb-2">
          <div className="flex justify-between items-center">
            <CardTitle className="text-sm font-medium">
              {camera.name}
            </CardTitle>
            <Badge variant={getStatusBadgeVariant(camera.streamStatus)}>
              {camera.streamStatus}
            </Badge>
          </div>
          <p className="text-xs text-gray-500">{camera.location}</p>
        </CardHeader>
        
        <CardContent className="space-y-3">
          {/* Camera Feed */}
          <div className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden">
            <img
              ref={(el) => {
                if (el) frameRefs.current.set(camera.id, el);
              }}
              className="w-full h-full object-cover"
              alt={`Camera ${camera.id} feed`}
              onError={(e) => {
                e.target.src = '/api/placeholder/320/180';
              }}
            />
            
            {/* Motion Alert Overlay */}
            {isMotionActive && (
              <div className="absolute inset-0 bg-red-500 bg-opacity-20 flex items-center justify-center">
                <div className="bg-red-500 text-white px-2 py-1 rounded text-xs font-bold animate-pulse">
                  🚨 MOTION DETECTED
                </div>
              </div>
            )}

            {/* Camera Controls Overlay */}
            <div className="absolute bottom-2 left-2 right-2 flex justify-between">
              <Button
                size="sm"
                variant={camera.isStreaming ? "secondary" : "default"}
                onClick={() => toggleCameraStream(camera.id)}
                className="opacity-80 hover:opacity-100"
              >
                {camera.isStreaming ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => startRecording(camera.id)}
                className="opacity-80 hover:opacity-100"
              >
                <Record className="w-3 h-3 text-red-500" />
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelectedCamera(camera)}
                className="opacity-80 hover:opacity-100"
              >
                <Maximize className="w-3 h-3" />
              </Button>
            </div>
          </div>

          {/* AI Detections */}
          {detections.length > 0 && (
            <div className="space-y-1">
              <h4 className="text-xs font-medium text-gray-700">AI Detections:</h4>
              {detections.slice(0, 2).map((detection) => (
                <div key={detection.id} className="text-xs bg-blue-50 p-2 rounded">
                  <div className="flex justify-between">
                    <span className="font-medium">{detection.detection_type}</span>
                    <Badge variant="outline" className="text-xs">
                      {Math.round(detection.confidence)}%
                    </Badge>
                  </div>
                  {detection.objects && detection.objects.length > 0 && (
                    <div className="text-gray-600 mt-1">
                      Objects: {detection.objects.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Camera Info */}
          <div className="text-xs text-gray-500 space-y-1">
            <div>Resolution: {camera.resolutionWidth}x{camera.resolutionHeight}</div>
            <div className="flex justify-between">
              <span>Motion: {camera.enableMotionDetection ? '✅' : '❌'}</span>
              <span>Recording: {camera.enableRecording ? '✅' : '❌'}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">🎥 Multi-Camera AI Surveillance</h1>
        <div className="flex items-center gap-4">
          <Badge variant={isConnected ? "default" : "destructive"}>
            {isConnected ? "🟢 Connected" : "🔴 Disconnected"}
          </Badge>
          <span className="text-sm text-gray-600">
            {cameras.length} cameras • {cameras.filter(c => c.isStreaming).length} streaming
          </span>
        </div>
      </div>

      {/* Controls */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Streaming FPS:</label>
              <select 
                value={streamingFPS} 
                onChange={(e) => updateStreamingFPS(parseInt(e.target.value))}
                className="px-2 py-1 border rounded text-sm"
              >
                <option value={5}>5 FPS</option>
                <option value={10}>10 FPS</option>
                <option value={15}>15 FPS</option>
                <option value={30}>30 FPS</option>
              </select>
            </div>

            <Button
              variant={aiDetectionEnabled ? "default" : "outline"}
              onClick={toggleAIDetection}
              size="sm"
            >
              <Eye className="w-4 h-4 mr-2" />
              AI Detection {aiDetectionEnabled ? 'ON' : 'OFF'}
            </Button>

            <Button
              variant="outline"
              onClick={() => window.location.reload()}
              size="sm"
            >
              <Settings className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Connection Error */}
      {!isConnected && (
        <Alert className="mb-6">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to connect to camera streaming service. Make sure your FastAPI service is running on port 8001.
          </AlertDescription>
        </Alert>
      )}

      {/* Camera Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {cameras.map(renderCameraCard)}
      </div>

      {/* No Cameras Message */}
      {cameras.length === 0 && isConnected && (
        <Card className="text-center p-8">
          <Camera className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-medium mb-2">No Cameras Found</h3>
          <p className="text-gray-600 mb-4">
            No cameras are configured for your company. Add cameras through your admin panel.
          </p>
          <Button variant="outline">
            Add Camera
          </Button>
        </Card>
      )}

      {/* Fullscreen Camera Modal */}
      {selectedCamera && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 max-w-4xl max-h-[90vh] w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">{selectedCamera.name}</h3>
              <Button
                variant="outline"
                onClick={() => setSelectedCamera(null)}
                size="sm"
              >
                <Minimize className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden mb-4">
              <img
                src={frameRefs.current.get(selectedCamera.id)?.src || '/api/placeholder/800/450'}
                className="w-full h-full object-cover"
                alt={`${selectedCamera.name} fullscreen`}
              />
            </div>
            
            <div className="flex gap-2">
              <Button onClick={() => startRecording(selectedCamera.id, 120)}>
                <Record className="w-4 h-4 mr-2 text-red-500" />
                Record 2min
              </Button>
              <Button 
                variant="outline"
                onClick={() => toggleCameraStream(selectedCamera.id)}
              >
                {selectedCamera.isStreaming ? 'Stop Stream' : 'Start Stream'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MultiCameraAIDashboard;
