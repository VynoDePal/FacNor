# Repository notes

- FacNor backend is a FastAPI application exposed as both `app.main:app` and `main:app`.
- SQLite schema is centralized in root `schema.sql`; production startup and pytest fixtures both call `app.db.initialize_database()`.
- Required tables are `users`, `clients`, `invoices`, and `invoice_lines` with foreign keys enabled per connection.
- Tests should run from the repository root with `python -m pytest`.
- Authentication uses HS256 JWT bearer tokens generated in `app.main`; configure the signing secret with `FACNOR_JWT_SECRET`.

- Client management exposes authenticated CRUD endpoints under `/clients`; clients are scoped to the current JWT user.
- Client records support `client_type` values `b2c` and `b2b`; B2B clients require valid French SIREN and VAT (`FR` key + SIREN) that match.

