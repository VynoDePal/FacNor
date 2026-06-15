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
