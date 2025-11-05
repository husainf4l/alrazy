#!/bin/bash
# WebRTC Token Management Script
# Usage: ./webrtc-token.sh [generate|validate|revoke|list] [options]

set -e

SERVER="${WEBRTC_SERVER:-http://localhost:8000}"
COLORS_ENABLED=true

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}❌ Error: $1${NC}" >&2
    exit 1
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_usage() {
    cat << EOF
🎫 WebRTC Token Management Tool

Usage: $(basename "$0") [command] [options]

Commands:
  generate [OPTIONS]    Generate a new token
  validate TOKEN        Validate a token
  revoke TOKEN          Revoke a token
  list                  List all tokens
  share [OPTIONS]       Generate and display share link
  help                  Show this help

Generate Options:
  --cameras ROOM1,ROOM2    Cameras (default: all)
  --hours N                Expiry in hours (default: 24)
  --json                   Output as JSON

Validate Options:
  TOKEN                    Token to validate

Share Options:
  --cameras ROOM1,ROOM2    Cameras (default: all)
  --hours N                Expiry in hours (default: 24)
  --ip IP_ADDRESS          Your backend IP (for link generation)

Examples:
  # Generate 24-hour token for all cameras
  $(basename "$0") generate

  # Generate 1-hour token for room1 only
  $(basename "$0") generate --cameras room1 --hours 1

  # Generate and show share link
  $(basename "$0") share --ip 192.168.1.100

  # Validate a token
  $(basename "$0") validate ApGwF4O5ziu_y7fQQ2Mya7lXkvN0Iq_Yxn7AkONnVbk

  # Revoke a token
  $(basename "$0") revoke ApGwF4O5ziu_y7fQQ2Mya7lXkvN0Iq_Yxn7AkONnVbk

  # List all tokens
  $(basename "$0") list

EOF
}

generate_token() {
    local cameras="room1&camera_ids=room2&camera_ids=room3&camera_ids=room4"
    local hours=24
    local json_output=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --cameras)
                IFS=',' read -ra CAMERA_ARRAY <<< "$2"
                cameras=$(IFS='&camera_ids='; echo "${CAMERA_ARRAY[*]}")
                shift 2
                ;;
            --hours)
                hours=$2
                shift 2
                ;;
            --json)
                json_output=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    info "Generating token (expires in $hours hours)..."
    
    response=$(curl -s -X POST "${SERVER}/webrtc/token/generate?camera_ids=${cameras}&expires_hours=${hours}")
    
    if [ "$json_output" = true ]; then
        echo "$response" | python3 -m json.tool
    else
        token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null || echo "")
        if [ -z "$token" ]; then
            error "Failed to generate token. Response: $response"
        fi
        
        expires=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['expires_at'])" 2>/dev/null)
        cameras_list=$(echo "$response" | python3 -c "import sys, json; print(', '.join(json.load(sys.stdin)['camera_ids']))" 2>/dev/null)
        
        echo ""
        success "Token generated!"
        echo ""
        echo "📋 Token Details:"
        echo "   Token:    $token"
        echo "   Expires:  $expires"
        echo "   Cameras:  $cameras_list"
        echo "   Hours:    $hours"
        echo ""
        echo "🔗 Share Links:"
        echo "   Without IP: http://<your-ip>:8000/webrtc.html?token=$token"
        echo "   API:        ${SERVER}/webrtc/offer?camera_id=room1&token=$token"
        echo ""
    fi
}

validate_token() {
    local token=$1
    
    if [ -z "$token" ]; then
        error "Token required"
    fi
    
    info "Validating token..."
    
    response=$(curl -s "${SERVER}/webrtc/token/validate?token=${token}")
    valid=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['valid'])" 2>/dev/null || echo "false")
    
    if [ "$valid" = "True" ] || [ "$valid" = "true" ]; then
        success "Token is valid!"
        echo "$response" | python3 -m json.tool
    else
        warn "Token is invalid or expired"
        echo "$response" | python3 -m json.tool
    fi
}

revoke_token() {
    local token=$1
    
    if [ -z "$token" ]; then
        error "Token required"
    fi
    
    info "Revoking token..."
    
    response=$(curl -s -X DELETE "${SERVER}/webrtc/token/revoke?token=${token}")
    success_val=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['success'])" 2>/dev/null || echo "false")
    
    if [ "$success_val" = "True" ] || [ "$success_val" = "true" ]; then
        success "Token revoked!"
    else
        warn "Failed to revoke token"
    fi
    echo "$response" | python3 -m json.tool
}

list_tokens() {
    info "Fetching active tokens..."
    
    response=$(curl -s "${SERVER}/webrtc/tokens")
    count=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_tokens'])" 2>/dev/null || echo "0")
    
    echo ""
    success "Found $count active tokens"
    echo ""
    echo "$response" | python3 -m json.tool
}

share_token() {
    local cameras="room1&camera_ids=room2&camera_ids=room3&camera_ids=room4"
    local hours=24
    local ip=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --cameras)
                IFS=',' read -ra CAMERA_ARRAY <<< "$2"
                cameras=$(IFS='&camera_ids='; echo "${CAMERA_ARRAY[*]}")
                shift 2
                ;;
            --hours)
                hours=$2
                shift 2
                ;;
            --ip)
                ip=$2
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    info "Generating shareable token..."
    
    response=$(curl -s -X POST "${SERVER}/webrtc/token/generate?camera_ids=${cameras}&expires_hours=${hours}")
    token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null || echo "")
    
    if [ -z "$token" ]; then
        error "Failed to generate token"
    fi
    
    if [ -z "$ip" ]; then
        ip="<YOUR-IP>"
        warn "No IP provided. Using placeholder. Use --ip to specify."
    fi
    
    echo ""
    success "Shareable Token Generated!"
    echo ""
    echo "📱 Mobile Link:"
    echo "   http://${ip}:8000/webrtc.html?token=${token}"
    echo ""
    echo "✏️ Copy & Share (Email, WhatsApp, etc):"
    echo "   Token expires in $hours hours"
    echo "   http://${ip}:8000/webrtc.html?token=${token}"
    echo ""
    echo "🔍 Token Details:"
    echo "   Token: $token"
    echo ""
}

# Main
if [ $# -eq 0 ]; then
    print_usage
    exit 0
fi

command=$1
shift

case $command in
    generate)
        generate_token "$@"
        ;;
    validate)
        validate_token "$@"
        ;;
    revoke)
        revoke_token "$@"
        ;;
    list)
        list_tokens
        ;;
    share)
        share_token "$@"
        ;;
    help|-h|--help)
        print_usage
        ;;
    *)
        error "Unknown command: $command"
        ;;
esac
