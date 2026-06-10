from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Facture(Base):
    __tablename__ = "factures"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String, unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    date_facture = Column(Date, nullable=False)
    date_echeance = Column(Date)
    statut = Column(String, default="brouillon") # 'brouillon', 'envoyee', 'payee', 'annulee'
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="factures")
    lignes = relationship("LigneFacture", back_populates="facture", cascade="all, delete-orphan")

class LigneFacture(Base):
    __tablename__ = "lignes_facture"

    id = Column(Integer, primary_key=True, index=True)
    facture_id = Column(Integer, ForeignKey("factures.id", ondelete="CASCADE"), nullable=False)
    description = Column(String, nullable=False)
    quantite = Column(Float, nullable=False)
    prix_unitaire_ht = Column(Float, nullable=False)
    taux_tva = Column(Float, nullable=False)

    facture = relationship("Facture", back_populates="lignes")
