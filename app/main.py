from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from sqlalchemy import text

app = FastAPI(title="FacNor API")

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Simple query to verify database connection
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")
