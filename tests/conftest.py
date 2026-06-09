"""Infrastructure de test partagée (fournie par l'opérateur du run autonome).

Crée le schéma de base de données AVANT chaque test (sinon les tests qui touchent
la BDD échouent en `OperationalError: no such table`, car le fichier `*.db` n'est
pas versionné). Importe récursivement les modules de `app` pour que TOUS les
modèles SQLAlchemy soient enregistrés sur `Base.metadata` avant `create_all`.
"""

import importlib
import pkgutil

import pytest

from app.core.database import Base, engine

import app as _app_pkg

for _mod in pkgutil.walk_packages(_app_pkg.__path__, _app_pkg.__name__ + "."):
    try:
        importlib.import_module(_mod.name)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _db_schema():
    """Schéma frais par test : create_all avant, drop_all après (isolation)."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
