from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[3]
DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'smart_sotek.db').as_posix()}"


def create_sqlite_engine(database_url: str) -> Engine:
    return create_engine(database_url)


def create_session_factory(database_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=database_engine,
        autoflush=False,
        expire_on_commit=False,
    )


def verify_database_connection(database_engine: Engine) -> None:
    with database_engine.connect() as connection:
        connection.execute(text("SELECT 1"))


engine = create_sqlite_engine(DATABASE_URL)
SessionFactory = create_session_factory(engine)
