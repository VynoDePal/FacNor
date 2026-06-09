"""Infrastructure de test partagée (fournie par l'opérateur du run autonome).

Crée le schéma de base de données AVANT chaque test (sinon les tests qui touchent
la BDD échouent en `OperationalError: no such table`, car le fichier `*.db` n'est
pas versionné). Importe récursivement les modules de `app` pour que TOUS les
modèles SQLAlchemy soient enregistrés sur `Base.metadata` avant `create_all`.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db

# Use a separate database for tests
TEST_DATABASE_URL = "sqlite:///./test_facnor.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db():
    connection = TestingSessionLocal()
    try:
        yield connection
    finally:
        connection.close()

@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
