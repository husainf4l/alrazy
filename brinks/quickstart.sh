#!/bin/bash
# Quick start script for SafeRoom Detection System

set -e

echo "🚀 SafeRoom Detection System - Quick Start"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

echo -e "${GREEN}✓ Python found$(python3 --version)${NC}"

# Check if Redis is available
if ! command -v redis-cli &> /dev/null; then
    echo -e "${YELLOW}⚠️  Redis CLI not found. Install with: docker run -d -p 6379:6379 redis:7-alpine${NC}"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}📦 Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source .venv/bin/activate

# Install dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
pip install -q -r requirements.txt

# Test camera connections
echo -e "\n${BLUE}🔍 Testing camera connections...${NC}"
python test_cameras.py

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}📋 Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env (customize if needed)${NC}"
fi

# Display next steps
echo -e "\n${GREEN}✅ Setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1️⃣  Start Redis:"
echo "   docker run -d -p 6379:6379 redis:7-alpine"
echo ""
echo "2️⃣  Start the backend (in a new terminal):"
echo "   source .venv/bin/activate"
echo "   python -m uvicorn backend.main:app --reload"
echo ""
echo "3️⃣  Start frame ingestion (in another new terminal):"
echo "   source .venv/bin/activate"
echo "   python ingest_frames.py --camera room1 --fps 5"
echo ""
echo "4️⃣  Open dashboard:"
echo "   http://localhost:8000"
echo ""
echo -e "${YELLOW}Or use Docker Compose to start everything:${NC}"
echo "   docker-compose up -d"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "   - Quick start: README.md"
echo "   - Full guide: SYSTEM.md"
echo "   - API docs: http://localhost:8000/docs"
echo ""