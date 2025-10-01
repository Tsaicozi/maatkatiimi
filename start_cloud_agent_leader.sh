#!/bin/bash

# Cloud Agent Leader Startup Script
# Runs the Cloud Agent Leader in Cursor's cloud environment

echo "🚀 Starting Cloud Agent Leader in Cursor Cloud..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import psutil" 2>/dev/null || {
    echo "⚠️ psutil not found. Installing..."
    pip3 install psutil
}

# Create log directory if it doesn't exist
mkdir -p logs

# Start the Cloud Agent Leader
echo "🎯 Launching Cloud Agent Leader..."
echo "   - Monitoring agents in Cursor Cloud"
echo "   - Health checks every 5 minutes"
echo "   - Reports every 10 minutes"
echo "   - Logs: cloud_agent_leader.log"
echo ""
echo "Press Ctrl+C to stop gracefully"
echo ""

# Run the Cloud Agent Leader
python3 cloud_agent_leader.py

echo "👋 Cloud Agent Leader stopped"
