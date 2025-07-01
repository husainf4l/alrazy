import { NextRequest } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const cameraId = searchParams.get('cameraId');
  
  if (!cameraId) {
    return new Response('Camera ID is required', { status: 400 });
  }

  const cameraConfig = {
    base_ip: "192.168.1.186",
    username: "admin",
    password: "tt55oo77",
  };

  // Create WebSocket upgrade response
  if (request.headers.get('upgrade') === 'websocket') {
    // This would require a WebSocket server implementation
    // For now, return upgrade information
    return new Response('WebSocket upgrade required for real-time streaming', {
      status: 426,
      headers: {
        'Upgrade': 'websocket',
        'Connection': 'Upgrade',
      }
    });
  }

  // Return streaming endpoint information
  const streamInfo = {
    cameraId,
    endpoints: {
      rtsp: `rtsp://${cameraConfig.username}:${cameraConfig.password}@${cameraConfig.base_ip}:554/Streaming/Channels/${cameraId}01`,
      mjpeg: `/api/camera-stream?cameraId=${cameraId}`,
      snapshot: `/api/camera-snapshot?cameraId=${cameraId}`,
      websocket: `/api/camera-websocket?cameraId=${cameraId}`
    },
    status: 'available',
    timestamp: new Date().toISOString()
  };

  return Response.json(streamInfo);
}
