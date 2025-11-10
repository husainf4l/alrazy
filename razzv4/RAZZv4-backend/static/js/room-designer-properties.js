/**
 * Room Designer - Properties Panel
 * Manages the properties sidebar
 */

const RoomDesignerProperties = {
    /**
     * Show properties for selected object
     */
    showProperties(obj, state) {
        const generalProps = document.getElementById('generalProps');
        const selectionProps = document.getElementById('selectionProps');
        const cameraProps = document.getElementById('cameraProps');
        
        if (!obj) {
            generalProps.style.display = 'block';
            selectionProps.style.display = 'none';
            cameraProps.style.display = 'none';
            return;
        }
        
        generalProps.style.display = 'none';
        selectionProps.style.display = 'block';
        
        // Update selection properties
        document.getElementById('objType').value = obj.type;
        
        if (obj.type === 'camera') {
            document.getElementById('objX').value = obj.x?.toFixed(2) || 0;
            document.getElementById('objY').value = obj.y?.toFixed(2) || 0;
            
            // Show camera-specific properties
            cameraProps.style.display = 'block';
            document.getElementById('cameraId').value = obj.id || '';
            document.getElementById('cameraAngle').value = obj.angle || 0;
            document.getElementById('cameraFOV').value = obj.fov || 90;
            document.getElementById('cameraRange').value = obj.range || 5;
            
            // Update camera properties on change
            this.bindCameraProperties(obj, state);
        } else {
            cameraProps.style.display = 'none';
        }
        
        // Update position on input change
        this.bindPositionProperties(obj, state);
    },

    /**
     * Hide properties panel
     */
    hideProperties() {
        document.getElementById('generalProps').style.display = 'block';
        document.getElementById('selectionProps').style.display = 'none';
        document.getElementById('cameraProps').style.display = 'none';
    },

    /**
     * Bind position property changes
     */
    bindPositionProperties(obj, state) {
        const objX = document.getElementById('objX');
        const objY = document.getElementById('objY');
        
        if (objX && objY) {
            objX.onchange = () => {
                if (obj.type === 'camera') {
                    obj.x = parseFloat(objX.value) || 0;
                    RoomDesignerRenderer.render(state);
                }
            };
            
            objY.onchange = () => {
                if (obj.type === 'camera') {
                    obj.y = parseFloat(objY.value) || 0;
                    RoomDesignerRenderer.render(state);
                }
            };
        }
    },

    /**
     * Bind camera-specific properties
     */
    bindCameraProperties(obj, state) {
        const cameraId = document.getElementById('cameraId');
        const cameraAngle = document.getElementById('cameraAngle');
        const cameraFOV = document.getElementById('cameraFOV');
        const cameraRange = document.getElementById('cameraRange');
        
        if (cameraId) {
            cameraId.onchange = () => {
                obj.id = cameraId.value;
                RoomDesignerRenderer.render(state);
            };
        }
        
        if (cameraAngle) {
            cameraAngle.oninput = () => {
                obj.angle = parseFloat(cameraAngle.value) || 0;
                RoomDesignerRenderer.render(state);
            };
        }
        
        if (cameraFOV) {
            cameraFOV.oninput = () => {
                obj.fov = parseFloat(cameraFOV.value) || 90;
                RoomDesignerRenderer.render(state);
            };
        }
        
        if (cameraRange) {
            cameraRange.oninput = () => {
                obj.range = parseFloat(cameraRange.value) || 5;
                RoomDesignerRenderer.render(state);
            };
        }
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RoomDesignerProperties;
}
