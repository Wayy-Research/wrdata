"""
Database utility functions for managing database schema and migrations.
"""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional
import os

from wrdata.models.database import Base, DataProvider, Symbol, OptionsContract, OptionsChainSnapshot


def get_engine(database_url: Optional[str] = None):
    """
    Get SQLAlchemy engine.

    Args:
        database_url: Database URL. If None, uses WRDATA_DATABASE_URL env var
                      or defaults to sqlite://wrdata.db

    Returns:
        SQLAlchemy engine
    """
    if database_url is None:
        database_url = os.getenv(
            'WRDATA_DATABASE_URL',
            'sqlite:///wrdata.db'
        )

    return create_engine(database_url, echo=False)


def get_session(database_url: Optional[str] = None) -> Session:
    """
    Get SQLAlchemy session.

    Args:
        database_url: Database URL. If None, uses default

    Returns:
        SQLAlchemy session
    """
    engine = get_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_database(database_url: Optional[str] = None, drop_existing: bool = False):
    """
    Initialize the database with all tables.

    Args:
        database_url: Database URL. If None, uses default
        drop_existing: If True, drop all existing tables before creating

    Returns:
        SQLAlchemy engine
    """
    engine = get_engine(database_url)

    if drop_existing:
        print("Dropping existing tables...")
        Base.metadata.drop_all(engine)

    print("Creating tables...")
    Base.metadata.create_all(engine)

    # Verify tables were created
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"Created {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")

    return engine


def verify_database_schema(database_url: Optional[str] = None) -> bool:
    """
    Verify that all required tables exist in the database.

    Args:
        database_url: Database URL. If None, uses default

    Returns:
        True if all tables exist, False otherwise
    """
    engine = get_engine(database_url)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    required_tables = {
        'data_providers',
        'symbols',
        'options_contracts',
        'options_chain_snapshots'
    }

    missing_tables = required_tables - existing_tables

    if missing_tables:
        print(f"Missing tables: {missing_tables}")
        return False

    print("All required tables exist")
    return True


def migrate_add_options_tables(database_url: Optional[str] = None):
    """
    Migration: Add options chain tables to existing database.

    This migration adds:
    - options_contracts table
    - options_chain_snapshots table

    Args:
        database_url: Database URL. If None, uses default
    """
    engine = get_engine(database_url)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    print("Running migration: Add options tables")

    # Only create options tables if they don't exist
    tables_to_create = []

    if 'options_contracts' not in existing_tables:
        tables_to_create.append('options_contracts')

    if 'options_chain_snapshots' not in existing_tables:
        tables_to_create.append('options_chain_snapshots')

    if not tables_to_create:
        print("Options tables already exist, skipping migration")
        return

    print(f"Creating tables: {tables_to_create}")

    # Create only the options tables
    for table in [OptionsContract.__table__, OptionsChainSnapshot.__table__]:
        if table.name in tables_to_create:
            table.create(engine, checkfirst=True)
            print(f"  Created table: {table.name}")

    print("Migration completed successfully")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "init":
            drop = "--drop" in sys.argv
            init_database(drop_existing=drop)

        elif command == "verify":
            verify_database_schema()

        elif command == "migrate":
            migrate_add_options_tables()

        else:
            print(f"Unknown command: {command}")
            print("Usage: python db_utils.py [init|verify|migrate] [--drop]")
    else:
        print("Usage: python db_utils.py [init|verify|migrate] [--drop]")
        print("  init    - Initialize database (use --drop to drop existing tables)")
        print("  verify  - Verify database schema")
        print("  migrate - Run migration to add options tables")
