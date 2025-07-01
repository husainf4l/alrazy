'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';

interface Camera {
  id: string;
  name: string;
  url: string;
  status: 'connected' | 'disconnected' | 'loading' | 'error';
  location?: string;
  resolution?: string;
  fps?: number;
  lastConnected?: Date;
  errorMessage?: string;
}

interface CameraStreamGridProps {
  cameras?: Camera[];
  onCameraSelect?: (cameraId: string) => void;
  enableFullscreen?: boolean;
}

const CameraStreamGrid: React.FC<CameraStreamGridProps> = ({ 
  cameras: propCameras, 
  onCameraSelect,
  enableFullscreen = true 
}) => {
  const [selectedCamera, setSelectedCamera] = useState<string>('1');
  const [isLoading, setIsLoading] = useState(true);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [streamingQuality, setStreamingQuality] = useState<'high' | 'medium' | 'low'>('high');
  const [debugMode, setDebugMode] = useState(true);
  const [connectionTest, setConnectionTest] = useState<{ [key: string]: string }>({});
  const videoRefs = useRef<{ [key: string]: HTMLVideoElement | null }>({});
  const wsRef = useRef<WebSocket | null>(null);
  const [frameData, setFrameData] = useState<{ [key: string]: string }>({});
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Camera configuration with RTSP URLs
  const cameraConfig = {
    base_ip: "192.168.1.186",
    username: "admin", 
    password: "tt55oo77",
    port: "554",
    cameras: {
      "1": "/Streaming/Channels/101",
      "2": "/Streaming/Channels/201", 
      "3": "/Streaming/Channels/301",
      "4": "/Streaming/Channels/401"
    }
  };

  // Default camera config based on provided RTSP streams
  const defaultCameras: Camera[] = [
    {
      id: '1',
      name: 'Front Entrance',
      url: `rtsp://${cameraConfig.username}:${cameraConfig.password}@${cameraConfig.base_ip}:${cameraConfig.port}${cameraConfig.cameras[1]}`,
      status: 'loading',
      location: 'Main Building',
      resolution: '1920x1080',
      fps: 30
    },
    {
      id: '2', 
      name: 'Parking Area',
      url: `rtsp://${cameraConfig.username}:${cameraConfig.password}@${cameraConfig.base_ip}:${cameraConfig.port}${cameraConfig.cameras[2]}`,
      status: 'loading',
      location: 'Exterior',
      resolution: '1920x1080',
      fps: 30
    },
    {
      id: '3',
      name: 'Back Garden',
      url: `rtsp://${cameraConfig.username}:${cameraConfig.password}@${cameraConfig.base_ip}:${cameraConfig.port}${cameraConfig.cameras[3]}`,
      status: 'loading',
      location: 'Garden',
      resolution: '1920x1080',
      fps: 30
    },
    {
      id: '4',
      name: 'Side Yard',
      url: `rtsp://${cameraConfig.username}:${cameraConfig.password}@${cameraConfig.base_ip}:${cameraConfig.port}${cameraConfig.cameras[4]}`,
      status: 'loading',
      location: 'Perimeter',
      resolution: '1920x1080',
      fps: 30
    }
  ];

  // Test camera connectivity
  const testCameraConnection = async (camera: Camera) => {
    try {
      console.log(`🔍 Testing connection to Camera ${camera.id}: ${camera.url}`);
      setConnectionTest(prev => ({ ...prev, [camera.id]: 'Testing...' }));
      
      // Test IP connectivity first
      const baseIp = cameraConfig.base_ip;
      const testResponse = await fetch(`/api/test-camera-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          ip: baseIp, 
          port: cameraConfig.port,
          url: camera.url,
          cameraId: camera.id 
        })
      }).catch(err => {
        console.warn(`❌ API endpoint not available, using client-side test for Camera ${camera.id}`);
        return null;
      });

      if (testResponse && testResponse.ok) {
        const result = await testResponse.json();
        setConnectionTest(prev => ({ ...prev, [camera.id]: result.status }));
        return result.connected;
      } else {
        // Fallback: Test basic connectivity using Image loading
        return new Promise((resolve) => {
          const img = new Image();
          const timeout = setTimeout(() => {
            setConnectionTest(prev => ({ ...prev, [camera.id]: 'Timeout - Camera may not support HTTP preview' }));
            resolve(false);
          }, 5000);
          
          img.onload = () => {
            clearTimeout(timeout);
            setConnectionTest(prev => ({ ...prev, [camera.id]: 'Connected via HTTP preview' }));
            resolve(true);
          };
          
          img.onerror = () => {
            clearTimeout(timeout);
            setConnectionTest(prev => ({ ...prev, [camera.id]: 'RTSP only - No HTTP preview available' }));
            resolve(false);
          };
          
          // Try to load a snapshot URL (common for IP cameras)
          img.src = `http://${baseIp}/ISAPI/Streaming/channels/${camera.id}01/picture`;
        });
      }
    } catch (error) {
      console.error(`❌ Error testing Camera ${camera.id}:`, error);
      setConnectionTest(prev => ({ ...prev, [camera.id]: `Error: ${error}` }));
      return false;
    }
  };

  useEffect(() => {
    const initCameras = async () => {
      const cameraList = propCameras || defaultCameras;
      setCameras(cameraList);
      
      // Test all camera connections
      for (const camera of cameraList) {
        await testCameraConnection(camera);
      }
      
      setIsLoading(false);
    };
    
    initCameras();
  }, [propCameras]);

  // Simulate WebSocket connection for live streaming
  useEffect(() => {
    if (isLoading) return;

    const simulateStream = () => {
      cameras.forEach(camera => {
        // Generate simulated frame data with camera info
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 360;
        const ctx = canvas.getContext('2d');
        
        if (ctx) {
          // Create a gradient background with timestamp
          const gradient = ctx.createLinearGradient(0, 0, 640, 360);
          gradient.addColorStop(0, '#1f2937');
          gradient.addColorStop(1, '#374151');
          ctx.fillStyle = gradient;
          ctx.fillRect(0, 0, 640, 360);
          
          // Add camera info text
          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 24px system-ui';
          ctx.textAlign = 'center';
          ctx.fillText(`${camera.name}`, 320, 120);
          
          ctx.font = '16px system-ui';
          ctx.fillText(`Camera ${camera.id} • ${camera.location}`, 320, 150);
          ctx.fillText(`LIVE - ${new Date().toLocaleTimeString()}`, 320, 180);
          ctx.fillText(`${camera.url}`, 320, 210);
          
          // Connection status
          ctx.fillStyle = connectionTest[camera.id]?.includes('Connected') ? '#10b981' : '#ef4444';
          ctx.fillText(`Status: ${connectionTest[camera.id] || 'Testing...'}`, 320, 240);
          
          // Add some animated elements to simulate activity
          const time = Date.now() / 1000;
          ctx.fillStyle = '#ef4444';
          const x = 100 + Math.sin(time + parseInt(camera.id)) * 80;
          const y = 100 + Math.cos(time + parseInt(camera.id)) * 40;
          ctx.beginPath();
          ctx.arc(x, y, 5, 0, 2 * Math.PI);
          ctx.fill();
          
          // Add moving detection box simulation
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = 2;
          const boxX = 200 + Math.sin(time * 0.5 + parseInt(camera.id)) * 100;
          const boxY = 280 + Math.cos(time * 0.3 + parseInt(camera.id)) * 30;
          ctx.strokeRect(boxX, boxY, 60, 40);
          
          setFrameData(prev => ({
            ...prev,
            [camera.id]: canvas.toDataURL('image/jpeg', 0.8)
          }));
        }
      });
      setLastUpdate(new Date());
    };

    const interval = setInterval(simulateStream, 200); // 5 FPS simulation
    simulateStream(); // Initial call
    
    return () => clearInterval(interval);
  }, [cameras, connectionTest, isLoading]);

  const handleCameraSelect = useCallback((cameraId: string) => {
    setSelectedCamera(cameraId);
    onCameraSelect?.(cameraId);
    console.log(`📹 Selected Camera ${cameraId}: ${cameras.find(c => c.id === cameraId)?.url}`);
  }, [onCameraSelect, cameras]);

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleQualityChange = (quality: 'high' | 'medium' | 'low') => {
    setStreamingQuality(quality);
    console.log(`🎥 Quality changed to: ${quality}`);
  };

  const refreshConnections = async () => {
    setIsLoading(true);
    setConnectionTest({});
    
    for (const camera of cameras) {
      await testCameraConnection(camera);
    }
    
    setIsLoading(false);
  };

  const selectedCameraData = cameras.find(cam => cam.id === selectedCamera);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96 bg-white rounded-2xl border border-gray-100">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Testing camera connections...</p>
          <p className="text-sm text-gray-500 mt-2">IP: {cameraConfig.base_ip}:{cameraConfig.port}</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden transition-all duration-300 ${
        isFullscreen ? 'fixed inset-4 z-50 shadow-2xl' : ''
      }`}>
        {/* Enhanced Header with Debug Info */}
        <div className="p-4 bg-gray-50 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              <h3 className="font-semibold text-gray-900">Live Camera Feeds</h3>
              <span className="text-sm text-gray-500">• {cameras.filter(c => connectionTest[c.id]?.includes('Connected')).length}/4 tested</span>
              {debugMode && (
                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                  {cameraConfig.base_ip}:{cameraConfig.port}
                </span>
              )}
            </div>
            
            <div className="flex items-center space-x-2">
              {/* Debug Toggle */}
              <button
                onClick={() => setDebugMode(!debugMode)}
                className={`px-2 py-1 text-xs font-medium rounded transition-all ${
                  debugMode ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-600'
                }`}
              >
                DEBUG
              </button>
              
              {/* Refresh Button */}
              <button
                onClick={refreshConnections}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-white rounded-lg transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
              
              {/* Quality Selector */}
              <div className="flex items-center space-x-1 bg-white rounded-lg p-1 border border-gray-200">
                {(['high', 'medium', 'low'] as const).map((quality) => (
                  <button
                    key={quality}
                    onClick={() => handleQualityChange(quality)}
                    className={`px-2 py-1 text-xs font-medium rounded transition-all ${
                      streamingQuality === quality
                        ? 'bg-blue-500 text-white'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {quality.toUpperCase()}
                  </button>
                ))}
              </div>
              
              {/* Fullscreen Button */}
              {enableFullscreen && (
                <button
                  onClick={toggleFullscreen}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-white rounded-lg transition-all"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={
                      isFullscreen 
                        ? "M9 9V4.5M9 9H4.5M9 9L3.5 3.5M15 9V4.5M15 9h4.5M15 9l5.5-5.5M9 15v4.5M9 15H4.5M9 15l-5.5 5.5M15 15v4.5M15 15h4.5M15 15l5.5 5.5"
                        : "M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5-5-5m5 5v-4m0 4h-4"
                    } />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Main Camera Display */}
        <div className="relative">
          <div className={`aspect-video bg-black overflow-hidden relative group ${
            isFullscreen ? 'h-[calc(100vh-300px)]' : ''
          }`}>
            {selectedCameraData ? (
              <>
                {/* Live Stream */}
                <div className="w-full h-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center relative">
                  {frameData[selectedCamera] ? (
                    <img
                      src={frameData[selectedCamera]}
                      alt={`${selectedCameraData.name} Live Stream`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="text-center text-white">
                      <div className="w-16 h-16 border-4 border-white border-t-transparent rounded-full animate-spin mx-auto mb-4 opacity-50"></div>
                      <p className="text-lg font-medium opacity-75">Connecting to {selectedCameraData.name}</p>
                      <p className="text-sm opacity-50 mt-2">{selectedCameraData.url}</p>
                    </div>
                  )}
                  
                  {/* Live Indicator */}
                  <div className="absolute top-4 left-4 flex items-center space-x-2">
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse shadow-lg"></div>
                    <span className="text-white text-sm font-semibold bg-black bg-opacity-50 px-3 py-1 rounded-full backdrop-blur-sm">
                      LIVE
                    </span>
                  </div>

                  {/* Camera Info */}
                  <div className="absolute top-4 right-4 bg-black bg-opacity-50 text-white px-3 py-2 rounded-lg backdrop-blur-sm">
                    <div className="text-sm font-medium">{selectedCameraData.name}</div>
                    <div className="text-xs opacity-75">{selectedCameraData.location}</div>
                    {debugMode && (
                      <div className="text-xs opacity-60 mt-1">ID: {selectedCameraData.id}</div>
                    )}
                  </div>

                  {/* Connection Status */}
                  {debugMode && (
                    <div className="absolute bottom-4 left-4 bg-black bg-opacity-50 text-white px-3 py-2 rounded-lg backdrop-blur-sm">
                      <div className="text-xs">Status: {connectionTest[selectedCamera] || 'Unknown'}</div>
                      <div className="text-xs opacity-75">Updated: {lastUpdate.toLocaleTimeString()}</div>
                    </div>
                  )}

                  {/* Quality Indicator */}
                  <div className="absolute bottom-4 right-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded-lg backdrop-blur-sm">
                    <div className="text-xs">{selectedCameraData.resolution} • {selectedCameraData.fps}fps • {streamingQuality.toUpperCase()}</div>
                  </div>

                  {/* Control Overlay */}
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300 flex items-center justify-center opacity-0 group-hover:opacity-100">
                    <div className="flex space-x-4">
                      <button className="w-14 h-14 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full flex items-center justify-center text-white transition-all backdrop-blur-sm"
                              title="Record">
                        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      </button>
                      <button className="w-14 h-14 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full flex items-center justify-center text-white transition-all backdrop-blur-sm"
                              title="Capture">
                        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </button>
                      <button 
                        className="w-14 h-14 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full flex items-center justify-center text-white transition-all backdrop-blur-sm"
                        onClick={() => refreshConnections()}
                        title="Refresh Connection"
                      >
                        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="w-full h-full flex items-center justify-center text-white">
                <p className="text-lg">No camera selected</p>
              </div>
            )}
          </div>
        </div>

        {/* Camera Grid */}
        <div className="p-4 bg-gray-50">
          <div className="grid grid-cols-4 gap-3">
            {cameras.map((camera) => (
              <button
                key={camera.id}
                onClick={() => handleCameraSelect(camera.id)}
                className={`
                  relative aspect-video rounded-xl overflow-hidden transition-all duration-200 group
                  ${selectedCamera === camera.id
                    ? 'ring-2 ring-blue-500 shadow-lg scale-105 z-10'
                    : 'ring-1 ring-gray-200 hover:ring-gray-300 hover:scale-102 hover:shadow-md'
                  }
                `}
              >
                <div className="w-full h-full bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center relative">
                  {frameData[camera.id] ? (
                    <img
                      src={frameData[camera.id]}
                      alt={`${camera.name} Preview`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="text-white text-xs opacity-50">Loading...</div>
                  )}
                  
                  {/* Camera Label */}
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black via-black/70 to-transparent p-2">
                    <p className="text-white text-xs font-medium truncate">
                      {camera.name}
                    </p>
                    <p className="text-white text-xs opacity-75 truncate">
                      {camera.location}
                    </p>
                    {debugMode && (
                      <p className="text-white text-xs opacity-50 truncate">
                        {connectionTest[camera.id] || 'Testing...'}
                      </p>
                    )}
                  </div>

                  {/* Status Indicator */}
                  <div className="absolute top-2 left-2">
                    <div className={`w-2 h-2 rounded-full shadow-lg ${
                      connectionTest[camera.id]?.includes('Connected') ? 'bg-green-400' :
                      connectionTest[camera.id]?.includes('Testing') ? 'bg-yellow-400 animate-pulse' :
                      connectionTest[camera.id]?.includes('RTSP only') ? 'bg-blue-400' :
                      'bg-red-400'
                    }`}></div>
                  </div>

                  {/* Selected Indicator */}
                  {selectedCamera === camera.id && (
                    <div className="absolute inset-0 bg-blue-500 bg-opacity-20 flex items-center justify-center">
                      <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center shadow-lg">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    </div>
                  )}

                  {/* Hover Effect */}
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all duration-200"></div>
                </div>
              </button>
            ))}
          </div>

          {/* Enhanced Camera Info Bar */}
          {selectedCameraData && (
            <div className="mt-4 bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full animate-pulse ${
                      connectionTest[selectedCamera]?.includes('Connected') ? 'bg-green-500' :
                      connectionTest[selectedCamera]?.includes('RTSP only') ? 'bg-blue-500' :
                      'bg-yellow-500'
                    }`}></div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{selectedCameraData.name}</h3>
                      <p className="text-sm text-gray-500">
                        {selectedCameraData.location} • Camera {selectedCameraData.id} • {selectedCameraData.resolution} • {selectedCameraData.fps}fps
                      </p>
                      {debugMode && (
                        <p className="text-xs text-gray-400 mt-1 font-mono break-all">
                          {selectedCameraData.url}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    {/* Connection Status */}
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-500">Status:</span>
                      <span className={`text-sm font-medium ${
                        connectionTest[selectedCamera]?.includes('Connected') ? 'text-green-600' :
                        connectionTest[selectedCamera]?.includes('RTSP only') ? 'text-blue-600' :
                        connectionTest[selectedCamera]?.includes('Error') ? 'text-red-600' :
                        'text-yellow-600'
                      }`}>
                        {connectionTest[selectedCamera] || 'Testing...'}
                      </span>
                    </div>

                    {/* Signal Quality */}
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-500">Signal:</span>
                      <div className="flex space-x-1">
                        {[1, 2, 3, 4].map((bar) => (
                          <div
                            key={bar}
                            className={`w-1 h-4 rounded-full ${
                              connectionTest[selectedCamera]?.includes('Connected') && bar <= 4 ? 'bg-green-500' :
                              connectionTest[selectedCamera]?.includes('RTSP only') && bar <= 3 ? 'bg-blue-500' :
                              bar <= 1 ? 'bg-yellow-500' : 'bg-gray-200'
                            }`}
                          ></div>
                        ))}
                      </div>
                    </div>

                    {/* Recording Status */}
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                      <span className="text-sm text-gray-500">Recording</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen Overlay */}
      {isFullscreen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={toggleFullscreen} />
      )}
    </>
  );
};

export default CameraStreamGrid;
