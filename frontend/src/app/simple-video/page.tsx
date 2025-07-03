"use client";

import { useEffect, useRef, useState } from 'react';

export default function VideoStreamPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<string>('Disconnected');
  const [error, setError] = useState<string | null>(null);
  const [availableStreams, setAvailableStreams] = useState<string[]>([]);
  const [selectedStream, setSelectedStream] = useState<string>('');
  
  // Configuration
  const apiUrl = "http://localhost:8000";

  useEffect(() => {
    fetchAvailableStreams();
  }, []);

  useEffect(() => {
    if (selectedStream) {
      connectToStream(selectedStream);
    }
    
    return () => {
      disconnect();
    };
  }, [selectedStream]);

  const fetchAvailableStreams = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/streams/status`);
      if (response.ok) {
        const data = await response.json();
        console.log('Streams data:', data); // Debug log
        
        // Get streams from the API response
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
        
        // If no stream selected and streams available, select first one
        if (!selectedStream && streams.length > 0) {
          setSelectedStream(streams[0]);
        }
      } else {
        console.error('Failed to fetch streams:', response.status);
      }
    } catch (err) {
      console.error('Error fetching streams:', err);
      // Try to get streams from another endpoint
      try {
        const fallbackResponse = await fetch(`${apiUrl}/api/status`);
        if (fallbackResponse.ok) {
          const data = await fallbackResponse.json();
          console.log('Fallback data:', data);
          if (data.streaming?.persistent_streams) {
            const streams = Object.keys(data.streaming.persistent_streams);
            setAvailableStreams(streams);
            if (!selectedStream && streams.length > 0) {
              setSelectedStream(streams[0]);
            }
          }
        }
      } catch (fallbackErr) {
        console.error('Fallback fetch failed:', fallbackErr);
      }
    }
  };

  const disconnect = () => {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    setConnectionStatus('Disconnected');
  };

  const connectToStream = async (sessionId: string) => {
    if (!sessionId) {
      setError('No session ID provided');
      return;
    }

    try {
      setConnectionStatus('Connecting...');
      setError(null);

      console.log(`Connecting to stream: ${sessionId}`);

      // Check if stream exists
      const streamCheck = await fetch(`${apiUrl}/api/webrtc/stream/${sessionId}`);
      if (!streamCheck.ok) {
        throw new Error(`Stream ${sessionId} not found. Available streams: ${availableStreams.join(', ')}`);
      }

      // Create RTCPeerConnection
      const pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' }
        ]
      });

      pcRef.current = pc;

      // Handle incoming stream
      pc.ontrack = (event) => {
        console.log('Received remote stream:', event);
        if (videoRef.current && event.streams[0]) {
          videoRef.current.srcObject = event.streams[0];
          setConnectionStatus('Connected');
        }
      };

      // Handle connection state changes
      pc.onconnectionstatechange = () => {
        console.log('Connection state:', pc.connectionState);
        setConnectionStatus(pc.connectionState);
        
        if (pc.connectionState === 'failed') {
          setError('Connection failed');
        }
      };

      // Handle ICE candidate events
      pc.onicecandidate = async (event) => {
        if (event.candidate) {
          try {
            await fetch(`${apiUrl}/api/streams/${sessionId}/ice-candidate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(event.candidate)
            });
          } catch (err) {
            console.error('Error sending ICE candidate:', err);
          }
        }
      };

      // Get offer from server
      const offerResponse = await fetch(`${apiUrl}/api/streams/${sessionId}/offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!offerResponse.ok) {
        throw new Error('Failed to get offer from server');
      }

      const offerData = await offerResponse.json();
      console.log('Received offer:', offerData);

      // Set remote description
      await pc.setRemoteDescription(new RTCSessionDescription(offerData.offer));

      // Create answer
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      // Send answer to server
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
    }
  };

  const reconnect = () => {
    disconnect();
    setTimeout(() => connectToStream(selectedStream), 1000);
  };

  const refreshStreams = () => {
    fetchAvailableStreams();
  };

  return (
    <div className="min-h-screen bg-gray-900 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-gray-800 rounded-t-lg px-6 py-4">
          <h1 className="text-2xl font-bold text-white mb-4">Live Camera Stream</h1>
          
          {/* Stream Selection */}
          <div className="flex items-center space-x-4 mb-4">
            <label className="text-white text-sm font-medium">Select Camera:</label>
            <select
              value={selectedStream}
              onChange={(e) => setSelectedStream(e.target.value)}
              className="bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
            >
              <option value="">Select a stream...</option>
              {availableStreams.map((streamId) => (
                <option key={streamId} value={streamId}>
                  Camera {streamId}
                </option>
              ))}
            </select>
            
            <span className="text-gray-400">or</span>
            
            <input
              type="text"
              placeholder="Enter stream ID (4_0, 3_1, 2_2, 1_3...)"
              value={selectedStream}
              onChange={(e) => setSelectedStream(e.target.value)}
              className="bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none w-48"
            />
            
            <button
              onClick={refreshStreams}
              className="px-3 py-2 bg-gray-600 hover:bg-gray-500 text-white text-sm rounded transition-colors"
            >
              🔄 Refresh
            </button>
          </div>

          {/* Quick Stream Buttons */}
          {availableStreams.length > 0 && (
            <div className="flex items-center space-x-2 mb-4">
              <span className="text-white text-sm font-medium">Quick Select:</span>
              {availableStreams.map((streamId) => (
                <button
                  key={streamId}
                  onClick={() => setSelectedStream(streamId)}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    selectedStream === streamId
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-600 hover:bg-gray-500 text-white'
                  }`}
                >
                  Cam {streamId}
                </button>
              ))}
            </div>
          )}

          {/* Status Bar */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${
                connectionStatus === 'Connected' || connectionStatus === 'connected' 
                  ? 'bg-green-400' 
                  : connectionStatus === 'Connecting...' || connectionStatus === 'connecting'
                  ? 'bg-yellow-400 animate-pulse'
                  : 'bg-red-400'
              }`}></div>
              <span className="text-white text-sm font-medium">
                {selectedStream ? `Camera ${selectedStream}` : 'No camera selected'} - {connectionStatus}
              </span>
            </div>
            
            <div className="flex space-x-2">
              <button
                onClick={reconnect}
                disabled={!selectedStream}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
              >
                Reconnect
              </button>
            </div>
          </div>
        </div>

        {/* Video Container */}
        <div className="relative bg-black aspect-video rounded-b-lg overflow-hidden">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-contain"
          />
          
          {/* Loading/Error Overlay */}
          {(connectionStatus !== 'Connected' && connectionStatus !== 'connected') && (
            <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-75">
              <div className="text-center text-white max-w-md px-4">
                {error ? (
                  <div>
                    <div className="text-red-400 text-xl mb-3">⚠️ Connection Error</div>
                    <div className="text-sm text-gray-300 mb-4 break-words">{error}</div>
                    <div className="space-y-2">
                      <button
                        onClick={reconnect}
                        disabled={!selectedStream}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded transition-colors"
                      >
                        Try Again
                      </button>
                      <div className="text-xs text-gray-400">
                        Available streams: {availableStreams.length > 0 ? availableStreams.join(', ') : 'None'}
                      </div>
                    </div>
                  </div>
                ) : !selectedStream ? (
                  <div>
                    <div className="text-xl mb-3">📹 Select a Camera</div>
                    <div className="text-sm text-gray-300 mb-4">
                      Choose a camera from the dropdown above to start streaming
                    </div>
                    <button
                      onClick={refreshStreams}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
                    >
                      🔄 Check for Cameras
                    </button>
                  </div>
                ) : (
                  <div>
                    <div className="text-xl mb-3">📡 {connectionStatus}</div>
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-3"></div>
                    <div className="text-sm text-gray-300">
                      Connecting to camera {selectedStream}...
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Info Panel */}
        <div className="bg-gray-800 rounded-b-lg px-6 py-4 mt-0">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-gray-400 font-medium">Stream ID:</div>
              <div className="text-white">{selectedStream || 'None selected'}</div>
            </div>
            <div>
              <div className="text-gray-400 font-medium">API Endpoint:</div>
              <div className="text-white truncate">{apiUrl}</div>
            </div>
            <div>
              <div className="text-gray-400 font-medium">Available Streams:</div>
              <div className="text-white">{availableStreams.length}</div>
            </div>
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-6 bg-blue-900 border border-blue-700 rounded-lg p-4">
          <h3 className="text-blue-200 font-medium mb-2">How to use:</h3>
          <ul className="text-blue-100 text-sm space-y-1">
            <li>1. Make sure your FastAPI server is running on localhost:8000</li>
            <li>2. Select a camera from the dropdown menu</li>
            <li>3. The video stream will automatically connect and display</li>
            <li>4. Use the Reconnect button if the connection fails</li>
            <li>5. Click Refresh to check for new cameras</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
