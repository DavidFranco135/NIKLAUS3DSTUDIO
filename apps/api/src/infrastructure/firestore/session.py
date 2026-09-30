"""A minimal stand-in for SQLAlchemy's Session, so application/*/use_cases.py

can keep its existing "mutate attributes on an entity, then call
db.commit()" pattern unchanged when the entity is Firestore-backed instead
of SQL-backed. Firestore has no implicit dirty-tracking (unlike an ORM
Session, which watches attribute writes automatically), so this session
re-writes the whole document body for every tracked entity on
commit/flush. Full-document overwrites are perfectly fine at this app's
data volume (a small print shop's records, not a high-write-throughput
system).

It also acts as an identity map: `hydrate()` returns the *same* Python
object for a given document path every time within one session, updating
it in place on repeat reads instead of handing back a second, separate
copy. Without that, fetching the same document twice (e.g. once via
`get()`, once via a `list_for_org()` that happens to include it) would let
whichever copy gets tracked last silently win on flush, discarding a
mutation made to the other, now-orphaned copy - repositories must use
`hydrate()` (not `track()` + a freshly built entity) for every read so
this guarantee holds.

Repositories call `add()` for newly created entities and `delete()` for
hard deletes. Soft deletes just mutate `deleted_at` like any other field -
no special casing needed here.
"""
import dataclasses
from typing import Any, TypeVar

from google.cloud.firestore import Client, DocumentReference

from src.infrastructure.firestore.serialization import from_dict, to_dict

T = TypeVar("T")


class FirestoreSession:
    def __init__(self, client: Client) -> None:
        self.client = client
        self._tracked: dict[str, tuple[Any, DocumentReference]] = {}
        self._pending_deletes: list[DocumentReference] = []

    def hydrate(self, cls: type[T], doc_id: str, data: dict, doc_ref: DocumentReference) -> T:
        path = doc_ref.path
        existing = self._tracked.get(path)
        if existing is not None:
            entity = existing[0]
            fresh = from_dict(cls, doc_id, data)
            for f in dataclasses.fields(cls):
                setattr(entity, f.name, getattr(fresh, f.name))
            return entity
        entity = from_dict(cls, doc_id, data)
        self.track(entity, doc_ref)
        return entity

    def track(self, entity: Any, doc_ref: DocumentReference) -> None:
        self._tracked[doc_ref.path] = (entity, doc_ref)

    def add(self, entity: Any, doc_ref: DocumentReference) -> None:
        self.track(entity, doc_ref)

    def delete(self, entity: Any) -> None:
        for path, (tracked_entity, doc_ref) in list(self._tracked.items()):
            if tracked_entity is entity:
                del self._tracked[path]
                self._pending_deletes.append(doc_ref)
                return

    def flush(self) -> None:
        for entity, doc_ref in self._tracked.values():
            doc_ref.set(to_dict(entity))
        for doc_ref in self._pending_deletes:
            doc_ref.delete()
        self._pending_deletes.clear()

    def commit(self) -> None:
        self.flush()

    def rollback(self) -> None:
        self._tracked.clear()
        self._pending_deletes.clear()

    def close(self) -> None:
        """No-op - matches SQLAlchemy Session's interface for get_db()'s

        `finally: db.close()`. The Firestore client itself is a
        long-lived singleton (see client.py), not a per-request resource.
        """
