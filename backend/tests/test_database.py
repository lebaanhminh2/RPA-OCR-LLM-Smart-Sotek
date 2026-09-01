from pathlib import Path

from sqlalchemy import text

from app.infra.db.database import (
    create_session_factory,
    create_sqlite_engine,
    verify_database_connection,
)


def test_sqlite_connection_and_session_factory(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    test_engine = create_sqlite_engine(
        f"sqlite:///{database_path.as_posix()}"
    )

    try:
        verify_database_connection(test_engine)
        session_factory = create_session_factory(test_engine)

        with session_factory() as session:
            result = session.execute(text("SELECT 1")).scalar_one()

        assert result == 1
        assert database_path.exists()
    finally:
        test_engine.dispose()
