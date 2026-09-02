from pathlib import Path

from sqlalchemy import Engine, create_engine, inspect, text
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


def ensure_ocr_block_kind_column(database_engine: Engine) -> None:
    """Upgrade pre-M4 SQLite databases without replacing existing data."""
    inspector = inspect(database_engine)
    if "ocr_blocks" not in inspector.get_table_names():
        return
    if "block_kind" in {
        column["name"] for column in inspector.get_columns("ocr_blocks")
    }:
        return

    with database_engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE ocr_blocks "
                "ADD COLUMN block_kind VARCHAR(18) "
                "NOT NULL DEFAULT 'TEXT'"
            )
        )


engine = create_sqlite_engine(DATABASE_URL)
SessionFactory = create_session_factory(engine)
