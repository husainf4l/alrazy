/**
 * Room Designer - Interactive Canvas for Camera Positioning
 */

const canvas = document.getElementById('roomCanvas');
const ctx = canvas.getContext('2d');

// State
let currentTool = 'select';
let scale = 100; // pixels per meter
let roomDimensions = { width: 10, length: 8, height: 3 };
let cameras = [];
let overlapZones = [];
let selectedCamera = null;
let isDragging = false;
let dragStart = null;
let showGrid = true;
let rooms = [];
let currentRoomId = null;
let floorPlanImage = null;
let floorPlanOpacity = 0.5;

// Camera colors
const CAMERA_COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    updateTime();
    setInterval(updateTime, 1000);
    loadRooms();
    setupEventListeners();
    redraw();
});

function updateTime() {
    const now = new Date();
    document.getElementById('currentTime').textContent = now.toLocaleTimeString();
}

async function loadRooms() {
    try {
        const response = await fetch('/api/rooms/');
        rooms = await response.json();
        
        const select = document.getElementById('roomSelect');
        select.innerHTML = '<option value="">Select a room...</option>';
        rooms.forEach(room => {
            const option = document.createElement('option');
            option.value = room.id;
            option.textContent = `${room.name} (${room.camera_count} cameras)`;
            select.appendChild(option);
        });
        
        select.addEventListener('change', (e) => {
            if (e.target.value) {
                loadRoomLayout(parseInt(e.target.value));
            }
        });
    } catch (error) {
        console.error('Error loading rooms:', error);
    }
}

async function loadRoomLayout(roomId) {
    currentRoomId = roomId;
    const room = rooms.find(r => r.id === roomId);
    
    // Load room cameras
    cameras = room.cameras.map((cam, idx) => ({
        id: cam.id,
        name: cam.name,
        x: 100 + idx * 150, // Default position
        y: 100 + idx * 100,
        rotation: 0,
        fov: 90,
        distance: 10,
        height: 2.5,
        color: CAMERA_COLORS[idx % CAMERA_COLORS.length]
    }));
    
    // Try to load saved layout
    try {
        const response = await fetch(`/api/rooms/${roomId}/layout`);
        if (response.ok) {
            const layout = await response.json();
            if (layout.dimensions) {
                roomDimensions = layout.dimensions;
                document.getElementById('roomWidth').value = layout.dimensions.width;
                document.getElementById('roomLength').value = layout.dimensions.length;
                document.getElementById('roomHeight').value = layout.dimensions.height;
            }
            if (layout.camera_positions && layout.camera_positions.length > 0) {
                layout.camera_positions.forEach(pos => {
                    const cam = cameras.find(c => c.id === pos.camera_id);
                    if (cam) {
                        cam.x = pos.position.x * scale;
                        cam.y = pos.position.y * scale;
                        cam.rotation = pos.rotation;
                        cam.fov = pos.fov_angle;
                        cam.distance = pos.fov_distance;
                        cam.height = pos.height;
                    }
                });
            }
            if (layout.overlap_zones) {
                overlapZones = layout.overlap_zones;
            }
            if (layout.scale) {
                scale = layout.scale;
                document.getElementById('scaleSlider').value = scale;
                document.getElementById('scaleDisplay').textContent = scale;
            }
            if (layout.floor_plan_image) {
                loadFloorPlanFromBase64(layout.floor_plan_image);
            }
        }
    } catch (error) {
        console.log('No saved layout, using defaults');
    }
    
    updateCameraList();
    updateDimensions();
    redraw();
}

function setupEventListeners() {
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', handleMouseUp);
    
    // Drag and drop for floor plan
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('border-blue-500', 'bg-blue-50');
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('border-blue-500', 'bg-blue-50');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('border-blue-500', 'bg-blue-50');
        
        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type.startsWith('image/')) {
            handleFloorPlanFile(files[0]);
        }
    });
}

function setTool(tool) {
    currentTool = tool;
    document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(tool + 'Tool').classList.add('active');
    
    if (tool === 'select') {
        canvas.style.cursor = 'default';
    } else if (tool === 'camera') {
        canvas.style.cursor = 'crosshair';
    } else if (tool === 'overlap') {
        canvas.style.cursor = 'crosshair';
    }
}

