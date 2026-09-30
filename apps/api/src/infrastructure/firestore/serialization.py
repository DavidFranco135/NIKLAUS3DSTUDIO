"""Generic dataclass <-> Firestore document conversion.

Every entity in `entities.py` is a plain dataclass mirroring the field
names of its SQLAlchemy model in `infrastructure/db/models.py`. UUID fields
follow one exact naming convention throughout this codebase - the field is
named exactly `id`, or ends with `_id` or `_by` - which lets this module
convert UUID <-> str generically by field name instead of needing a
hand-written mapping per entity.

The document's own id (the UUID) is never stored inside its body - it's the
Firestore document ID - so `to_dict` drops the `id` field and `from_dict`
re-injects it from the document reference/snapshot id.
"""
import dataclasses
import uuid
from typing import TypeVar

T = TypeVar("T")


def _is_uuid_field(name: str) -> bool:
    return name == "id" or name.endswith("_id") or name.endswith("_by")


def _encode_value(name: str, value: object) -> object:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _encode_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_encode_value(name, v) for v in value]
    return value


def to_dict(entity: object) -> dict:
    """Serializes a dataclass entity to a Firestore-writable dict, excluding `id`."""
    data = dataclasses.asdict(entity)
    data.pop("id", None)
    return {k: _encode_value(k, v) for k, v in data.items()}


def _decode_value(name: str, value: object) -> object:
    if value is None:
        return None
    if _is_uuid_field(name) and isinstance(value, str):
        return uuid.UUID(value)
    return value


def from_dict(cls: type[T], doc_id: str, data: dict) -> T:
    """Builds a dataclass entity from a Firestore document id + body dict.

    Any dataclass field missing from `data` (e.g. an old document predating
    a newly added field) falls back to that field's declared default.
    """
    kwargs: dict = {"id": uuid.UUID(doc_id)}
    for f in dataclasses.fields(cls):
        if f.name == "id" or f.name not in data:
            continue
        kwargs[f.name] = _decode_value(f.name, data[f.name])
    return cls(**kwargs)
