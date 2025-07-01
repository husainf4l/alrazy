import { NextRequest, NextResponse } from 'next/server';
import net from 'net';

export async function POST(request: NextRequest) {
  try {
    const { ip, port, cameraId, url } = await request.json();
    
    console.log(`🔍 Testing connectivity to Camera ${cameraId} at ${ip}:${port}`);
    
    // Test TCP connectivity to the IP and port
    const isConnectable = await testTcpConnection(ip, parseInt(port));
    
    if (isConnectable) {
      return NextResponse.json({
        connected: true,
        status: `Connected to ${ip}:${port}`,
        cameraId,
        timestamp: new Date().toISOString(),
        details: {
          ip,
          port,
          protocol: 'RTSP',
          tested: true
        }
      });
    } else {
      return NextResponse.json({
        connected: false,
        status: `Cannot reach ${ip}:${port}`,
        cameraId,
        timestamp: new Date().toISOString(),
        details: {
          ip,
          port,
          protocol: 'RTSP',
          tested: true,
          error: 'Connection timeout or refused'
        }
      });
    }
  } catch (error) {
    console.error('❌ Camera connection test error:', error);
    return NextResponse.json({
      connected: false,
      status: `Error: ${error}`,
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}

function testTcpConnection(host: string, port: number, timeout = 5000): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    
    const timer = setTimeout(() => {
      socket.destroy();
      resolve(false);
    }, timeout);
    
    socket.connect(port, host, () => {
      clearTimeout(timer);
      socket.destroy();
      resolve(true);
    });
    
    socket.on('error', () => {
      clearTimeout(timer);
      resolve(false);
    });
  });
}
