"""
This module instantiates the database and tables.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from src.settings import settings
from sqlalchemy_utils import create_database, database_exists
from sqlmodel import Session as SQLModelSession
from sqlmodel import SQLModel, create_engine

last_generation_time = datetime.now() - timedelta(minutes=15)
cur_token = ""


def __get_engine():
    connection_uri = settings.DATABASE_URL
    if connection_uri[:9] == "postgres:":
        connection_uri = connection_uri.replace("postgres:", "postgresql:", 1)

    return create_engine(
        connection_uri,
        poolclass=NullPool,
        pool_size=10,
        isolation_level="READ COMMITTED",
    )


def create_db():
    """Initialize db with an engine"""
    engine = __get_engine()

    if db_exists():
        logging.warning(f"Database Already Exists, Proceeding...")
    else:
        logging.warning(f"Database Does Not Exist, Creating...")
        create_database(engine.url)

    # Import all models to be created by SQLModel engine.
    import src.models  # noqa

    SQLModel.metadata.create_all(engine)


def get_session():
    """
    Returns a new session object with the current engine

    :return: sqlmodel Session
    :rtype: session

    """
    Session = sessionmaker(bind=__get_engine(), class_=SQLModelSession)
    return Session()


def session_dep():
    """Yields a dbm session for dependency injection"""
    session = get_session()
    try:
        yield session
    finally:
        session.commit()
        session.close()


def db_exists():
    """
    Checks if the auth database exists
    :return: True if database exists, False otherwise
    """

    return database_exists(__get_engine().url)
