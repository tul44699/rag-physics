import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Ensure server modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from db import Base, get_db
from services import ingest_textbook

TEST_DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/physics_rag_test"


@pytest.fixture(scope="session")
def engine():
    """Create test database engine, drop/create test db."""
    # Create test database
    root_engine = create_engine(
        "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
        isolation_level="AUTOCOMMIT",
    )
    with root_engine.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS physics_rag_test"))
        conn.execute(text("CREATE DATABASE physics_rag_test"))
    root_engine.dispose()

    eng = create_engine(TEST_DB_URL, pool_pre_ping=True)
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture
def db(engine):
    """Provide a database session, rollback after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_pdf_path():
    path = Path(__file__).parent / "data" / "test_physics.pdf"
    assert path.exists(), f"Test PDF not found at {path}"
    return str(path)


@pytest.fixture
def ingested_textbook(db, test_pdf_path):
    """Ingest the test PDF and return (textbook_id, chunk_count)."""
    return ingest_textbook(
        db=db,
        title="Test Physics Textbook",
        pdf_path=test_pdf_path,
        group_name="test",
        chapter_hint="Newton's Laws",
        chunk_size=600,
        chunk_overlap=100,
    )
