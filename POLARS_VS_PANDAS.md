# Polars vs Pandas - Quick Guide for wrdata Users

## The Big Difference: No Index in Polars

**Polars does NOT have an index concept like Pandas.**

This is by design - Polars focuses on pure columnar operations without the overhead of maintaining an index.

## Your Questions Answered

### 1. Why is timestamp on the right instead of left?

**Answer:** Column order in Polars comes from the data source.

If the data provider returns a dict like:
```python
{"open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000, "timestamp": "2024-01-01"}
```

Then `timestamp` will be the last column. The order depends on how each provider structures their response.

**Fix:** You can reorder columns:
```python
# Reorder columns
df = df.select(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
```

### 2. Is timestamp indexed? Should it be?

**Answer:** No, Polars doesn't have indexes at all.

In Pandas, you would do:
```python
df = df.set_index('timestamp')
```

In Polars, there is no index. If you need "indexed" behavior, you:
1. Keep timestamp as a regular column
2. Sort by timestamp
3. Use timestamp in your queries/filters

**Polars approach:**
```python
# Sort by timestamp (fast!)
df = df.sort('timestamp')

# Filter by timestamp
df_filtered = df.filter(pl.col('timestamp') > '2024-01-01')

# No need for .loc or .iloc - just use column operations
```

## Converting to Pandas (If You Prefer It)

```python
from wrdata import DataStream

stream = DataStream()
df_polars = stream.get("AAPL")

# Convert to Pandas
df_pandas = df_polars.to_pandas()

# Set datetime index (like you're used to)
df_pandas['timestamp'] = pd.to_datetime(df_pandas['timestamp'])
df_pandas = df_pandas.set_index('timestamp')

# Now you have familiar Pandas DataFrame with datetime index
```

## Polars vs Pandas API Comparison

### Creating DataFrames

**Pandas:**
```python
import pandas as pd

df = pd.DataFrame({
    'timestamp': ['2024-01-01', '2024-01-02'],
    'close': [100, 105]
})
df = df.set_index('timestamp')
```

**Polars:**
```python
import polars as pl

df = pl.DataFrame({
    'timestamp': ['2024-01-01', '2024-01-02'],
    'close': [100, 105]
})
# No index needed!
```

### Selecting Columns

**Pandas:**
```python
# Single column
df['close']
df.close

# Multiple columns
df[['open', 'close']]
```

**Polars:**
```python
# Single column
df['close']
df.select('close')

# Multiple columns
df[['open', 'close']]
df.select(['open', 'close'])
df.select(pl.col('open'), pl.col('close'))
```

### Filtering Rows

**Pandas:**
```python
# Filter
df[df['close'] > 100]

# Multiple conditions
df[(df['close'] > 100) & (df['volume'] > 1000)]

# By index
df.loc['2024-01-01':'2024-01-10']
```

**Polars:**
```python
# Filter
df.filter(pl.col('close') > 100)

# Multiple conditions
df.filter(
    (pl.col('close') > 100) &
    (pl.col('volume') > 1000)
)

# By timestamp (no index needed)
df.filter(
    (pl.col('timestamp') >= '2024-01-01') &
    (pl.col('timestamp') <= '2024-01-10')
)
```

### Sorting

**Pandas:**
```python
df.sort_values('close')
df.sort_index()
```

**Polars:**
```python
df.sort('close')
df.sort('timestamp')

# Multiple columns
df.sort(['timestamp', 'close'])
```

### Aggregations

**Pandas:**
```python
df['close'].mean()
df.groupby('symbol').agg({'close': 'mean'})
```

**Polars:**
```python
df['close'].mean()
df.group_by('symbol').agg(pl.col('close').mean())

# Can do multiple at once (faster!)
df.group_by('symbol').agg([
    pl.col('close').mean().alias('avg_close'),
    pl.col('volume').sum().alias('total_volume')
])
```

### Adding Columns

**Pandas:**
```python
df['returns'] = df['close'].pct_change()
df['sma_20'] = df['close'].rolling(20).mean()
```

