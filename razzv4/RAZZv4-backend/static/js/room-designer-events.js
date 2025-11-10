/**
 * Room Designer - Event Handlers
 * Handles all user interactions
 */

const RoomDesignerEvents = {
    /**
     * Initialize all event listeners
     */
    init(state) {
        this.initCanvasEvents(state);
        this.initToolButtons(state);
        this.initPropertyHandlers(state);
        this.initKeyboardShortcuts(state);
    },

    /**
     * Canvas mouse events
     */
    initCanvasEvents(state) {
        const { canvas } = state;
        
        if (!canvas) {
            console.error('Canvas not available for event binding');
            return;
        }

        console.log('Binding canvas events to:', canvas);

        // Mouse down
        canvas.addEventListener('mousedown', (e) => {
            try {
                const rect = canvas.getBoundingClientRect();
                const screenX = e.clientX - rect.left;
                const screenY = e.clientY - rect.top;
                const worldPos = RoomDesignerUtils.screenToWorld(screenX, screenY, state);
                let snappedPos = RoomDesignerUtils.snapPoint(worldPos, state);
                
                // Try to snap to nearby objects if enabled
                if (state.snapToObjects) {
                    const objectSnap = RoomDesignerUtils.snapToNearbyObjects(snappedPos, state.objects, 0.5);
                    if (objectSnap) {
                        snappedPos = objectSnap;
                        console.log('Snapped to object:', objectSnap.type);
                    }
                }
                
                console.log('Mousedown - Tool:', state.currentTool, 'Position:', snappedPos);
                
                if (state.currentTool === 'pan') {
                    state.isPanning = true;
                    state.lastPanPoint = { x: e.clientX, y: e.clientY };
                    canvas.style.cursor = 'grabbing';
                    return;
                }
                
                if (state.currentTool === 'wall') {
                    if (!state.startPoint) {
                        state.startPoint = snappedPos;
                        state.dragStartPoint = snappedPos;  // Track for orthogonal mode
                        console.log('Wall start point set:', state.startPoint);
                    } else {
                        // Apply orthogonal mode if enabled
                        let endPoint = snappedPos;
                        if (state.orthoMode) {
                            endPoint = RoomDesignerUtils.enforceOrthogonalWall(state.startPoint, snappedPos);
                            console.log('Orthogonal wall enforced');
                        }
                        
                        state.objects.push({
                            type: 'wall',
                            start: state.startPoint,
                            end: endPoint,
                            color: '#ffffff'
                        });
                        console.log('Wall created:', state.objects[state.objects.length - 1]);
                        state.startPoint = null;
                        state.dragStartPoint = null;
                        state.saveToHistory();
                        RoomDesignerRenderer.render(state);
                    }
                } else if (state.currentTool === 'camera') {
                    // Show camera picker dialog
                    this.showCameraPicker(snappedPos, state);
                } else if (state.currentTool === 'zone') {
                    // Check if clicking on a camera to adjust its angle
                    const clickedCamera = state.objects.find(obj => {
                        if (obj.type !== 'camera') return false;
                        const dist = Math.sqrt(
                            Math.pow(obj.x - snappedPos.x, 2) + 
                            Math.pow(obj.y - snappedPos.y, 2)
                        );
                        return dist < 1; // 1 meter tolerance
                    });
                    
                    if (clickedCamera) {
                        // Start adjusting camera angle
                        state.selectedObject = clickedCamera;
                        state.isDragging = false;
                        state.isAdjustingAngle = true;
                        document.getElementById('statusMsg').textContent = 'Drag to adjust camera angle';
                    } else {
                        // Regular zone point placement
                        state.tempPoints.push(snappedPos);
                        console.log('Zone point added:', snappedPos);
                    }
                    RoomDesignerRenderer.render(state);
                } else if (state.currentTool === 'select') {
                    // Find and select object
                    state.selectedObject = RoomDesignerUtils.findObjectAt(snappedPos, state.objects);
                    
                    console.log('Select tool - Found object:', state.selectedObject);
                    
                    if (state.selectedObject) {
                        state.isDragging = true;
                        
                        // Store drag offset
                        if (state.selectedObject.type === 'camera') {
                            state.dragOffset.x = snappedPos.x - state.selectedObject.x;
                            state.dragOffset.y = snappedPos.y - state.selectedObject.y;
                        } else if (state.selectedObject.type === 'wall') {
                            state.dragOffset.x = snappedPos.x;
                            state.dragOffset.y = snappedPos.y;
                            state.selectedObject.originalStart = { ...state.selectedObject.start };
                            state.selectedObject.originalEnd = { ...state.selectedObject.end };
                        } else if (state.selectedObject.type === 'zone') {
                            state.dragOffset.x = snappedPos.x;
                            state.dragOffset.y = snappedPos.y;
                            state.selectedObject.originalPoints = state.selectedObject.points.map(p => ({ ...p }));
                        }
                        
                        canvas.style.cursor = 'move';
                    }
                    
                    RoomDesignerProperties.showProperties(state.selectedObject, state);
                    RoomDesignerRenderer.render(state);
                }
            } catch (err) {
                console.error('Error in mousedown handler:', err);
            }
        });

        // Mouse move
        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            const screenX = e.clientX - rect.left;
            const screenY = e.clientY - rect.top;
            const worldPos = RoomDesignerUtils.screenToWorld(screenX, screenY, state);
            let snappedPos = RoomDesignerUtils.snapPoint(worldPos, state);
            
            // Try to snap to nearby objects if enabled
            if (state.snapToObjects) {
                const objectSnap = RoomDesignerUtils.snapToNearbyObjects(snappedPos, state.objects, 0.5);
                if (objectSnap) {
                    snappedPos = objectSnap;
                }
            }
            
            // Update coordinates display
            document.getElementById('coords').textContent = 
                `X: ${snappedPos.x.toFixed(2)}m, Y: ${snappedPos.y.toFixed(2)}m`;
            
            // Panning
            if (state.isPanning && state.lastPanPoint) {
                const dx = e.clientX - state.lastPanPoint.x;
                const dy = e.clientY - state.lastPanPoint.y;
                state.panOffset.x += dx;
                state.panOffset.y += dy;
                state.lastPanPoint = { x: e.clientX, y: e.clientY };
                RoomDesignerRenderer.render(state);
            }
            
            // Adjusting camera angle (in zone mode)
            if (state.isAdjustingAngle && state.selectedObject && state.selectedObject.type === 'camera') {
                // Calculate angle from camera position to mouse position
                const dx = worldPos.x - state.selectedObject.x;
                const dy = worldPos.y - state.selectedObject.y;
                const angleRadians = Math.atan2(dy, dx);
                const angleDegrees = angleRadians * (180 / Math.PI);
                
                // Update camera angle
                state.selectedObject.angle = angleDegrees;
                
                // Update status with current angle
                document.getElementById('statusMsg').textContent = 
                    `Adjusting camera angle: ${Math.round(angleDegrees)}°`;
                
                RoomDesignerRenderer.render(state);
            }
            
            // Dragging objects
            if (state.isDragging && state.selectedObject) {
                if (state.selectedObject.type === 'camera') {
                    state.selectedObject.x = snappedPos.x - state.dragOffset.x;
                    state.selectedObject.y = snappedPos.y - state.dragOffset.y;
                } else if (state.selectedObject.type === 'wall' && state.selectedObject.originalStart) {
                    const dx = snappedPos.x - state.dragOffset.x;
                    const dy = snappedPos.y - state.dragOffset.y;
                    state.selectedObject.start.x = state.selectedObject.originalStart.x + dx;
                    state.selectedObject.start.y = state.selectedObject.originalStart.y + dy;
                    state.selectedObject.end.x = state.selectedObject.originalEnd.x + dx;
                    state.selectedObject.end.y = state.selectedObject.originalEnd.y + dy;
                } else if (state.selectedObject.type === 'zone' && state.selectedObject.originalPoints) {
                    const dx = snappedPos.x - state.dragOffset.x;
                    const dy = snappedPos.y - state.dragOffset.y;
                    state.selectedObject.points = state.selectedObject.originalPoints.map(p => ({
                        x: p.x + dx,
                        y: p.y + dy
                    }));
                }
                RoomDesignerRenderer.render(state);
            }
            
            // Preview for wall drawing
            if (state.startPoint && state.currentTool === 'wall') {
                RoomDesignerRenderer.render(state);
                
                // Apply orthogonal mode to preview if enabled
                let previewEnd = snappedPos;
                if (state.orthoMode) {
                    previewEnd = RoomDesignerUtils.enforceOrthogonalWall(state.startPoint, snappedPos);
                }
                
                const start = RoomDesignerUtils.worldToScreen(state.startPoint.x, state.startPoint.y, state);
                const end = RoomDesignerUtils.worldToScreen(previewEnd.x, previewEnd.y, state);
                state.ctx.strokeStyle = state.orthoMode ? '#00ff00' : '#ffffff';  // Green if ortho mode
                state.ctx.lineWidth = 4;
                state.ctx.setLineDash([5, 5]);
                state.ctx.beginPath();
                state.ctx.moveTo(start.x, start.y);
                state.ctx.lineTo(end.x, end.y);
                state.ctx.stroke();
                state.ctx.setLineDash([]);
                
                // Calculate and display live measurement
                const dx = previewEnd.x - state.startPoint.x;
                const dy = previewEnd.y - state.startPoint.y;
                const lengthMeters = Math.sqrt(dx * dx + dy * dy);
                
                // Draw measurement label at midpoint
                const midX = (start.x + end.x) / 2;
                const midY = (start.y + end.y) / 2;
                
                // Calculate angle for text rotation
                const angle = Math.atan2(end.y - start.y, end.x - start.x);
                
                // Draw measurement background
                state.ctx.fillStyle = 'rgba(59, 130, 246, 0.95)';
                const labelWidth = 70;
                const labelHeight = 24;
                
                state.ctx.save();
                state.ctx.translate(midX, midY);
                state.ctx.rotate(angle);
                state.ctx.fillRect(-labelWidth / 2, -labelHeight / 2 - 15, labelWidth, labelHeight);
                
                // Draw measurement text
                state.ctx.fillStyle = '#ffffff';
                state.ctx.font = 'bold 13px Arial';
                state.ctx.textAlign = 'center';
                state.ctx.textBaseline = 'middle';
                state.ctx.fillText(`${lengthMeters.toFixed(2)} m`, 0, -15);
                state.ctx.restore();
            }
        });

        // Mouse up
        canvas.addEventListener('mouseup', () => {
            if (state.isPanning) {
                state.isPanning = false;
                canvas.style.cursor = 'grab';
            }
            
            if (state.isAdjustingAngle) {
                state.isAdjustingAngle = false;
                canvas.style.cursor = 'crosshair';
                
                if (state.selectedObject && state.selectedObject.type === 'camera') {
                    const finalAngle = Math.round(state.selectedObject.angle);
                    document.getElementById('statusMsg').textContent = 
                        `Camera angle set to ${finalAngle}°. Click camera to adjust again or add zone points.`;
                    
                    // Update properties panel if it's showing camera properties
                    RoomDesignerProperties.showProperties(state.selectedObject, state);
                }
                
                state.selectedObject = null;
            }
            
            if (state.isDragging) {
                state.isDragging = false;
                canvas.style.cursor = 'default';
                
                // Cleanup and save to history after dragging
                if (state.selectedObject) {
                    delete state.selectedObject.originalStart;
                    delete state.selectedObject.originalEnd;
                    delete state.selectedObject.originalPoints;
                    
                    // Save to history after object moved
                    state.saveToHistory();
                    
                    RoomDesignerProperties.showProperties(state.selectedObject, state);
                }
            }
        });

        // Mouse wheel for zoom
        canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            state.zoom = Math.max(0.1, Math.min(5, state.zoom * delta));
            RoomDesignerRenderer.render(state);
        });
    },

    /**
     * Tool button events
     */
    initToolButtons(state) {
        document.querySelectorAll('[data-tool]').forEach(button => {
            button.addEventListener('click', () => {
                state.currentTool = button.dataset.tool;
                document.querySelectorAll('[data-tool]').forEach(b => b.classList.remove('active'));
                button.classList.add('active');
                
                // Update cursor based on tool
                if (state.currentTool === 'pan') {
                    state.canvas.style.cursor = 'grab';
                } else if (state.currentTool === 'zone') {
                    state.canvas.style.cursor = 'crosshair';
                    document.getElementById('statusMsg').textContent = 'Zone Mode: Click camera to adjust angle, or click empty area to add zone points. Press ENTER to finish zone.';
                } else if (state.currentTool === 'wall') {
                    state.canvas.style.cursor = 'crosshair';
                    document.getElementById('statusMsg').textContent = 'Wall Mode: Click twice to draw a wall';
                } else if (state.currentTool === 'camera') {
                    state.canvas.style.cursor = 'crosshair';
                    document.getElementById('statusMsg').textContent = '📷 Camera Mode: Click on canvas to select camera, or click camera from list →';
                } else {
                    state.canvas.style.cursor = 'default';
                    document.getElementById('statusMsg').textContent = 'Ready';
                }
            });
        });
    },

    /**
     * Property panel handlers
     */
    initPropertyHandlers(state) {
        // Grid toggle
        const gridToggleBtn = document.getElementById('gridToggle');
        if (gridToggleBtn) {
            gridToggleBtn.addEventListener('click', () => {
                state.showGrid = !state.showGrid;
                gridToggleBtn.classList.toggle('active', state.showGrid);
                RoomDesignerRenderer.render(state);
                const statusMsg = document.getElementById('statusMsg');
                if (statusMsg) {
                    statusMsg.textContent = state.showGrid ? 'Grid shown' : 'Grid hidden';
                }
            });
        }

        // Snap toggles
        const snapGridBtn = document.getElementById('snapGrid');
        if (snapGridBtn) {
            snapGridBtn.addEventListener('click', () => {
                state.snapToGrid = !state.snapToGrid;
                snapGridBtn.classList.toggle('active', state.snapToGrid);
                const statusMsg = document.getElementById('statusMsg');
                if (statusMsg) {
                    statusMsg.textContent = state.snapToGrid ? 'Snap to grid enabled' : 'Snap to grid disabled';
                }
            });
        }

        const orthoModeBtn = document.getElementById('orthoMode');
        if (orthoModeBtn) {
            orthoModeBtn.addEventListener('click', () => {
                state.orthoMode = !state.orthoMode;
                orthoModeBtn.classList.toggle('active', state.orthoMode);
                const statusMsg = document.getElementById('statusMsg');
                if (statusMsg) {
                    statusMsg.textContent = state.orthoMode ? 'Orthogonal mode enabled' : 'Orthogonal mode disabled';
                }
            });
        }

        const snapObjectBtn = document.getElementById('snapObject');
        if (snapObjectBtn) {
            snapObjectBtn.addEventListener('click', () => {
                state.snapToObjects = !state.snapToObjects;
                snapObjectBtn.classList.toggle('active', state.snapToObjects);
                const statusMsg = document.getElementById('statusMsg');
                if (statusMsg) {
                    statusMsg.textContent = state.snapToObjects ? 
                        '🧲 Snap to objects enabled - objects will snap to nearby edges and centers' : 
                        'Snap to objects disabled';
                }
            });
        }

        // Delete object
        const deleteBtn = document.getElementById('deleteObj');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                if (state.selectedObject) {
                    const index = state.objects.indexOf(state.selectedObject);
                    if (index > -1) {
                        state.objects.splice(index, 1);
                        state.selectedObject = null;
                        RoomDesignerProperties.hideProperties();
                        RoomDesignerRenderer.render(state);
                        const statusMsg = document.getElementById('statusMsg');
                        if (statusMsg) {
                            statusMsg.textContent = 'Object deleted';
                        }
                    }
                }
            });
        }
    },

    /**
     * Keyboard shortcuts
     */
    initKeyboardShortcuts(state) {
        document.addEventListener('keydown', (e) => {
            // Undo - Ctrl+Z or Cmd+Z
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                if (state.undo()) {
                    RoomDesignerProperties.hideProperties();
                    RoomDesignerRenderer.render(state);
                    const statusMsg = document.getElementById('statusMsg');
                    if (statusMsg) {
                        statusMsg.textContent = '↶ Undo';
                        setTimeout(() => statusMsg.textContent = 'Ready', 1500);
                    }
                }
                return;
            }
            
            // Redo - Ctrl+Shift+Z or Ctrl+Y
            if ((e.ctrlKey || e.metaKey) && (e.shiftKey && e.key === 'z' || e.key === 'y')) {
                e.preventDefault();
                if (state.redo()) {
                    RoomDesignerProperties.hideProperties();
                    RoomDesignerRenderer.render(state);
                    const statusMsg = document.getElementById('statusMsg');
                    if (statusMsg) {
                        statusMsg.textContent = '↷ Redo';
                        setTimeout(() => statusMsg.textContent = 'Ready', 1500);
                    }
                }
                return;
            }
            
            // Backspace - undo last zone point while drawing
            if (e.key === 'Backspace' && state.currentTool === 'zone' && state.tempPoints.length > 0) {
                e.preventDefault();
                state.tempPoints.pop();
                RoomDesignerRenderer.render(state);
                const statusMsg = document.getElementById('statusMsg');
                if (statusMsg) {
                    statusMsg.textContent = `Removed last point (${state.tempPoints.length} points remaining)`;
                }
                return;
            }
            
            // Enter - finish zone
            if (e.key === 'Enter' && state.currentTool === 'zone' && state.tempPoints.length >= 3) {
                const zoneCount = state.objects.filter(o => o.type === 'zone').length + 1;
                state.objects.push({
                    type: 'zone',
                    id: 'zone' + zoneCount,
                    points: state.tempPoints,
                    name: 'Zone ' + zoneCount
                });
                state.tempPoints = [];
                state.saveToHistory();
                RoomDesignerRenderer.render(state);
                const statusMsg = document.getElementById('statusMsg');
                if (statusMsg) {
                    statusMsg.textContent = `Zone ${zoneCount} created`;
                }
            } 
            // Escape - cancel current action or deselect
            else if (e.key === 'Escape') {
                if (state.tempPoints.length > 0) {
                    // Cancel zone drawing
                    state.tempPoints = [];
                    const statusMsg = document.getElementById('statusMsg');
                    if (statusMsg) {
                        statusMsg.textContent = 'Zone creation cancelled';
                    }
                } else if (state.selectedObject) {
                    // Deselect object
                    state.selectedObject = null;
                    RoomDesignerProperties.hideProperties();
                    const statusMsg = document.getElementById('statusMsg');
                    if (statusMsg) {
                        statusMsg.textContent = 'Selection cleared';
                    }
                } else {
                    // Return to select tool
                    state.currentTool = 'select';
                    state.startPoint = null;
                    document.querySelectorAll('[data-tool]').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('[data-tool="select"]').forEach(b => b.classList.add('active'));
                }
                RoomDesignerRenderer.render(state);
            }
            // Delete or Backspace - remove selected object
            else if ((e.key === 'Delete' || e.key === 'Backspace') && state.selectedObject && state.currentTool !== 'zone') {
                e.preventDefault();
                const index = state.objects.indexOf(state.selectedObject);
                if (index > -1) {
                    const objType = state.selectedObject.type;
                    const objName = state.selectedObject.name || state.selectedObject.id || objType;
                    state.objects.splice(index, 1);
                    state.selectedObject = null;
                    state.saveToHistory();
                    RoomDesignerProperties.hideProperties();
                    RoomDesignerRenderer.render(state);
                    const statusMsg = document.getElementById('statusMsg');
                    if (statusMsg) {
                        statusMsg.textContent = `Deleted ${objName}`;
                    }
                }
            }
        });
    },

    /**
     * Show camera picker dialog to select from available cameras
     */
    showCameraPicker(position, state) {
        const availableCameras = state.availableCameras || [];
        
        // Filter out cameras that are already placed
        const placedCameraIds = state.objects
            .filter(obj => obj.type === 'camera' && obj.cameraId)
            .map(obj => obj.cameraId);
        
        const unplacedCameras = availableCameras.filter(
            cam => !placedCameraIds.includes(cam.id)
        );
        
        if (unplacedCameras.length === 0) {
            alert('All cameras have been placed on the canvas. Use the camera list in the properties panel to select and position cameras.');
            return;
        }
        
        // Create camera selection dialog
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #2d2d2d;
            border: 2px solid #0078d7;
            border-radius: 8px;
            padding: 20px;
            min-width: 350px;
            max-width: 500px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8);
            z-index: 10000;
            color: white;
        `;
        
        dialog.innerHTML = `
            <div style="margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px 0; color: #0078d7; font-size: 16px;">
                    <i class="fas fa-video"></i> Select Camera to Place
                </h3>
                <p style="margin: 0; font-size: 13px; color: #999;">
                    Choose a camera from the list below:
                </p>
            </div>
            
            <div style="max-height: 300px; overflow-y: auto; margin-bottom: 15px;">
                ${unplacedCameras.map(camera => `
                    <div class="camera-picker-item" data-camera-id="${camera.id}" 
                         style="padding: 12px; margin: 8px 0; background: #1a1a1a; 
                                border: 2px solid #4a4a4a; border-radius: 4px; 
                                cursor: pointer; transition: all 0.2s;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <i class="fas fa-video" style="color: #00ffff; font-size: 20px;"></i>
                            <div style="flex: 1;">
                                <div style="font-weight: bold; font-size: 14px;">${camera.name}</div>
                                <div style="font-size: 11px; color: #888; margin-top: 4px;">
                                    FOV: ${camera.field_of_view}° | Direction: ${camera.direction}°
                                </div>
                            </div>
                            <i class="fas fa-chevron-right" style="color: #666;"></i>
                        </div>
                    </div>
                `).join('')}
            </div>
            
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button id="cameraPickerCancel" style="padding: 8px 16px; background: #666; 
                        border: none; border-radius: 4px; color: white; cursor: pointer; 
                        font-weight: 600; font-size: 12px;">
                    <i class="fas fa-times"></i> Cancel
                </button>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        // Add hover effects
        const items = dialog.querySelectorAll('.camera-picker-item');
        items.forEach(item => {
            item.addEventListener('mouseenter', () => {
                item.style.background = '#2a2a2a';
                item.style.borderColor = '#0078d7';
            });
            item.addEventListener('mouseleave', () => {
                item.style.background = '#1a1a1a';
                item.style.borderColor = '#4a4a4a';
            });
            item.addEventListener('click', () => {
                const cameraId = parseInt(item.dataset.cameraId);
                const camera = availableCameras.find(c => c.id === cameraId);
                
                if (camera) {
                    // Place camera at clicked position
                    state.objects.push({
                        type: 'camera',
                        cameraId: camera.id,
                        x: position.x,
                        y: position.y,
                        angle: camera.direction || 0,
                        fov: camera.field_of_view || 90,
                        range: 5,
                        id: camera.name
                    });
                    
                    state.saveToHistory();
                    RoomDesignerRenderer.render(state);
                    RoomDesignerAPI.updateCamerasList(state);
                    
                    document.getElementById('statusMsg').textContent = 
                        `Placed: ${camera.name}`;
                }
                
                dialog.remove();
            });
        });
        
        // Cancel button
        document.getElementById('cameraPickerCancel').addEventListener('click', () => {
            dialog.remove();
            document.getElementById('statusMsg').textContent = 'Camera placement cancelled';
        });
        
        // Close on ESC key
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                dialog.remove();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RoomDesignerEvents;
}
