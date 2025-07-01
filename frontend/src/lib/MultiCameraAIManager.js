/*
Multi-Camera AI Streaming Manager for Frontend
Handles real-time streaming of all cameras with AI detection
*/

class MultiCameraAIManager {
    constructor() {
        this.websocket = null;
        this.cameras = new Map(); // Store camera data
        this.streamingCameras = new Set(); // Track which cameras are streaming
        this.companyId = null;
        this.accessToken = null;
        this.aiDetectionEnabled = true;
        this.streamingFPS = 10;
        
        // Callbacks
        this.onCameraFrame = null;
        this.onMotionDetected = null;
        this.onCameraStatusChange = null;
        this.onAIDetection = null;
    }

    /**
     * Initialize the manager with authentication data
     */
    async initialize(accessToken, companyId) {
        this.accessToken = accessToken;
        this.companyId = companyId;
        
        try {
            // Step 1: Get all cameras from NestJS backend
            await this.loadCamerasFromBackend();
            
            // Step 2: Connect to FastAPI WebSocket
            await this.connectWebSocket();
            
            // Step 3: Initialize all camera streams
            await this.initializeAllCameraStreams();
            
            console.log('✅ Multi-Camera AI Manager initialized successfully');
            return true;
        } catch (error) {
            console.error('❌ Failed to initialize Multi-Camera AI Manager:', error);
            return false;
        }
    }

