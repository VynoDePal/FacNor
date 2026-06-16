# Repository notes

- Backend is a FastAPI application exposed via `main.py` and `app.main:app`.
- SQLite is initialized through `app.db.init_db()` using the root `schema.sql`; tests should reuse this same path.
- Automated tests run with `python -m pytest` and import application code from the repository root package (`app.*`).
- Authentication uses PBKDF2 password hashes and HMAC-signed Bearer tokens implemented with Python standard library in `app/main.py`.
