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


@dataclass
class Customer:
    organization_id: uuid.UUID
    name: str
    id: uuid.UUID = field(default_factory=_uuid4)
    email: str | None = None
    phone: str | None = None
    document: str | None = None
    address: dict | None = None
    notes: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None


@dataclass
class Machine:
    organization_id: uuid.UUID
    name: str
    technology: str
    id: uuid.UUID = field(default_factory=_uuid4)
    brand: str | None = None
    model: str | None = None
    build_volume_x_mm: float | None = None
    build_volume_y_mm: float | None = None
    build_volume_z_mm: float | None = None
    power_watts: float | None = None
    cost_per_hour: float | None = None
    speed_profile: dict | None = None
    compatible_materials: list | None = None
    status: str = "active"
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None


@dataclass
class Product:
    organization_id: uuid.UUID
    name: str
    id: uuid.UUID = field(default_factory=_uuid4)
    description: str | None = None
    print_time_hours: float | None = None
    machine_id: uuid.UUID | None = None
    manual_price: float | None = None
    size: str | None = None
    photo_url: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None


@dataclass
class ProductMaterial:
    product_id: uuid.UUID
    material_id: uuid.UUID
    quantity_g: float
    id: uuid.UUID = field(default_factory=_uuid4)


@dataclass
class InventoryItem:
    organization_id: uuid.UUID
    name: str
    category: str
    unit: str
    id: uuid.UUID = field(default_factory=_uuid4)
    material_id: uuid.UUID | None = None
    quantity_on_hand: float = 0
    minimum_stock: float = 0
    unit_cost: float | None = None
    supplier: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None


@dataclass
class InventoryMovement:
    inventory_item_id: uuid.UUID
    organization_id: uuid.UUID
    type: str
    quantity: float
    id: uuid.UUID = field(default_factory=_uuid4)
    reference_order_id: uuid.UUID | None = None
    unit_cost: float | None = None
    notes: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class Quote:
    organization_id: uuid.UUID
    cost_profile_id: uuid.UUID
    cost_breakdown_snapshot: dict
    production_cost: float
    suggested_price: float
    id: uuid.UUID = field(default_factory=_uuid4)
    customer_id: uuid.UUID | None = None
    project_version_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    piece_name: str | None = None
    printer_name: str | None = None
    machine_id: uuid.UUID | None = None
    material_id: uuid.UUID | None = None
    weight_g: float | None = None
    cost_per_kg: float | None = None
    extra_items: list | None = None
    print_time_hours: float | None = None
    depreciation_mode: str | None = None
    depreciation_value: float | None = None
    labor_hours: float | None = None
    profit_margin_percentage: float | None = None
    quantity: int = 1
    final_price: float | None = None
    status: str = "draft"
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None


@dataclass
class Order:
    organization_id: uuid.UUID
    customer_id: uuid.UUID
    id: uuid.UUID = field(default_factory=_uuid4)
    quote_id: uuid.UUID | None = None
    status: str = "quote"
    total_amount: float = 0
    notes: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None


@dataclass
class OrderItem:
    order_id: uuid.UUID
    organization_id: uuid.UUID
    id: uuid.UUID = field(default_factory=_uuid4)
    project_version_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    machine_id: uuid.UUID | None = None
    material_id: uuid.UUID | None = None
    quantity: int = 1
    unit_cost: float | None = None
    unit_price: float | None = None
    status: str = "pending"
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class FinancialTransaction:
    organization_id: uuid.UUID
    type: str
    category: str
    amount: float
    id: uuid.UUID = field(default_factory=_uuid4)
    cost_center: str | None = None
    reference_order_id: uuid.UUID | None = None
    due_date: datetime | None = None
    paid_at: datetime | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None


@dataclass
class Project:
    organization_id: uuid.UUID
    name: str
    id: uuid.UUID = field(default_factory=_uuid4)
    customer_id: uuid.UUID | None = None
    description: str | None = None
    status: str = "draft"
    active_version_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    deleted_at: datetime | None = None


@dataclass
class ProjectVersion:
    project_id: uuid.UUID
    version_number: int
    id: uuid.UUID = field(default_factory=_uuid4)
    label: str | None = None
    source_type: str = "manual_upload"
    status: str = "draft"
    created_by: uuid.UUID | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class FileAsset:
    organization_id: uuid.UUID
    kind: str
    storage_key: str
    mime_type: str
    id: uuid.UUID = field(default_factory=_uuid4)
    project_id: uuid.UUID | None = None
    project_version_id: uuid.UUID | None = None
    sha256_hash: str | None = None
    size_bytes: int | None = None
    status: str = "pending"
    uploaded_by: uuid.UUID | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class Plan:
    code: str
    name: str
    id: uuid.UUID = field(default_factory=_uuid4)
    is_active: bool = True
    trial_period_days: int | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class PlanEntitlement:
    plan_id: uuid.UUID
    key: str
    limit_type: str
    id: uuid.UUID = field(default_factory=_uuid4)
    bool_value: bool | None = None
    numeric_value: float | None = None


@dataclass
class Subscription:
    organization_id: uuid.UUID
    plan_id: uuid.UUID
    status: str
    current_period_start: datetime
    current_period_end: datetime
    id: uuid.UUID = field(default_factory=_uuid4)
    trial_start: datetime | None = None
    trial_end: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    external_provider: str = "mock"
    external_subscription_id: str | None = None
    external_customer_id: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class BillingEvent:
    provider: str
    external_event_id: str
    event_type: str
    payload: dict
    id: uuid.UUID = field(default_factory=_uuid4)
    organization_id: uuid.UUID | None = None
    status: str = "received"
    error_message: str | None = None
    received_at: datetime = field(default_factory=_now)
    processed_at: datetime | None = None
