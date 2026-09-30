"""Generic dataclass <-> Firestore document conversion.

Every entity in `entities.py` is a plain dataclass mirroring the field
names of its SQLAlchemy model in `infrastructure/db/models.py`.

UUID fields are decoded by their *declared type* (`uuid.UUID` or
`uuid.UUID | None`), not by field name - a naming convention (`id`/`*_id`/
`*_by`) was tried first and seemed to hold everywhere, but broke on
`external_event_id`/`external_subscription_id`/`external_customer_id`
(Billing/Subscription fields that are plain provider-supplied strings,
not UUIDs, despite the `_id` suffix). Encoding doesn't have this problem -
`_encode_value` checks the actual runtime value's type, which is never
ambiguous.

The entity's `id` is stored inside the document body like any other field,
*not* dropped in favor of the Firestore document ID. Most repositories do
address a document by `str(entity.id)`, making the two redundant - but a
few don't (`PlanEntitlement` is keyed by its `key` for the SQL schema's
`(plan_id, key)` uniqueness, `Subscription` by `organization_id` for its
1:1 uniqueness), and for those the document ID and the entity's own `id`
are genuinely different values. Trusting the document ID for `id` would
silently reconstruct the wrong value for those two; storing `id` in the
body sidesteps the whole distinction.
"""
import dataclasses
import typing
import uuid
from typing import TypeVar

T = TypeVar("T")


def _encode_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _encode_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_encode_value(v) for v in value]
    return value


def to_dict(entity: object) -> dict:
    """Serializes a dataclass entity to a Firestore-writable dict."""
    data = dataclasses.asdict(entity)
    return {k: _encode_value(v) for k, v in data.items()}


def _field_is_uuid_typed(field_type: object) -> bool:
    if field_type is uuid.UUID:
        return True
    return uuid.UUID in typing.get_args(field_type)


def _decode_value(field_type: object, value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str) and _field_is_uuid_typed(field_type):
        return uuid.UUID(value)
    return value


def from_dict(cls: type[T], doc_id: str, data: dict) -> T:
    """Builds a dataclass entity from a Firestore document id + body dict.

    Any dataclass field missing from `data` (e.g. an old document predating
    a newly added field) falls back to that field's declared default. `id`
    is read from `data` (see module docstring for why) - `doc_id` is used
    only as a fallback for documents written before this field existed.
    """
    hints = typing.get_type_hints(cls)
    kwargs: dict = {}
    for f in dataclasses.fields(cls):
        if f.name not in data:
            continue
        kwargs[f.name] = _decode_value(hints.get(f.name), data[f.name])
    if "id" not in kwargs:
        kwargs["id"] = uuid.UUID(doc_id)
    return cls(**kwargs)
