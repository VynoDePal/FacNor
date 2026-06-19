# FacNor

Application web de gestion de factures normalisées (particuliers + entreprises),
conforme à la facturation électronique française.

> Dépôt réinitialisé pour la construction autonome V10 (Collègue MCP).


## Backend API

L’API backend utilise FastAPI et expose les premières routes d’authentification :

- `POST /auth/register` : inscription avec `email` et `password` ;
- `POST /auth/login` : authentification et retour d’un JWT bearer ;
- `GET /auth/me` : route protégée retournant l’utilisateur courant ;
- `GET /health` : vérification de santé de l’API.

Configuration principale via variables d’environnement préfixées `FACNOR_`, notamment `FACNOR_DATABASE_URL` et `FACNOR_JWT_SECRET_KEY`.

Lancement local :

```bash
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Tests :

```bash
PYTHONPATH=. pytest
```
