# Zone Overlap Detection Feature

## Overview
The room designer now automatically detects and visualizes **overlapping areas** where camera coverage zones intersect with each other.

## Features Implemented

### ✅ 1. Automatic Overlap Detection
- **Algorithm**: Polygon intersection using edge intersection detection + point-in-polygon testing
- **Location**: `room-designer-utils.js`
- **Function**: `detectZoneOverlaps(objects)` - finds all overlapping zone pairs
- **Function**: `findPolygonIntersection(polygon1, polygon2, zone1Id, zone2Id)` - calculates intersection geometry

### ✅ 2. Visual Representation
- **Color**: Purple/Magenta (`#dd00ff`) with semi-transparent fill (`rgba(200, 0, 255, 0.3)`)
- **Display**: 
  - Filled overlapping area
  - Border outline
  - Vertices marked with small dots
  - Area text in square meters at centroid
- **Location**: `room-designer-renderer.js` - `drawOverlap()` method

### ✅ 3. Data Persistence
- **Storage**: Zone overlaps saved in `room_layout` JSON field
- **Fields per overlap**:
  ```json
  {
    "id": "overlap_zone1_zone2",
    "type": "overlap",
    "zone1Id": "zone1",
    "zone2Id": "zone2",
    "points": [...],
    "area": 9.0
  }
  ```
- **Auto-calculated**: Overlaps are recalculated on every save automatically

### ✅ 4. Real-time Updates
- Overlaps display in real-time as you draw/move zones
- Stored in `state.detectedOverlaps` array
- Auto-updates when zones layer is toggled visible

## How to Use

### 1. Create Zones
1. Click **Zone** tool in left toolbar
2. Click on canvas to add zone points
3. Press **ENTER** to finish zone
4. Repeat to create multiple zones

### 2. View Overlaps
- If zones overlap, overlapping areas automatically display in **purple**
- Hover over overlap to see its area in square meters
- Overlap areas are visible when **Zones** layer is visible (eye icon)

### 3. Save Overlaps
- Click **Save** button in **Annotate** tab
- Status bar shows: `✓ Design saved! X camera(s) + Y overlap(s)`
- Overlaps are automatically included in saved layout

### 4. Load Overlaps
- Overlaps are automatically loaded when you reload the page
- Display is automatically rendered on canvas

## Technical Details

### Overlap Detection Algorithm

#### Step 1: Find Edge Intersections
```javascript
// For each edge pair (zone1 edge vs zone2 edge)
lineIntersection(p1, p2, p3, p4)
// Returns intersection point if edges cross
```

#### Step 2: Find Points Inside Other Zones
```javascript
// For each point in zone1, check if inside zone2
pointInPolygon(point, polygon)
pointOnPolygon(point, polygon)  // Handles boundary points
```

#### Step 3: Sort Points by Angle
```javascript
// Sort intersection points by angle from centroid
// Creates proper polygon for area calculation
```

#### Step 4: Calculate Area
```javascript
// Use Shoelace formula
area = |Σ(xi * yi+1 - xi+1 * yi)| / 2
```

### Utility Functions

#### `pointInPolygon(point, polygon)`
- Ray casting algorithm
- Returns true if point is strictly inside polygon
- Does NOT include boundary points

#### `pointOnPolygon(point, polygon)`
- Checks if point lies on any edge
- Uses distance calculation: dist(p1→point) + dist(point→p2) = dist(p1→p2)

#### `lineIntersection(p1, p2, p3, p4)`
- Finds intersection of two line segments
- Uses parametric line equation
- Only returns intersection if within both segments (0 ≤ t ≤ 1, 0 ≤ u ≤ 1)

#### `polygonArea(polygon)`
- Shoelace formula for any polygon
- Works for both convex and non-convex shapes

#### `detectZoneOverlaps(objects)`
- Main entry point for overlap detection
- Returns array of all overlap objects
- Called automatically during render

### Data Flow