**Polars:**
```python
df = df.with_columns([
    pl.col('close').pct_change().alias('returns'),
    pl.col('close').rolling_mean(window_size=20).alias('sma_20')
])
```

### Method Chaining (Polars Shines Here!)

**Pandas:**
```python
df = (df
    .query('close > 100')
    .assign(returns=lambda x: x['close'].pct_change())
    .dropna()
    .sort_values('timestamp')
)
```

**Polars:**
```python
df = (df
    .filter(pl.col('close') > 100)
    .with_columns(pl.col('close').pct_change().alias('returns'))
    .drop_nulls()
    .sort('timestamp')
)
```

## Key Advantages of Polars

### 1. **Speed** - Much faster than Pandas
```python
# Polars is often 5-10x faster for large datasets
df.filter(pl.col('close') > 100)  # Blazing fast!
```

### 2. **Memory Efficient** - Uses less RAM
```python
# Polars uses Apache Arrow format - very memory efficient
```

### 3. **Lazy Evaluation** - Optimize queries before execution
```python
# Build query
lazy_df = pl.scan_parquet('data.parquet')
result = (lazy_df
    .filter(pl.col('close') > 100)
    .group_by('symbol')
    .agg(pl.col('close').mean())
)

# Execute (Polars optimizes the whole query!)
df = result.collect()
```

### 4. **Better Parallelization** - Uses all CPU cores automatically
```python
# Polars automatically uses all cores - no configuration needed!
```

### 5. **Type Safety** - Strict typing prevents errors
```python
# Polars enforces types strictly
df.select(pl.col('close').cast(pl.Float64))
```

## When to Use Each?

### Use Polars When:
- ✅ Working with large datasets (> 1GB)
- ✅ Performance matters
- ✅ Writing new code
- ✅ You don't need time-series specific features
- ✅ Method chaining and clean code

### Use Pandas When:
- ✅ Need datetime index features (resample, asfreq, etc.)
- ✅ Using libraries that only support Pandas (matplotlib, seaborn)
- ✅ Existing codebase is Pandas
- ✅ Need advanced time-series methods
- ✅ Lots of existing Pandas knowledge

## Best Practice for wrdata

**Recommended approach:**

```python
from wrdata import DataStream
import polars as pl

stream = DataStream()

# Get data as Polars (default)
df = stream.get("AAPL")

# Sort by timestamp
df = df.sort('timestamp')

# Do your analysis in Polars (fast!)
returns = df.with_columns(
    pl.col('close').pct_change().alias('returns')
)

# Convert to Pandas only if needed
if need_pandas:
    df_pandas = df.to_pandas()
    df_pandas = df_pandas.set_index('timestamp')
```

## Quick Reference

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Select columns | `df[['a', 'b']]` | `df.select(['a', 'b'])` |
| Filter rows | `df[df.a > 5]` | `df.filter(pl.col('a') > 5)` |
| Add column | `df['new'] = df.a * 2` | `df.with_columns((pl.col('a') * 2).alias('new'))` |
| Sort | `df.sort_values('a')` | `df.sort('a')` |
| Group by | `df.groupby('a').sum()` | `df.group_by('a').sum()` |
| Mean | `df['a'].mean()` | `df['a'].mean()` |
| Rolling mean | `df['a'].rolling(20).mean()` | `df['a'].rolling_mean(20)` |
| Drop nulls | `df.dropna()` | `df.drop_nulls()` |
| Unique | `df['a'].unique()` | `df['a'].unique()` |
| Head | `df.head(10)` | `df.head(10)` |

## Bottom Line

**Polars is the future** - it's faster, more memory efficient, and has a cleaner API.

**For wrdata:**
- We use Polars by default for performance
- Easy to convert to Pandas if needed: `df.to_pandas()`
- Timestamp is just a regular column (no special index)
- Sort by timestamp when you need chronological order

**The "no index" thing is actually a feature, not a bug** - it simplifies the API and improves performance!