    /**
     * Load all cameras from NestJS backend
     */
    async loadCamerasFromBackend() {
        const response = await fetch('http://localhost:3000/api/cameras', {
            headers: {
                'Authorization': `Bearer ${this.accessToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to load cameras: ${response.status}`);
        }

        const cameras = await response.json();
        
        // Store cameras in our map
        this.cameras.clear();
        cameras.forEach(camera => {
            this.cameras.set(camera.id, {
                ...camera,
                isStreaming: false,
                lastFrame: null,
                motionDetected: false,
                aiDetections: [],
                streamStatus: 'disconnected'
            });
        });

        console.log(`📹 Loaded ${cameras.length} cameras from backend`);
        return cameras;
    }

    /**
     * Connect to FastAPI WebSocket for real-time streaming
     */
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://localhost:8001/ws/camera-stream?company_id=${this.companyId}`;
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('📡 Connected to FastAPI streaming WebSocket');
                resolve();
            };

            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(JSON.parse(event.data));
            };

            this.websocket.onclose = () => {
                console.log('📡 WebSocket connection closed');
                // Auto-reconnect after 3 seconds
                setTimeout(() => this.connectWebSocket(), 3000);
            };

            this.websocket.onerror = (error) => {
                console.error('📡 WebSocket error:', error);
                reject(error);
            };
        });
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'connection_established':
                console.log('📡 WebSocket connection established');
                break;

            case 'frame':
                this.handleCameraFrame(data);
                break;

            case 'motion_result':
                this.handleMotionDetection(data);
                break;

            case 'ai_detection':
                this.handleAIDetection(data);
                break;

            case 'stream_started':
                this.handleStreamStarted(data);
                break;

            case 'stream_error':
                this.handleStreamError(data);
                break;

            default:
                console.log('📡 Unknown WebSocket message:', data);
        }
    }

    /**
     * Handle camera frame updates
     */
    handleCameraFrame(data) {
        const camera = this.cameras.get(data.camera_id);
        if (camera) {
            camera.lastFrame = data.frame;
            camera.streamStatus = 'streaming';
            
            // Update UI
            if (this.onCameraFrame) {
                this.onCameraFrame(data.camera_id, data.frame, data.timestamp);
            }
        }
    }

    /**
     * Handle motion detection results
     */
    handleMotionDetection(data) {
        const camera = this.cameras.get(data.camera_id);
        if (camera) {
            camera.motionDetected = data.motion_detected;
            
            if (data.motion_detected) {
                console.log(`🚨 Motion detected in camera ${data.camera_id} (${camera.name})`);
                
                // Trigger AI analysis if enabled
                if (this.aiDetectionEnabled) {
                    this.requestAIAnalysis(data.camera_id);
                }
            }
            
            // Callback to UI
            if (this.onMotionDetected) {
                this.onMotionDetected(data.camera_id, data.motion_detected, data.confidence);
            }
        }
    }

    /**
     * Handle AI detection results
     */
    handleAIDetection(data) {
        const camera = this.cameras.get(data.camera_id);
        if (camera) {
            camera.aiDetections.push({
                timestamp: Date.now(),
                type: data.detection_type,
                confidence: data.confidence,
                objects: data.objects || [],
                threat_level: data.threat_level || 'LOW'
            });

            // Keep only last 10 detections
            if (camera.aiDetections.length > 10) {
                camera.aiDetections = camera.aiDetections.slice(-10);
            }

            // Callback to UI
            if (this.onAIDetection) {
                this.onAIDetection(data.camera_id, data);
            }
        }
    }

    /**
     * Handle stream started confirmation
     */
    handleStreamStarted(data) {
        const camera = this.cameras.get(data.camera_id);
        if (camera) {
            camera.isStreaming = true;
            camera.streamStatus = 'connected';
            this.streamingCameras.add(data.camera_id);
            
            console.log(`📹 Stream started for ${data.camera_name} (ID: ${data.camera_id})`);
            
            if (this.onCameraStatusChange) {
                this.onCameraStatusChange(data.camera_id, 'connected');
            }
        }
    }

    /**
     * Handle stream errors
     */
    handleStreamError(data) {
        const camera = this.cameras.get(data.camera_id);
        if (camera) {
            camera.isStreaming = false;
            camera.streamStatus = 'error';
            this.streamingCameras.delete(data.camera_id);
            
            console.error(`❌ Stream error for camera ${data.camera_id}:`, data.error);
            
            if (this.onCameraStatusChange) {
                this.onCameraStatusChange(data.camera_id, 'error');
            }
        }
    }

    /**
     * Initialize streaming for all cameras
     */
    async initializeAllCameraStreams() {
        const promises = [];
        
        for (const [cameraId, camera] of this.cameras) {
            if (camera.isActive) {
                promises.push(this.startCameraStream(cameraId));
            }
        }
        
        const results = await Promise.allSettled(promises);
        const successful = results.filter(r => r.status === 'fulfilled').length;
        
        console.log(`📹 Started streaming for ${successful}/${this.cameras.size} cameras`);
    }

    /**
     * Start streaming for a specific camera
     */
    async startCameraStream(cameraId) {
        try {
            // First initialize the camera in FastAPI
            const initResponse = await fetch(`http://localhost:8001/api/stream/camera/${cameraId}/initialize`, {
                method: 'POST',
                headers: {
                    'X-Company-Id': this.companyId.toString()
                }
            });

            if (!initResponse.ok) {
                throw new Error(`Failed to initialize camera ${cameraId}`);
            }

            // Start WebSocket streaming
            this.websocket.send(JSON.stringify({
                type: 'start_stream',
                camera_id: cameraId,
                fps: this.streamingFPS
            }));

            // Enable motion detection
            this.websocket.send(JSON.stringify({
                type: 'enable_motion_detection',
                camera_id: cameraId
            }));

            return true;
        } catch (error) {
            console.error(`❌ Failed to start stream for camera ${cameraId}:`, error);
            return false;
        }
    }

    /**
     * Start streaming for a specific camera with AI detection enabled
     */
    async startCameraStreamWithAI(cameraId) {
        try {
            // First initialize the camera in FastAPI
            const initResponse = await fetch(`http://localhost:8001/api/stream/camera/${cameraId}/initialize`, {
                method: 'POST',
                headers: {
                    'X-Company-Id': this.companyId.toString()
                }
            });

            if (!initResponse.ok) {
                throw new Error(`Failed to initialize camera ${cameraId}`);
            }

            // Start WebSocket streaming with AI detection
            this.websocket.send(JSON.stringify({
                type: 'start_stream_with_ai',
                camera_id: cameraId,
                fps: this.streamingFPS,
                enable_motion_detection: true,
                enable_ai_detection: this.aiDetectionEnabled
            }));

            return true;
        } catch (error) {
            console.error(`❌ Failed to start stream with AI for camera ${cameraId}:`, error);
            return false;
        }
    }

    /**
     * Stop streaming for a specific camera
     */
    stopCameraStream(cameraId) {
        this.websocket.send(JSON.stringify({
            type: 'stop_stream',
            camera_id: cameraId
        }));

        const camera = this.cameras.get(cameraId);
        if (camera) {
            camera.isStreaming = false;
            camera.streamStatus = 'stopped';
            this.streamingCameras.delete(cameraId);
        }
    }

    /**
     * Stop streaming for all cameras
     */
    async stopAllCameraStreams() {
        console.log('⏸️ Stopping all camera streams...');
        
        const promises = [];
        
        for (const cameraId of this.streamingCameras) {
            promises.push(this.stopCameraStream(cameraId));
        }
        
        await Promise.allSettled(promises);
        
        console.log('⏹️ All camera streams stopped');
        return true;
    }

    /**
     * Request AI analysis for a camera
     */
    requestAIAnalysis(cameraId) {
        this.websocket.send(JSON.stringify({
            type: 'ai_analysis',
            camera_id: cameraId,
            analysis_type: 'full' // Can be 'motion', 'objects', 'faces', 'full'
        }));
    }

    /**
     * Get current frame from a camera (HTTP fallback)
     */
    async getCameraFrame(cameraId) {
        try {
            const response = await fetch(`http://localhost:8001/api/stream/camera/${cameraId}/frame`, {
                headers: {
                    'X-Company-Id': this.companyId.toString()
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to get frame: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`❌ Failed to get frame for camera ${cameraId}:`, error);
            return null;
        }
    }

    /**
     * Start manual recording for a camera
     */
    async startRecording(cameraId, duration = 60) {
        try {
            const response = await fetch(`http://localhost:8001/api/stream/camera/${cameraId}/record?duration=${duration}`, {
                method: 'POST',
                headers: {
                    'X-Company-Id': this.companyId.toString()
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to start recording: ${response.status}`);
            }

            const result = await response.json();
            console.log(`📹 Recording started for camera ${cameraId}:`, result);
            return result;
        } catch (error) {
            console.error(`❌ Failed to start recording for camera ${cameraId}:`, error);
            return null;
        }
    }

    /**
     * Start streaming for all active cameras with AI detection
     */
    async startAllCameraStreams() {
        console.log('🚀 Starting all camera streams with AI detection...');
        
        const promises = [];
        
        for (const [cameraId, camera] of this.cameras) {
            if (camera.isActive) {
                promises.push(this.startCameraStreamWithAI(cameraId));
            }
        }
        
        const results = await Promise.allSettled(promises);
        const successful = results.filter(r => r.status === 'fulfilled' && r.value === true).length;
        
        console.log(`📹 Started streaming for ${successful}/${this.cameras.size} cameras`);
        return successful;
    }

    /**
     * Enable/disable AI detection for all streaming cameras
     */
    toggleAIDetectionForAll(enabled) {
        this.aiDetectionEnabled = enabled;
        
        for (const cameraId of this.streamingCameras) {
            this.websocket.send(JSON.stringify({
                type: 'toggle_ai_detection',
                camera_id: cameraId,
                enabled: enabled
            }));
        }
        
        console.log(`🤖 AI detection ${enabled ? 'enabled' : 'disabled'} for all cameras`);
    }

    /**
     * Get streaming statistics
     */
    getStreamingStats() {
        const totalCameras = this.cameras.size;
        const streamingCameras = this.streamingCameras.size;
        const activeCameras = Array.from(this.cameras.values()).filter(c => c.isActive).length;
        
        return {
            total: totalCameras,
            active: activeCameras,
            streaming: streamingCameras,
            aiEnabled: this.aiDetectionEnabled
        };
    }

    /**
     * Cleanup and disconnect
     */
    disconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        this.cameras.clear();
        this.streamingCameras.clear();
        
        console.log('📡 Multi-Camera AI Manager disconnected');
    }
}

// Export for use in your frontend
window.MultiCameraAIManager = MultiCameraAIManager;
