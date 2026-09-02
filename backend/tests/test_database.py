from pathlib import Path

from sqlalchemy import inspect, text

from app.infra.db.database import (
    create_session_factory,
    create_sqlite_engine,
    ensure_ocr_block_kind_column,
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


def test_adds_text_kind_to_legacy_ocr_blocks_table(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    test_engine = create_sqlite_engine(
        f"sqlite:///{database_path.as_posix()}"
    )

    try:
        with test_engine.begin() as connection:
            connection.execute(
                text("CREATE TABLE ocr_blocks (id VARCHAR PRIMARY KEY)")
            )
            connection.execute(
                text("INSERT INTO ocr_blocks (id) VALUES ('legacy-block')")
            )

        ensure_ocr_block_kind_column(test_engine)
        ensure_ocr_block_kind_column(test_engine)

        columns = {
            column["name"]
            for column in inspect(test_engine).get_columns("ocr_blocks")
        }
        with test_engine.connect() as connection:
            kind = connection.execute(
                text(
                    "SELECT block_kind FROM ocr_blocks "
                    "WHERE id = 'legacy-block'"
                )
            ).scalar_one()

        assert "block_kind" in columns
        assert kind == "TEXT"
    finally:
        test_engine.dispose()
