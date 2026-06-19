# Repository Notes

- Backend is a minimal FastAPI app exposed through `backend.main:app` and implemented in `backend/app/main.py`.
- Database layer uses SQLAlchemy 2.0 declarative models in `backend/app/models.py` with shared `Base`, `engine`, `SessionLocal`, and `init_db()` in `backend/app/database.py`.
- Current schema includes `users`, `clients`, `invoices`, `invoice_items`, and `invoice_sequences`; tests validate table creation, foreign keys, and ORM relationships in `backend/tests/test_database_schema.py`.
- Invoice numbering lives in `backend/app/invoice_numbering.py`; use `generate_invoice_number(db, user_id)` inside the same transaction as invoice creation so rollbacks do not create sequence gaps.
- Authentication is implemented in `backend/app/auth.py` using PBKDF2 password hashes and signed Bearer tokens; protected endpoints should depend on `get_current_user`.
- Auth routes live in `backend/app/main.py`: `POST /api/auth/register`, `POST /api/auth/login`, and protected `GET /api/auth/me`; invoice creation is `POST /api/invoices`.

