"""
Unit tests for Coinbase Level2 orderbook functionality.
"""

from wrdata.streaming.coinbase_stream import CoinbaseStreamProvider


def test_provider_init():
    """Test that provider initializes with orderbook tracking."""
    provider = CoinbaseStreamProvider()

    assert provider is not None
    assert hasattr(provider, '_orderbooks')
    assert isinstance(provider._orderbooks, dict)
    assert len(provider._orderbooks) == 0


def test_provider_has_depth_method():
    """Test that subscribe_depth method exists."""
    provider = CoinbaseStreamProvider()

    assert hasattr(provider, 'subscribe_depth')
    assert callable(provider.subscribe_depth)


def test_provider_has_snapshot_method():
    """Test that get_orderbook_snapshot method exists."""
    provider = CoinbaseStreamProvider()

    assert hasattr(provider, 'get_orderbook_snapshot')
    assert callable(provider.get_orderbook_snapshot)


def test_orderbook_snapshot_processing():
    """Test orderbook snapshot processing."""
    provider = CoinbaseStreamProvider()

    # Simulate snapshot message
    snapshot_msg = {
        'type': 'snapshot',
        'product_id': 'BTC-USD',
        'bids': [['50000.00', '0.5'], ['49999.00', '1.0']],
        'asks': [['50001.00', '0.3'], ['50002.00', '0.8']]
    }

    provider._orderbooks['BTC-USD'] = {'bids': {}, 'asks': {}}
    provider._process_snapshot('BTC-USD', snapshot_msg)

    orderbook = provider._orderbooks['BTC-USD']

    assert 50000.0 in orderbook['bids']
    assert orderbook['bids'][50000.0] == 0.5
    assert 49999.0 in orderbook['bids']

    assert 50001.0 in orderbook['asks']
    assert orderbook['asks'][50001.0] == 0.3
    assert 50002.0 in orderbook['asks']


def test_orderbook_update_processing():
    """Test orderbook incremental update processing."""
    provider = CoinbaseStreamProvider()

    # Initialize with some data
    provider._orderbooks['BTC-USD'] = {
        'bids': {50000.0: 0.5},
        'asks': {50001.0: 0.3}
    }

    # Simulate update message
    update_msg = {
        'type': 'l2update',
        'changes': [
            ['buy', '50000.00', '1.0'],  # Update existing bid
            ['sell', '50002.00', '0.5'],  # Add new ask
            ['buy', '49999.00', '0.0'],  # Remove bid (doesn't exist, should be safe)
        ]
    }

    provider._process_l2update('BTC-USD', update_msg)

    orderbook = provider._orderbooks['BTC-USD']

    # Check bid was updated
    assert orderbook['bids'][50000.0] == 1.0

    # Check new ask was added
    assert 50002.0 in orderbook['asks']
    assert orderbook['asks'][50002.0] == 0.5


def test_orderbook_message_creation():
    """Test creating StreamMessage from orderbook state."""
    provider = CoinbaseStreamProvider()

    # Set up orderbook
    provider._orderbooks['ETH-USD'] = {
        'bids': {3000.0: 1.0, 2999.0: 2.0, 2998.0: 1.5},
        'asks': {3001.0: 0.8, 3002.0: 1.2, 3003.0: 0.5}
    }

    msg = provider._create_orderbook_message('ETH-USD')

    assert msg.symbol == 'ETH-USD'
    assert msg.stream_type == 'depth'
    assert msg.bid == 3000.0  # Highest bid
    assert msg.ask == 3001.0  # Lowest ask
    assert msg.price == 3000.5  # Mid price
    assert len(msg.bids) == 3
    assert len(msg.asks) == 3

    # Check bids are sorted descending
    assert msg.bids[0][0] > msg.bids[1][0]

    # Check asks are sorted ascending
    assert msg.asks[0][0] < msg.asks[1][0]


def test_get_orderbook_snapshot():
    """Test getting current orderbook snapshot."""
    provider = CoinbaseStreamProvider()

    # No orderbook yet
    snapshot = provider.get_orderbook_snapshot('BTC-USD')
    assert snapshot is None

    # Add orderbook
    provider._orderbooks['BTC-USD'] = {
        'bids': {50000.0: 0.5},
        'asks': {50001.0: 0.3}
    }

    snapshot = provider.get_orderbook_snapshot('BTC-USD')
    assert snapshot is not None
    assert 'bids' in snapshot
    assert 'asks' in snapshot
    assert 50000.0 in snapshot['bids']


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
