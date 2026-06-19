from enum import StrEnum

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ClientType(StrEnum):
    PARTICULIER = "Particulier"
    ENTREPRISE = "Entreprise"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[ClientType] = mapped_column(Enum(ClientType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    siren: Mapped[str | None] = mapped_column(String(9), nullable=True, index=True)
    vat_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
