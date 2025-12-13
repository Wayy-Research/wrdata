"""
Whale detection utilities for identifying large volume transactions.

Implements percentile-based detection algorithms for real-time whale transaction monitoring.
"""

from collections import deque
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Tuple, Deque
import numpy as np
from threading import Lock


class VolumeTracker:
    """
    Tracks transaction volumes for percentile-based whale detection.

    Uses a rolling window approach to maintain recent transaction history
    and compute volume percentiles in real-time.
    """

    def __init__(
        self,
        window_size: int = 1000,
        time_window_seconds: Optional[int] = None,
        percentile_threshold: float = 99.0
    ):
        """
        Initialize volume tracker.

        Args:
            window_size: Number of transactions to keep in rolling window
            time_window_seconds: Optional time-based window (e.g., last 3600 seconds)
            percentile_threshold: Percentile threshold for whale detection (0-100)
        """
        self.window_size = window_size
        self.time_window_seconds = time_window_seconds
        self.percentile_threshold = percentile_threshold

        # Per-symbol tracking
        self._volumes: Dict[str, Deque[Tuple[float, datetime]]] = {}
        self._locks: Dict[str, Lock] = {}

        # Statistics cache
        self._stats_cache: Dict[str, Dict] = {}
        self._cache_invalidation: Dict[str, int] = {}

    def add_transaction(
        self,
        symbol: str,
        volume: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Add a transaction to the rolling window.

        Args:
            symbol: Trading symbol
            volume: Transaction volume
            timestamp: Transaction timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Initialize symbol tracking if needed
        if symbol not in self._volumes:
            self._volumes[symbol] = deque(maxlen=self.window_size)
            self._locks[symbol] = Lock()
            self._cache_invalidation[symbol] = 0

        with self._locks[symbol]:
            # Add to rolling window
            self._volumes[symbol].append((volume, timestamp))

            # Prune old entries if time window is set
            if self.time_window_seconds:
                cutoff_time = datetime.now() - timedelta(seconds=self.time_window_seconds)
                while self._volumes[symbol] and self._volumes[symbol][0][1] < cutoff_time:
                    self._volumes[symbol].popleft()

            # Invalidate cache
            self._cache_invalidation[symbol] += 1

    def is_whale_transaction(
        self,
        symbol: str,
        volume: float,
        percentile_threshold: Optional[float] = None
    ) -> Tuple[bool, Optional[float], Optional[int]]:
        """
        Check if a transaction qualifies as a whale transaction.

        Args:
            symbol: Trading symbol
            volume: Transaction volume to check
            percentile_threshold: Override default threshold

        Returns:
            Tuple of (is_whale, percentile, rank)
            - is_whale: True if volume exceeds threshold
            - percentile: Volume percentile (0-100)
            - rank: Rank among recent transactions (1 = largest)
        """
        if symbol not in self._volumes or len(self._volumes[symbol]) == 0:
            # No history yet - cannot determine
            return False, None, None

        threshold = percentile_threshold or self.percentile_threshold

        with self._locks[symbol]:
            volumes = [v for v, _ in self._volumes[symbol]]

            # Calculate percentile
            if len(volumes) < 2:
                percentile = 100.0  # Single transaction is always top percentile
            else:
                percentile = float(np.percentile(volumes, (volume >= np.array(volumes)).mean() * 100))

            # Calculate rank
            sorted_volumes = sorted(volumes, reverse=True)
            rank = sorted_volumes.index(volume) + 1 if volume in sorted_volumes else len(sorted_volumes) + 1

            is_whale = percentile >= threshold

            return is_whale, percentile, rank

    def get_statistics(self, symbol: str) -> Dict:
        """
        Get volume statistics for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with mean, median, std, min, max, percentiles
        """
        if symbol not in self._volumes:
            return {}

        # Check cache
        if symbol in self._stats_cache and self._cache_invalidation[symbol] == 0:
            return self._stats_cache[symbol]

        with self._locks[symbol]:
            volumes = [v for v, _ in self._volumes[symbol]]

            if not volumes:
                return {}

            volumes_array = np.array(volumes)

            stats = {
                'count': len(volumes),
                'mean': float(np.mean(volumes_array)),
                'median': float(np.median(volumes_array)),
                'std': float(np.std(volumes_array)),
                'min': float(np.min(volumes_array)),
                'max': float(np.max(volumes_array)),
                'p50': float(np.percentile(volumes_array, 50)),
                'p75': float(np.percentile(volumes_array, 75)),
                'p90': float(np.percentile(volumes_array, 90)),
                'p95': float(np.percentile(volumes_array, 95)),
                'p99': float(np.percentile(volumes_array, 99)),
                'p99_9': float(np.percentile(volumes_array, 99.9)),
            }

            # Cache results
            self._stats_cache[symbol] = stats
            self._cache_invalidation[symbol] = 0

            return stats

    def get_threshold_volume(self, symbol: str, percentile: float = 99.0) -> Optional[float]:
        """
        Get the volume threshold for a given percentile.

        Args:
            symbol: Trading symbol
            percentile: Desired percentile (0-100)

        Returns:
            Volume threshold at the specified percentile
        """
        if symbol not in self._volumes or len(self._volumes[symbol]) == 0:
            return None

        with self._locks[symbol]:
            volumes = [v for v, _ in self._volumes[symbol]]
            if len(volumes) < 2:
                return volumes[0] if volumes else None

            return float(np.percentile(volumes, percentile))

    def clear(self, symbol: Optional[str] = None) -> None:
        """
        Clear tracking data.

        Args:
            symbol: Symbol to clear (None = clear all)
        """
        if symbol:
            if symbol in self._volumes:
                with self._locks[symbol]:
                    self._volumes[symbol].clear()
                    self._cache_invalidation[symbol] = 0
                    if symbol in self._stats_cache:
                        del self._stats_cache[symbol]
        else:
            for sym in list(self._volumes.keys()):
                self.clear(sym)


class WhaleDetector:
    """
    High-level whale detection coordinator.

    Manages multiple volume trackers and provides unified whale detection
    across different symbols and exchanges.
    """

    def __init__(
        self,
        default_percentile: float = 99.0,
        window_size: int = 1000,
        time_window_seconds: Optional[int] = 3600,
        min_usd_value: Optional[float] = None
    ):
        """
        Initialize whale detector.

        Args:
            default_percentile: Default percentile threshold
            window_size: Number of transactions in rolling window
            time_window_seconds: Time-based window in seconds
            min_usd_value: Minimum USD value to consider as whale
        """
        self.default_percentile = default_percentile
        self.window_size = window_size
        self.time_window_seconds = time_window_seconds
        self.min_usd_value = min_usd_value

        # Per-exchange trackers
        self._trackers: Dict[str, VolumeTracker] = {}
        self._global_tracker = VolumeTracker(
            window_size=window_size,
            time_window_seconds=time_window_seconds,
            percentile_threshold=default_percentile
        )

    def get_tracker(self, exchange: Optional[str] = None) -> VolumeTracker:
        """
        Get volume tracker for an exchange.

        Args:
            exchange: Exchange name (None = global tracker)

        Returns:
            VolumeTracker instance
        """
        if exchange is None:
            return self._global_tracker

        if exchange not in self._trackers:
            self._trackers[exchange] = VolumeTracker(
                window_size=self.window_size,
                time_window_seconds=self.time_window_seconds,
                percentile_threshold=self.default_percentile
            )

        return self._trackers[exchange]

    def process_transaction(
        self,
        symbol: str,
        volume: float,
        price: float,
        exchange: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        percentile_threshold: Optional[float] = None
    ) -> Tuple[bool, Dict]:
        """
        Process a transaction and determine if it's a whale transaction.

        Args:
            symbol: Trading symbol
            volume: Transaction volume
            price: Transaction price
            exchange: Exchange name
            timestamp: Transaction timestamp
            percentile_threshold: Custom percentile threshold

        Returns:
            Tuple of (is_whale, metadata)
        """
        usd_value = volume * price

        # Check absolute USD value threshold if set
        if self.min_usd_value and usd_value < self.min_usd_value:
            return False, {'reason': 'below_min_usd_value'}

        # Get appropriate tracker
        tracker = self.get_tracker(exchange)

        # Add to history
        tracker.add_transaction(symbol, volume, timestamp)

        # Check if whale
        is_whale, percentile, rank = tracker.is_whale_transaction(
            symbol, volume, percentile_threshold
        )

        metadata = {
            'percentile': percentile,
            'rank': rank,
            'usd_value': usd_value,
            'statistics': tracker.get_statistics(symbol)
        }

        return is_whale, metadata

    def get_all_statistics(self) -> Dict[str, Dict]:
        """
        Get statistics for all tracked symbols across all exchanges.

        Returns:
            Dictionary mapping (exchange, symbol) to statistics
        """
        all_stats = {}

        # Global tracker stats
        for symbol in list(self._global_tracker._volumes.keys()):
            key = f"global:{symbol}"
            all_stats[key] = self._global_tracker.get_statistics(symbol)

        # Per-exchange tracker stats
        for exchange, tracker in self._trackers.items():
            for symbol in list(tracker._volumes.keys()):
                key = f"{exchange}:{symbol}"
                all_stats[key] = tracker.get_statistics(symbol)

        return all_stats
