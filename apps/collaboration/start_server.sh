#!/bin/bash
# Start the Aurora Energy Collaboration Server

set -e

echo "🚀 Starting Aurora Energy Collaboration Server..."
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start server
echo "📡 Starting FastAPI server on http://localhost:8000"
echo "📱 Web UI available at http://localhost:8000"
echo "🔌 WebSocket available at ws://localhost:8000/ws"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uvicorn apps.collaboration.api:app --host 0.0.0.0 --port 8000 --reload
