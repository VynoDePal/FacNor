# Repository notes

- FacNor backend is a FastAPI application exposed as both `app.main:app` and `main:app`.
- SQLite schema is centralized in root `schema.sql`; production startup and pytest fixtures both call `app.db.initialize_database()`.
- Required tables are `users`, `clients`, `invoices`, and `invoice_lines` with foreign keys enabled per connection.
- Tests should run from the repository root with `python -m pytest`.
- Authentication uses HS256 JWT bearer tokens generated in `app.main`; configure the signing secret with `FACNOR_JWT_SECRET`.

