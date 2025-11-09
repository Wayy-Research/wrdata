# Testing Guide for WRData

This document provides comprehensive information about testing in the WRData package.

## Table of Contents

- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Writing Tests](#writing-tests)
- [CI/CD](#cicd)

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── unit/                    # Fast, isolated unit tests
│   ├── test_config.py
│   ├── test_providers.py
│   └── test_data_fetcher.py
├── integration/             # Tests that hit external APIs
│   └── test_yfinance_integration.py
└── fixtures/                # Test data and mock objects
```

### Test Types

- **Unit Tests**: Fast, isolated tests that mock external dependencies
  - Mark with `@pytest.mark.unit`
  - Should run in < 1 second each
  - No external API calls

- **Integration Tests**: Tests that make real API calls
  - Mark with `@pytest.mark.integration`
  - May be slow or rate-limited
  - Mark network-dependent tests with `@pytest.mark.requires_network`

## Running Tests

### Basic Usage

```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run tests with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_provider"
```

### With Coverage

```bash
# Run with coverage report
pytest --cov=wrdata --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=wrdata --cov-report=html
open htmlcov/index.html

# Generate XML coverage (for CI)
pytest --cov=wrdata --cov-report=xml
```

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/unit/test_config.py

# Run a specific test class
pytest tests/unit/test_providers.py::TestYFinanceProvider

# Run a specific test method
pytest tests/unit/test_providers.py::TestYFinanceProvider::test_initialization
```

### Using Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Skip tests requiring API keys
pytest -m "not requires_api_key"
```

## Test Coverage

### Current Coverage

Run `pytest --cov=wrdata --cov-report=term` to see current coverage:

```
Name                                    Stmts   Miss   Cover
--------------------------------------------------------------
wrdata/core/config.py                      82      1  98.78%
wrdata/providers/base.py                   12      1  91.67%
wrdata/providers/binance_provider.py       78     32  58.97%
wrdata/providers/yfinance_provider.py     123     91  26.02%
wrdata/services/data_fetcher.py            55      6  89.09%
--------------------------------------------------------------
TOTAL                                     954    476  50.10%
```

### Coverage Goals

- **Overall target**: 80%+
- **Critical modules** (core, services): 90%+
- **Provider modules**: 60%+ (harder to test without mocking external APIs)

### Viewing Coverage Reports

```bash
# Generate HTML report
pytest --cov=wrdata --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Writing Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Unit Test

```python
import pytest
from wrdata.providers.yfinance_provider import YFinanceProvider

@pytest.mark.unit
class TestYFinanceProvider:
    """Test YFinance provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = YFinanceProvider()

        assert provider.name == 'yfinance'
        assert provider.api_key is None

    def test_supports_historical_options(self):
        """Test that YFinance doesn't support historical options."""
        provider = YFinanceProvider()

        assert provider.supports_historical_options() is False
```

### Example Integration Test

```python
import pytest
from datetime import datetime, timedelta
from wrdata.providers.yfinance_provider import YFinanceProvider

@pytest.mark.integration
@pytest.mark.requires_network
class TestYFinanceIntegration:
    """Integration tests for YFinance provider."""

    def test_fetch_stock_data(self, skip_if_no_network):
        """Test fetching real stock data."""
        provider = YFinanceProvider()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        response = provider.fetch_timeseries(
            symbol='AAPL',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval='1d'
        )

        assert response.success is True
        assert len(response.data) > 0
```

### Using Fixtures

Fixtures are defined in `tests/conftest.py`:

```python
def test_with_db_session(test_db_session):
    """Test using database session fixture."""
    # test_db_session is an in-memory SQLite database
    # pre-populated with test data
    pass

def test_with_sample_data(mock_ohlcv_data):
    """Test using mock OHLCV data."""
    # mock_ohlcv_data provides sample data
    assert len(mock_ohlcv_data) > 0
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test using mocks."""
    with patch('wrdata.providers.yfinance_provider.yf.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {'symbol': 'AAPL'}

        # Your test code here
        provider = YFinanceProvider()
        result = provider.validate_connection()

        assert result is True
```

## CI/CD

### GitHub Actions

Tests run automatically on:
- Every push to `main` and `develop` branches
- Every pull request

Workflow files:
- `.github/workflows/test.yml` - Main test workflow
- `.github/workflows/coverage-badge.yml` - Coverage badge generation

### Test Workflow

1. **Unit Tests**: Run on Python 3.10, 3.11, 3.12
2. **Integration Tests**: Run on Python 3.10 (may be flaky)
3. **Linting**: Check code formatting, linting, and type hints
4. **Coverage**: Generate coverage report and badge

### Setting Up Coverage Badge

To enable the coverage badge on GitHub:

1. Create a GitHub Gist for storing the badge data
2. Generate a GitHub token with gist permissions
3. Add secrets to your repository:
   - `GIST_TOKEN`: GitHub personal access token
   - `GIST_ID`: ID of the gist (from the URL)

### Pre-commit Hooks

Install pre-commit hooks to run tests before committing:

```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest unit tests
        entry: pytest tests/unit/
        language: system
        pass_filenames: false
        always_run: true
```

## Best Practices

1. **Write tests first** (TDD) when adding new features
2. **Keep tests fast** - mock external dependencies in unit tests
3. **Use descriptive test names** that explain what is being tested
4. **Test edge cases** and error conditions
5. **Maintain high coverage** on critical code paths
6. **Use fixtures** to avoid code duplication
7. **Mark tests appropriately** (unit, integration, slow, etc.)
8. **Keep tests isolated** - each test should be independent

## Troubleshooting

### Tests Failing Locally

```bash
# Clear pytest cache
pytest --cache-clear

# Run tests in verbose mode
pytest -vv

# Show local variables on failure
pytest --showlocals
```

### Coverage Not Accurate

```bash
# Delete coverage data and re-run
rm .coverage
pytest --cov=wrdata --cov-report=term
```

### Integration Tests Timing Out

```bash
# Run with longer timeout
pytest tests/integration/ --timeout=60
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
