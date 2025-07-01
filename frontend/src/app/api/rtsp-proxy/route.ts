import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';

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
    port: "554"
  };

  try {
    // Channel mapping
    const channelMap: Record<string, string> = {
      '1': '101',
      '2': '201', 
      '3': '301',
      '4': '401'
    };
    
    const channel = channelMap[cameraId] || '101';
    const rtspUrl = `rtsp://${cameraConfig.username}:${cameraConfig.password}@${cameraConfig.base_ip}:${cameraConfig.port}/Streaming/Channels/${channel}`;

    console.log(`Starting RTSP to MJPEG conversion for Camera ${cameraId}`);
    console.log(`RTSP URL: ${rtspUrl.replace(cameraConfig.password, '***')}`);

    // Create ReadableStream for MJPEG
    const stream = new ReadableStream({
      start(controller) {
        // FFmpeg command to convert RTSP to MJPEG
        const ffmpeg = spawn('ffmpeg', [
          '-i', rtspUrl,
          '-f', 'mjpeg',
          '-q:v', '3', // Quality (1-31, lower is better)
          '-r', '10', // Frame rate (10 FPS for web streaming)
          '-s', '640x360', // Scale down for web performance
          '-an', // No audio
          '-'
        ]);

        // Handle FFmpeg output (MJPEG frames)
        ffmpeg.stdout.on('data', (chunk) => {
          try {
            controller.enqueue(chunk);
          } catch (error) {
            console.error('Stream controller error:', error);
          }
        });

        // Handle FFmpeg errors
        ffmpeg.stderr.on('data', (data) => {
          console.error(`FFmpeg stderr: ${data}`);
        });

        ffmpeg.on('close', (code) => {
          console.log(`FFmpeg process closed with code ${code}`);
          try {
            controller.close();
          } catch (error) {
            console.error('Error closing controller:', error);
          }
        });

        ffmpeg.on('error', (error) => {
          console.error(`FFmpeg error: ${error}`);
          try {
            controller.error(error);
          } catch (controllerError) {
            console.error('Error with controller:', controllerError);
          }
        });

        // Cleanup on stream cancellation
        return () => {
          console.log(`Cleaning up FFmpeg process for Camera ${cameraId}`);
          ffmpeg.kill('SIGTERM');
        };
      }
    });

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'Access-Control-Allow-Origin': '*',
        'Connection': 'keep-alive'
      }
    });

  } catch (error) {
    console.error('Error starting RTSP proxy:', error);
    
    // Return error as JSON
    return NextResponse.json({
      error: 'Failed to start RTSP stream',
      details: error instanceof Error ? error.message : 'Unknown error',
      suggestion: 'Make sure FFmpeg is installed and RTSP URL is accessible'
    }, { status: 500 });
  }
}
