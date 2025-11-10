/**
 * Room Designer - Rendering Engine
 * Handles all canvas drawing operations
 */

const RoomDesignerRenderer = {
    /**
     * Main render function
     */
    render(state) {
        const { canvas, ctx } = state;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw grid
        if (state.showGrid) {
            this.drawGrid(state);
        }
        
        // Draw all objects respecting layer visibility
        state.objects.forEach(obj => {
            switch (obj.type) {
                case 'wall':
                    if (state.layers.walls) {
                        this.drawWall(obj, state);
                    }
                    break;
                case 'camera':
                    if (state.layers.cameras) {
                        this.drawCamera(obj, state);
                    }
                    break;
                case 'zone':
                    if (state.layers.zones) {
                        this.drawZone(obj, state);
                    }
                    break;
            }
        });

        // Detect and draw overlapping zones
        if (state.layers.zones) {
            const overlaps = RoomDesignerUtils.detectZoneOverlaps(state.objects);
            overlaps.forEach(overlap => {
                this.drawOverlap(overlap, state);
            });
            // Store overlaps in state for saving
            state.detectedOverlaps = overlaps;
        }

        
        // Draw temp points for zone creation
        if (state.tempPoints && state.tempPoints.length > 0) {
            this.drawTempZone(state.tempPoints, state);
        }
        
        // Highlight selected object
        if (state.selectedObject) {
            this.highlightObject(state.selectedObject, state);
        }
        
        // Draw angle adjustment indicator
        if (state.isAdjustingAngle && state.selectedObject && state.selectedObject.type === 'camera') {
            this.drawAngleAdjustment(state.selectedObject, state);
        }
    },

    /**
     * Draw grid
     */
    drawGrid(state) {
        const { ctx, canvas, gridSize, scale, zoom, panOffset } = state;
        
        ctx.save();
        ctx.strokeStyle = '#1a1a1a';
        ctx.lineWidth = 1;
        
        const gridPixels = gridSize * scale * zoom;
        const startX = panOffset.x % gridPixels;
        const startY = panOffset.y % gridPixels;
        
        // Vertical lines
        for (let x = startX; x < canvas.width; x += gridPixels) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, canvas.height);
            ctx.stroke();
        }
        
        // Horizontal lines
        for (let y = startY; y < canvas.height; y += gridPixels) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
            ctx.stroke();
        }
        
        // Draw origin
        const originX = panOffset.x;
        const originY = panOffset.y;
        
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(originX - 10, originY);
        ctx.lineTo(originX + 10, originY);
        ctx.moveTo(originX, originY - 10);
        ctx.lineTo(originX, originY + 10);
        ctx.stroke();
        
        ctx.restore();
    },

    /**
     * Draw wall
     */
    drawWall(wall, state) {
        const { ctx } = state;
        const start = RoomDesignerUtils.worldToScreen(wall.start.x, wall.start.y, state);
        const end = RoomDesignerUtils.worldToScreen(wall.end.x, wall.end.y, state);
        
        ctx.save();
        ctx.strokeStyle = wall.color || '#ffffff';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
        
        // Calculate wall length in meters
        const dx = wall.end.x - wall.start.x;
        const dy = wall.end.y - wall.start.y;
        const lengthMeters = Math.sqrt(dx * dx + dy * dy);
        
        // Draw measurement label at midpoint
        const midX = (start.x + end.x) / 2;
        const midY = (start.y + end.y) / 2;
        
        // Calculate angle for text rotation
        const angle = Math.atan2(end.y - start.y, end.x - start.x);
        
        // Draw measurement background
        ctx.fillStyle = 'rgba(59, 130, 246, 0.95)';
        const labelWidth = 70;
        const labelHeight = 24;
        
        ctx.save();
        ctx.translate(midX, midY);
        ctx.rotate(angle);
        ctx.fillRect(-labelWidth / 2, -labelHeight / 2 - 15, labelWidth, labelHeight);
        
        // Draw measurement text
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 13px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${lengthMeters.toFixed(2)} m`, 0, -15);
        ctx.restore();
        
        ctx.restore();
    },

    /**
     * Draw camera
     */
    drawCamera(camera, state) {
        const { ctx } = state;
        const pos = RoomDesignerUtils.worldToScreen(camera.x, camera.y, state);
        
        ctx.save();
        
        // Draw FOV cone
        if (camera.fov && camera.range) {
            const angleRad = (camera.angle || 0) * Math.PI / 180;
            const fovRad = (camera.fov || 90) * Math.PI / 180;
            const range = camera.range * state.scale * state.zoom;
            
            ctx.fillStyle = 'rgba(0, 255, 255, 0.1)';
            ctx.strokeStyle = '#00ffff';
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 5]);
            
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
            ctx.arc(pos.x, pos.y, range, 
                angleRad - fovRad / 2, 
                angleRad + fovRad / 2);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
            ctx.setLineDash([]);
        }
        
        // Draw camera icon
        ctx.fillStyle = '#00ffff';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        
        // Draw camera label
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(camera.id || '?', pos.x, pos.y + 25);
        
        ctx.restore();
    },

    /**
     * Draw zone
     */
    drawZone(zone, state) {
        const { ctx } = state;
        
        if (!zone.points || zone.points.length < 2) return;
        
        // Check if this zone is involved in any overlap
        const isInOverlap = state.detectedOverlaps && state.detectedOverlaps.some(overlap => 
            overlap.zone1Id === zone.id || overlap.zone2Id === zone.id
        );
        
        ctx.save();
        
        // Different colors for overlapping vs normal zones
        if (isInOverlap) {
            // Overlapping zones: RED/ORANGE color
            ctx.fillStyle = 'rgba(255, 100, 0, 0.2)';    // Orange semi-transparent
            ctx.strokeStyle = '#ff6400';                  // Orange
        } else {
            // Normal zones: MAGENTA color
            ctx.fillStyle = 'rgba(255, 0, 255, 0.15)';   // Magenta semi-transparent
            ctx.strokeStyle = '#ff00ff';                  // Magenta
        }
        
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 4]);
        
        ctx.beginPath();
        const first = RoomDesignerUtils.worldToScreen(zone.points[0].x, zone.points[0].y, state);
        ctx.moveTo(first.x, first.y);
        
        for (let i = 1; i < zone.points.length; i++) {
            const point = RoomDesignerUtils.worldToScreen(zone.points[i].x, zone.points[i].y, state);
            ctx.lineTo(point.x, point.y);
        }
        
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        ctx.setLineDash([]);
        
        ctx.restore();
    },

    /**
     * Draw temporary zone points (while creating)
     */
    drawTempZone(tempPoints, state) {
        const { ctx } = state;
        
        if (!tempPoints || tempPoints.length === 0) return;
        
        ctx.save();
        
        // Draw lines connecting points
        if (tempPoints.length > 1) {
            ctx.strokeStyle = '#ff00ff';
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 4]);
            
            ctx.beginPath();
            const first = RoomDesignerUtils.worldToScreen(tempPoints[0].x, tempPoints[0].y, state);
            ctx.moveTo(first.x, first.y);
            
            for (let i = 1; i < tempPoints.length; i++) {
                const point = RoomDesignerUtils.worldToScreen(tempPoints[i].x, tempPoints[i].y, state);
                ctx.lineTo(point.x, point.y);
            }
            
            ctx.stroke();
            ctx.setLineDash([]);
        }
        
        // Draw points as circles
        tempPoints.forEach((p, index) => {
            const screen = RoomDesignerUtils.worldToScreen(p.x, p.y, state);
            
            // Point circle
            ctx.fillStyle = '#ff00ff';
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(screen.x, screen.y, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
            
            // Point number
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 11px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(index + 1, screen.x, screen.y - 12);
        });
        
        // Draw closing line preview (from last point to first)
        if (tempPoints.length >= 3) {
            ctx.strokeStyle = 'rgba(255, 0, 255, 0.4)';
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 2]);
            
            const first = RoomDesignerUtils.worldToScreen(tempPoints[0].x, tempPoints[0].y, state);
            const last = RoomDesignerUtils.worldToScreen(
                tempPoints[tempPoints.length - 1].x, 
                tempPoints[tempPoints.length - 1].y, 
                state
            );
            
            ctx.beginPath();
            ctx.moveTo(last.x, last.y);
            ctx.lineTo(first.x, first.y);
            ctx.stroke();
            ctx.setLineDash([]);
            
            // Show "Press Enter to finish" message
            ctx.fillStyle = 'rgba(255, 0, 255, 0.9)';
            ctx.fillRect(first.x - 80, first.y - 40, 160, 24);
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Press ENTER to finish', first.x, first.y - 22);
        }
        
        ctx.restore();
    },

    /**
     * Highlight selected object
     */
    highlightObject(obj, state) {
        const { ctx } = state;
        
        ctx.save();
        ctx.strokeStyle = '#ffff00';
        ctx.lineWidth = 3;
        ctx.setLineDash([5, 5]);
        
        if (obj.type === 'wall') {
            const start = RoomDesignerUtils.worldToScreen(obj.start.x, obj.start.y, state);
            const end = RoomDesignerUtils.worldToScreen(obj.end.x, obj.end.y, state);
            ctx.beginPath();
            ctx.moveTo(start.x, start.y);
            ctx.lineTo(end.x, end.y);
            ctx.stroke();
        } else if (obj.type === 'camera') {
            const pos = RoomDesignerUtils.worldToScreen(obj.x, obj.y, state);
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 12, 0, Math.PI * 2);
            ctx.stroke();
        } else if (obj.type === 'zone' && obj.points) {
            ctx.beginPath();
            const first = RoomDesignerUtils.worldToScreen(obj.points[0].x, obj.points[0].y, state);
            ctx.moveTo(first.x, first.y);
            for (let i = 1; i < obj.points.length; i++) {
                const point = RoomDesignerUtils.worldToScreen(obj.points[i].x, obj.points[i].y, state);
                ctx.lineTo(point.x, point.y);
            }
            ctx.closePath();
            ctx.stroke();
        }
        
        ctx.setLineDash([]);
        ctx.restore();
    },

    /**
     * Draw angle adjustment indicator
     */
    drawAngleAdjustment(camera, state) {
        const { ctx } = state;
        const pos = RoomDesignerUtils.worldToScreen(camera.x, camera.y, state);
        
        ctx.save();
        
        // Draw angle line from camera center
        const angleRad = (camera.angle || 0) * Math.PI / 180;
        const lineLength = 100; // pixels
        const endX = pos.x + Math.cos(angleRad) * lineLength;
        const endY = pos.y + Math.sin(angleRad) * lineLength;
        
        // Angle line
        ctx.strokeStyle = '#ffff00';
        ctx.lineWidth = 3;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
        ctx.lineTo(endX, endY);
        ctx.stroke();
        
        // Arrow head
        const arrowSize = 12;
        ctx.fillStyle = '#ffff00';
        ctx.beginPath();
        ctx.moveTo(endX, endY);
        ctx.lineTo(
            endX - arrowSize * Math.cos(angleRad - Math.PI / 6),
            endY - arrowSize * Math.sin(angleRad - Math.PI / 6)
        );
        ctx.lineTo(
            endX - arrowSize * Math.cos(angleRad + Math.PI / 6),
            endY - arrowSize * Math.sin(angleRad + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fill();
        
        // Draw angle arc
        ctx.strokeStyle = 'rgba(255, 255, 0, 0.5)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 40, 0, angleRad, angleRad < 0);
        ctx.stroke();
        
        // Display angle text
        ctx.fillStyle = '#ffff00';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`${Math.round(camera.angle)}°`, pos.x, pos.y - 50);
        
        ctx.restore();
    },

    /**
     * Draw overlapping zone areas
     */
    drawOverlap(overlap, state) {
        const { ctx } = state;
        
        ctx.save();
        
        // Draw filled overlap area with semi-transparent purple
        ctx.fillStyle = 'rgba(200, 0, 255, 0.3)';
        ctx.strokeStyle = '#dd00ff';
        ctx.lineWidth = 2;
        
        if (overlap.points && overlap.points.length >= 3) {
            ctx.beginPath();
            const first = RoomDesignerUtils.worldToScreen(overlap.points[0].x, overlap.points[0].y, state);
            ctx.moveTo(first.x, first.y);
            
            for (let i = 1; i < overlap.points.length; i++) {
                const point = RoomDesignerUtils.worldToScreen(overlap.points[i].x, overlap.points[i].y, state);
                ctx.lineTo(point.x, point.y);
            }
            
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
            
            // Draw vertices as small dots
            overlap.points.forEach(p => {
                const screen = RoomDesignerUtils.worldToScreen(p.x, p.y, state);
                ctx.fillStyle = '#dd00ff';
                ctx.beginPath();
                ctx.arc(screen.x, screen.y, 3, 0, Math.PI * 2);
                ctx.fill();
            });
            
            // Display overlap area info
            const centroid = {
                x: overlap.points.reduce((sum, p) => sum + p.x, 0) / overlap.points.length,
                y: overlap.points.reduce((sum, p) => sum + p.y, 0) / overlap.points.length
            };
            const centroidScreen = RoomDesignerUtils.worldToScreen(centroid.x, centroid.y, state);
            
            ctx.fillStyle = '#dd00ff';
            ctx.font = 'bold 11px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(`${overlap.area.toFixed(2)} m²`, centroidScreen.x, centroidScreen.y);
        }
        
        ctx.restore();
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RoomDesignerRenderer;
}
