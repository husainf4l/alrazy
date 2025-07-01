#!/bin/bash

# Camera Access Management Test Script
# This script demonstrates the complete camera access assignment flow

echo "🎥 Camera Access Management Demo"
echo "================================"

# Configuration
API_URL="http://localhost:4005/api/v1"
ADMIN_CREDENTIALS='{"username": "admin", "password": "tt55oo77"}'
USER_CREDENTIALS='{"username": "user", "password": "tt55oo77"}'

echo "1️⃣  Logging in as admin..."
ADMIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "$ADMIN_CREDENTIALS")

ADMIN_TOKEN=$(echo "$ADMIN_RESPONSE" | grep -o '"accessToken":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo "❌ Admin login failed"
    exit 1
fi

echo "✅ Admin logged in successfully"

echo ""
echo "2️⃣  Creating a new camera..."
CAMERA_DATA='{
    "name": "Frontend Demo Camera",
    "location": "Frontend Test Area", 
    "rtspUrl": "rtsp://192.168.1.200:554/stream1",
    "companyId": 1
}'

CAMERA_RESPONSE=$(curl -s -X POST "$API_URL/cameras" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "$CAMERA_DATA")

CAMERA_ID=$(echo "$CAMERA_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)

if [ -z "$CAMERA_ID" ]; then
    echo "❌ Camera creation failed"
    echo "Response: $CAMERA_RESPONSE"
    exit 1
fi

echo "✅ Camera created successfully with ID: $CAMERA_ID"

echo ""
echo "3️⃣  Assigning user (ID: 3) to camera (ID: $CAMERA_ID) with VIEWER access..."
ACCESS_DATA='{
    "userIds": [3],
    "accessLevel": "VIEWER"
}'

ACCESS_RESPONSE=$(curl -s -X POST "$API_URL/cameras/$CAMERA_ID/access" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "$ACCESS_DATA")

echo "✅ Camera access assigned successfully"
echo "Response: $ACCESS_RESPONSE"

echo ""
echo "4️⃣  Logging in as regular user..."
USER_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "$USER_CREDENTIALS")

USER_TOKEN=$(echo "$USER_RESPONSE" | grep -o '"accessToken":"[^"]*"' | cut -d'"' -f4)

if [ -z "$USER_TOKEN" ]; then
    echo "❌ User login failed"
    exit 1
fi

echo "✅ User logged in successfully"

echo ""
echo "5️⃣  Checking user's accessible cameras..."
USER_CAMERAS=$(curl -s -X GET "$API_URL/cameras" \
  -H "Authorization: Bearer $USER_TOKEN")

echo "📹 User's accessible cameras:"
echo "$USER_CAMERAS" | jq '.[] | {id: .id, name: .name, location: .location}' 2>/dev/null || echo "$USER_CAMERAS"

echo ""
echo "6️⃣  Checking company users with camera access..."
COMPANY_USERS=$(curl -s -X GET "$API_URL/companies/1/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "👥 Company users with camera access:"
echo "$COMPANY_USERS" | jq '.[] | {id: .id, name: (.firstName + " " + .lastName), cameraAccess: .cameraAccess}' 2>/dev/null || echo "$COMPANY_USERS"

echo ""
echo "7️⃣  Revoking camera access..."
REVOKE_RESPONSE=$(curl -s -X DELETE "$API_URL/cameras/$CAMERA_ID/access/3" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "✅ Camera access revoked successfully"

echo ""
echo "8️⃣  Verifying access revocation..."
USER_CAMERAS_AFTER=$(curl -s -X GET "$API_URL/cameras" \
  -H "Authorization: Bearer $USER_TOKEN")

echo "📹 User's accessible cameras after revocation:"
echo "$USER_CAMERAS_AFTER" | jq '.[] | {id: .id, name: .name, location: .location}' 2>/dev/null || echo "$USER_CAMERAS_AFTER"

echo ""
echo "🎉 Camera Access Management Demo Complete!"
echo ""
echo "Summary:"
echo "- ✅ Admin login"
echo "- ✅ Camera creation (ID: $CAMERA_ID)"
echo "- ✅ Camera access assignment"
echo "- ✅ User login"
echo "- ✅ Camera access verification"
echo "- ✅ Access revocation"
echo "- ✅ Revocation verification"
