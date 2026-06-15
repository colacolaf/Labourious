from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from backend.database.models import Base
from backend.utils.logger import logger


_engine = None
_SessionLocal = None


def get_engine(database_url: str):
    global _engine
    if _engine is not None:
        return _engine

    connect_args = {}
    kwargs = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        kwargs["poolclass"] = StaticPool

        db_path = database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_engine(
        database_url,
        connect_args=connect_args,
        echo=False,
        **kwargs,
    )

    if database_url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    logger.info(f"Database engine created: {database_url}")
    return _engine


def get_session_factory(database_url: str) -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is not None:
        return _SessionLocal

    engine = get_engine(database_url)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_db(database_url: str) -> None:
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def drop_db(database_url: str) -> None:
    engine = get_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


@contextmanager
def get_db_session(database_url: str) -> Generator[Session, None, None]:
    factory = get_session_factory(database_url)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db(database_url: str):
    factory = get_session_factory(database_url)
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()
