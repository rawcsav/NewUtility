from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool
from app import db


def make_engine_with_pool_options():
    # Define your database URL
    database_url = current_app.config["SQLALCHEMY_DATABASE_URI"]

    # Configure engine with QueuePool and other options
    engine = create_engine(
        database_url,
        poolclass=QueuePool,  # Explicitly specify QueuePool, though it's the default
        pool_recycle=299,  # Example: recycle connections after 299 seconds
        pool_pre_ping=True,  # Test connections before using them
        pool_size=10,  # Maximum number of connections in the pool
        max_overflow=20,  # Allow up to 20 connections beyond `pool_size`
        # Add any other engine options here
    )
    return engine


# Use the custom engine with configured pool options for your session
def make_session():
    engine = make_engine_with_pool_options()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return scoped_session(SessionLocal)