function handleMouseDown(e) {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    if (currentTool === 'select') {
        // Check if clicking on a camera
        selectedCamera = null;
        for (let i = cameras.length - 1; i >= 0; i--) {
            const cam = cameras[i];
            const dist = Math.sqrt((x - cam.x) ** 2 + (y - cam.y) ** 2);
            if (dist < 15) {
                selectedCamera = cam;
                isDragging = true;
                dragStart = { x, y };
                showCameraProperties(cam);
                break;
            }
        }
        if (!selectedCamera) {
            hideCameraProperties();
        }
    } else if (currentTool === 'camera') {
        // Place new camera
        if (currentRoomId && cameras.length < 10) {
            const availableCam = cameras.find(c => !c.placed);
            if (availableCam || cameras.length === 0) {
                // Just position existing cameras
                alert('Please use the camera assignment feature in Rooms page to add cameras first');
            }
        }
    }
    
    redraw();
}

function handleMouseMove(e) {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Update coordinates display
    const meterX = (x / scale).toFixed(2);
    const meterY = (y / scale).toFixed(2);
    document.getElementById('canvasInfo').textContent = `Position: ${meterX}m, ${meterY}m`;
    
    if (isDragging && selectedCamera) {
        selectedCamera.x = x;
        selectedCamera.y = y;
        redraw();
    }
}

function handleMouseUp(e) {
    isDragging = false;
    dragStart = null;
}

function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw floor plan first (as background)
    if (floorPlanImage && document.getElementById('showFloorPlan').checked) {
        drawFloorPlan();
    }
    
    // Draw grid
    if (showGrid) {
        drawGrid();
    }
    
    // Draw room boundary
    drawRoomBoundary();
    
    // Draw overlap zones
    overlapZones.forEach(zone => {
        drawOverlapZone(zone);
    });
    
    // Draw cameras
    cameras.forEach(cam => {
        drawCamera(cam, cam === selectedCamera);
    });
}

function drawGrid() {
    ctx.strokeStyle = '#f3f4f6';
    ctx.lineWidth = 1;
    
    const gridSize = scale; // 1 meter
    
    for (let x = 0; x <= canvas.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
    }
    
    for (let y = 0; y <= canvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
    }
    
    // Draw meter labels
    ctx.fillStyle = '#9ca3af';
    ctx.font = '10px Inter';
    for (let x = gridSize; x <= canvas.width; x += gridSize) {
        ctx.fillText((x / scale) + 'm', x - 12, 12);
    }
    for (let y = gridSize; y <= canvas.height; y += gridSize) {
        ctx.fillText((y / scale) + 'm', 5, y - 5);
    }
}

function drawRoomBoundary() {
    const width = roomDimensions.width * scale;
    const length = roomDimensions.length * scale;
    
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 3;
    ctx.setLineDash([]);
    ctx.strokeRect(0, 0, width, length);
    
    ctx.fillStyle = '#9ca3af';
    ctx.font = '12px Inter';
    ctx.fillText(`${roomDimensions.width}m × ${roomDimensions.length}m`, 10, length + 20);
}

