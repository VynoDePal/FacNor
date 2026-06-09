from sqlalchemy.orm import Session
from app.models import models

def get_next_invoice_number(db: Session, prefix: str = "FAC-") -> str:
    """
    Generates the next sequential invoice number.
    Ensures atomicity by using a row-level lock (with_for_update).
    """
    sequence = db.query(models.InvoiceSequence).filter(
        models.InvoiceSequence.sequence_name == "invoice_number"
    ).with_for_update().first()

    if not sequence:
        # Initialize sequence if it doesn't exist
        sequence = models.InvoiceSequence(sequence_name="invoice_number", current_value=0)
        db.add(sequence)
        db.flush()

    sequence.current_value += 1
    db.flush()
    
    return f"{prefix}{sequence.current_value:06d}"
