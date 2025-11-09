#!/bin/bash
# Start IB Gateway Docker container
# Usage: ./start.sh

set -e

echo "=================================================="
echo "  IB Gateway Docker Startup"
echo "=================================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed"
    echo "Install docker-compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating from .env.example..."

    if [ ! -f .env.example ]; then
        echo "❌ Error: .env.example not found"
        exit 1
    fi

    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your IBKR credentials:"
    echo "   nano .env"
    echo ""
    echo "Then run this script again."
    exit 0
fi

# Check if credentials are set
source .env

if [ "$IBKR_USERNAME" = "your_username" ] || [ -z "$IBKR_USERNAME" ]; then
    echo "❌ Error: IBKR_USERNAME not set in .env"
    echo "Edit .env and add your IBKR credentials"
    exit 1
fi

if [ "$IBKR_PASSWORD" = "your_password" ] || [ -z "$IBKR_PASSWORD" ]; then
    echo "❌ Error: IBKR_PASSWORD not set in .env"
    echo "Edit .env and add your IBKR credentials"
    exit 1
fi

echo "✅ Docker installed"
echo "✅ docker-compose installed"
echo "✅ .env file configured"
echo ""

# Show configuration
echo "Configuration:"
echo "  Username: $IBKR_USERNAME"
echo "  Password: ********"
echo "  Trading Mode: ${IBKR_TRADING_MODE:-paper}"
echo "  Read-Only: ${IBKR_READONLY:-yes}"
echo ""

# Determine port
if [ "${IBKR_TRADING_MODE:-paper}" = "paper" ]; then
    PORT=4002
else
    PORT=4001
fi

echo "API will be available on: localhost:$PORT"
echo ""

# Pull latest image
echo "📥 Pulling latest IB Gateway image..."
docker-compose pull

echo ""
echo "🚀 Starting IB Gateway container..."
docker-compose up -d

echo ""
echo "⏳ Waiting for container to be healthy..."

# Wait for container to be healthy (max 120 seconds)
SECONDS=0
MAX_WAIT=120

while [ $SECONDS -lt $MAX_WAIT ]; do
    STATUS=$(docker-compose ps -q ib-gateway | xargs docker inspect -f '{{.State.Health.Status}}' 2>/dev/null || echo "starting")

    if [ "$STATUS" = "healthy" ]; then
        echo "✅ IB Gateway is healthy and ready!"
        break
    fi

    echo "   Status: $STATUS (${SECONDS}s elapsed)"
    sleep 5
done

if [ $SECONDS -ge $MAX_WAIT ]; then
    echo "⚠️  Warning: Container did not become healthy within ${MAX_WAIT}s"
    echo "Check logs with: docker-compose logs ib-gateway"
fi

echo ""
echo "=================================================="
echo "  IB Gateway Started Successfully!"
echo "=================================================="
echo ""
echo "Container Status:"
docker-compose ps

echo ""
echo "API Connection Info:"
echo "  Host: localhost"
echo "  Port: $PORT"
echo "  Trading Mode: ${IBKR_TRADING_MODE:-paper}"
echo ""
echo "Python Example:"
echo "  from wrdata.providers import IBKRProvider"
echo "  ibkr = IBKRProvider(host='localhost', port=$PORT)"
echo "  ibkr.connect()"
echo ""
echo "Useful Commands:"
echo "  View logs:    docker-compose logs -f ib-gateway"
echo "  Stop gateway: docker-compose down"
echo "  Restart:      docker-compose restart ib-gateway"
echo "  Status:       docker-compose ps"
echo ""
echo "VNC Access (optional):"
echo "  Connect to: localhost:5900"
echo "  Password: ${VNC_PASSWORD:-password}"
echo ""
