from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import InvoiceSequence


def generate_invoice_number(db: Session, user_id: int) -> str:
    sequence = db.get(InvoiceSequence, user_id, with_for_update=True)
    if sequence is None:
        sequence = _create_sequence(db, user_id)

    value = sequence.next_number
    sequence.next_number += 1
    return format_invoice_number(value)


def format_invoice_number(value: int) -> str:
    if value < 1:
        raise ValueError("Invoice number sequence must be positive")
    return f"{value:04d}"


def _create_sequence(db: Session, user_id: int) -> InvoiceSequence:
    sequence = InvoiceSequence(user_id=user_id, next_number=1)
    db.add(sequence)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing_sequence = db.get(InvoiceSequence, user_id, with_for_update=True)
        if existing_sequence is None:
            raise
        return existing_sequence
    return sequence
