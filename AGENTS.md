# Repository notes

- Backend is a FastAPI application exposed via `main.py` and `app.main:app`.
- SQLite is initialized through `app.db.init_db()` using the root `schema.sql`; tests should reuse this same path.
- Automated tests run with `python -m pytest` and import application code from the repository root package (`app.*`).
- Authentication uses PBKDF2 password hashes and HMAC-signed Bearer tokens implemented with Python standard library in `app/main.py`.
- Frontend is a Vite React TypeScript app at the repository root; use `npm run dev` and configure API URL with `VITE_API_BASE_URL`.

- Invoice CRUD lives in `app.main` and reuses helpers in `app.db`; ownership checks return 404 for cross-user client/invoice access.
- Invoice totals are stored in integer centimes, and `total_including_tax` must equal the sum of each invoice line `total_including_tax` on create and update.
- Invoice numbering is sequential per user via `invoice_sequences`, formatted as `FAC-000001`.
- Frontend client management UI is implemented in `src/App.tsx` and calls the backend through `src/api.ts` using `VITE_API_BASE_URL`.
- For the Vite app to build reliably on a fresh install, keep `typescript`, `vite`, and `@vitejs/plugin-react` available via `package.json` devDependencies, then run `npm install` before `npm run build`.
- PDF invoice export is implemented in `app.pdf` without external PDF dependencies; API route is `GET /invoices/{invoice_id}/pdf` and reuses invoice ownership checks.
- Current pytest suite covers schema initialization through `app.db.init_db`, invoice numbering/totals, authentication, ownership checks, and PDF content/download behavior.
- `requirements.txt` currently lists both pinned and duplicate unpinned dependencies, plus `httpx2` for the Starlette/FastAPI test client deprecation path.



