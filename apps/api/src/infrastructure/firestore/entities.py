"""Firestore-backed entities, mirroring infrastructure/db/models.py field for

field (see that file's docstrings for the *why* behind each field - this is
intentionally a structural port, not a redesign). Plain dataclasses, no
SQLAlchemy - persistence is handled entirely by
infrastructure/firestore/repositories.py.

Every UUID field is named `id`, or ends with `_id`/`_by` - see
serialization.py, which relies on that convention to encode/decode UUIDs
without a per-entity field map.
"""
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _uuid4() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Organization:
    name: str
    slug: str
    id: uuid.UUID = field(default_factory=_uuid4)
    plan: str = "free"
    settings: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class User:
    email: str
    password_hash: str
    id: uuid.UUID = field(default_factory=_uuid4)
    full_name: str | None = None
    email_verified_at: datetime | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class OrgMember:
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    id: uuid.UUID = field(default_factory=_uuid4)
    invited_by: uuid.UUID | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class RefreshToken:
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    id: uuid.UUID = field(default_factory=_uuid4)
    revoked_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class Material:
    organization_id: uuid.UUID
    name: str
    type: str
    id: uuid.UUID = field(default_factory=_uuid4)
    color: str | None = None
    density_g_cm3: float | None = None
    cost_per_kg: float | None = None
    supplier: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None


@dataclass
class CostProfile:
    organization_id: uuid.UUID
    name: str
    energy_cost_per_kwh: float
    labor_cost_per_hour: float
    packaging_cost_flat: float
    waste_percentage: float
    fees_percentage: float
    profit_margin_percentage: float
    id: uuid.UUID = field(default_factory=_uuid4)
    tax_percentage: float | None = None
    is_default: bool = False
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None
