from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    email = Column(String)
    adresse = Column(String)
    siat_siren = Column(String)
    tva_intracommunautaire = Column(String)
    type_client = Column(String, nullable=False) # 'particulier' or 'entreprise'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
