"""
Database models for wrdata package.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index, Float, Date, Numeric
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DataProvider(Base):
    """
    Data provider model representing external data sources.
    """
    __tablename__ = "data_providers"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    provider_type = Column(String(50), nullable=False)  # yfinance, binance, fred, etc.
    api_key_required = Column(Boolean, default=False)
    has_api_key = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    supported_assets = Column(Text, nullable=True)  # JSON array of asset types
    base_url = Column(String(500), nullable=True)
    rate_limit = Column(Integer, nullable=True)  # requests per minute
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    symbols = relationship("Symbol", back_populates="provider", cascade="all, delete-orphan")


class Symbol(Base):
    """
    Symbol model representing tradeable assets across providers.
    """
    __tablename__ = "symbols"
    __table_args__ = (
        Index('idx_symbol_provider', 'symbol', 'provider_id'),
        Index('idx_asset_type', 'asset_type'),
        Index('idx_exchange', 'exchange'),
    )

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("data_providers.id"), nullable=False)
    symbol = Column(String(50), nullable=False)
    name = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    asset_type = Column(String(50), nullable=True)  # stock, crypto, forex, bond, etc.
    exchange = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=True)
    extra_metadata = Column(Text, nullable=True)  # JSON for additional provider-specific data
    is_active = Column(Boolean, default=True)
    last_verified = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    provider = relationship("DataProvider", back_populates="symbols")
    options_contracts = relationship("OptionsContract", back_populates="underlying_symbol", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Symbol(symbol='{self.symbol}', provider='{self.provider.name if self.provider else 'N/A'}', type='{self.asset_type}')>"


class OptionsContract(Base):
    """
    Options contract metadata - represents a specific options contract.
    """
    __tablename__ = "options_contracts"
    __table_args__ = (
        Index('idx_underlying_expiry', 'underlying_symbol_id', 'expiration_date'),
        Index('idx_contract_symbol', 'contract_symbol'),
        Index('idx_option_type_strike', 'option_type', 'strike_price'),
    )

    id = Column(Integer, primary_key=True)
    underlying_symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    contract_symbol = Column(String(100), unique=True, nullable=False)  # e.g., "AAPL250117C00150000"
    option_type = Column(String(10), nullable=False)  # "call" or "put"
    strike_price = Column(Numeric(precision=12, scale=4), nullable=False)
    expiration_date = Column(Date, nullable=False)
    exchange = Column(String(100), nullable=True)
    contract_size = Column(Integer, default=100)  # Typically 100 shares per contract
    currency = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    underlying_symbol = relationship("Symbol", back_populates="options_contracts")
    chain_snapshots = relationship("OptionsChainSnapshot", back_populates="contract", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OptionsContract(symbol='{self.contract_symbol}', type='{self.option_type}', strike={self.strike_price}, expiry='{self.expiration_date}')>"


class OptionsChainSnapshot(Base):
    """
    Point-in-time snapshot of options chain data.
    Stores historical timeseries of options prices, greeks, and other metrics.
    """
    __tablename__ = "options_chain_snapshots"
    __table_args__ = (
        Index('idx_contract_timestamp', 'contract_id', 'snapshot_timestamp'),
        Index('idx_snapshot_timestamp', 'snapshot_timestamp'),
        Index('idx_provider_snapshot', 'provider_id', 'snapshot_timestamp'),
    )

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("options_contracts.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("data_providers.id"), nullable=False)
    snapshot_timestamp = Column(DateTime, nullable=False)

    # Price data
    bid = Column(Numeric(precision=12, scale=4), nullable=True)
    ask = Column(Numeric(precision=12, scale=4), nullable=True)
    last_price = Column(Numeric(precision=12, scale=4), nullable=True)
    mark_price = Column(Numeric(precision=12, scale=4), nullable=True)  # (bid + ask) / 2

    # Volume and interest
    volume = Column(Integer, nullable=True)
    open_interest = Column(Integer, nullable=True)

    # Greeks
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    rho = Column(Float, nullable=True)

    # Volatility metrics
    implied_volatility = Column(Float, nullable=True)

    # Additional metrics
    intrinsic_value = Column(Numeric(precision=12, scale=4), nullable=True)
    extrinsic_value = Column(Numeric(precision=12, scale=4), nullable=True)
    in_the_money = Column(Boolean, nullable=True)

    # Underlying price at snapshot time
    underlying_price = Column(Numeric(precision=12, scale=4), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contract = relationship("OptionsContract", back_populates="chain_snapshots")
    provider = relationship("DataProvider")

    def __repr__(self):
        return f"<OptionsChainSnapshot(contract_id={self.contract_id}, timestamp='{self.snapshot_timestamp}', last={self.last_price}, iv={self.implied_volatility})>"
