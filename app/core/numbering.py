from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.sequence import Sequence

def get_next_sequence_value(db: Session, sequence_name: str) -> int:
    # Use SELECT FOR UPDATE to handle concurrent requests
    seq = db.query(Sequence).filter(Sequence.name == sequence_name).with_for_update().first()
    
    if not seq:
        try:
            # Create the sequence if it doesn't exist
            seq = Sequence(name=sequence_name, value=0)
            db.add(seq)
            db.flush() 
        except IntegrityError:
            # If another thread created it in the meantime, rollback the failed insert and fetch it
            db.rollback()
            seq = db.query(Sequence).filter(Sequence.name == sequence_name).with_for_update().first()
            if not seq:
                # This should theoretically not happen if we only have one name
                raise RuntimeError("Could not retrieve sequence after IntegrityError")
    
    seq.value += 1
    db.flush()
    return seq.value
