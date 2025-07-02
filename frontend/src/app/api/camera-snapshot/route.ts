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
    port: "80" // HTTP port for snapshots
  };

  try {
    // Use the correct Hikvision ISAPI URL format
    // Channel mapping: 1->101, 2->201, 3->301, 4->401
    const channelMap: Record<string, string> = {
      '1': '101',
      '2': '201', 
      '3': '301',
      '4': '401'
    };
    
    const channel = channelMap[cameraId] || '101';
    const snapshotUrl = `http://${cameraConfig.base_ip}/ISAPI/Streaming/channels/${channel}/picture`;

    console.log(`Fetching snapshot from: ${snapshotUrl}`);
    
    const response = await fetch(snapshotUrl, {
      headers: {
        'Authorization': `Basic ${Buffer.from(`${cameraConfig.username}:${cameraConfig.password}`).toString('base64')}`,
      },
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });

    if (response.ok) {
      const imageBuffer = await response.arrayBuffer();
      
      return new NextResponse(imageBuffer, {
        headers: {
          'Content-Type': 'image/jpeg',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    } else {
      console.error(`Camera ${cameraId} returned status: ${response.status}`);
      return generatePlaceholderImage(cameraId, `HTTP ${response.status}`);
    }
    
  } catch (error) {
    console.error('Error fetching camera snapshot:', error);
    return generatePlaceholderImage(cameraId, error instanceof Error ? error.message : 'Connection failed');
  }
}

function generatePlaceholderImage(cameraId: string, errorMessage: string = 'No snapshot available') {
  // Generate SVG placeholder
  const svg = `
    <svg width="640" height="360" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#1f2937;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#374151;stop-opacity:1" />
        </linearGradient>
      </defs>
      <rect width="640" height="360" fill="url(#grad1)" />
      <text x="320" y="150" font-family="Arial, sans-serif" font-size="24" fill="white" text-anchor="middle">Camera ${cameraId}</text>
      <text x="320" y="180" font-family="Arial, sans-serif" font-size="16" fill="#9ca3af" text-anchor="middle">${errorMessage}</text>
      <text x="320" y="200" font-family="Arial, sans-serif" font-size="14" fill="#6b7280" text-anchor="middle">RTSP: rtsp://admin:***@149.200.251.12:554/Streaming/Channels/${cameraId}01</text>
      <text x="320" y="220" font-family="Arial, sans-serif" font-size="12" fill="#6b7280" text-anchor="middle">${new Date().toLocaleTimeString()}</text>
      <circle cx="320" cy="250" r="5" fill="#ef4444" opacity="0.8">
        <animate attributeName="opacity" values="0.8;0.2;0.8" dur="2s" repeatCount="indefinite"/>
      </circle>
    </svg>
  `;

  return new NextResponse(svg, {
    headers: {
      'Content-Type': 'image/svg+xml',
      'Cache-Control': 'no-cache',
    },
  });
}
