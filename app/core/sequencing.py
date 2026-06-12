from sqlalchemy.orm import Session
from sqlalchemy import text

def get_next_invoice_number(db: Session, prefix: str = "F-", start_value: int = 1) -> str:
    """
    Generates the next sequential invoice number.
    Uses a sequence table and UPDATE ... RETURNING to ensure uniqueness under concurrency.
    """
    # Try to increment and return the value atomically
    try:
        result = db.execute(
            text("UPDATE sequences SET value = value + 1 WHERE name = :name RETURNING value"),
            {"name": "invoice"}
        ).scalar()
        
        if result is not None:
            return f"{prefix}{result:03d}"
            
    except Exception:
        # In case of any database error, we'll handle it in the fallback
        pass

    # Fallback: Initialize sequence if it doesn't exist
    try:
        # Use a subquery or separate check to avoid duplicate inserts
        db.execute(
            text("INSERT INTO sequences (name, value) VALUES (:name, :value)"),
            {"name": "invoice", "value": start_value}
        )
        return f"{prefix}{start_value:03d}"
    except Exception:
        # If another thread inserted it in the meantime, retry the update
        return get_next_invoice_number(db, prefix, start_value)
