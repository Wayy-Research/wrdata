# IB Gateway Docker Setup

Run Interactive Brokers Gateway in a Docker container - no local installation required!

This allows you to use the IBKR provider without installing TWS or IB Gateway on your machine.

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Interactive Brokers account (paper trading account works too!)
- IBKR account with API access enabled

### 2. Enable API Access in IBKR

Before running the container, you need to enable API access:

1. Log in to [IBKR Account Management](https://www.interactivebrokers.com/portal)
2. Go to **Settings** → **API** → **Settings**
3. Enable **ActiveX and Socket Clients**
4. Click **OK**

**Note:** API settings may take a few minutes to propagate.

### 3. Configure Credentials

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your IBKR credentials
nano .env
```

Set your credentials:
```bash
IBKR_USERNAME=your_username
IBKR_PASSWORD=your_password
IBKR_TRADING_MODE=paper  # or 'live'
IBKR_READONLY=yes
```

### 4. Start IB Gateway

```bash
# Start the container
docker-compose up -d

# Check logs
docker-compose logs -f ib-gateway

# Wait for "Gateway is ready" message
```

### 5. Use with wrdata

Once the container is running, connect from your Python code:

```python
from wrdata.providers import IBKRProvider

# Connect to IB Gateway running in Docker
ibkr = IBKRProvider(
    host="localhost",  # or "ib-gateway" if running in same docker network
    port=4002,         # 4002 for paper, 4001 for live
    client_id=1,
    readonly=True
)

# Use as normal
if ibkr.connect():
    response = ibkr.fetch_timeseries(
        symbol="AAPL",
        start_date="2024-01-01",
        end_date="2024-11-08",
        interval="1d"
    )
    print(f"Retrieved {len(response.data)} records")
```

## Architecture

```
┌─────────────────────────────────────────┐
│  Your Machine / Cloud Server            │
│                                          │
│  ┌────────────────────────────────┐    │
│  │  Docker Container              │    │
│  │                                 │    │
│  │  ┌──────────────────────┐     │    │
│  │  │   IB Gateway         │     │    │
│  │  │   (Headless)         │     │    │
│  │  └──────────────────────┘     │    │
│  │           │                     │    │
│  │           │ Port 4001/4002      │    │
│  └───────────┼─────────────────────┘    │
│              │                           │
│  ┌───────────▼─────────────────────┐    │
│  │  Your Python Application         │    │
│  │  (wrdata IBKRProvider)           │    │
│  └──────────────────────────────────┘    │
│                                          │
└──────────────────┬───────────────────────┘
                   │
                   │ Internet
                   │
         ┌─────────▼──────────┐
         │  IBKR Servers      │
         └────────────────────┘
```

## Ports

- **4001**: Live trading API
- **4002**: Paper trading API (default)
- **5900**: VNC server (optional GUI access)

## Accessing the GUI (Optional)

If you need to see the IB Gateway GUI:

1. Download a VNC viewer (e.g., RealVNC, TigerVNC)
2. Connect to `localhost:5900`
3. Password: Value of `VNC_PASSWORD` in `.env`

This is useful for:
- Troubleshooting connection issues
- Accepting trading permissions
- Verifying settings

## Paper Trading vs Live Trading

### Paper Trading (Recommended for Testing)

```bash
# In .env file
IBKR_TRADING_MODE=paper
```

Uses port **4002**. This is a simulated trading account with fake money. Perfect for:
- Testing your strategies
- Learning the API
- Development

### Live Trading

```bash
# In .env file
IBKR_TRADING_MODE=live
```

Uses port **4001**. Real money, real trades. Only use when you're ready!

## Read-Only Mode

For data fetching only (no trading), set:

```bash
IBKR_READONLY=yes
```

This prevents accidental trades and is recommended for data analysis applications.

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs ib-gateway

# Common issues:
# 1. Wrong credentials
# 2. API not enabled in IBKR account
# 3. Port conflicts (something using 4001/4002)
```

### Can't connect from Python

```python
# Test connection manually
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 4002))
if result == 0:
    print("Port is open!")
else:
    print("Port is closed - check if container is running")
sock.close()
```

### Container stops immediately

Check credentials:
```bash
docker-compose logs ib-gateway | grep -i error
```

Common issues:
- Invalid username/password
- Two-factor authentication not configured properly
- Account locked

### Connection refused

Make sure:
1. Container is running: `docker-compose ps`
2. Port is exposed: `docker-compose port ib-gateway 4002`
3. No firewall blocking: `sudo ufw allow 4002` (Linux)

## Running in Production

### Cloud Deployment (AWS, GCP, Azure)

1. **Launch a VM** (e.g., t3.small on AWS)
2. **Install Docker**:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   ```

3. **Copy your setup**:
   ```bash
   scp -r docker/ibkr user@your-server:~/
   ```

4. **Start container**:
   ```bash
   ssh user@your-server
   cd ibkr
   docker-compose up -d
   ```

5. **Connect from anywhere**:
   ```python
   ibkr = IBKRProvider(
       host="your-server-ip",
       port=4002,
       client_id=1
   )
   ```

### Using with docker-compose in Your App

If your application is also in Docker:

```yaml
version: '3.8'

services:
  ib-gateway:
    # ... (as above)

  your-app:
    build: .
    depends_on:
      - ib-gateway
    environment:
      IBKR_HOST: ib-gateway  # Use container name
      IBKR_PORT: 4002
    networks:
      - ibkr-network
```

Then in your code:
```python
ibkr = IBKRProvider(
    host=os.getenv("IBKR_HOST", "localhost"),
    port=int(os.getenv("IBKR_PORT", 4002)),
    client_id=1
)
```

## Security Best Practices

### 1. Don't commit credentials
```bash
# Make sure .env is in .gitignore
echo ".env" >> .gitignore
```

### 2. Use secrets management in production
```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
    --name ibkr-credentials \
    --secret-string '{"username":"xxx","password":"xxx"}'
```

### 3. Use read-only mode for data apps
```bash
IBKR_READONLY=yes
```

### 4. Restrict network access
```bash
# Only allow localhost
docker-compose.yml:
  ports:
    - "127.0.0.1:4002:4002"
```

## Advanced Configuration

### Multiple Client Connections

You can connect multiple applications to the same IB Gateway:

```python
# App 1
ibkr1 = IBKRProvider(client_id=1)

# App 2
ibkr2 = IBKRProvider(client_id=2)

# App 3
ibkr3 = IBKRProvider(client_id=3)
```

Each needs a unique `client_id`.

### Auto-restart on Failure

The Docker container will automatically restart if it crashes:

```yaml
restart: unless-stopped
```

### Persistent Settings

Gateway settings are persisted in a Docker volume:

```bash
# View volume
docker volume inspect ibkr_ib-gateway-settings

# Backup volume
docker run --rm -v ibkr_ib-gateway-settings:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/ibkr-backup.tar.gz /data
```

## Monitoring

### Health Check

```bash
# Check if gateway is healthy
docker-compose ps

# Expected output:
# NAME        STATE     PORTS
# ib-gateway  Up (healthy)
```

### Logs

```bash
# Follow logs
docker-compose logs -f ib-gateway

# Last 100 lines
docker-compose logs --tail=100 ib-gateway

# Filter for errors
docker-compose logs ib-gateway | grep -i error
```

### Container Stats

```bash
# CPU, memory usage
docker stats ib-gateway
```

## Stopping and Cleaning Up

```bash
# Stop container
docker-compose down

# Stop and remove volumes (resets all settings)
docker-compose down -v

# Remove everything including images
docker-compose down -v --rmi all
```

## Alternative: Local IB Gateway

If you prefer to run IB Gateway locally instead of Docker:

1. Download from: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
2. Install and run
3. Enable API (same as Docker setup)
4. Connect with `host="127.0.0.1"`, `port=4002`

## FAQ

**Q: Do I need an IBKR account with money?**
A: No! Paper trading accounts are completely free and work with this setup.

**Q: Can I run this on my laptop?**
A: Yes! Docker runs on Windows, Mac, and Linux.

**Q: Can I deploy this to the cloud?**
A: Yes! Works great on AWS, GCP, Azure, DigitalOcean, etc.

**Q: How much does this cost to run?**
A: Docker container is free. IBKR account is free. Cloud VM costs vary ($5-20/month typically).

**Q: Is this secure?**
A: Yes, when configured properly. Use read-only mode, strong passwords, and keep credentials secret.

**Q: Can multiple people use the same container?**
A: Yes, multiple clients can connect with different `client_id` values.

**Q: What if the container crashes?**
A: It will automatically restart (see `restart: unless-stopped` in docker-compose.yml).

**Q: Can I use this for live trading?**
A: Yes, but test thoroughly with paper trading first!

## Support

- **IB Gateway Docker Image**: https://github.com/gnzsnz/ib-gateway
- **IBKR API Docs**: https://interactivebrokers.github.io/tws-api/
- **wrdata Issues**: File an issue in the wrdata repository

## Summary

✅ **Pros of Docker Setup:**
- No local IB Gateway installation
- Easy deployment to cloud
- Isolated environment
- Auto-restart on failures
- Portable across machines

❌ **Cons:**
- Requires Docker knowledge
- One more service to manage
- Slightly more complex than local install

**Recommendation:** Use Docker if you're deploying to cloud or want a cleaner setup. Use local IB Gateway if you're just testing locally.

---

**Next Steps:**
1. Set up credentials in `.env`
2. Run `docker-compose up -d`
3. Test with `test_ibkr_live.py`
4. Start building your trading application!
