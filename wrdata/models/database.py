"""
Database models for wrdata package.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index
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

    def __repr__(self):
        return f"<Symbol(symbol='{self.symbol}', provider='{self.provider.name if self.provider else 'N/A'}', type='{self.asset_type}')>"
