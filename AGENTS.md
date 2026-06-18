# Repository notes

- FacNor backend is a FastAPI application exposed as both `app.main:app` and `main:app`.
- SQLite schema is centralized in root `schema.sql`; production startup and pytest fixtures both call `app.db.initialize_database()`.
- Required tables are `users`, `clients`, `invoices`, and `invoice_lines` with foreign keys enabled per connection.
- Tests should run from the repository root with `python -m pytest`.
- Authentication uses HS256 JWT bearer tokens generated in `app.main`; configure the signing secret with `FACNOR_JWT_SECRET`.

- Frontend authentication lives in `frontend/` as a Vite React TypeScript app; configure backend URL with `VITE_API_BASE_URL` and run `npm run dev` or `npm run build` there.
- Backend CORS is configured in `app.main` with `FACNOR_CORS_ORIGINS`, defaulting to the Vite dev origin `http://localhost:5173`.

- Client management exposes authenticated CRUD endpoints under `/clients`; clients are scoped to the current JWT user.
- Client records support `client_type` values `b2c` and `b2b`; B2B clients require valid French SIREN and VAT (`FR` key + SIREN) that match.
- Invoice management exposes authenticated endpoints under `/invoices`; invoices are scoped to the current JWT user and include their lines on creation/detail responses.
- Automatic invoice numbering uses `invoice_sequences` and generates `FAC-YYYY-NNNN` per user/year inside a `BEGIN IMMEDIATE` transaction.

- Frontend client management is implemented in `frontend/src/main.tsx` via `ClientsManager`, using authenticated helper functions from `frontend/src/api.ts` for `/clients` CRUD.
