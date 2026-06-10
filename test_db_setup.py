from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.models.user import User
from app.models.client import Client
from app.models.facture import Facture, LigneFacture

SQLALCHEMY_DATABASE_URL = "sqlite:///"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tables created:", Base.metadata.tables.keys())

    db = TestingSessionLocal()
    try:
        # Try to insert a user
        user = User(username="testuser", email="test@example.com", hashed_password="hashed_password")
        db.add(user)
        db.commit()
        print("User inserted successfully")
    except Exception as e:
        print(f"Error inserting user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_create_tables()
