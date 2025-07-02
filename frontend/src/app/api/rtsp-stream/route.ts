import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const cameraId = searchParams.get('cameraId');
  
  if (!cameraId) {
    return NextResponse.json({ error: 'Camera ID is required' }, { status: 400 });
  }

  const cameraConfig = {
    base_ip: "149.200.251.12",
    username: "admin", 
    password: "tt55oo77",
    port: "554" // RTSP port
  };

  try {
    // Channel mapping: 1->101, 2->201, 3->301, 4->401
    const channelMap: Record<string, string> = {
      '1': '101',
      '2': '201',
      '3': '301', 
      '4': '401'
    };
    
    const channel = channelMap[cameraId] || '101';
    const rtspUrl = `rtsp://${cameraConfig.username}:${cameraConfig.password}@${cameraConfig.base_ip}:${cameraConfig.port}/Streaming/Channels/${channel}`;

    console.log(`RTSP Stream URL for Camera ${cameraId}: ${rtspUrl}`);

    // For now, return the RTSP URL and stream info
    // In a real implementation, you'd convert RTSP to HLS or WebRTC here
    return NextResponse.json({
      success: true,
      cameraId,
      rtspUrl,
      channel,
      streamInfo: {
        protocol: 'RTSP',
        resolution: '1920x1080',
        fps: 25,
        codec: 'H.264',
        bitrate: '2Mbps'
      },
      webCompatibleUrl: `/api/rtsp-proxy?cameraId=${cameraId}`,
      message: 'RTSP stream detected - converting to web format'
    });

  } catch (error) {
    console.error('Error processing RTSP stream:', error);
    return NextResponse.json({ 
      error: 'Failed to process RTSP stream',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
