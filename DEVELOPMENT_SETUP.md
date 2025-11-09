# WRData Development Environment Setup

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Python 3.10+ installed
- Git

### 1. Start Infrastructure

```bash
# Start TimescaleDB and Redis
docker-compose up -d

# Verify services are running
docker-compose ps

# Check TimescaleDB logs
docker-compose logs timescaledb

# Expected output:
# "TimescaleDB initialized successfully for WRData!"
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### 3. Configure Environment Variables

```bash
# Copy example .env file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

Example `.env`:
```bash
# Database
DATABASE_URL=postgresql://wrdata_user:wrdata_dev_password@localhost:5432/wrdata

# Redis
REDIS_URL=redis://localhost:6379/0

# Data Provider API Keys (Free Tier)
ALPHA_VANTAGE_API_KEY=your_key_here
TWELVE_DATA_API_KEY=your_key_here

# Data Provider API Keys (Pro Tier - Optional)
POLYGON_API_KEY=your_key_here
IEX_API_KEY=your_key_here

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
```

### 4. Initialize Database

```bash
# Run migrations
python -m wrdata.utils.db_utils init

# Expected output:
# "Created 4 tables: data_providers, symbols, options_contracts, options_chain_snapshots"
```

### 5. Verify Setup

```bash
# Test database connection
python -c "
from wrdata.utils.db_utils import get_session
from sqlalchemy import text

session = get_session()
result = session.execute(text('SELECT version()'))
print('PostgreSQL version:', result.scalar())

# Check if TimescaleDB is enabled
result = session.execute(text(\"SELECT extname FROM pg_extension WHERE extname='timescaledb'\"))
if result.scalar():
    print('✓ TimescaleDB extension enabled')
else:
    print('✗ TimescaleDB extension not found')

session.close()
"
```

---

## Development Tools

### Docker Compose Services

#### Core Services (Always Running)
```bash
# Start core services
docker-compose up -d timescaledb redis
```

- **TimescaleDB**: `localhost:5432`
- **Redis**: `localhost:6379`

#### Development Tools (Optional)
```bash
# Start with development tools
docker-compose --profile dev up -d
```

- **PgAdmin**: http://localhost:5050
  - Email: `admin@wrdata.local`
  - Password: `admin`

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`

### Useful Docker Commands

```bash
# View logs
docker-compose logs -f timescaledb
docker-compose logs -f redis

# Restart a service
docker-compose restart timescaledb

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes all data)
docker-compose down -v

# Execute SQL directly
docker exec -it wrdata-timescaledb psql -U wrdata_user -d wrdata
```

### Database Commands (psql)

```sql
-- List all tables
\dt

-- List all hypertables
SELECT hypertable_name FROM timescaledb_information.hypertables;

-- Check table sizes
SELECT hypertable_name,
       pg_size_pretty(total_bytes) AS total_size,
       pg_size_pretty(index_bytes) AS index_size
FROM timescaledb_information.hypertable;

-- View compression stats
SELECT * FROM timescaledb_information.compression_settings;

-- Query recent OHLCV data
SELECT * FROM timeseries.ohlcv_data
ORDER BY time DESC
LIMIT 10;

-- Exit psql
\q
```

---

## Project Structure

```
wrdata/
├── wrdata/                      # Main package
│   ├── __init__.py
│   ├── core/                    # Core utilities (config, auth, etc.)
│   │   └── config.py            # Configuration management
│   ├── models/                  # Data models
│   │   ├── database.py          # SQLAlchemy models
│   │   └── schemas.py           # Pydantic schemas
│   ├── providers/               # Data provider implementations
│   │   ├── base.py              # Abstract base class
│   │   ├── yfinance_provider.py # YFinance implementation
│   │   ├── binance_provider.py  # Binance (TODO)
│   │   └── ...
│   ├── services/                # Business logic
│   │   ├── options_fetcher.py   # Options data service
│   │   ├── data_fetcher.py      # Generic data fetcher (TODO)
│   │   └── symbol_manager.py    # Symbol discovery
│   ├── streaming/               # WebSocket/streaming (TODO)
│   │   └── ws_manager.py
│   └── utils/                   # Utilities
│       └── db_utils.py          # Database utilities
├── config/                      # Configuration files
│   └── grafana/
│       └── datasources.yml
├── scripts/                     # Setup scripts
│   └── init_timescale.sql       # TimescaleDB initialization
├── examples/                    # Example scripts
│   └── options_chain_example.py
├── tests/                       # Tests (TODO)
│   ├── unit/
│   └── integration/
├── docs/                        # Documentation
│   ├── OPTIONS_CHAINS.md
│   ├── DATA_PROVIDER_TOS_ANALYSIS.md
│   └── DEPLOYMENT_ARCHITECTURE.md
├── docker-compose.yml           # Local development infrastructure
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Package configuration
├── .env.example                 # Example environment variables
└── README.md                    # Project README
```

---

## Development Workflow

### 1. Feature Development

```bash
# Create a new branch
git checkout -b feature/new-provider

