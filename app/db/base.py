from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.client import Client  # noqa: E402,F401
from app.models.invoice import Invoice, InvoiceItem  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
