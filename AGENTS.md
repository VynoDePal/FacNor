# Repository notes

- Backend is a FastAPI application exposed via `main.py` and `app.main:app`.
- SQLite is initialized through `app.db.init_db()` using the root `schema.sql`; tests should reuse this same path.
- Automated tests run with `python -m pytest` and import application code from the repository root package (`app.*`).
- Authentication uses PBKDF2 password hashes and HMAC-signed Bearer tokens implemented with Python standard library in `app/main.py`.
- Frontend is a Vite React TypeScript app at the repository root; use `npm run dev` and configure API URL with `VITE_API_BASE_URL`.

- Invoice CRUD lives in `app.main` and reuses helpers in `app.db`; ownership checks return 404 for cross-user client/invoice access.
- Invoice totals are stored in integer centimes, and `total_including_tax` must equal the sum of each invoice line `total_including_tax` on create and update.
- Invoice numbering is sequential per user via `invoice_sequences`, formatted as `FAC-000001`.

