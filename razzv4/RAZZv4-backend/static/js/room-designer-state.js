/**
 * Room Designer - State Management
 * Manages all application state variables
 */

const RoomDesignerState = {
    // Canvas and context
    canvas: null,
    ctx: null,
    
    // Tools and interaction
    currentTool: 'select',
    isDrawing: false,
    isDragging: false,
    isPanning: false,
    isAdjustingAngle: false,
    
    // Objects and selection
    objects: [],
    selectedObject: null,
    startPoint: null,
    dragStartPoint: null,
    tempPoints: [],
    
    // Dragging
    dragOffset: { x: 0, y: 0 },
    
    // View settings
    scale: 20, // pixels per meter
    gridSize: 0.1, // meters (10cm grid for better precision)
    showGrid: true,
    snapToGrid: true,
    snapToObjects: false,
    orthoMode: false,
    zoom: 7, // Default 7x zoom for better visibility
    panOffset: { x: 0, y: 0 },
    lastPanPoint: null,
    
    // Layer visibility
    layers: {
        walls: true,
        cameras: true,
        zones: true
    },
    
    // Room data
    roomId: null,
    availableCameras: [],
    
    // Overlap detection
    detectedOverlaps: [],
    
    // Undo/Redo history
    history: [],
    historyIndex: -1,
    maxHistory: 50,
    
    // Initialize state
    init(canvasElement, roomId) {
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        this.roomId = roomId;
        this.panOffset = { 
            x: canvasElement.width / 2, 
            y: canvasElement.height / 2 
        };
    },
    
    // Reset state
    reset() {
        this.objects = [];
        this.selectedObject = null;
        this.startPoint = null;
        this.tempPoints = [];
        this.isDragging = false;
        this.isDrawing = false;
    },
    
    // Save current state to history for undo/redo
    saveToHistory() {
        // Remove any states after current index (user did undo then made new action)
        this.history = this.history.slice(0, this.historyIndex + 1);
        
        // Deep clone the objects array
        const stateCopy = JSON.parse(JSON.stringify(this.objects));
        this.history.push(stateCopy);
        
        // Keep history within max limit
        if (this.history.length > this.maxHistory) {
            this.history.shift();
        } else {
            this.historyIndex++;
        }
    },
    
    // Undo last action
    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.objects = JSON.parse(JSON.stringify(this.history[this.historyIndex]));
            this.selectedObject = null;
            return true;
        }
        return false;
    },
    
    // Redo previously undone action
    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.objects = JSON.parse(JSON.stringify(this.history[this.historyIndex]));
            this.selectedObject = null;
            return true;
        }
        return false;
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RoomDesignerState;
}
