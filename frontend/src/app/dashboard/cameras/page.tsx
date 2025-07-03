"use client";

import { useRouter } from "next/navigation";
import { Sidebar } from "../../../components";
import { useAuth } from "../../../contexts/AuthContext";
import { useState, useEffect, useRef } from "react";

interface Camera {
  id: string;
  name: string;
  location: string;
  status: string;
  quality: string;
  streamType: string;
  sessionId?: string;
  isLive: boolean;
}

export default function CamerasPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  
  // WebRTC state
  const videoRef = useRef<HTMLVideoElement>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<string>('Disconnected');
  const [error, setError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  
  // Backend data state
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [availableStreams, setAvailableStreams] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Configuration
  const apiUrl = "http://localhost:8000";

  // Fetch available streams from backend - exact same logic as simple-video
  useEffect(() => {
    fetchAvailableStreams();
  }, []);

  const fetchAvailableStreams = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/streams/status`);
      if (response.ok) {
        const data = await response.json();
        console.log('Streams data:', data); // Debug log
        
        // Get streams from the API response - exact same logic as simple-video
        let streams: string[] = [];
        
        if (data.active_streams?.active_sessions) {
          // Use the session IDs directly (e.g., "4_0", "3_1", "2_2", "1_3")
          streams = data.active_streams.active_sessions;
        } else if (data.persistent_streams?.persistent_streams) {
          // Get session IDs from persistent streams
          streams = Object.values(data.persistent_streams.persistent_streams)
            .map((stream: any) => stream.session_id);
        }
        
        console.log('Found streams:', streams); // Debug log
        setAvailableStreams(streams);
        
        // Create camera objects from available streams - NO DEMO DATA
        const cameraList: Camera[] = streams.map((sessionId) => ({
          id: sessionId,
          name: `Camera ${sessionId}`,
          location: getLocationFromSessionId(sessionId),
          status: "active",
          quality: "HD",
          streamType: "webrtc",
          sessionId: sessionId,
          isLive: true,
        }));

        setCameras(cameraList);
        setLoading(false);
        
        // Auto-select first camera if none selected and cameras available - SAME AS SIMPLE-VIDEO
        if (!selectedCamera && cameraList.length > 0) {
          setSelectedCamera(cameraList[0].id);
        }
        
      } else {
        console.error('Failed to fetch streams:', response.status);
        setLoading(false);
      }
    } catch (err) {
      console.error('Error fetching streams:', err);
      // Try to get streams from another endpoint - exact same fallback as simple-video
      try {
        const fallbackResponse = await fetch(`${apiUrl}/api/status`);
        if (fallbackResponse.ok) {
          const data = await fallbackResponse.json();
          console.log('Fallback data:', data);
          if (data.streaming?.persistent_streams) {
            const streams = Object.keys(data.streaming.persistent_streams);
            setAvailableStreams(streams);
            
            // Create camera objects from fallback streams - NO DEMO DATA
            const cameraList: Camera[] = streams.map((sessionId) => ({
              id: sessionId,
              name: `Camera ${sessionId}`,
              location: getLocationFromSessionId(sessionId),
              status: "active",
              quality: "HD",
              streamType: "webrtc",
              sessionId: sessionId,
              isLive: true,
            }));

            setCameras(cameraList);
            
            // Auto-select first camera if none selected and cameras available - SAME AS SIMPLE-VIDEO
            if (!selectedCamera && cameraList.length > 0) {
              setSelectedCamera(cameraList[0].id);
            }
          }
        }
      } catch (fallbackErr) {
        console.error('Fallback fetch failed:', fallbackErr);
      }
      setLoading(false);
    }
  };

  const getLocationFromSessionId = (sessionId: string): string => {
    const locations: { [key: string]: string } = {
      "1_3": "Front Entrance",
      "2_2": "Parking Area", 
      "3_1": "Back Garden",
      "4_0": "Side Yard",
    };
    return locations[sessionId] || "Unknown Location";
  };

  const handleItemClick = (itemId: string) => {
    if (itemId === 'dashboard') {
      router.push('/dashboard');
    } else if (itemId === 'settings') {
      router.push('/dashboard/settings');
    }
  };

  // WebRTC connection functions
  const disconnect = () => {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    setConnectionStatus('Disconnected');
    setIsConnecting(false);
  };

  const connectToWebRTC = async (sessionId: string) => {
    if (!sessionId) {
      setError('No session ID provided');
      return;
    }

    try {
      setIsConnecting(true);
      setConnectionStatus('Connecting...');
      setError(null);

      console.log(`Connecting to stream: ${sessionId}`);

      // Check if stream exists - exact same logic as simple-video
      const streamCheck = await fetch(`${apiUrl}/api/webrtc/stream/${sessionId}`);
      if (!streamCheck.ok) {
        throw new Error(`Stream ${sessionId} not found. Available streams: ${availableStreams.join(', ')}`);
      }

      // Create RTCPeerConnection - exact same config as simple-video
      const pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' }
        ]
      });

      pcRef.current = pc;

      // Handle incoming stream - exact same logic as simple-video
      pc.ontrack = (event) => {
        console.log('Received remote stream:', event);
        if (videoRef.current && event.streams[0]) {
          videoRef.current.srcObject = event.streams[0];
          setConnectionStatus('Connected');
          setIsConnecting(false);
        }
      };

      // Handle connection state changes - exact same logic as simple-video
      pc.onconnectionstatechange = () => {
        console.log('Connection state:', pc.connectionState);
        setConnectionStatus(pc.connectionState);
        
        if (pc.connectionState === 'failed') {
          setError('Connection failed');
          setIsConnecting(false);
        }
      };

      // Handle ICE candidate events - try different format for backend compatibility
      pc.onicecandidate = async (event) => {
        if (event.candidate) {
          try {
            console.log('Sending ICE candidate:', event.candidate);
            
            // Try sending the candidate in the format the backend expects
            const candidateData = {
              candidate: event.candidate.candidate,
              sdpMLineIndex: event.candidate.sdpMLineIndex,
              sdpMid: event.candidate.sdpMid,
              usernameFragment: event.candidate.usernameFragment
            };
            
            console.log('Formatted ICE candidate:', candidateData);
            
            const response = await fetch(`${apiUrl}/api/streams/${sessionId}/ice-candidate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(candidateData)
            });
            
            if (!response.ok) {
              const errorText = await response.text();
              console.error('ICE candidate error:', response.status, errorText);
              
              // Fallback: try sending the original format
              console.log('Trying fallback format...');
              const fallbackResponse = await fetch(`${apiUrl}/api/streams/${sessionId}/ice-candidate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(event.candidate)
              });
              
              if (!fallbackResponse.ok) {
                console.error('Fallback also failed:', fallbackResponse.status);
              }
            } else {
              console.log('ICE candidate sent successfully');
            }
          } catch (err) {
            console.error('Error sending ICE candidate:', err);
          }
        }
      };

      // Get offer from server - exact same logic as simple-video
      const offerResponse = await fetch(`${apiUrl}/api/streams/${sessionId}/offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!offerResponse.ok) {
        throw new Error('Failed to get offer from server');
      }

      const offerData = await offerResponse.json();
      console.log('Received offer:', offerData);

      // Set remote description - exact same logic as simple-video
      await pc.setRemoteDescription(new RTCSessionDescription(offerData.offer));

      // Create answer - exact same logic as simple-video
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      // Send answer to server - exact same logic as simple-video
      const answerResponse = await fetch(`${apiUrl}/api/streams/${sessionId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: answer.sdp,
          type: answer.type
        })
      });

      if (!answerResponse.ok) {
        throw new Error('Failed to send answer to server');
      }

      console.log('WebRTC connection established');

    } catch (err) {
      console.error('Connection error:', err);
      setError(err instanceof Error ? err.message : 'Connection failed');
      setConnectionStatus('Error');
      setIsConnecting(false);
    }
  };

  // Auto-connect to WebRTC stream when camera is selected
  useEffect(() => {
    if (selectedCamera) {
      const camera = cameras.find(c => c.id === selectedCamera);
      if (camera && camera.streamType === "webrtc" && camera.sessionId) {
        disconnect();
        setTimeout(() => connectToWebRTC(camera.sessionId!), 500);
      } else {
        disconnect();
      }
    }

    return () => {
      if (!selectedCamera) {
        disconnect();
      }
    };
  }, [selectedCamera, cameras]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  const filteredCameras = cameras.filter((camera) => {
    const matchesSearch = camera.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         camera.location.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === "all" || camera.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active": return "bg-green-500";
      case "offline": return "bg-gray-400";
      case "warning": return "bg-yellow-500";
      case "error": return "bg-red-500";
      default: return "bg-gray-400";
    }
  };

  const openStream = (camera: Camera) => {
    if (camera.streamType === "webrtc") {
      setSelectedCamera(camera.id);
    } else {
      alert(`RTSP stream for ${camera.name} - Implementation pending`);
      console.log(`Opening RTSP stream for camera: ${camera.name}`);
    }
  };

  const reconnect = () => {
    if (selectedCamera) {
      const camera = cameras.find(c => c.id === selectedCamera);
      if (camera?.sessionId) {
        disconnect();
        setTimeout(() => connectToWebRTC(camera.sessionId!), 1000);
      }
    }
  };

  const refreshStreams = () => {
    setLoading(true);
    fetchAvailableStreams();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading cameras...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar activeItem="cameras" onItemClick={handleItemClick} />

      {/* Main Content */}
      <div className="ml-14 flex flex-col min-h-screen">
        {/* Header */}
        <header className="h-16 bg-white/95 backdrop-blur-xl border-b border-gray-200/50 flex items-center justify-between px-6 shadow-sm sticky top-0 z-30">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              Cameras
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {cameras.length} cameras • {cameras.filter(c => c.isLive).length} live
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Refresh Button */}
            <button 
              onClick={refreshStreams}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
            >
              Refresh
            </button>

            {/* Add Camera Button */}
            <button className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors">
              Add Camera
            </button>

            {/* Profile */}
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-xs font-semibold">
              {user?.firstName && user?.lastName 
                ? `${user.firstName[0]}${user.lastName[0]}`.toUpperCase() 
                : user?.username?.substring(0, 2).toUpperCase() || 'U'}
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            
            {/* Search and Filters */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center space-x-4">
                <div className="flex-1">
                  <input
                    type="text"
                    placeholder="Search cameras..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-gray-50"
                  />
                </div>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-gray-50"
                >
                  <option value="all">All Status</option>
                  <option value="active">Active</option>
                  <option value="offline">Offline</option>
                  <option value="warning">Warning</option>
                  <option value="error">Error</option>
                </select>
              </div>
            </div>

            {/* Live View */}
            {selectedCamera && (
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="p-6 border-b border-gray-100">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className={`w-3 h-3 rounded-full ${getStatusColor('active')}`}></div>
                      <div>
                        <h2 className="text-lg font-semibold text-gray-900">
                          {cameras.find(c => c.id === selectedCamera)?.name || 'Unknown Camera'}
                        </h2>
                        <p className="text-sm text-gray-500">
                          {cameras.find(c => c.id === selectedCamera)?.location} • {cameras.find(c => c.id === selectedCamera)?.quality}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        WebRTC
                      </span>
                      
                      {/* Connection Status */}
                      <div className="flex items-center space-x-2">
                        <div className={`w-2 h-2 rounded-full ${
                          connectionStatus === 'Connected' ? 'bg-green-500' :
                          connectionStatus === 'Connecting...' ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`}></div>
                        <span className="text-sm text-gray-600">{connectionStatus}</span>
                      </div>
                      
                      <button 
                        onClick={reconnect}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors"
                      >
                        Reconnect
                      </button>
                    </div>
                  </div>
                </div>

                <div className="aspect-video bg-black relative">
                  {/* Video Element */}
                  <video
                    ref={videoRef}
                    className="w-full h-full"
                    autoPlay
                    playsInline
                    muted
                  />
                  
                  {/* Status Overlays */}
                  {isConnecting && (
                    <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
                      <div className="text-center text-white">
                        <div className="w-16 h-16 border-4 border-white/30 border-t-white rounded-full animate-spin mx-auto mb-4"></div>
                        <p>Connecting to stream...</p>
                      </div>
                    </div>
                  )}
                  
                  {error && (
                    <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
                      <div className="text-center text-white">
                        <div className="text-red-400 text-xl mb-3">⚠️ Connection Error</div>
                        <p className="text-gray-300 mb-4">{error}</p>
                        <button 
                          onClick={reconnect}
                          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                        >
                          Retry Connection
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Live Indicator */}
                  {connectionStatus === 'Connected' && (
                    <div className="absolute top-4 left-4 flex items-center space-x-2 px-3 py-1 bg-black/70 backdrop-blur-sm rounded-full">
                      <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                      <span className="text-white text-sm font-medium">LIVE</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Camera Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredCameras.map((camera) => (
                <div
                  key={camera.id}
                  className={`group bg-white rounded-xl border-2 overflow-hidden hover:shadow-lg transition-all duration-300 cursor-pointer ${
                    selectedCamera === camera.id ? 'border-blue-400 shadow-lg' : 'border-gray-200'
                  }`}
                  onClick={() => openStream(camera)}
                >
                  {/* Camera Preview */}
                  <div className="aspect-video bg-gray-900 relative">
                    {camera.streamType === 'webrtc' ? (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        <div className="text-center">
                          <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          <p className="text-sm">WebRTC Stream</p>
                        </div>
                      </div>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        <div className="text-center">
                          <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          <p className="text-sm">RTSP Stream</p>
                        </div>
                      </div>
                    )}

                    {/* Live Indicator */}
                    {camera.isLive && (
                      <div className="absolute top-3 left-3 flex items-center space-x-1 px-2 py-1 bg-black/70 backdrop-blur-sm rounded-full">
                        <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></div>
                        <span className="text-white text-xs font-medium">LIVE</span>
                      </div>
                    )}

                    {/* Quality Badge */}
                    <div className="absolute top-3 right-3 px-2 py-1 bg-black/70 backdrop-blur-sm rounded-full">
                      <span className="text-white text-xs font-medium">{camera.quality}</span>
                    </div>

                    {/* Selection Indicator */}
                    {selectedCamera === camera.id && (
                      <div className="absolute inset-0 border-2 border-blue-400 rounded-lg bg-blue-400/10"></div>
                    )}
                  </div>

                  {/* Camera Info */}
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-gray-900">{camera.name}</h3>
                      <div className={`w-2 h-2 rounded-full ${getStatusColor(camera.status)}`}></div>
                    </div>
                    
                    <div className="flex items-center text-sm text-gray-500 mb-2">
                      <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      {camera.location}
                    </div>

                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        camera.streamType === 'webrtc' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                      }`}>
                        {camera.streamType.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-400 capitalize">{camera.status}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Empty State */}
            {filteredCameras.length === 0 && (
              <div className="text-center py-16">
                <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No cameras found</h3>
                <p className="text-gray-500 mb-6">
                  {cameras.length === 0 ? 'No cameras available from backend' : 'Try adjusting your search or filter criteria.'}
                </p>
                <button 
                  onClick={refreshStreams}
                  className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Refresh Cameras
                </button>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