```
User draws zones
    ↓
[Mouse events] → zone created in state.objects
    ↓
[Render called] → detectZoneOverlaps(state.objects)
    ↓
Overlaps calculated → stored in state.detectedOverlaps
    ↓
[drawOverlap() called for each] → rendered on canvas
    ↓
User clicks Save → saveDesign()
    ↓
overlaps included in layout JSON
    ↓
POST to /vault-rooms/save-layout
    ↓
Database saved with overlaps
```

## Example Output

### Test Case: Two Overlapping Squares
```
Zone 1: (0,0) → (6,0) → (6,6) → (0,6)  [6x6 square]
Zone 2: (3,3) → (9,3) → (9,9) → (3,9)  [6x6 square]

Overlap Area: (3,3) → (6,3) → (6,6) → (3,6)
Area: 9.0 m²
Color: Purple/Magenta

Saved JSON:
{
  "id": "overlap_zone1_zone2",
  "type": "overlap",
  "zone1Id": "zone1",
  "zone2Id": "zone2", 
  "points": [
    {"x": 3, "y": 3},
    {"x": 6, "y": 3},
    {"x": 6, "y": 6},
    {"x": 3, "y": 6}
  ],
  "area": 9.0
}
```

## Visual Guide

### Canvas View
```
┌─────────────────────────────────────┐
│ Zone 1 (Blue outline)               │
│ ┌───────────────────────┐            │
│ │                       │            │
│ │   ┌─ Zone 2 (Green)   │            │
│ │   │   ┌────────┐      │            │
│ │   │   │ PURPLE │      │   Zone 2   │
│ │   │   │ OVERLAP│      │   extends  │
│ │   │   │ 9.0 m² │      │   beyond   │
│ │   │   └────────┘      │            │
│ │   │                   │            │
│ │   └─────────────────┐ │            │
│ └─────────────────────┴─┘            │
└─────────────────────────────────────┘

Legend:
- Blue = Zone 1
- Green = Zone 2  
- Purple = Overlap (9.0 m²)
```

## Performance Considerations

- **Complexity**: O(n²) for n zones (quadratic growth)
- **Threshold**: Only detects overlaps > 0.01 m² (avoids noise)
- **Rendering**: Cached during render cycle, recalculated on each render
- **Optimization**: Could implement spatial partitioning for 100+ zones

## Testing

To test overlap detection:

1. **Load Room Designer**: `http://localhost:8003/vault-rooms`
2. **Select Room 5** (has test data)
3. **View Zones Layer** - should see 2 zones
4. **Observe Purple Area** - overlap visualization appears
5. **Click Save** - status shows overlap count
6. **Verify Database**: 
   ```bash
   python3 -c "from database import SessionLocal; from models import VaultRoom; import json; room = SessionLocal().query(VaultRoom).filter(VaultRoom.id==5).first(); print(json.dumps(json.loads(room.room_layout), indent=2))"
   ```

## Future Enhancements

- [ ] Highlight specific overlap when clicked
- [ ] Show overlap coverage statistics (% of room covered, etc.)
- [ ] Export overlap data to separate table
- [ ] Union of overlaps (total covered area)
- [ ] Gap detection (uncovered areas)
- [ ] Overlap heatmap for multiple zone configurations
- [ ] Export overlaps as separate SVG layer

## Troubleshooting

### Overlaps Not Showing
- **Check**: Are zones actually overlapping? Draw zones to test
- **Check**: Is Zones layer visible? (Eye icon in properties panel)
- **Check**: Open browser console for debug messages

### Incorrect Area Calculation
- **Cause**: Zones may be non-convex or self-intersecting
- **Solution**: Ensure zones are simple polygons with no self-intersections

### Performance Slow with Many Zones
- **Cause**: O(n²) complexity checks all zone pairs
- **Solution**: Limit zones or implement spatial partitioning

## Code References

| Component | File | Lines |
|-----------|------|-------|
| Overlap Detection | `room-designer-utils.js` | 426-530 |
| Overlap Rendering | `room-designer-renderer.js` | 373-417 |
| Save Overlaps | `room-designer-api.js` | 192-285 |
| State Management | `room-designer-state.js` | 40 |
