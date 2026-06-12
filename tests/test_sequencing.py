import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.sequencing import get_next_invoice_number
import threading
from concurrent.futures import ThreadPoolExecutor
import os

# Setup an in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    # We also need the sequences table which is created via schema.sql
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS sequences (name TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0)"))
        conn.commit()
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_sequential_numbering(db):
    # First invoice
    num1 = get_next_invoice_number(db)
    assert num1 == "F-001"
    
    # Second invoice
    num2 = get_next_invoice_number(db)
    assert num2 == "F-002"
    
    # Third invoice
    num3 = get_next_invoice_number(db)
    assert num3 == "F-003"

def test_concurrent_numbering():
    # We need a real file for concurrent tests because :memory: is per-connection
    db_path = "test_concurrent.db"
    engine_concurrent = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal_concurrent = sessionmaker(autocommit=False, autoflush=False, bind=engine_concurrent)
    
    with engine_concurrent.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS sequences (name TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0)"))
        conn.commit()

    def get_num():
        session = SessionLocal_concurrent()
        try:
            num = get_next_invoice_number(session)
            session.commit()
            return num
        finally:
            session.close()

    # Use ThreadPoolExecutor to simulate concurrent requests
    num_requests = 50
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: get_num(), range(num_requests)))

    # Check that all numbers are unique and sequential
    results.sort()
    expected = [f"F-{i:03d}" for i in range(1, num_requests + 1)]
    assert results == expected

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
