from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models import Sequence

def get_next_sequence_value(db: Session, sequence_name: str, prefix: str = "") -> str:
    """
    Generates the next sequential number for a given sequence.
    Ensures that the number is sequential and unique.
    """
    try:
        # Attempt to lock and get the sequence
        sequence = db.query(Sequence).filter(Sequence.name == sequence_name).with_for_update().first()
        
        if sequence:
            sequence.current_value += 1
            db.commit()
            return f"{prefix}{sequence.current_value:03d}"
        
        # If sequence doesn't exist, create it
        sequence = Sequence(name=sequence_name, current_value=1)
        db.add(sequence)
        db.commit()
        return f"{prefix}{sequence.current_value:03d}"
        
    except IntegrityError:
        # In case of a race condition during creation, roll back and retry
        db.rollback()
        # Now it must exist, so we can just call the function again (recursive) or just repeat the logic
        return get_next_sequence_value(db, sequence_name, prefix)
