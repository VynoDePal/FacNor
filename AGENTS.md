# Repository Notes

- Backend is a minimal FastAPI app exposed through `backend.main:app` and implemented in `backend/app/main.py`.
- Database layer uses SQLAlchemy 2.0 declarative models in `backend/app/models.py` with shared `Base`, `engine`, `SessionLocal`, and `init_db()` in `backend/app/database.py`.
- Current schema includes `users`, `clients`, `invoices`, and `invoice_items`; tests validate table creation, foreign keys, and ORM relationships in `backend/tests/test_database_schema.py`.
