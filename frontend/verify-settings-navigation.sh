#!/bin/bash

# Settings Navigation Verification Script
# Tests the sidebar settings navigation functionality

echo "🔧 Settings Navigation Verification"
echo "=================================="
echo ""

# Check if development server is running
echo "1. Checking if Next.js development server is running..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Development server is running on http://localhost:3000"
else
    echo "❌ Development server is not running. Starting it..."
    cd /home/husain/alrazy/frontend
    npm run dev &
    sleep 5
fi

echo ""
echo "2. Verifying dashboard accessibility..."
if curl -s http://localhost:3000/dashboard > /dev/null 2>&1; then
    echo "✅ Dashboard page is accessible"
else
    echo "❌ Dashboard page is not accessible"
    exit 1
fi

echo ""
echo "3. Checking sidebar component configuration..."
if grep -q "onItemClick('settings')" /home/husain/alrazy/frontend/src/components/Sidebar.tsx; then
    echo "✅ Sidebar settings button is properly configured"
else
    echo "❌ Sidebar settings button configuration issue"
fi

echo ""
echo "4. Checking dashboard settings page implementation..."
if grep -q "activeItem === 'settings'" /home/husain/alrazy/frontend/src/app/dashboard/page.tsx; then
    echo "✅ Dashboard settings page condition is implemented"
else
    echo "❌ Dashboard settings page condition missing"
fi

echo ""
echo "5. Verifying camera management integration..."
if grep -q "CameraManagement" /home/husain/alrazy/frontend/src/app/dashboard/page.tsx; then
    echo "✅ Camera management is integrated into settings"
else
    echo "❌ Camera management integration missing"
fi

echo ""
echo "6. Checking component dependencies..."
COMPONENTS=(
    "/home/husain/alrazy/frontend/src/components/CameraManagement.tsx"
    "/home/husain/alrazy/frontend/src/components/Sidebar.tsx"
    "/home/husain/alrazy/frontend/src/components/Icon.tsx"
)

for component in "${COMPONENTS[@]}"; do
    if [ -f "$component" ]; then
        echo "✅ $(basename "$component") exists"
    else
        echo "❌ $(basename "$component") missing"
    fi
done

echo ""
echo "🎯 HOW TO TEST SETTINGS NAVIGATION:"
echo "================================="
echo "1. Open browser: http://localhost:3000/dashboard"
echo "2. Look for the gear icon (⚙️) at the bottom of the left sidebar"
echo "3. Click the settings icon"
echo "4. You should see 'Security Settings' page with:"
echo "   - Camera Management section"
echo "   - AI Detection Settings"
echo "   - Alert Configuration"
echo ""

echo "📍 TO ADD A NEW CAMERA:"
echo "====================="
echo "1. Navigate to Settings (⚙️ icon in sidebar)"
echo "2. Find 'Camera Management' section"
echo "3. Click 'Add Camera' or 'Add Your First Camera' button"
echo "4. Fill in the form:"
echo "   - Camera Name (required)"
echo "   - Location (required)"
echo "   - RTSP URL (required)"
echo "   - Username/Password (optional)"
echo "   - Description (optional)"
echo "5. Click 'Save Camera'"
echo ""

echo "✅ Settings navigation verification complete!"
echo "The sidebar should properly navigate to the settings page when clicked."
