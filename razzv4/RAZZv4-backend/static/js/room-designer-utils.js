/**
 * Room Designer - Utility Functions
 * Coordinate transformations and geometry calculations
 */

const RoomDesignerUtils = {
    /**
     * Convert world coordinates to screen coordinates
     */
    worldToScreen(worldX, worldY, state) {
        return {
            x: worldX * state.scale * state.zoom + state.panOffset.x,
            y: worldY * state.scale * state.zoom + state.panOffset.y
        };
    },

    /**
     * Convert screen coordinates to world coordinates
     */
    screenToWorld(screenX, screenY, state) {
        return {
            x: (screenX - state.panOffset.x) / (state.scale * state.zoom),
            y: (screenY - state.panOffset.y) / (state.scale * state.zoom)
        };
    },

    /**
     * Snap point to grid if enabled
     */
    snapPoint(point, state) {
        let snappedPoint = point;
        
        // Grid snapping
        if (state.snapToGrid) {
            const snapSize = state.gridSize;
            snappedPoint = {
                x: Math.round(point.x / snapSize) * snapSize,
                y: Math.round(point.y / snapSize) * snapSize
            };
        }
        
        // Orthogonal snapping (force horizontal or vertical movement)
        if (state.orthoMode && state.dragStartPoint) {
            const dx = Math.abs(snappedPoint.x - state.dragStartPoint.x);
            const dy = Math.abs(snappedPoint.y - state.dragStartPoint.y);
            
            // Move more horizontally than vertically = snap to horizontal
            if (dx > dy) {
                snappedPoint.y = state.dragStartPoint.y;
            } else {
                // Move more vertically than horizontally = snap to vertical
                snappedPoint.x = state.dragStartPoint.x;
            }
        }
        
        return snappedPoint;
    },

    /**
     * Snap point to nearby objects (edges and centers)
     */
    snapToNearbyObjects(point, objects, threshold = 0.5) {
        let closestSnap = null;
        let closestDistance = threshold;

        objects.forEach(obj => {
            if (obj.type === 'camera') {
                // Snap to camera center
                const dist = Math.sqrt(
                    Math.pow(point.x - obj.x, 2) + 
                    Math.pow(point.y - obj.y, 2)
                );
                if (dist < closestDistance) {
                    closestDistance = dist;
                    closestSnap = { x: obj.x, y: obj.y, type: 'camera-center' };
                }
            } else if (obj.type === 'wall') {
                // Snap to wall start/end points
                const distStart = Math.sqrt(
                    Math.pow(point.x - obj.start.x, 2) + 
                    Math.pow(point.y - obj.start.y, 2)
                );
                if (distStart < closestDistance) {
                    closestDistance = distStart;
                    closestSnap = { x: obj.start.x, y: obj.start.y, type: 'wall-point' };
                }

                const distEnd = Math.sqrt(
                    Math.pow(point.x - obj.end.x, 2) + 
                    Math.pow(point.y - obj.end.y, 2)
                );
                if (distEnd < closestDistance) {
                    closestDistance = distEnd;
                    closestSnap = { x: obj.end.x, y: obj.end.y, type: 'wall-point' };
                }

                // Snap to wall midpoint
                const midX = (obj.start.x + obj.end.x) / 2;
                const midY = (obj.start.y + obj.end.y) / 2;
                const distMid = Math.sqrt(
                    Math.pow(point.x - midX, 2) + 
                    Math.pow(point.y - midY, 2)
                );
                if (distMid < closestDistance) {
                    closestDistance = distMid;
                    closestSnap = { x: midX, y: midY, type: 'wall-midpoint' };
                }
            } else if (obj.type === 'zone' && obj.points) {
                // Snap to zone vertices
                obj.points.forEach(p => {
                    const dist = Math.sqrt(
                        Math.pow(point.x - p.x, 2) + 
                        Math.pow(point.y - p.y, 2)
                    );
                    if (dist < closestDistance) {
                        closestDistance = dist;
                        closestSnap = { x: p.x, y: p.y, type: 'zone-point' };
                    }
                });
            }
        });

        return closestSnap;
    },

    /**
     * Snap angle to orthogonal (0°, 90°, 180°, 270°)
     */
    snapAngleToOrtho(angle) {
        // Normalize angle to 0-360
        const normalized = ((angle % 360) + 360) % 360;
        
        // Find closest 90° angle
        const angles = [0, 90, 180, 270];
        let closest = angles[0];
        let minDiff = Math.abs(normalized - closest);
        
        for (let a of angles) {
            const diff = Math.abs(normalized - a);
            if (diff < minDiff) {
                minDiff = diff;
                closest = a;
            }
        }
        
        return closest;
    },

    /**
     * Enforce orthogonal wall drawing
     */
    enforceOrthogonalWall(startPoint, endPoint) {
        const dx = Math.abs(endPoint.x - startPoint.x);
        const dy = Math.abs(endPoint.y - startPoint.y);
        
        // If movement is more horizontal, force Y to match start
        if (dx > dy) {
            return { ...endPoint, y: startPoint.y };
        } else {
            // If movement is more vertical, force X to match start
            return { ...endPoint, x: startPoint.x };
        }
    },

    /**
     * Calculate distance from point to line segment
     */
    distanceToLine(point, lineStart, lineEnd) {
        const A = point.x - lineStart.x;
        const B = point.y - lineStart.y;
        const C = lineEnd.x - lineStart.x;
        const D = lineEnd.y - lineStart.y;
        
        const dot = A * C + B * D;
        const lenSq = C * C + D * D;
        let param = -1;
        
        if (lenSq !== 0) param = dot / lenSq;
        
        let xx, yy;
        
        if (param < 0) {
            xx = lineStart.x;
            yy = lineStart.y;
        } else if (param > 1) {
            xx = lineEnd.x;
            yy = lineEnd.y;
        } else {
            xx = lineStart.x + param * C;
            yy = lineStart.y + param * D;
        }
        
        const dx = point.x - xx;
        const dy = point.y - yy;
        return Math.sqrt(dx * dx + dy * dy);
    },

    /**
     * Check if point is inside polygon
     */
    isPointInPolygon(point, polygon) {
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i].x, yi = polygon[i].y;
            const xj = polygon[j].x, yj = polygon[j].y;
            
            const intersect = ((yi > point.y) !== (yj > point.y))
                && (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    },

    /**
     * Find object at given position
     */
    findObjectAt(pos, objects) {
        // Check cameras first (easier to select)
        for (let i = objects.length - 1; i >= 0; i--) {
            const obj = objects[i];
            if (obj.type === 'camera') {
                const dist = Math.sqrt(
                    Math.pow(obj.x - pos.x, 2) + 
                    Math.pow(obj.y - pos.y, 2)
                );
                if (dist < 1) return obj; // 1 meter tolerance
            }
        }
        
        // Check zones (point in polygon test)
        for (let i = objects.length - 1; i >= 0; i--) {
            const obj = objects[i];
            if (obj.type === 'zone' && obj.points && obj.points.length >= 3) {
                if (this.isPointInPolygon(pos, obj.points)) {
                    return obj;
                }
            }
        }
        
        // Check walls
        for (let i = objects.length - 1; i >= 0; i--) {
            const obj = objects[i];
            if (obj.type === 'wall') {
                const dist = this.distanceToLine(pos, obj.start, obj.end);
                if (dist < 0.5) return obj; // 0.5 meter tolerance
            }
        }
        
        return null;
    },

    /**
     * Calculate bounding box for all objects
     */
    calculateBounds(objects) {
        if (!objects || objects.length === 0) {
            return { minX: -10, maxX: 10, minY: -10, maxY: 10 };
        }

        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;

        objects.forEach(obj => {
            if (obj.type === 'wall') {
                minX = Math.min(minX, obj.start.x, obj.end.x);
                maxX = Math.max(maxX, obj.start.x, obj.end.x);
                minY = Math.min(minY, obj.start.y, obj.end.y);
                maxY = Math.max(maxY, obj.start.y, obj.end.y);
            } else if (obj.type === 'camera') {
                minX = Math.min(minX, obj.x - obj.range);
                maxX = Math.max(maxX, obj.x + obj.range);
                minY = Math.min(minY, obj.y - obj.range);
                maxY = Math.max(maxY, obj.y + obj.range);
            } else if (obj.type === 'zone' && obj.points) {
                obj.points.forEach(p => {
                    minX = Math.min(minX, p.x);
                    maxX = Math.max(maxX, p.x);
                    minY = Math.min(minY, p.y);
                    maxY = Math.max(maxY, p.y);
                });
            }
        });

        // If no bounds found, return default
        if (!isFinite(minX)) {
            return { minX: -10, maxX: 10, minY: -10, maxY: 10 };
        }

        // Add padding (20% of size)
        const width = maxX - minX;
        const height = maxY - minY;
        const padding = Math.max(width, height) * 0.2 || 5;

        return {
            minX: minX - padding,
            maxX: maxX + padding,
            minY: minY - padding,
            maxY: maxY + padding
        };
    },

    /**
     * Fit view to show all objects
     */
    zoomToFit(state) {
        const bounds = this.calculateBounds(state.objects);
        const canvas = state.canvas;

        const boundsWidth = bounds.maxX - bounds.minX;
        const boundsHeight = bounds.maxY - bounds.minY;

        // Calculate zoom to fit both width and height
        const zoomX = canvas.width / (boundsWidth * state.scale);
        const zoomY = canvas.height / (boundsHeight * state.scale);
        const targetZoom = Math.min(zoomX, zoomY, 2); // Cap at 2x max zoom

        // Ensure minimum zoom
        state.zoom = Math.max(0.1, targetZoom);

        // Center the view on the bounds
        const centerX = (bounds.minX + bounds.maxX) / 2;
        const centerY = (bounds.minY + bounds.maxY) / 2;

        state.panOffset = {
            x: canvas.width / 2 - centerX * state.scale * state.zoom,
            y: canvas.height / 2 - centerY * state.scale * state.zoom
        };

        RoomDesignerRenderer.render(state);
        
        const statusMsg = document.getElementById('statusMsg');
        if (statusMsg) {
            statusMsg.textContent = `Zoomed to fit (${Math.round(state.zoom * 100)}%)`;
        }
    },

    /**
     * Check if point is inside polygon using ray casting algorithm
     */
    pointInPolygon(point, polygon) {
        const x = point.x;
        const y = point.y;
        let inside = false;

        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i].x;
            const yi = polygon[i].y;
            const xj = polygon[j].x;
            const yj = polygon[j].y;

            const intersect = ((yi > y) !== (yj > y)) && (x < ((xj - xi) * (y - yi) / (yj - yi) + xi));
            if (intersect) inside = !inside;
        }

        return inside;
    },

    /**
     * Find line segment intersection
     */
    lineIntersection(p1, p2, p3, p4) {
        const x1 = p1.x, y1 = p1.y;
        const x2 = p2.x, y2 = p2.y;
        const x3 = p3.x, y3 = p3.y;
        const x4 = p4.x, y4 = p4.y;

        const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
        
        if (Math.abs(denom) < 1e-10) return null; // Lines are parallel

        const t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom;
        const u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom;

        if (t >= 0 && t <= 1 && u >= 0 && u <= 1) {
            return {
                x: x1 + t * (x2 - x1),
                y: y1 + t * (y2 - y1)
            };
        }

        return null;
    },

    /**
     * Calculate polygon area using shoelace formula
     */
    polygonArea(polygon) {
        if (polygon.length < 3) return 0;

        let area = 0;
        for (let i = 0; i < polygon.length; i++) {
            const j = (i + 1) % polygon.length;
            area += polygon[i].x * polygon[j].y;
            area -= polygon[j].x * polygon[i].y;
        }
        return Math.abs(area) / 2;
    },

    /**
     * Detect all zone overlaps in the design
     */
    detectZoneOverlaps(objects) {
        const zones = objects.filter(obj => obj.type === 'zone' && obj.points && obj.points.length >= 3);
        const overlaps = [];

        // Check each pair of zones
        for (let i = 0; i < zones.length; i++) {
            for (let j = i + 1; j < zones.length; j++) {
                const overlap = this.findPolygonIntersection(zones[i].points, zones[j].points, zones[i].id, zones[j].id);
                if (overlap) {
                    overlaps.push(overlap);
                }
            }
        }

        return overlaps;
    },

    /**
     * Find intersection polygon between two zones
     */
    findPolygonIntersection(polygon1, polygon2, zone1Id, zone2Id) {
        const intersectionPoints = [];

        // Find edge intersections
        for (let i = 0; i < polygon1.length; i++) {
            const p1 = polygon1[i];
            const p2 = polygon1[(i + 1) % polygon1.length];

            for (let j = 0; j < polygon2.length; j++) {
                const p3 = polygon2[j];
                const p4 = polygon2[(j + 1) % polygon2.length];

                const intersection = this.lineIntersection(p1, p2, p3, p4);
                if (intersection) {
                    // Check if point already exists (avoid duplicates)
                    const isDuplicate = intersectionPoints.some(
                        pt => Math.abs(pt.x - intersection.x) < 1e-6 && Math.abs(pt.y - intersection.y) < 1e-6
                    );
                    if (!isDuplicate) {
                        intersectionPoints.push(intersection);
                    }
                }
            }
        }

        // Add polygon1 points inside or on polygon2
        for (let point of polygon1) {
            if (this.pointInPolygon(point, polygon2) || this.pointOnPolygon(point, polygon2)) {
                const isDuplicate = intersectionPoints.some(
                    pt => Math.abs(pt.x - point.x) < 1e-6 && Math.abs(pt.y - point.y) < 1e-6
                );
                if (!isDuplicate) {
                    intersectionPoints.push(point);
                }
            }
        }

        // Add polygon2 points inside or on polygon1
        for (let point of polygon2) {
            if (this.pointInPolygon(point, polygon1) || this.pointOnPolygon(point, polygon1)) {
                const isDuplicate = intersectionPoints.some(
                    pt => Math.abs(pt.x - point.x) < 1e-6 && Math.abs(pt.y - point.y) < 1e-6
                );
                if (!isDuplicate) {
                    intersectionPoints.push(point);
                }
            }
        }

        // Need at least 3 points to form a valid polygon
        if (intersectionPoints.length < 3) {
            return null;
        }

        // Sort points by angle from centroid (convex hull approach)
        const centroid = {
            x: intersectionPoints.reduce((sum, p) => sum + p.x, 0) / intersectionPoints.length,
            y: intersectionPoints.reduce((sum, p) => sum + p.y, 0) / intersectionPoints.length
        };

        intersectionPoints.sort((a, b) => {
            const angleA = Math.atan2(a.y - centroid.y, a.x - centroid.x);
            const angleB = Math.atan2(b.y - centroid.y, b.x - centroid.x);
            return angleA - angleB;
        });

        const area = this.polygonArea(intersectionPoints);
        
        if (area < 0.01) { // Minimum area threshold
            return null;
        }

        return {
            id: `overlap_${zone1Id}_${zone2Id}`,
            type: 'overlap',
            zone1Id: zone1Id,
            zone2Id: zone2Id,
            points: intersectionPoints,
            area: area
        };
    },

    /**
     * Check if point is on polygon edge
     */
    pointOnPolygon(point, polygon) {
        for (let i = 0; i < polygon.length; i++) {
            const p1 = polygon[i];
            const p2 = polygon[(i + 1) % polygon.length];

            // Check if point is on line segment p1-p2
            const dist1 = Math.hypot(p1.x - point.x, p1.y - point.y);
            const dist2 = Math.hypot(p2.x - point.x, p2.y - point.y);
            const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);

            if (Math.abs(dist1 + dist2 - dist) < 1e-6) {
                return true;
            }
        }
        return false;
    },

    /**
     * Auto-generate zones from cameras considering walls
     * Creates FOV zones clipped by walls
     */
    autoGenerateZonesFromCameras(objects) {
        const cameras = objects.filter(obj => obj.type === 'camera');
        const walls = objects.filter(obj => obj.type === 'wall');
        const generatedZones = [];
        
        cameras.forEach((camera, index) => {
            const zone = this.generateCameraZone(camera, walls, index);
            if (zone) {
                generatedZones.push(zone);
            }
        });
        
        return generatedZones;
    },

    /**
     * Generate a zone from a single camera's FOV, clipped by walls
     */
    generateCameraZone(camera, walls, index) {
        if (!camera.fov || !camera.range) {
            return null;
        }

        const angleRad = (camera.angle || 0) * Math.PI / 180;
        const fovRad = (camera.fov || 90) * Math.PI / 180;
        const range = camera.range;

        // Create FOV cone points (arc with more segments for accuracy)
        const segments = 32;
        const points = [{ x: camera.x, y: camera.y }]; // Start at camera position

        // Generate arc points
        for (let i = 0; i <= segments; i++) {
            const segmentAngle = angleRad - fovRad / 2 + (fovRad * i / segments);
            const x = camera.x + Math.cos(segmentAngle) * range;
            const y = camera.y + Math.sin(segmentAngle) * range;
            points.push({ x, y });
        }

        // Clip the FOV polygon by walls
        let clippedPoints = this.clipPolygonByWalls(points, walls);

        if (clippedPoints.length < 3) {
            return null;
        }

        return {
            id: `camera_zone_${camera.id || index}`,
            type: 'zone',
            cameraId: camera.id,
            points: clippedPoints,
            color: '#ff00ff',
            autoGenerated: true
        };
    },

    /**
     * Clip a polygon by walls (simple wall blocking)
     */
    clipPolygonByWalls(points, walls) {
        // For now, return original points
        // TODO: Implement proper polygon clipping algorithm (Sutherland-Hodgman)
        // This is a simplified version - walls will affect visibility in rendering
        return points;
    }

};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RoomDesignerUtils;
}

