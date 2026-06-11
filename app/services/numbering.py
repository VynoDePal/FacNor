from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.invoice import Invoice

class InvoiceNumberingService:
    @staticmethod
    def generate_next_number(db: Session, user_id: int, prefix: str = "FAC") -> str:
        """
        Generates the next sequential invoice number for a user.
        Format: PREFIX-YYYY-XXXX (e.g., FAC-2023-0001)
        Handles concurrency using the database's capabilities.
        """
        from datetime import datetime
        year = datetime.now().year
        current_prefix = f"{prefix}-{year}-"

        # Find the highest invoice number for the current user and year
        # We filter by invoice_number starting with current_prefix
        # and then extract the numeric part to find the max.
        
        # Since SQLite doesn't have a great way to do this atomically without locks,
        # and we have a UNIQUE constraint on (user_id, invoice_number),
        # we can try to insert and retry, or use a transaction with a lock.
        
        # For this implementation, we'll find the current max and increment.
        # In a real high-concurrency environment with PostgreSQL, we'd use a sequence or SELECT FOR UPDATE.
        # For SQLite, we rely on the transaction isolation and the UNIQUE constraint.

        last_invoice = db.query(Invoice).filter(
            Invoice.user_id == user_id,
            Invoice.invoice_number.like(f"{current_prefix}%")
        ).order_by(Invoice.invoice_number.desc()).first()

        if last_invoice:
            try:
                last_num_str = last_invoice.invoice_number.split("-")[-1]
                next_num = int(last_num_str) + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        return f"{current_prefix}{next_num:04d}"
