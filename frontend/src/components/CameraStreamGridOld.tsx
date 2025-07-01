'use client';

import React, { useState, useEffect, useRef } from 'react';

interface Camera {
  id: string;
  name: string;
  url: string;
  status: 'connected' | 'disconnected' | 'loading';
}

interface CameraStreamGridProps {
  cameras?: Camera[];
}

const CameraStreamGrid: React.FC<CameraStreamGridProps> = ({ cameras: propCameras }) => {
  const [selectedCamera, setSelectedCamera] = useState<string>('1');
  const [isLoading, setIsLoading] = useState(true);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const videoRefs = useRef<{ [key: string]: HTMLVideoElement | null }>({});

  // Default camera config based on provided RTSP streams
  const defaultCameras: Camera[] = [
    {
      id: '1',
      name: 'Front Entrance',
      url: 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/101',
      status: 'loading'
    },
    {
      id: '2', 
      name: 'Parking Area',
      url: 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/201',
      status: 'loading'
    },
    {
      id: '3',
      name: 'Back Garden',
      url: 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/301',
      status: 'loading'
    },
    {
      id: '4',
      name: 'Side Yard',
      url: 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/401',
      status: 'loading'
    }
  ];

  useEffect(() => {
    setCameras(propCameras || defaultCameras);
    setIsLoading(false);
  }, [propCameras]);

  const handleCameraSelect = (cameraId: string) => {
    setSelectedCamera(cameraId);
  };

  const getStreamUrl = (camera: Camera) => {
    // In a real implementation, this would convert RTSP to HLS or WebRTC
    // For now, we'll simulate with placeholder streams
    return `https://via.placeholder.com/1280x720/2c3e50/ffffff?text=Camera+${camera.id}+Live+Stream`;
  };

  const selectedCameraData = cameras.find(cam => cam.id === selectedCamera);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-2xl">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading camera streams...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Main Camera Display */}
      <div className="relative">
        <div className="aspect-video bg-black rounded-t-2xl overflow-hidden relative group">
          {selectedCameraData ? (
            <>
              {/* Simulated Video Stream */}
              <div className="w-full h-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center relative">
                <img
                  src={getStreamUrl(selectedCameraData)}
                  alt={`${selectedCameraData.name} Live Stream`}
                  className="w-full h-full object-cover"
                />
                
                {/* Live Indicator */}
                <div className="absolute top-4 left-4 flex items-center space-x-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                  <span className="text-white text-sm font-medium bg-black bg-opacity-40 px-2 py-1 rounded-md">
                    LIVE
                  </span>
                </div>

                {/* Camera Info */}
                <div className="absolute top-4 right-4 bg-black bg-opacity-40 text-white px-3 py-1 rounded-md text-sm">
                  {selectedCameraData.name}
                </div>

                {/* Control Overlay (appears on hover) */}
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300 flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <div className="flex space-x-3">
                    <button className="w-12 h-12 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full flex items-center justify-center text-white transition-all">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </button>
                    <button className="w-12 h-12 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full flex items-center justify-center text-white transition-all">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                      </svg>
                    </button>
                    <button className="w-12 h-12 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full flex items-center justify-center text-white transition-all">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="w-full h-full flex items-center justify-center text-white">
              <p>No camera selected</p>
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
                relative aspect-video rounded-xl overflow-hidden transition-all duration-200
                ${selectedCamera === camera.id
                  ? 'ring-2 ring-blue-500 shadow-lg scale-105'
                  : 'ring-1 ring-gray-200 hover:ring-gray-300 hover:scale-102'
                }
              `}
            >
              <div className="w-full h-full bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center">
                <img
                  src={getStreamUrl(camera)}
                  alt={`${camera.name} Preview`}
                  className="w-full h-full object-cover"
                />
                
                {/* Camera Label */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-2">
                  <p className="text-white text-xs font-medium truncate">
                    {camera.name}
                  </p>
                </div>

                {/* Status Indicator */}
                <div className="absolute top-2 left-2">
                  <div className={`w-2 h-2 rounded-full ${
                    camera.status === 'connected' ? 'bg-green-500' :
                    camera.status === 'loading' ? 'bg-yellow-500 animate-pulse' :
                    'bg-red-500'
                  }`}></div>
                </div>

                {/* Selected Indicator */}
                {selectedCamera === camera.id && (
                  <div className="absolute inset-0 bg-blue-500 bg-opacity-10 flex items-center justify-center">
                    <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Camera Info Bar */}
        {selectedCameraData && (
          <div className="mt-4 flex items-center justify-between p-3 bg-white rounded-xl border border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              <div>
                <h3 className="font-medium text-gray-900">{selectedCameraData.name}</h3>
                <p className="text-sm text-gray-500">Camera {selectedCameraData.id} • 1080p • 30fps</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500">Quality:</span>
              <div className="flex space-x-1">
                {[1, 2, 3, 4].map((bar) => (
                  <div
                    key={bar}
                    className={`w-1 h-4 rounded-full ${
                      bar <= 4 ? 'bg-green-500' : 'bg-gray-200'
                    }`}
                  ></div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraStreamGrid;