function drawCamera(cam, isSelected) {
    const showFOV = document.getElementById('showFOV').checked;
    
    // Draw FOV cone
    if (showFOV) {
        ctx.fillStyle = cam.color + '33'; // 20% opacity
        ctx.strokeStyle = cam.color;
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 5]);
        
        ctx.beginPath();
        ctx.moveTo(cam.x, cam.y);
        
        const fovRad = (cam.fov * Math.PI) / 180;
        const rotRad = (cam.rotation * Math.PI) / 180;
        const distance = cam.distance * scale;
        
        const angle1 = rotRad - fovRad / 2;
        const angle2 = rotRad + fovRad / 2;
        
        const x1 = cam.x + Math.cos(angle1) * distance;
        const y1 = cam.y + Math.sin(angle1) * distance;
        const x2 = cam.x + Math.cos(angle2) * distance;
        const y2 = cam.y + Math.sin(angle2) * distance;
        
        ctx.lineTo(x1, y1);
        ctx.arc(cam.x, cam.y, distance, angle1, angle2);
        ctx.lineTo(cam.x, cam.y);
        ctx.closePath();
        
        ctx.fill();
        ctx.stroke();
        ctx.setLineDash([]);
    }
    
    // Draw camera marker
    ctx.fillStyle = cam.color;
    ctx.strokeStyle = isSelected ? '#fbbf24' : '#1e40af';
    ctx.lineWidth = isSelected ? 3 : 2;
    
    ctx.beginPath();
    ctx.arc(cam.x, cam.y, 12, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
    
    // Draw camera icon
    ctx.fillStyle = 'white';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('📹', cam.x, cam.y);
    
    // Draw camera name
    ctx.fillStyle = '#374151';
    ctx.font = 'bold 11px Inter';
    ctx.fillText(cam.name, cam.x, cam.y + 25);
}

function drawOverlapZone(zone) {
    if (zone.polygon_points && zone.polygon_points.length >= 3) {
        ctx.fillStyle = '#fef3c7';
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 2;
        ctx.setLineDash([10, 5]);
        
        ctx.beginPath();
        ctx.moveTo(zone.polygon_points[0].x * scale, zone.polygon_points[0].y * scale);
        zone.polygon_points.forEach(point => {
            ctx.lineTo(point.x * scale, point.y * scale);
        });
        ctx.closePath();
        
        ctx.fill();
        ctx.stroke();
        ctx.setLineDash([]);
    }
}

function showCameraProperties(cam) {
    document.getElementById('cameraProperties').classList.remove('hidden');
    document.getElementById('cameraFOV').value = cam.fov;
    document.getElementById('cameraRotation').value = cam.rotation;
    document.getElementById('cameraDistance').value = cam.distance;
    document.getElementById('cameraHeight').value = cam.height;
}

function hideCameraProperties() {
    document.getElementById('cameraProperties').classList.add('hidden');
    selectedCamera = null;
    redraw();
}

function updateCameraProperty(prop, value) {
    if (!selectedCamera) return;
    
    value = parseFloat(value);
    
    if (prop === 'fov') {
        selectedCamera.fov = value;
    } else if (prop === 'rotation') {
        // Normalize rotation to 0-360 range
        value = value % 360;
        if (value < 0) {
            value = 360 + value; // Convert negative to positive (e.g., -10 becomes 350)
        }
        selectedCamera.rotation = value;
        // Update the input field to show normalized value
        document.getElementById('cameraRotation').value = value;
    } else if (prop === 'distance') {
        selectedCamera.distance = value;
    } else if (prop === 'height') {
        selectedCamera.height = value;
    }
    
    redraw();
}

function deleteSelectedCamera() {
    if (!selectedCamera) return;
    
    if (confirm(`Remove camera "${selectedCamera.name}" from layout?`)) {
        cameras = cameras.filter(c => c !== selectedCamera);
        selectedCamera = null;
        hideCameraProperties();
        updateCameraList();
        redraw();
    }
}

function updateCameraList() {
    const list = document.getElementById('cameraList');
    
    if (cameras.length === 0) {
        list.innerHTML = '<p class="text-xs text-gray-500">No cameras assigned</p>';
        return;
    }
    
    list.innerHTML = cameras.map(cam => `
        <div class="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
            <div class="flex items-center space-x-2">
                <div class="w-3 h-3 rounded-full" style="background-color: ${cam.color}"></div>
                <span class="text-xs font-medium">${cam.name}</span>
            </div>
            <button onclick="selectCamera(${cam.id})" class="text-xs text-blue-600 hover:text-blue-800">
                Edit
            </button>
        </div>
    `).join('');
}

function selectCamera(cameraId) {
    selectedCamera = cameras.find(c => c.id === cameraId);
    if (selectedCamera) {
        showCameraProperties(selectedCamera);
        redraw();
    }
}

function updateDimensions() {
    roomDimensions.width = parseFloat(document.getElementById('roomWidth').value);
    roomDimensions.length = parseFloat(document.getElementById('roomLength').value);
    roomDimensions.height = parseFloat(document.getElementById('roomHeight').value);
    redraw();
}

