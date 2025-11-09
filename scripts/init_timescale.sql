-- TimescaleDB Initialization Script for WRData
-- This script sets up the TimescaleDB extension and creates hypertables

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create schema for time-series data (separate from metadata)
CREATE SCHEMA IF NOT EXISTS timeseries;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA timeseries TO wrdata_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA timeseries TO wrdata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA timeseries GRANT ALL ON TABLES TO wrdata_user;

-- OHLCV Data Table (Hypertable for bars/candles)
CREATE TABLE IF NOT EXISTS timeseries.ohlcv_data (
    time TIMESTAMPTZ NOT NULL,
    symbol_id INTEGER NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(20, 8),
    trades INTEGER,  -- Number of trades (if available)
    interval TEXT NOT NULL,  -- '1m', '5m', '1h', '1d', etc.
    provider_id INTEGER NOT NULL,
    UNIQUE (time, symbol_id, interval, provider_id)
);

-- Convert to hypertable (partitioned by time)
SELECT create_hypertable(
    'timeseries.ohlcv_data',
    'time',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '7 days'  -- One chunk per week
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_time ON timeseries.ohlcv_data (symbol_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_interval ON timeseries.ohlcv_data (interval, time DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_provider ON timeseries.ohlcv_data (provider_id, time DESC);

-- Tick Data Table (Hypertable for trade-by-trade data)
CREATE TABLE IF NOT EXISTS timeseries.tick_data (
    time TIMESTAMPTZ NOT NULL,
    symbol_id INTEGER NOT NULL,
    price NUMERIC(20, 8) NOT NULL,
    size NUMERIC(20, 8) NOT NULL,  -- Quantity/volume of this trade
    side TEXT,  -- 'buy', 'sell', or NULL
    trade_id TEXT,  -- Exchange trade ID (if available)
    provider_id INTEGER NOT NULL
);

-- Convert to hypertable (partitioned by time)
SELECT create_hypertable(
    'timeseries.tick_data',
    'time',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'  -- One chunk per day (ticks are high volume)
);

-- Create indexes for tick data
CREATE INDEX IF NOT EXISTS idx_tick_symbol_time ON timeseries.tick_data (symbol_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_tick_provider ON timeseries.tick_data (provider_id, time DESC);

-- Order Book Snapshots (for crypto/high-frequency data)
CREATE TABLE IF NOT EXISTS timeseries.orderbook_snapshots (
    time TIMESTAMPTZ NOT NULL,
    symbol_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    bids JSONB NOT NULL,  -- Array of [price, size] pairs
    asks JSONB NOT NULL,  -- Array of [price, size] pairs
    checksum TEXT  -- Optional checksum for validation
);

-- Convert to hypertable
SELECT create_hypertable(
    'timeseries.orderbook_snapshots',
    'time',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- Create indexes for order book data
CREATE INDEX IF NOT EXISTS idx_orderbook_symbol_time ON timeseries.orderbook_snapshots (symbol_id, time DESC);

-- Compression policy (compress data older than 7 days)
SELECT add_compression_policy('timeseries.ohlcv_data', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('timeseries.tick_data', INTERVAL '3 days', if_not_exists => TRUE);
SELECT add_compression_policy('timeseries.orderbook_snapshots', INTERVAL '3 days', if_not_exists => TRUE);

-- Retention policy (drop data older than 1 year for free tier)
-- Commented out for development - enable in production with appropriate retention period
-- SELECT add_retention_policy('timeseries.ohlcv_data', INTERVAL '1 year', if_not_exists => TRUE);
-- SELECT add_retention_policy('timeseries.tick_data', INTERVAL '90 days', if_not_exists => TRUE);

-- Continuous aggregates for common queries (materialized views)
CREATE MATERIALIZED VIEW IF NOT EXISTS timeseries.ohlcv_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS time,
    symbol_id,
    provider_id,
    first(open, time) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, time) AS close,
    sum(volume) AS volume,
    sum(trades) AS trades
FROM timeseries.ohlcv_data
WHERE interval = '1m'  -- Aggregate from 1-minute data
GROUP BY time_bucket('1 hour', time), symbol_id, provider_id;

-- Refresh policy for continuous aggregates (every 10 minutes)
SELECT add_continuous_aggregate_policy('timeseries.ohlcv_1h',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes',
    if_not_exists => TRUE);

-- Create view for latest prices (fast lookup)
CREATE OR REPLACE VIEW timeseries.latest_prices AS
SELECT DISTINCT ON (symbol_id, interval)
    symbol_id,
    time,
    close AS price,
    volume,
    interval,
    provider_id
FROM timeseries.ohlcv_data
ORDER BY symbol_id, interval, time DESC;

-- Provider sync tracking table (not a hypertable - regular table)
CREATE TABLE IF NOT EXISTS timeseries.provider_sync_status (
    id SERIAL PRIMARY KEY,
    symbol_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    interval TEXT NOT NULL,
    last_sync_time TIMESTAMPTZ NOT NULL,
    last_data_timestamp TIMESTAMPTZ,  -- Latest data point fetched
    status TEXT NOT NULL,  -- 'success', 'failed', 'in_progress'
    error_message TEXT,
    records_fetched INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (symbol_id, provider_id, interval)
);

CREATE INDEX IF NOT EXISTS idx_sync_status ON timeseries.provider_sync_status (symbol_id, provider_id, interval);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
CREATE TRIGGER update_provider_sync_status_updated_at
    BEFORE UPDATE ON timeseries.provider_sync_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant all permissions on new tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA timeseries TO wrdata_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA timeseries TO wrdata_user;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'TimescaleDB initialized successfully for WRData!';
    RAISE NOTICE 'Created hypertables: ohlcv_data, tick_data, orderbook_snapshots';
    RAISE NOTICE 'Created continuous aggregate: ohlcv_1h';
    RAISE NOTICE 'Compression policies enabled for data older than 7 days';
END $$;
