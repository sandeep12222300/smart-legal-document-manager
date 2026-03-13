"""
database.py — SQLAlchemy engine, session factory, and Base declaration.

Uses SQLite by default (legal_docs.db) for zero-config local development.
Swap DATABASE_URL to a PostgreSQL connection string for production:
  postgresql+psycopg2://user:password@host/dbname
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./legal_docs.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base shared across all ORM models."""
    pass


def get_db():
    """FastAPI dependency that yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