function updateScale(value) {
    scale = parseInt(value);
    document.getElementById('scaleDisplay').textContent = scale;
    redraw();
}

function toggleGrid() {
    showGrid = document.getElementById('showGrid').checked;
    redraw();
}

function handleFloorPlanUpload(event) {
    const file = event.target.files[0];
    if (file) {
        handleFloorPlanFile(file);
    }
}

function handleFloorPlanFile(file) {
    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
        alert('File size must be less than 5MB');
        return;
    }
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Please upload an image file (PNG, JPG, etc.)');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        loadFloorPlanFromBase64(e.target.result);
    };
    reader.readAsDataURL(file);
}

function loadFloorPlanFromBase64(base64Data) {
    const img = new Image();
    img.onload = function() {
        floorPlanImage = img;
        
        // Show preview
        document.getElementById('floorPlanPreview').classList.remove('hidden');
        document.getElementById('floorPlanImage').src = base64Data;
        
        // Auto-adjust scale based on image size
        const suggestedScale = Math.min(
            canvas.width / roomDimensions.width,
            canvas.height / roomDimensions.length
        );
        
        console.log('Floor plan loaded:', img.width, 'x', img.height);
        redraw();
    };
    img.src = base64Data;
}

function removeFloorPlan() {
    if (confirm('Remove floor plan image?')) {
        floorPlanImage = null;
        document.getElementById('floorPlanPreview').classList.add('hidden');
        document.getElementById('floorPlanInput').value = '';
        redraw();
    }
}

function updateFloorPlanOpacity(value) {
    floorPlanOpacity = parseFloat(value);
    redraw();
}

function drawFloorPlan() {
    if (!floorPlanImage) return;
    
    ctx.save();
    ctx.globalAlpha = floorPlanOpacity;
    
    // Draw floor plan scaled to room dimensions
    const width = roomDimensions.width * scale;
    const length = roomDimensions.length * scale;
    
    // Maintain aspect ratio
    const imgAspect = floorPlanImage.width / floorPlanImage.height;
    const roomAspect = width / length;
    
    let drawWidth = width;
    let drawHeight = length;
    let offsetX = 0;
    let offsetY = 0;
    
    if (imgAspect > roomAspect) {
        // Image is wider - fit to width
        drawHeight = width / imgAspect;
        offsetY = (length - drawHeight) / 2;
    } else {
        // Image is taller - fit to height
        drawWidth = length * imgAspect;
        offsetX = (width - drawWidth) / 2;
    }
    
    ctx.drawImage(floorPlanImage, offsetX, offsetY, drawWidth, drawHeight);
    ctx.restore();
}

function clearCanvas() {
    if (confirm('Clear all cameras and overlap zones?')) {
        cameras = [];
        overlapZones = [];
        selectedCamera = null;
        hideCameraProperties();
        updateCameraList();
        redraw();
    }
}

async function saveLayout() {
    if (!currentRoomId) {
        alert('Please select a room first');
        return;
    }
    
    // Get floor plan base64 if exists
    let floorPlanBase64 = null;
    if (floorPlanImage) {
        floorPlanBase64 = document.getElementById('floorPlanImage').src;
    }
    
    const layout = {
        dimensions: roomDimensions,
        scale: scale,
        floor_plan_image: floorPlanBase64,
        camera_positions: cameras.map(cam => ({
            camera_id: cam.id,
            position: {
                x: cam.x / scale,
                y: cam.y / scale
            },
            rotation: cam.rotation,
            fov_angle: cam.fov,
            fov_distance: cam.distance,
            height: cam.height,
            tilt_angle: 0
        })),
        overlap_zones: overlapZones
    };
    
    try {
        const response = await fetch(`/api/rooms/${currentRoomId}/layout`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(layout)
        });
        
        if (response.ok) {
            alert('✅ Layout saved successfully!');
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail}`);
        }
    } catch (error) {
        console.error('Error saving layout:', error);
        alert('Failed to save layout');
    }
}
