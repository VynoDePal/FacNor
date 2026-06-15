# AGENTS.md

## Repository conventions

- Backend entrypoint is `main.py` and the ASGI app is exposed as `main:app`.
- Database helpers live in `app/database.py`.
- SQLite schema is defined in the repository root `schema.sql`.
- Production and tests must share the same database initialization path via `app.database.init_db()`.
- Tests are executed from the repository root with `python -m pytest`.
- Frontend is a Vite + React + TypeScript app rooted at `src/` with scripts declared in `package.json`.
- Frontend backend URL is configured through `VITE_API_BASE_URL` and currently calls `/health`.
- Python dependencies are declared in the root `requirements.txt`.
- Authentication routes live in `app/auth.py` under `/auth`; JWTs are HS256 signed with `FACNOR_JWT_SECRET` and passwords use PBKDF2-SHA256.
- Invoice creation routes live in `app/invoices.py` under `/invoices`; invoice numbers use `invoice_sequences` from `schema.sql` and are generated as per-user `F-001`, `F-002`, ... inside a `BEGIN IMMEDIATE` transaction.
- Client CRUD routes live in `app/clients.py` under `/clients`; deletes use `status_code=204` with `response_class=Response` and return an empty `Response` to satisfy FastAPI's no-body rule.


- Financial calculation logic lives in `app/financial.py`; use `Decimal` with `ROUND_HALF_UP` via `money()`, and keep invoice totals invariant as `total_excluding_tax + total_tax = total_including_tax`.