# Make your changes
# Edit files in wrdata/providers/

# Run tests
pytest tests/

# Commit changes
git add .
git commit -m "feat: add new data provider"

# Push and create PR
git push origin feature/new-provider
```

### 2. Testing Data Fetching

```python
# test_fetch.py
from wrdata.utils.db_utils import get_session
from wrdata.services.options_fetcher import OptionsFetcher
from wrdata.models.schemas import OptionsChainRequest

session = get_session()
fetcher = OptionsFetcher(session)

# Fetch options chain
request = OptionsChainRequest(symbol="SPY")
response = fetcher.fetch_and_store_options_chain(request)

if response.success:
    print(f"✓ Fetched {len(response.calls)} calls and {len(response.puts)} puts")
else:
    print(f"✗ Error: {response.error}")

session.close()
```

### 3. Database Migrations

```bash
# Check current database state
python -m wrdata.utils.db_utils verify

# Run migration (if needed)
python -m wrdata.utils.db_utils migrate

# Reset database (⚠️ destroys data)
python -m wrdata.utils.db_utils init --drop
```

---

## Troubleshooting

### TimescaleDB Connection Issues

**Problem:** `connection refused` or `could not connect to server`

**Solution:**
```bash
# Check if container is running
docker ps | grep timescaledb

# If not running, start it
docker-compose up -d timescaledb

# Check logs for errors
docker-compose logs timescaledb

# Verify port 5432 is not in use
lsof -i :5432  # On Linux/Mac
netstat -ano | findstr :5432  # On Windows
```

### TimescaleDB Extension Not Found

**Problem:** `extension "timescaledb" does not exist`

**Solution:**
```bash
# Recreate the database
docker-compose down -v
docker-compose up -d timescaledb

# Wait for initialization
docker-compose logs -f timescaledb
# Look for: "TimescaleDB initialized successfully"
```

### Redis Connection Issues

**Problem:** `Error connecting to Redis`

**Solution:**
```bash
# Check if Redis is running
docker-compose ps redis

# Test connection
docker exec -it wrdata-redis redis-cli ping
# Should return: PONG

# Check logs
docker-compose logs redis
```

### Python Import Errors

**Problem:** `ModuleNotFoundError: No module named 'wrdata'`

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall in development mode
pip install -e .

# Verify installation
python -c "import wrdata; print(wrdata.__version__)"
```

### API Rate Limiting

**Problem:** `Rate limit exceeded` from data providers

**Solution:**
- Add delays between requests
- Use rate limiting utilities (tenacity, aiolimiter)
- Check provider-specific rate limits in docs

---

## Performance Testing

### Load Testing with Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class WRDataUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_ohlcv(self):
        self.client.get("/api/v1/ohlcv/SPY?interval=1d&start=2024-01-01")

    @task
    def get_options(self):
        self.client.get("/api/v1/options/AAPL")
```

Run load test:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

### Database Performance

```sql
-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE schemaname = 'timeseries'
ORDER BY idx_scan;

-- Vacuum analyze (optimize tables)
VACUUM ANALYZE timeseries.ohlcv_data;
```

---

## Best Practices

### 1. Environment Variables
- ✅ Never commit `.env` files
- ✅ Use `.env.example` as template
- ✅ Store secrets in environment, not code

### 2. Database Queries
- ✅ Use parameterized queries (avoid SQL injection)
- ✅ Create indexes for frequently queried columns
- ✅ Use `EXPLAIN ANALYZE` to optimize slow queries

### 3. Code Style
- ✅ Follow PEP 8 (use `black` for formatting)
- ✅ Type hints everywhere (use `mypy` for checking)
- ✅ Docstrings for public functions

### 4. Testing
- ✅ Write tests for new providers
- ✅ Use fixtures for database setup
- ✅ Mock external API calls in tests

### 5. Logging
- ✅ Use structured logging (JSON format)
- ✅ Include request IDs for tracing
- ✅ Log errors with full context

---

## Next Steps

1. ✅ Complete local setup
2. ⏭️ Implement first free provider (Binance)
3. ⏭️ Add API server (FastAPI)
4. ⏭️ Implement authentication (JWT)
5. ⏭️ Deploy to staging (DigitalOcean)

---

## Getting Help

- **Documentation:** `/docs` folder
- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Community:** Discord (link TBD)

Happy coding! 🚀
