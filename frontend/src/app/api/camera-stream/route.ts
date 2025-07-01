import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const cameraId = searchParams.get('cameraId');
  
  if (!cameraId) {
    return NextResponse.json({ error: 'Camera ID is required' }, { status: 400 });
  }

  const cameraConfig = {
    base_ip: "192.168.1.186",
    username: "admin",
    password: "tt55oo77",
    rtsp_port: "554",
    http_port: "80"
  };

  // This DVR model doesn't support MJPEG streaming via HTTP
  // Return information about available streaming options
  const channelMap: Record<string, string> = {
    '1': '101',
    '2': '201', 
    '3': '301',
    '4': '401'
  };
  
  const channel = channelMap[cameraId] || '101';
  const rtspUrl = `rtsp://${cameraConfig.username}:${cameraConfig.password}@${cameraConfig.base_ip}:${cameraConfig.rtsp_port}/Streaming/Channels/${channel}`;

  return NextResponse.json({
    cameraId,
    streamingOptions: {
      rtsp: {
        url: rtspUrl,
        description: "Primary RTSP stream (requires conversion for web)",
        supported: true
      },
      mjpeg: {
        description: "MJPEG not supported by this DVR model",
        supported: false
      },
      snapshot: {
        url: `/api/camera-snapshot?cameraId=${cameraId}`,
        description: "HTTP snapshot images",
        supported: true,
        refreshRate: "500ms - 2000ms based on quality setting"
      }
    },
    recommendation: "Use snapshot-based streaming with fast refresh rate",
    note: "For true video streaming, RTSP must be converted to HLS/WebRTC server-side"
  });
}
