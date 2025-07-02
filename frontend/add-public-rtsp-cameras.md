# Adding Public RTSP Cameras for Testing

Here are some known public RTSP camera streams that you can add to your dashboard for testing:

## Well-Known Public RTSP Streams

### Big Buck Bunny Test Stream

```
rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov
```

### Wowza Test Streams

```
rtsp://184.72.239.149/vod/mp4:BigBuckBunny_115k.mov
rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov
```

### Sample Streams

```
rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream
rtsp://demo.beenius.com:554/multicast/test/elementary
```

## How to Add These to Your Dashboard

### Method 1: Update CameraStreamGridEnhanced Component

Open `/src/components/CameraStreamGridEnhanced.tsx` and add these cameras to the test configuration:

```tsx
const publicTestCameras = [
  {
    id: "public-1",
    name: "Big Buck Bunny Test",
    rtspUrl: "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov",
    username: "",
    password: "",
    location: "Test Stream",
    status: "active" as const,
  },
  {
    id: "public-2",
    name: "Wowza Demo Stream",
    rtspUrl: "rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov",
    username: "",
    password: "",
    location: "Test Stream",
    status: "active" as const,
  },
  {
    id: "public-3",
    name: "Strba Lake View",
    rtspUrl: "rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream",
    username: "",
    password: "",
    location: "Slovakia",
    status: "active" as const,
  },
];

// Then in your component, combine with local cameras:
const allCameras = [...cameras, ...publicTestCameras];
```

### Method 2: Add via Environment Variables

Add these to your `.env` file:

```env
# Public test cameras
PUBLIC_RTSP_1=rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov
PUBLIC_RTSP_2=rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov
PUBLIC_RTSP_3=rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream
```

### Method 3: Test with MediaMTX

You can proxy these streams through your MediaMTX server by adding paths to your `mediamtx.yml`:

```yaml
paths:
  public-test-1:
    source: rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov
    sourceOnDemand: yes

  public-test-2:
    source: rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov
    sourceOnDemand: yes

  public-test-3:
    source: rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream
    sourceOnDemand: yes
```

Then access them via:

```
rtsp://localhost:8554/public-test-1
rtsp://localhost:8554/public-test-2
rtsp://localhost:8554/public-test-3
```

## Alternative: Use MediaMTX's Built-in Test Stream

MediaMTX can generate test streams. Add this to your `mediamtx.yml`:

```yaml
paths:
  test-pattern:
    runOnInit: >
      ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 
      -f lavfi -i sine=frequency=1000:sample_rate=44100 
      -c:v libx264 -pix_fmt yuv420p -preset ultrafast -b:v 1000k 
      -c:a aac -b:a 128k 
      -f rtsp rtsp://localhost:$RTSP_PORT/$MTX_PATH
    runOnInitRestart: yes
```

This creates a test pattern with audio at `rtsp://localhost:8554/test-pattern`.

## Testing These Streams

1. **VLC Test**: Open VLC and try to play these URLs directly
2. **FFplay Test**: `ffplay rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov`
3. **Dashboard Test**: Add them to your React dashboard and test streaming

## Notes

- These are public streams and may not always be available
- Some streams might require specific codecs or have connection limits
- Always test connectivity before deploying in production
- Consider using your own RTSP server with test content for reliable testing
