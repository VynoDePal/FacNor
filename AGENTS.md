# Repository Notes

- Backend is a minimal FastAPI app exposed through `backend.main:app` and implemented in `backend/app/main.py`.
- Database layer uses SQLAlchemy 2.0 declarative models in `backend/app/models.py` with shared `Base`, `engine`, `SessionLocal`, and `init_db()` in `backend/app/database.py`.
- Current schema includes `users`, `clients`, `invoices`, `invoice_items`, and `invoice_sequences`; tests validate table creation, foreign keys, and ORM relationships in `backend/tests/test_database_schema.py`.
- Invoice numbering lives in `backend/app/invoice_numbering.py`; use `generate_invoice_number(db, user_id)` inside the same transaction as invoice creation so rollbacks do not create sequence gaps.
- Authentication is implemented in `backend/app/auth.py` using PBKDF2 password hashes and signed Bearer tokens; protected endpoints should depend on `get_current_user`.
- Auth routes live in `backend/app/main.py`: `POST /api/auth/register`, `POST /api/auth/login`, and protected `GET /api/auth/me`.
- Client CRUD API is implemented in `backend/app/main.py` with protected `/api/clients` endpoints (`POST`, `GET` list/detail, `PUT`, `DELETE`), using `get_current_user` and `user_id` ownership isolation.
- Invoice CRUD API is implemented in `backend/app/main.py` with protected `/api/invoices` endpoints (`POST`, `GET` list/detail, `PUT`, `DELETE`), eager-loading lines and recalculating totals through shared helpers.
- Invoice monetary calculations are centralized in `backend/app/invoice_calculation.py`; `calculate_invoice()` returns per-line totals and invoice totals rounded with `Decimal`/`ROUND_HALF_UP`.

- Invoice PDF export lives in `backend/app/pdf_export.py` and is dependency-free: it builds a minimal paginated PDF with WinAnsi/Latin-1-safe text normalization and escaping.

- Backend tests may need `PYTHONPATH=/workspace pytest backend/tests` so imports like `backend.app...` resolve reliably in this environment.

- Frontend React entrypoint is `frontend/src/main.tsx`; auth state uses localStorage keys `facnor.authToken` and `facnor.authUser`, and protected API calls send `Authorization: Bearer <token>`.
- Frontend invoice list exports PDFs from `GET /api/invoices/{id}/pdf` using an authenticated fetch, Blob download, and the `Content-Disposition` filename when present.
- Frontend tests use Vitest with jsdom and Testing Library; run them with `npm test` from `/workspace`.


