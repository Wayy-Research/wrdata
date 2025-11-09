#!/bin/bash
# Stop IB Gateway Docker container
# Usage: ./stop.sh

set -e

echo "=================================================="
echo "  Stopping IB Gateway"
echo "=================================================="
echo ""

# Check if container is running
if ! docker-compose ps -q ib-gateway &> /dev/null; then
    echo "⚠️  IB Gateway container is not running"
    exit 0
fi

echo "🛑 Stopping IB Gateway container..."
docker-compose down

echo ""
echo "✅ IB Gateway stopped successfully"
echo ""
echo "To start again: ./start.sh"
echo "To remove all data: docker-compose down -v"
echo ""
