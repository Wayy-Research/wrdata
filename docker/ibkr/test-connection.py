#!/usr/bin/env python3
"""
Test connection to IB Gateway running in Docker.

Usage: python test-connection.py [--port PORT]
"""

import socket
import sys
import argparse
from datetime import datetime


def test_port(host: str, port: int) -> bool:
    """Test if a port is open."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)

    try:
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error testing port: {e}")
        return False


def test_ibkr_connection(host: str, port: int):
    """Test IB Gateway connection with ib_insync."""
    try:
        from ib_insync import IB
    except ImportError:
        print("❌ ib_insync not installed")
        print("Install with: pip install ib_insync")
        return False

    print(f"\nTesting IBKR API connection to {host}:{port}...")

    ib = IB()

    try:
        ib.connect(host, port, clientId=999, readonly=True, timeout=10)
        print("✅ Successfully connected to IB Gateway!")

        # Get account info if available
        accounts = ib.managedAccounts()
        if accounts:
            print(f"✅ Connected to account(s): {', '.join(accounts)}")

        ib.disconnect()
        return True

    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test IB Gateway Docker connection")
    parser.add_argument("--host", default="localhost", help="IB Gateway host")
    parser.add_argument("--port", type=int, default=4002, help="IB Gateway port (4002=paper, 4001=live)")
    args = parser.parse_args()

    print("=" * 60)
    print("  IB Gateway Connection Test")
    print("=" * 60)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {args.host}:{args.port}")

    # Test 1: Port connectivity
    print("\n" + "=" * 60)
    print("Test 1: Port Connectivity")
    print("=" * 60)

    if test_port(args.host, args.port):
        print(f"✅ Port {args.port} is open and reachable")
    else:
        print(f"❌ Port {args.port} is not accessible")
        print("\nTroubleshooting:")
        print("1. Is IB Gateway container running? Run: docker-compose ps")
        print("2. Check logs: docker-compose logs ib-gateway")
        print("3. Restart container: docker-compose restart ib-gateway")
        sys.exit(1)

    # Test 2: IBKR API connection
    print("\n" + "=" * 60)
    print("Test 2: IBKR API Connection")
    print("=" * 60)

    if test_ibkr_connection(args.host, args.port):
        print("\n" + "=" * 60)
        print("  ✅ All Tests Passed!")
        print("=" * 60)
        print("\nYour IB Gateway is ready to use!")
        print("\nPython Example:")
        print(f"""
from wrdata.providers import IBKRProvider

ibkr = IBKRProvider(
    host='{args.host}',
    port={args.port},
    client_id=1,
    readonly=True
)

if ibkr.connect():
    response = ibkr.fetch_timeseries(
        symbol='AAPL',
        start_date='2024-01-01',
        end_date='2024-11-08',
        interval='1d'
    )
    print(f"Retrieved {{len(response.data)}} records")
""")
    else:
        print("\n" + "=" * 60)
        print("  ❌ Connection Test Failed")
        print("=" * 60)
        print("\nCheck IB Gateway logs:")
        print("  docker-compose logs ib-gateway")
        sys.exit(1)


if __name__ == "__main__":
    main()
