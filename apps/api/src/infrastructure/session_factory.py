"""Backend-agnostic `get_db` dependency.

Yields a SQLAlchemy `Session` or a `FirestoreSession` depending on
`settings.db_backend` (see config.py) - this is the Phase 5 cutover
switch from the Firebase migration plan
(C:\\Users\\Gamer\\.claude\\plans\\hashed-seeking-stardust.md). Defaults to
"postgres", today's production behavior, completely unchanged unless this
is explicitly flipped after the data migration script has run.

Every route already gets `get_db` via `src.interfaces.http.dependencies`
(never directly from `src.infrastructure.db.session`), so this is the only
place the backend choice needs to be made - nothing else has to change to
pick this up.
"""
from collections.abc import Iterator
from typing import Union

from sqlalchemy.orm import Session

from src.config import get_settings
from src.infrastructure.db.session import get_db as _get_sql_db
from src.infrastructure.firestore.client import get_firestore_client
from src.infrastructure.firestore.session import FirestoreSession

DbSession = Union[Session, FirestoreSession]


def get_db() -> Iterator[DbSession]:
    settings = get_settings()
    if settings.db_backend == "firestore":
        session = FirestoreSession(get_firestore_client())
        try:
            yield session
        finally:
            session.close()
    else:
        yield from _get_sql_db()
