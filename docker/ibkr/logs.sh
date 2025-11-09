#!/bin/bash
# View IB Gateway Docker container logs
# Usage: ./logs.sh [--follow] [--tail N]

FOLLOW=false
TAIL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        --tail)
            TAIL="--tail $2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./logs.sh [--follow] [--tail N]"
            exit 1
            ;;
    esac
done

echo "=================================================="
echo "  IB Gateway Logs"
echo "=================================================="
echo ""

if [ "$FOLLOW" = true ]; then
    echo "Following logs (Ctrl+C to exit)..."
    echo ""
    docker-compose logs -f $TAIL ib-gateway
else
    docker-compose logs $TAIL ib-gateway
fi
