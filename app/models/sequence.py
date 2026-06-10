from sqlalchemy import Column, Integer, String
from app.db.database import Base

class Sequence(Base):
    __tablename__ = "sequences"

    name = Column(String, primary_key=True)
    value = Column(Integer, nullable=False, default=0)
