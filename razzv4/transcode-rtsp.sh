#!/bin/bash

# Transcode Camera 01 Main Stream (101 or 301) to clean H.264
ffmpeg -rtsp_transport tcp \
  -i "rtsp://admin:tt55oo77@192.168.1.75:554/Streaming/Channels/101/" \
  -c:v libx264 \
  -preset ultrafast \
  -tune zerolatency \
  -profile:v baseline \
  -level 3.1 \
  -b:v 2048k \
  -maxrate 2048k \
  -bufsize 4096k \
  -g 40 \
  -keyint_min 40 \
  -r 20 \
  -f rtsp \
  -rtsp_transport tcp \
  rtsp://localhost:8554/camera1

