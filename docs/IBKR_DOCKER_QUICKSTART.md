# IBKR Docker Quick Start Guide

Run Interactive Brokers Gateway in Docker - **no local software installation required!**

## Why Docker?

✅ **No local installation** - IB Gateway runs in a container
✅ **Cloud-ready** - Deploy anywhere Docker runs
✅ **Easy setup** - Just configure credentials and run
✅ **Isolated** - No conflicts with other software
✅ **Auto-restart** - Automatically recovers from crashes

## 5-Minute Setup

### Step 1: Prerequisites

Install Docker:
- **Windows/Mac**: https://www.docker.com/products/docker-desktop
- **Linux**: `curl -fsSL https://get.docker.com | sh`

### Step 2: Enable IBKR API

1. Log in to [IBKR Account Management](https://www.interactivebrokers.com/portal)
2. Go to **Settings** → **API** → **Settings**
3. Enable **ActiveX and Socket Clients**
4. Click **OK**

### Step 3: Configure Credentials

```bash
cd docker/ibkr
cp .env.example .env
nano .env  # or use any text editor
```

Edit the `.env` file:
```bash
IBKR_USERNAME=your_username
IBKR_PASSWORD=your_password
IBKR_TRADING_MODE=paper  # Use paper trading for testing
IBKR_READONLY=yes        # Read-only for data fetching
```

### Step 4: Start IB Gateway

```bash
./start.sh
```

You should see:
```
✅ IB Gateway is healthy and ready!
API Connection Info:
  Host: localhost
  Port: 4002
```

### Step 5: Test Connection

```bash
python test-connection.py
```

If successful, you'll see:
```
✅ All Tests Passed!
Your IB Gateway is ready to use!
```

### Step 6: Use in Your Code

```python
from wrdata.providers import IBKRProvider

# Connect to IB Gateway running in Docker
ibkr = IBKRProvider(
    host="localhost",
    port=4002,  # 4002 for paper, 4001 for live
    client_id=1,
    readonly=True
)

if ibkr.connect():
    print("Connected to IBKR!")

    # Fetch historical data
    response = ibkr.fetch_timeseries(
        symbol="AAPL",
        start_date="2024-01-01",
        end_date="2024-11-08",
        interval="1d"
    )

    print(f"Retrieved {len(response.data)} records")

    # Get real-time quote
    quote = ibkr.get_market_data("AAPL")
    print(f"AAPL: ${quote.get('last')}")

    # Get account info
    account = ibkr.get_account_summary()
    print(f"Account: {account}")
```

## Common Commands

```bash
# View logs
docker-compose logs -f ib-gateway

# Stop IB Gateway
./stop.sh

# Restart IB Gateway
docker-compose restart ib-gateway

# Check status
docker-compose ps
```

## Troubleshooting

### Container won't start

```bash
# Check logs for errors
docker-compose logs ib-gateway | grep -i error

# Common issues:
# - Wrong username/password
# - API not enabled
# - Account locked
```

### Can't connect from Python

```bash
# Test if port is open
python test-connection.py

# Check if container is running
docker-compose ps

# Restart container
docker-compose restart ib-gateway
```

### "Connection refused" error

Make sure:
1. Container is running: `docker-compose ps`
2. Wait for "healthy" status: `docker-compose ps | grep healthy`
3. Check port: `docker-compose port ib-gateway 4002`

## Paper Trading vs Live Trading

### Paper Trading (Recommended)

```bash
# In .env
IBKR_TRADING_MODE=paper
```

- Uses port **4002**
- Simulated trading with fake money
- Perfect for testing
- No risk

### Live Trading

```bash
# In .env
IBKR_TRADING_MODE=live
```

- Uses port **4001**
- Real money
- **Only use when ready!**

## Cloud Deployment

### AWS Example

```bash
# 1. Launch EC2 instance (t3.small recommended)

# 2. SSH into instance
ssh -i key.pem ubuntu@your-instance-ip

# 3. Install Docker
curl -fsSL https://get.docker.com | sh

# 4. Clone your repository
git clone https://github.com/your-repo.git
cd your-repo/docker/ibkr

# 5. Configure credentials
cp .env.example .env
nano .env

# 6. Start IB Gateway
./start.sh

# 7. Your app can now connect to your-instance-ip:4002
```

### GCP Example

```bash
# 1. Create VM instance (e2-small recommended)

# 2. SSH into instance (use GCP console or gcloud)
gcloud compute ssh your-instance

# 3. Follow same steps as AWS above
```

## Security Best Practices

1. **Use read-only mode** for data applications:
   ```bash
   IBKR_READONLY=yes
   ```

2. **Don't commit .env file**:
   ```bash
   echo ".env" >> .gitignore
   ```

3. **Restrict network access** in production:
   ```yaml
   ports:
     - "127.0.0.1:4002:4002"  # Only localhost
   ```

4. **Use strong VNC password**:
   ```bash
   VNC_PASSWORD=long-random-password-here
   ```

## Advanced Usage

### Multiple Applications

Connect multiple apps with different client IDs:

```python
# App 1
ibkr1 = IBKRProvider(client_id=1)

# App 2
ibkr2 = IBKRProvider(client_id=2)

# Streaming app
ibkr3 = IBKRProvider(client_id=3)
```

### Docker Compose with Your App

```yaml
version: '3.8'

services:
  ib-gateway:
    image: ghcr.io/gnzsnz/ib-gateway:latest
    # ... (config)

  my-trading-app:
    build: .
    depends_on:
      - ib-gateway
    environment:
      IBKR_HOST: ib-gateway  # Use container name
      IBKR_PORT: 4002
```

### VNC Access (Optional)

To see the IB Gateway GUI:

1. Install VNC viewer: https://www.realvnc.com/en/connect/download/viewer/
2. Connect to: `localhost:5900`
3. Password: Value of `VNC_PASSWORD` in `.env`

Useful for troubleshooting and accepting permissions.

## FAQ

**Q: Do I need to download IB Gateway?**
A: No! Docker container includes everything.

**Q: Can I use this on Windows/Mac?**
A: Yes! Docker Desktop works on all platforms.

**Q: How much RAM does it need?**
A: About 500MB-1GB. Most modern machines handle it fine.

**Q: Can I run this 24/7?**
A: Yes! Set `restart: unless-stopped` in docker-compose.yml (already configured).

**Q: Is my password secure?**
A: Yes - it's only in your local `.env` file and Docker container environment.

**Q: Can I deploy to Heroku/Railway/Render?**
A: Not ideal. IB Gateway needs persistent connection. Better on VPS (AWS, GCP, DigitalOcean).

**Q: What if IBKR kicks me out?**
A: Container will auto-reconnect. Check logs: `docker-compose logs ib-gateway`

## Comparison: Docker vs Local vs Alpaca

| Method | Setup | Cloud Deploy | Maintenance |
|--------|-------|--------------|-------------|
| **IBKR Docker** | Medium | Easy | Low |
| **IBKR Local** | Medium | Hard | Medium |
| **Alpaca** | Easy | Easy | None |

**Recommendation:**
- New to trading? → **Alpaca**
- Need options/futures? → **IBKR Docker**
- Local development only? → **IBKR Local**

## Support

- 📚 Full docs: `docker/ibkr/README.md`
- 🐛 Issues: File an issue in the repository
- 💬 IBKR API docs: https://interactivebrokers.github.io/tws-api/

## Next Steps

1. ✅ Start IB Gateway: `./start.sh`
2. ✅ Test connection: `python test-connection.py`
3. ✅ Run example: `python ../../test_ibkr_live.py`
4. 🚀 Build your trading app!

---

**Ready to go!** Your IB Gateway is now running in Docker and ready to use. No local software installation required! 🎉
