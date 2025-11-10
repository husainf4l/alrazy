/**
 * Room Designer - API Integration
 * Handles all server communication
 */

const RoomDesignerAPI = {
    /**
     * Load room data from server
     */
    async loadRoomData(roomId, state) {
        try {
            const response = await fetch('/vault-rooms/');
            const data = await response.json();
            const room = data.vault_rooms.find(r => r.id === roomId);
            
            if (room) {
                document.getElementById('roomName').value = room.name;
                
                // Load layout if exists
                if (room.room_layout) {
                    try {
                        const design = JSON.parse(room.room_layout);
                        state.objects = design.objects || [];
                        state.scale = design.scale || 20;
                        document.getElementById('scale').value = state.scale;
                        
                        // Save initial state to history after loading
                        state.saveToHistory();
                        
                        RoomDesignerRenderer.render(state);
                    } catch (err) {
                        console.error('Error parsing room layout:', err);
                    }
                }
                
                document.getElementById('statusMsg').textContent = `Loaded: ${room.name}`;
            }
            
            // Load cameras after room data
            await this.loadRoomCameras(roomId, state);
            
        } catch (err) {
            console.error('Error loading room data:', err);
            document.getElementById('statusMsg').textContent = 'Error loading room';
        }
    },

    /**
     * Load cameras for this room
     */
    async loadRoomCameras(roomId, state) {
        try {
            const response = await fetch(`/vault-rooms/${roomId}/cameras`);
            const data = await response.json();
            state.availableCameras = data.cameras || [];
            
            console.log(`Loaded ${state.availableCameras.length} cameras for room ${roomId}:`, state.availableCameras);
            
            // Update cameras list in UI
            this.updateCamerasList(state);
            
            // Add cameras to the design if they have positions
            state.availableCameras.forEach(camera => {
                if (camera.position_x !== null && camera.position_y !== null) {
                    const exists = state.objects.some(obj => 
                        obj.type === 'camera' && obj.cameraId === camera.id
                    );
                    
                    if (!exists) {
                        state.objects.push({
                            type: 'camera',
                            cameraId: camera.id,
                            x: camera.position_x,
                            y: camera.position_y,
                            angle: camera.direction || 0,
                            fov: camera.field_of_view || 90,
                            range: 5,
                            id: camera.name
                        });
                    }
                }
            });
            
            RoomDesignerRenderer.render(state);
            document.getElementById('statusMsg').textContent = 
                `Loaded ${state.availableCameras.length} cameras`;
            
        } catch (err) {
            console.error('Error loading room cameras:', err);
            document.getElementById('statusMsg').textContent = 'Error loading cameras';
            document.getElementById('camerasList').innerHTML = 
                '<div style="color: #ff0000; font-size: 12px; padding: 8px;">Error loading cameras</div>';
        }
    },

    /**
     * Update cameras list UI
     */
    updateCamerasList(state) {
        const camerasList = document.getElementById('camerasList');
        
        if (state.availableCameras.length === 0) {
            camerasList.innerHTML = '<div style="color: #888; font-size: 12px; padding: 8px;">No cameras assigned to this room</div>';
            return;
        }
        
        camerasList.innerHTML = state.availableCameras.map(camera => {
            const placed = state.objects.some(obj => 
                obj.type === 'camera' && obj.cameraId === camera.id
            );
            const statusIcon = placed ? '✓' : '+';
            const statusColor = placed ? '#00ff00' : '#00ffff';
            
            return `
                <div class="camera-list-item" 
                     data-camera-id="${camera.id}"
                     style="padding: 8px; margin: 4px 0; background: #1a1a1a; 
                            border-left: 3px solid ${statusColor}; 
                            cursor: pointer; font-size: 12px;
                            transition: background 0.2s;"
                     onmouseover="this.style.background='#2a2a2a'"
                     onmouseout="this.style.background='#1a1a1a'"
                     onclick="RoomDesignerAPI.placeCameraOnCanvas(${camera.id})">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>
                            <i class="fas fa-video" style="color: #00ffff; margin-right: 6px;"></i>
                            ${camera.name}
                        </span>
                        <span style="color: ${statusColor}; font-weight: bold;">${statusIcon}</span>
                    </div>
                    ${camera.position_x !== null ? 
                        `<div style="color: #666; font-size: 10px; margin-top: 4px;">
                            Pos: (${camera.position_x}, ${camera.position_y}) | FOV: ${camera.field_of_view}°
                        </div>` : 
                        '<div style="color: #888; font-size: 10px; margin-top: 4px;">Click to place on canvas</div>'
                    }
                </div>
            `;
        }).join('');
    },

    /**
     * Place camera on canvas
     */
    placeCameraOnCanvas(cameraId) {
        const state = window.roomDesignerState;
        if (!state) return;
        
        const camera = state.availableCameras.find(c => c.id === cameraId);
        if (!camera) return;
        
        // Check if already placed
        const existingIndex = state.objects.findIndex(obj => 
            obj.type === 'camera' && obj.cameraId === cameraId
        );
        
        if (existingIndex >= 0) {
            // Select existing camera
            state.selectedObject = state.objects[existingIndex];
            state.currentTool = 'select';
            document.getElementById('statusMsg').textContent = `Selected: ${camera.name}`;
        } else {
            // Add new camera at center of viewport
            const centerWorld = RoomDesignerUtils.screenToWorld(
                state.canvas.width / 2, 
                state.canvas.height / 2, 
                state
            );
            
            const newCamera = {
                type: 'camera',
                cameraId: camera.id,
                x: Math.round(centerWorld.x),
                y: Math.round(centerWorld.y),
                angle: camera.direction || 0,
                fov: camera.field_of_view || 90,
                range: 5,
                id: camera.name
            };
            
            state.objects.push(newCamera);
            state.selectedObject = newCamera;
            state.currentTool = 'select';
            
            document.getElementById('statusMsg').textContent = 
                `Placed: ${camera.name} - drag to position`;
        }
        
        // Refresh cameras list
        this.updateCamerasList(state);
        RoomDesignerRenderer.render(state);
    },

    /**
     * Save design to server
     */
    async saveDesign(state) {
        const design = {
            roomName: document.getElementById('roomName').value || 'Unnamed Room',
            scale: state.scale,
            objects: state.objects,
            overlaps: state.detectedOverlaps || []
        };
        
        const layoutData = JSON.stringify(design);
        
        // Show saving status
        const statusMsg = document.getElementById('statusMsg');
        if (statusMsg) {
            statusMsg.textContent = '💾 Saving design...';
        }
        
        try {
            // Save room layout
            const formData = new URLSearchParams();
            formData.append('room_id', state.roomId);
            formData.append('name', design.roomName);
            formData.append('location', 'Unknown');
            formData.append('width', 10);
            formData.append('height', 8);
            formData.append('layout_data', layoutData);
            
            console.log('Saving room layout with overlaps:', design);
            
            const response = await fetch('/vault-rooms/save-layout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData.toString()
            });
            
            if (!response.ok) {
                const error = await response.text();
                throw new Error(`Server error: ${error}`);
            }
            
            // Save camera positions
            const cameraObjects = state.objects.filter(obj => obj.type === 'camera' && obj.cameraId);
            let camerasSaved = 0;
            
            for (const cameraObj of cameraObjects) {
                try {
                    console.log(`Saving camera ${cameraObj.cameraId} position:`, {
                        x: Math.round(cameraObj.x),
                        y: Math.round(cameraObj.y),
                        angle: Math.round(cameraObj.angle || 0),
                        fov: Math.round(cameraObj.fov || 90)
                    });
                    
                    const camResponse = await fetch(
                        `/vault-rooms/${state.roomId}/cameras/${cameraObj.cameraId}/position`,
                        {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                position_x: Math.round(cameraObj.x),
                                position_y: Math.round(cameraObj.y),
                                direction: Math.round(cameraObj.angle || 0),
                                field_of_view: Math.round(cameraObj.fov || 90)
                            })
                        }
                    );
                    
                    if (camResponse.ok) {
                        camerasSaved++;
                        console.log(`✓ Camera ${cameraObj.cameraId} saved successfully`);
                    } else {
                        const camError = await camResponse.text();
                        console.error(`✗ Failed to save camera ${cameraObj.cameraId}:`, camError);
                    }
                } catch (camErr) {
                    console.error(`Error saving camera ${cameraObj.cameraId}:`, camErr);
                }
            }
            
            // Show success message with overlap info
            const overlapCount = state.detectedOverlaps ? state.detectedOverlaps.length : 0;
            const successMessage = cameraObjects.length > 0
                ? `✓ Design saved! ${camerasSaved}/${cameraObjects.length} camera(s) + ${overlapCount} overlap(s)`
                : `✓ Design saved! ${overlapCount} overlap(s)`;
            
            if (statusMsg) {
                statusMsg.textContent = successMessage;
                console.log(successMessage);
                
                // Keep success message for 3 seconds
                setTimeout(() => {
                    statusMsg.textContent = 'Ready';
                }, 3000);
            }
            
        } catch (err) {
            console.error('Error saving:', err);
            const errorMsg = `✗ Error saving design: ${err.message}`;
            if (statusMsg) {
                statusMsg.textContent = errorMsg;
                statusMsg.style.color = '#ff4444';
                setTimeout(() => {
                    statusMsg.textContent = 'Ready';
                    statusMsg.style.color = 'white';
                }, 4000);
            }
            alert(errorMsg);
        }
    },

    /**
     * Export design as JSON file
     */
    exportDesign(state) {
        const design = {
            roomName: document.getElementById('roomName').value,
            scale: state.scale,
            objects: state.objects
        };
        
        const json = JSON.stringify(design, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `room-${state.roomId}-design.json`;
        a.click();
    },

    /**
     * Import design from JSON file
     */
    importDesign(state) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = (e) => {
            const file = e.target.files[0];
            const reader = new FileReader();
            reader.onload = (event) => {
                try {
                    const design = JSON.parse(event.target.result);
                    state.objects = design.objects || [];
                    state.scale = design.scale || 20;
                    document.getElementById('roomName').value = design.roomName || 'Office';
                    document.getElementById('scale').value = state.scale;
                    RoomDesignerRenderer.render(state);
                    document.getElementById('statusMsg').textContent = 'Design loaded from file!';
                    setTimeout(() => {
                        document.getElementById('statusMsg').textContent = 'Ready';
                    }, 2000);
                } catch (err) {
                    alert('Error loading design: ' + err.message);
                }
            };
            reader.readAsText(file);
        };
        input.click();
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RoomDesignerAPI;
}
