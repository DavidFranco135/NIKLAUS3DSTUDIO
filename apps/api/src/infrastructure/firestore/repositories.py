"""Firestore-backed repositories, mirroring infrastructure/db/repositories.py

method-for-method (same class names, same method names, same signatures)
so application/*/use_cases.py needs only an import-path change - see the
migration plan for the full rationale.

Collection layout: tenant data lives under organizations/{org_id}/<name>
subcollections; users/refresh_tokens are global (not org-scoped, matching
their SQL tables). Two "index" collections (email_index, slug_index)
simulate the SQL UNIQUE constraints on User.email and Organization.slug -
Firestore has no native unique-constraint mechanism, so the document ID
*is* the unique value, making a lookup-or-reject an O(1) get instead of a
scan.

Writes: `create()` methods write immediately (so a unique-index write and
its entity are as atomic as a single repository call can make them).
Mutations made via `get()` then direct attribute assignment rely on the
caller's `db.commit()` (a FirestoreSession) to flush - this mirrors
SQLAlchemy's implicit dirty-tracking closely enough that
application/*/use_cases.py bodies don't need to change, only their
repository imports.

One deliberate signature deviation from the SQL repositories: a few
SQL methods address a child row by its parent's id alone (e.g.
`OrderItemRepository.get(order_id, item_id)`,
`ProjectVersionRepository.list_for_project(project_id)`) because a flat
SQL table doesn't need anything else. Firestore documents live at a path
that includes the organization id, so every such method gains an
`organization_id` parameter here - the one place this port isn't a pure
import-path swap for use_cases.py, which already has `organization_id` on
hand at every call site regardless.
"""
from datetime import UTC, date, datetime
from uuid import UUID

from google.cloud.firestore import Client
from google.cloud.firestore_v1.base_query import FieldFilter

from src.infrastructure.firestore.entities import (
    BillingEvent,
    CostProfile,
    Customer,
    FileAsset,
    FinancialTransaction,
    InventoryItem,
    InventoryMovement,
    Machine,
    Material,
    Order,
    OrderItem,
    Organization,
    OrgMember,
    Plan,
    PlanEntitlement,
    Product,
    ProductMaterial,
    Project,
    ProjectVersion,
    Quote,
    RefreshToken,
    Subscription,
    User,
)
from src.infrastructure.firestore.serialization import to_dict
from src.infrastructure.firestore.session import FirestoreSession


def _org_ref(client: Client, organization_id: UUID):
    return client.collection("organizations").document(str(organization_id))


class UserRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def get_by_email(self, email: str) -> User | None:
        index_snap = self.client.collection("email_index").document(email).get()
        if not index_snap.exists:
            return None
        user_id = index_snap.to_dict()["user_id"]
        return self.get_by_id(UUID(user_id))

    def get_by_id(self, user_id: UUID) -> User | None:
        doc_ref = self.client.collection("users").document(str(user_id))
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return self.session.hydrate(User, snap.id, snap.to_dict(), doc_ref)

    def create(self, *, email: str, password_hash: str, full_name: str | None) -> User:
        user = User(email=email, password_hash=password_hash, full_name=full_name)
        doc_ref = self.client.collection("users").document(str(user.id))
        doc_ref.set(to_dict(user))
        self.client.collection("email_index").document(email).set({"user_id": str(user.id)})
        self.session.track(user, doc_ref)
        return user


class OrganizationRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def get_by_id(self, organization_id: UUID) -> Organization | None:
        doc_ref = _org_ref(self.client, organization_id)
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return self.session.hydrate(Organization, snap.id, snap.to_dict(), doc_ref)

    def slug_exists(self, slug: str) -> bool:
        return self.client.collection("slug_index").document(slug).get().exists

    def create(self, *, name: str, slug: str) -> Organization:
        org = Organization(name=name, slug=slug)
        doc_ref = _org_ref(self.client, org.id)
        doc_ref.set(to_dict(org))
        self.client.collection("slug_index").document(slug).set({"organization_id": str(org.id)})
        self.session.track(org, doc_ref)
        return org

    def list_for_user(self, user_id: UUID) -> list[Organization]:
        member_snaps = (
            self.client.collection_group("members")
            .where(filter=FieldFilter("user_id", "==", str(user_id)))
            .stream()
        )
        org_ids = [snap.reference.parent.parent.id for snap in member_snaps]
        organizations = []
        for org_id in org_ids:
            doc_ref = self.client.collection("organizations").document(org_id)
            snap = doc_ref.get()
            if snap.exists:
                org = self.session.hydrate(Organization, snap.id, snap.to_dict(), doc_ref)
                organizations.append(org)
        organizations.sort(key=lambda o: o.created_at)
        return organizations


class OrgMemberRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("members")

    def get(self, organization_id: UUID, user_id: UUID) -> OrgMember | None:
        snaps = list(
            self._collection(organization_id)
            .where(filter=FieldFilter("user_id", "==", str(user_id)))
            .limit(1)
            .stream()
        )
        if not snaps:
            return None
        return self.session.hydrate(OrgMember, snaps[0].id, snaps[0].to_dict(), snaps[0].reference)

    def list_for_org(self, organization_id: UUID) -> list[OrgMember]:
        snaps = self._collection(organization_id).order_by("created_at").stream()
        members = []
        for snap in snaps:
            member = self.session.hydrate(OrgMember, snap.id, snap.to_dict(), snap.reference)
            members.append(member)
        return members

    def count_owners(self, organization_id: UUID) -> int:
        return len([m for m in self.list_for_org(organization_id) if m.role == "OWNER"])

    def create(
        self, *, organization_id: UUID, user_id: UUID, role: str, invited_by: UUID | None = None
    ) -> OrgMember:
        member = OrgMember(
            organization_id=organization_id, user_id=user_id, role=role, invited_by=invited_by
        )
        doc_ref = self._collection(organization_id).document(str(member.id))
        doc_ref.set(to_dict(member))
        self.session.track(member, doc_ref)
        return member

    def delete(self, member: OrgMember) -> None:
        self.session.delete(member)
        self.session.flush()


class RefreshTokenRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def create(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        doc_ref = self.client.collection("refresh_tokens").document(str(token.id))
        doc_ref.set(to_dict(token))
        self.session.track(token, doc_ref)
        return token

    def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        snaps = list(
            self.client.collection("refresh_tokens")
            .where(filter=FieldFilter("token_hash", "==", token_hash))
            .limit(1)
            .stream()
        )
        if not snaps:
            return None
        token = self.session.hydrate(
            RefreshToken, snaps[0].id, snaps[0].to_dict(), snaps[0].reference
        )
        if token.revoked_at is not None:
            return None
        if token.expires_at < datetime.now(UTC):
            return None
        return token

    def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        self.session.flush()


class MaterialRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("materials")

    def get(self, organization_id: UUID, material_id: UUID) -> Material | None:
        doc_ref = self._collection(organization_id).document(str(material_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(Material, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[Material]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at")
            .stream()
        )
        materials = []
        for snap in snaps:
            material = self.session.hydrate(Material, snap.id, snap.to_dict(), snap.reference)
            materials.append(material)
        return materials

    def soft_delete(self, material: Material) -> None:
        material.deleted_at = datetime.now(UTC)
        self.session.flush()

    def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        type: str,
        color: str | None,
        density_g_cm3: float | None,
        cost_per_kg: float | None,
        supplier: str | None,
    ) -> Material:
        material = Material(
            organization_id=organization_id,
            name=name,
            type=type,
            color=color,
            density_g_cm3=density_g_cm3,
            cost_per_kg=cost_per_kg,
            supplier=supplier,
        )
        doc_ref = self._collection(organization_id).document(str(material.id))
        doc_ref.set(to_dict(material))
        self.session.track(material, doc_ref)
        return material


class CostProfileRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("cost_profiles")

    def get(self, organization_id: UUID, cost_profile_id: UUID) -> CostProfile | None:
        doc_ref = self._collection(organization_id).document(str(cost_profile_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(CostProfile, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[CostProfile]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at")
            .stream()
        )
        profiles = []
        for snap in snaps:
            profile = self.session.hydrate(CostProfile, snap.id, snap.to_dict(), snap.reference)
            profiles.append(profile)
        return profiles

    def soft_delete(self, profile: CostProfile) -> None:
        profile.deleted_at = datetime.now(UTC)
        self.session.flush()

    def get_default(self, organization_id: UUID) -> CostProfile | None:
        snaps = list(
            self._collection(organization_id)
            .where(filter=FieldFilter("is_default", "==", True))
            .where(filter=FieldFilter("deleted_at", "==", None))
            .limit(1)
            .stream()
        )
        if not snaps:
            return None
        return self.session.hydrate(
            CostProfile, snaps[0].id, snaps[0].to_dict(), snaps[0].reference
        )

    def clear_default(self, organization_id: UUID) -> None:
        for profile in self.list_for_org(organization_id):
            if profile.is_default:
                profile.is_default = False
        self.session.flush()

    def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        energy_cost_per_kwh: float,
        labor_cost_per_hour: float,
        packaging_cost_flat: float,
        waste_percentage: float,
        fees_percentage: float,
        profit_margin_percentage: float,
        tax_percentage: float | None,
        is_default: bool,
    ) -> CostProfile:
        profile = CostProfile(
            organization_id=organization_id,
            name=name,
            energy_cost_per_kwh=energy_cost_per_kwh,
            labor_cost_per_hour=labor_cost_per_hour,
            packaging_cost_flat=packaging_cost_flat,
            waste_percentage=waste_percentage,
            fees_percentage=fees_percentage,
            profit_margin_percentage=profit_margin_percentage,
            tax_percentage=tax_percentage,
            is_default=is_default,
        )
        doc_ref = self._collection(organization_id).document(str(profile.id))
        doc_ref.set(to_dict(profile))
        self.session.track(profile, doc_ref)
        return profile


class CustomerRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("customers")

    def get(self, organization_id: UUID, customer_id: UUID) -> Customer | None:
        doc_ref = self._collection(organization_id).document(str(customer_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(Customer, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[Customer]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        return [
            self.session.hydrate(Customer, s.id, s.to_dict(), s.reference) for s in snaps
        ]

    def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        email: str | None,
        phone: str | None,
        document: str | None,
        address: dict | None,
        notes: str | None,
    ) -> Customer:
        customer = Customer(
            organization_id=organization_id,
            name=name,
            email=email,
            phone=phone,
            document=document,
            address=address,
            notes=notes,
        )
        doc_ref = self._collection(organization_id).document(str(customer.id))
        doc_ref.set(to_dict(customer))
        self.session.track(customer, doc_ref)
        return customer

    def soft_delete(self, customer: Customer) -> None:
        customer.deleted_at = datetime.now(UTC)
        self.session.flush()


class MachineRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("machines")

    def get(self, organization_id: UUID, machine_id: UUID) -> Machine | None:
        doc_ref = self._collection(organization_id).document(str(machine_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(Machine, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[Machine]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at")
            .stream()
        )
        return [self.session.hydrate(Machine, s.id, s.to_dict(), s.reference) for s in snaps]

    def soft_delete(self, machine: Machine) -> None:
        machine.deleted_at = datetime.now(UTC)
        self.session.flush()

    def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        brand: str | None,
        model: str | None,
        technology: str,
        build_volume_x_mm: float | None,
        build_volume_y_mm: float | None,
        build_volume_z_mm: float | None,
        power_watts: float | None,
        cost_per_hour: float | None,
        speed_profile: dict | None,
        compatible_materials: list | None,
    ) -> Machine:
        machine = Machine(
            organization_id=organization_id,
            name=name,
            brand=brand,
            model=model,
            technology=technology,
            build_volume_x_mm=build_volume_x_mm,
            build_volume_y_mm=build_volume_y_mm,
            build_volume_z_mm=build_volume_z_mm,
            power_watts=power_watts,
            cost_per_hour=cost_per_hour,
            speed_profile=speed_profile,
            compatible_materials=compatible_materials,
        )
        doc_ref = self._collection(organization_id).document(str(machine.id))
        doc_ref.set(to_dict(machine))
        self.session.track(machine, doc_ref)
        return machine


class ProductRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("products")

    def get(self, organization_id: UUID, product_id: UUID) -> Product | None:
        doc_ref = self._collection(organization_id).document(str(product_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(Product, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[Product]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at")
            .stream()
        )
        return [self.session.hydrate(Product, s.id, s.to_dict(), s.reference) for s in snaps]

    def soft_delete(self, product: Product) -> None:
        product.deleted_at = datetime.now(UTC)
        self.session.flush()

    def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        description: str | None,
        print_time_hours: float | None,
        machine_id: UUID | None,
    ) -> Product:
        product = Product(
            organization_id=organization_id,
            name=name,
            description=description,
            print_time_hours=print_time_hours,
            machine_id=machine_id,
        )
        doc_ref = self._collection(organization_id).document(str(product.id))
        doc_ref.set(to_dict(product))
        self.session.track(product, doc_ref)
        return product


class ProductMaterialRepository:
    """`list_for_product`/`create`/`delete_for_product` take `organization_id`

    in addition to the SQL signature (see module docstring) - a product's
    BOM lines live in a subcollection under its own document.
    """

    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID, product_id: UUID):
        return (
            _org_ref(self.client, organization_id)
            .collection("products")
            .document(str(product_id))
            .collection("materials")
        )

    def list_for_product(
        self, organization_id: UUID, product_id: UUID
    ) -> list[ProductMaterial]:
        snaps = self._collection(organization_id, product_id).stream()
        return [
            self.session.hydrate(ProductMaterial, s.id, s.to_dict(), s.reference) for s in snaps
        ]

    def create(
        self, *, organization_id: UUID, product_id: UUID, material_id: UUID, quantity_g: float
    ) -> ProductMaterial:
        line = ProductMaterial(
            product_id=product_id, material_id=material_id, quantity_g=quantity_g
        )
        doc_ref = self._collection(organization_id, product_id).document(str(line.id))
        doc_ref.set(to_dict(line))
        self.session.track(line, doc_ref)
        return line

    def delete_for_product(self, organization_id: UUID, product_id: UUID) -> None:
        for snap in self._collection(organization_id, product_id).stream():
            snap.reference.delete()


class InventoryItemRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("inventory_items")

    def get(self, organization_id: UUID, item_id: UUID) -> InventoryItem | None:
        doc_ref = self._collection(organization_id).document(str(item_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(InventoryItem, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[InventoryItem]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at")
            .stream()
        )
        return [
            self.session.hydrate(InventoryItem, s.id, s.to_dict(), s.reference) for s in snaps
        ]

    def soft_delete(self, item: InventoryItem) -> None:
        item.deleted_at = datetime.now(UTC)
        self.session.flush()

    def create(
        self,
        *,
        organization_id: UUID,
        material_id: UUID | None,
        name: str,
        category: str,
        unit: str,
        minimum_stock: float,
        unit_cost: float | None,
        supplier: str | None,
        initial_quantity: float,
    ) -> InventoryItem:
        item = InventoryItem(
            organization_id=organization_id,
            material_id=material_id,
            name=name,
            category=category,
            unit=unit,
            minimum_stock=minimum_stock,
            unit_cost=unit_cost,
            supplier=supplier,
            quantity_on_hand=initial_quantity,
        )
        doc_ref = self._collection(organization_id).document(str(item.id))
        doc_ref.set(to_dict(item))
        self.session.track(item, doc_ref)
        return item

    def update_quantity(self, item: InventoryItem, *, new_quantity: float) -> None:
        item.quantity_on_hand = new_quantity
        self.session.flush()


class InventoryMovementRepository:
    """`list_for_item`/`create` take `organization_id` in addition to the SQL

    signature (see module docstring) - movements live in a subcollection
    under their inventory item's own document.
    """

    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID, inventory_item_id: UUID):
        return (
            _org_ref(self.client, organization_id)
            .collection("inventory_items")
            .document(str(inventory_item_id))
            .collection("movements")
        )

    def list_for_item(
        self, organization_id: UUID, inventory_item_id: UUID
    ) -> list[InventoryMovement]:
        snaps = (
            self._collection(organization_id, inventory_item_id)
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        return [
            self.session.hydrate(InventoryMovement, s.id, s.to_dict(), s.reference) for s in snaps
        ]

    def create(
        self,
        *,
        inventory_item_id: UUID,
        organization_id: UUID,
        type: str,
        quantity: float,
        unit_cost: float | None,
        notes: str | None,
        created_by: UUID | None,
        reference_order_id: UUID | None,
    ) -> InventoryMovement:
        movement = InventoryMovement(
            inventory_item_id=inventory_item_id,
            organization_id=organization_id,
            type=type,
            quantity=quantity,
            unit_cost=unit_cost,
            notes=notes,
            created_by=created_by,
            reference_order_id=reference_order_id,
        )
        doc_ref = self._collection(organization_id, inventory_item_id).document(str(movement.id))
        doc_ref.set(to_dict(movement))
        self.session.track(movement, doc_ref)
        return movement


class QuoteRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("quotes")

    def get(self, organization_id: UUID, quote_id: UUID) -> Quote | None:
        doc_ref = self._collection(organization_id).document(str(quote_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(Quote, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[Quote]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        return [self.session.hydrate(Quote, s.id, s.to_dict(), s.reference) for s in snaps]

    def list_for_customer(self, organization_id: UUID, customer_id: UUID) -> list[Quote]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("customer_id", "==", str(customer_id)))
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        return [self.session.hydrate(Quote, s.id, s.to_dict(), s.reference) for s in snaps]

    def soft_delete(self, quote: Quote) -> None:
        quote.deleted_at = datetime.now(UTC)
        self.session.flush()

    def create(
        self,
        *,
        organization_id: UUID,
        cost_profile_id: UUID,
        project_version_id: UUID | None,
        customer_id: UUID | None,
        created_by: UUID | None,
        piece_name: str | None,
        printer_name: str | None,
        machine_id: UUID | None = None,
        material_id: UUID | None = None,
        weight_g: float | None,
        cost_per_kg: float | None = None,
        extra_items: list[dict] | None = None,
        print_time_hours: float | None = None,
        depreciation_mode: str | None = None,
        depreciation_value: float | None = None,
        labor_hours: float | None = None,
        profit_margin_percentage: float | None = None,
        quantity: int,
        cost_breakdown_snapshot: dict,
        production_cost: float,
        suggested_price: float,
    ) -> Quote:
        quote = Quote(
            organization_id=organization_id,
            cost_profile_id=cost_profile_id,
            project_version_id=project_version_id,
            customer_id=customer_id,
            created_by=created_by,
            piece_name=piece_name,
            printer_name=printer_name,
            machine_id=machine_id,
            material_id=material_id,
            weight_g=weight_g,
            cost_per_kg=cost_per_kg,
            extra_items=extra_items,
            print_time_hours=print_time_hours,
            depreciation_mode=depreciation_mode,
            depreciation_value=depreciation_value,
            labor_hours=labor_hours,
            profit_margin_percentage=profit_margin_percentage,
            quantity=quantity,
            cost_breakdown_snapshot=cost_breakdown_snapshot,
            production_cost=production_cost,
            suggested_price=suggested_price,
        )
        doc_ref = self._collection(organization_id).document(str(quote.id))
        doc_ref.set(to_dict(quote))
        self.session.track(quote, doc_ref)
        return quote


class OrderRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("orders")

    def get(self, organization_id: UUID, order_id: UUID) -> Order | None:
        doc_ref = self._collection(organization_id).document(str(order_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(Order, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[Order]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        return [self.session.hydrate(Order, s.id, s.to_dict(), s.reference) for s in snaps]

    def list_for_customer(self, organization_id: UUID, customer_id: UUID) -> list[Order]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("customer_id", "==", str(customer_id)))
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        return [self.session.hydrate(Order, s.id, s.to_dict(), s.reference) for s in snaps]

    def create(
        self,
        *,
        organization_id: UUID,
        customer_id: UUID,
        quote_id: UUID | None,
        total_amount: float,
        notes: str | None,
        created_by: UUID | None,
    ) -> Order:
        order = Order(
            organization_id=organization_id,
            customer_id=customer_id,
            quote_id=quote_id,
            total_amount=total_amount,
            notes=notes,
            created_by=created_by,
        )
        doc_ref = self._collection(organization_id).document(str(order.id))
        doc_ref.set(to_dict(order))
        self.session.track(order, doc_ref)
        return order

    def update_status(self, order: Order, *, new_status: str) -> None:
        order.status = new_status
        self.session.flush()

    def update_total_amount(self, order: Order, *, total_amount: float) -> None:
        order.total_amount = total_amount
        self.session.flush()

    def soft_delete(self, order: Order) -> None:
        order.deleted_at = datetime.now(UTC)
        self.session.flush()


class OrderItemRepository:
    """`get`/`list_for_order`/`create` take `organization_id` in addition to

    the SQL signature (see module docstring) - items live in a subcollection
    under their order's own document.
    """

    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID, order_id: UUID):
        return (
            _org_ref(self.client, organization_id)
            .collection("orders")
            .document(str(order_id))
            .collection("items")
        )

    def get(self, organization_id: UUID, order_id: UUID, item_id: UUID) -> OrderItem | None:
        doc_ref = self._collection(organization_id, order_id).document(str(item_id))
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return self.session.hydrate(OrderItem, snap.id, snap.to_dict(), doc_ref)

    def list_for_order(self, organization_id: UUID, order_id: UUID) -> list[OrderItem]:
        snaps = self._collection(organization_id, order_id).order_by("created_at").stream()
        return [self.session.hydrate(OrderItem, s.id, s.to_dict(), s.reference) for s in snaps]

    def create(
        self,
        *,
        order_id: UUID,
        organization_id: UUID,
        project_version_id: UUID | None,
        product_id: UUID | None,
        machine_id: UUID | None,
        material_id: UUID | None,
        quantity: int,
        unit_cost: float | None,
        unit_price: float | None,
    ) -> OrderItem:
        item = OrderItem(
            order_id=order_id,
            organization_id=organization_id,
            project_version_id=project_version_id,
            product_id=product_id,
            machine_id=machine_id,
            material_id=material_id,
            quantity=quantity,
            unit_cost=unit_cost,
            unit_price=unit_price,
        )
        doc_ref = self._collection(organization_id, order_id).document(str(item.id))
        doc_ref.set(to_dict(item))
        self.session.track(item, doc_ref)
        return item

    def update(
        self,
        item: OrderItem,
        *,
        quantity: int | None,
        unit_cost: float | None,
        unit_price: float | None,
    ) -> None:
        if quantity is not None:
            item.quantity = quantity
        if unit_cost is not None:
            item.unit_cost = unit_cost
        if unit_price is not None:
            item.unit_price = unit_price
        self.session.flush()

    def delete(self, item: OrderItem) -> None:
        self.session.delete(item)
        self.session.flush()


class FinancialTransactionRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("financial_transactions")

    def get(self, organization_id: UUID, transaction_id: UUID) -> FinancialTransaction | None:
        doc_ref = self._collection(organization_id).document(str(transaction_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(FinancialTransaction, snap.id, snap.to_dict(), doc_ref)

    def soft_delete(self, transaction: FinancialTransaction) -> None:
        transaction.deleted_at = datetime.now(UTC)
        self.session.flush()

    def list_for_org(
        self,
        organization_id: UUID,
        *,
        type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[FinancialTransaction]:
        query = self._collection(organization_id).where(
            filter=FieldFilter("deleted_at", "==", None)
        )
        if type is not None:
            query = query.where(filter=FieldFilter("type", "==", type))
        query = query.order_by("created_at", direction="DESCENDING")
        results = []
        for snap in query.stream():
            transaction = self.session.hydrate(
                FinancialTransaction, snap.id, snap.to_dict(), snap.reference
            )
            if start_date is not None and transaction.created_at.date() < start_date:
                continue
            if end_date is not None and transaction.created_at.date() > end_date:
                continue
            results.append(transaction)
        return results

    def create(
        self,
        *,
        organization_id: UUID,
        type: str,
        category: str,
        cost_center: str | None,
        amount: float,
        reference_order_id: UUID | None,
        due_date: date | None,
        paid_at: datetime | None,
        created_by: UUID | None,
    ) -> FinancialTransaction:
        transaction = FinancialTransaction(
            organization_id=organization_id,
            type=type,
            category=category,
            cost_center=cost_center,
            amount=amount,
            reference_order_id=reference_order_id,
            # Firestore has no date-only type - the SQL column is `Date`,
            # but the client library only accepts datetime for timestamps.
            due_date=(
                datetime(due_date.year, due_date.month, due_date.day, tzinfo=UTC)
                if due_date is not None
                else None
            ),
            paid_at=paid_at,
            created_by=created_by,
        )
        doc_ref = self._collection(organization_id).document(str(transaction.id))
        doc_ref.set(to_dict(transaction))
        self.session.track(transaction, doc_ref)
        return transaction

    def mark_paid(self, transaction: FinancialTransaction) -> None:
        transaction.paid_at = datetime.now(UTC)
        self.session.flush()


class ProjectRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("projects")

    def get(self, organization_id: UUID, project_id: UUID) -> Project | None:
        doc_ref = self._collection(organization_id).document(str(project_id))
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("deleted_at") is not None:
            return None
        return self.session.hydrate(Project, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[Project]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        return [self.session.hydrate(Project, s.id, s.to_dict(), s.reference) for s in snaps]

    def list_for_customer(self, organization_id: UUID, customer_id: UUID) -> list[Project]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("customer_id", "==", str(customer_id)))
            .where(filter=FieldFilter("deleted_at", "==", None))
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        return [self.session.hydrate(Project, s.id, s.to_dict(), s.reference) for s in snaps]

    def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        description: str | None,
        created_by: UUID,
        customer_id: UUID | None = None,
    ) -> Project:
        project = Project(
            organization_id=organization_id,
            name=name,
            description=description,
            created_by=created_by,
            customer_id=customer_id,
        )
        doc_ref = self._collection(organization_id).document(str(project.id))
        doc_ref.set(to_dict(project))
        self.session.track(project, doc_ref)
        return project

    def soft_delete(self, project: Project) -> None:
        project.deleted_at = datetime.now(UTC)
        self.session.flush()


class ProjectVersionRepository:
    """`get`/`list_for_project`/`next_version_number`/`create` take

    `organization_id` in addition to the SQL signature (see module
    docstring) - versions live in a subcollection under their project's
    own document.
    """

    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID, project_id: UUID):
        return (
            _org_ref(self.client, organization_id)
            .collection("projects")
            .document(str(project_id))
            .collection("versions")
        )

    def get(
        self, organization_id: UUID, project_id: UUID, version_id: UUID
    ) -> ProjectVersion | None:
        doc_ref = self._collection(organization_id, project_id).document(str(version_id))
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return self.session.hydrate(ProjectVersion, snap.id, snap.to_dict(), doc_ref)

    def list_for_project(
        self, organization_id: UUID, project_id: UUID
    ) -> list[ProjectVersion]:
        snaps = (
            self._collection(organization_id, project_id)
            .order_by("version_number", direction="DESCENDING")
            .stream()
        )
        return [
            self.session.hydrate(ProjectVersion, s.id, s.to_dict(), s.reference) for s in snaps
        ]

    def next_version_number(self, organization_id: UUID, project_id: UUID) -> int:
        versions = self.list_for_project(organization_id, project_id)
        return (max((v.version_number for v in versions), default=0)) + 1

    def create(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        version_number: int,
        label: str | None,
        source_type: str,
        created_by: UUID,
    ) -> ProjectVersion:
        version = ProjectVersion(
            project_id=project_id,
            version_number=version_number,
            label=label,
            source_type=source_type,
            status="ready",
            created_by=created_by,
        )
        doc_ref = self._collection(organization_id, project_id).document(str(version.id))
        doc_ref.set(to_dict(version))
        self.session.track(version, doc_ref)
        return version


class FileAssetRepository:
    """`list_for_version` takes `organization_id` in addition to the SQL

    signature (see module docstring) - files live in a flat subcollection
    directly under the organization, not nested under project/version.
    """

    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, organization_id: UUID):
        return _org_ref(self.client, organization_id).collection("files")

    def get(self, organization_id: UUID, file_id: UUID) -> FileAsset | None:
        doc_ref = self._collection(organization_id).document(str(file_id))
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return self.session.hydrate(FileAsset, snap.id, snap.to_dict(), doc_ref)

    def sum_size_bytes_for_org(self, organization_id: UUID) -> int:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("status", "==", "uploaded"))
            .stream()
        )
        return sum((s.to_dict().get("size_bytes") or 0) for s in snaps)

    def list_for_version(
        self, organization_id: UUID, project_version_id: UUID
    ) -> list[FileAsset]:
        snaps = (
            self._collection(organization_id)
            .where(filter=FieldFilter("project_version_id", "==", str(project_version_id)))
            .order_by("created_at")
            .stream()
        )
        return [self.session.hydrate(FileAsset, s.id, s.to_dict(), s.reference) for s in snaps]

    def create(
        self,
        *,
        organization_id: UUID,
        project_id: UUID | None,
        kind: str,
        storage_key: str,
        mime_type: str,
        uploaded_by: UUID,
    ) -> FileAsset:
        file_asset = FileAsset(
            organization_id=organization_id,
            project_id=project_id,
            kind=kind,
            storage_key=storage_key,
            mime_type=mime_type,
            uploaded_by=uploaded_by,
        )
        doc_ref = self._collection(organization_id).document(str(file_asset.id))
        doc_ref.set(to_dict(file_asset))
        self.session.track(file_asset, doc_ref)
        return file_asset

    def mark_uploaded(self, file_asset: FileAsset, *, size_bytes: int, mime_type: str) -> None:
        file_asset.status = "uploaded"
        file_asset.size_bytes = size_bytes
        file_asset.mime_type = mime_type
        self.session.flush()

    def attach_to_version(self, file_asset: FileAsset, *, project_version_id: UUID) -> None:
        file_asset.project_version_id = project_version_id
        self.session.flush()

    def create_uploaded(
        self,
        *,
        organization_id: UUID,
        project_id: UUID | None,
        kind: str,
        storage_key: str,
        mime_type: str,
        size_bytes: int,
        sha256_hash: str,
        uploaded_by: UUID | None,
    ) -> FileAsset:
        file_asset = FileAsset(
            organization_id=organization_id,
            project_id=project_id,
            kind=kind,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256_hash=sha256_hash,
            status="uploaded",
            uploaded_by=uploaded_by,
        )
        doc_ref = self._collection(organization_id).document(str(file_asset.id))
        doc_ref.set(to_dict(file_asset))
        self.session.track(file_asset, doc_ref)
        return file_asset


class PlanRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def get(self, plan_id: UUID) -> Plan | None:
        doc_ref = self.client.collection("plans").document(str(plan_id))
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return self.session.hydrate(Plan, snap.id, snap.to_dict(), doc_ref)

    def get_by_code(self, code: str) -> Plan | None:
        snaps = list(
            self.client.collection("plans")
            .where(filter=FieldFilter("code", "==", code))
            .limit(1)
            .stream()
        )
        if not snaps:
            return None
        return self.session.hydrate(Plan, snaps[0].id, snaps[0].to_dict(), snaps[0].reference)

    def list_active(self) -> list[Plan]:
        snaps = (
            self.client.collection("plans")
            .where(filter=FieldFilter("is_active", "==", True))
            .order_by("created_at")
            .stream()
        )
        return [self.session.hydrate(Plan, s.id, s.to_dict(), s.reference) for s in snaps]

    def create(
        self, *, code: str, name: str, is_active: bool, trial_period_days: int | None
    ) -> Plan:
        plan = Plan(code=code, name=name, is_active=is_active, trial_period_days=trial_period_days)
        doc_ref = self.client.collection("plans").document(str(plan.id))
        doc_ref.set(to_dict(plan))
        self.session.track(plan, doc_ref)
        return plan


class PlanEntitlementRepository:
    """Stored as a subcollection under the plan, with the entitlement's

    `key` as the document id - that alone enforces the SQL schema's
    `(plan_id, key)` uniqueness, and makes `get_for_plan` an O(1) get.
    """

    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def _collection(self, plan_id: UUID):
        return self.client.collection("plans").document(str(plan_id)).collection("entitlements")

    def get_for_plan(self, plan_id: UUID, key: str) -> PlanEntitlement | None:
        doc_ref = self._collection(plan_id).document(key)
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return self.session.hydrate(PlanEntitlement, snap.id, snap.to_dict(), doc_ref)

    def list_for_plan(self, plan_id: UUID) -> list[PlanEntitlement]:
        snaps = self._collection(plan_id).stream()
        return [
            self.session.hydrate(PlanEntitlement, s.id, s.to_dict(), s.reference) for s in snaps
        ]

    def create(
        self,
        *,
        plan_id: UUID,
        key: str,
        limit_type: str,
        bool_value: bool | None,
        numeric_value: float | None,
    ) -> PlanEntitlement:
        entitlement = PlanEntitlement(
            plan_id=plan_id,
            key=key,
            limit_type=limit_type,
            bool_value=bool_value,
            numeric_value=numeric_value,
        )
        doc_ref = self._collection(plan_id).document(key)
        doc_ref.set(to_dict(entitlement))
        self.session.track(entitlement, doc_ref)
        return entitlement


class SubscriptionRepository:
    """Doc id = organization_id, enforcing the SQL schema's one-subscription-

    per-org uniqueness naturally and making `get_by_organization` an O(1) get.
    """

    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def get(self, subscription_id: UUID) -> Subscription | None:
        doc_ref = self.client.collection("subscriptions").document(str(subscription_id))
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return self.session.hydrate(Subscription, snap.id, snap.to_dict(), doc_ref)

    def get_by_organization(self, organization_id: UUID) -> Subscription | None:
        return self.get(organization_id)

    def create(
        self,
        *,
        organization_id: UUID,
        plan_id: UUID,
        status: str,
        current_period_start: datetime,
        current_period_end: datetime,
        trial_start: datetime | None,
        trial_end: datetime | None,
        external_provider: str,
        external_subscription_id: str | None,
        external_customer_id: str | None,
    ) -> Subscription:
        subscription = Subscription(
            organization_id=organization_id,
            plan_id=plan_id,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            trial_start=trial_start,
            trial_end=trial_end,
            external_provider=external_provider,
            external_subscription_id=external_subscription_id,
            external_customer_id=external_customer_id,
        )
        # doc id = organization_id, not subscription.id, for the natural
        # 1:1 uniqueness - subscription.id is still a real distinct value,
        # just not the one used to address the document.
        doc_ref = self.client.collection("subscriptions").document(str(organization_id))
        doc_ref.set(to_dict(subscription))
        self.session.track(subscription, doc_ref)
        return subscription

    def update_status(self, subscription: Subscription, *, status: str) -> None:
        subscription.status = status
        self.session.flush()

    def update_plan(self, subscription: Subscription, *, plan_id: UUID) -> None:
        subscription.plan_id = plan_id
        self.session.flush()

    def mark_cancel_at_period_end(self, subscription: Subscription, *, value: bool) -> None:
        subscription.cancel_at_period_end = value
        self.session.flush()

    def mark_canceled_now(self, subscription: Subscription) -> None:
        subscription.status = "canceled"
        subscription.canceled_at = datetime.now(UTC)
        self.session.flush()


class BillingEventRepository:
    def __init__(self, session: FirestoreSession) -> None:
        self.session = session
        self.client = session.client

    def get_by_provider_and_external_id(
        self, provider: str, external_event_id: str
    ) -> BillingEvent | None:
        index_snap = (
            self.client.collection("billing_event_index")
            .document(f"{provider}:{external_event_id}")
            .get()
        )
        if not index_snap.exists:
            return None
        event_id = index_snap.to_dict()["event_id"]
        doc_ref = self.client.collection("billing_events").document(event_id)
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return self.session.hydrate(BillingEvent, snap.id, snap.to_dict(), doc_ref)

    def list_for_org(self, organization_id: UUID) -> list[BillingEvent]:
        snaps = (
            self.client.collection("billing_events")
            .where(filter=FieldFilter("organization_id", "==", str(organization_id)))
            .order_by("received_at", direction="DESCENDING")
            .stream()
        )
        return [
            self.session.hydrate(BillingEvent, s.id, s.to_dict(), s.reference) for s in snaps
        ]

    def create(
        self,
        *,
        provider: str,
        external_event_id: str,
        event_type: str,
        organization_id: UUID | None,
        payload: dict,
    ) -> BillingEvent:
        event = BillingEvent(
            provider=provider,
            external_event_id=external_event_id,
            event_type=event_type,
            organization_id=organization_id,
            payload=payload,
        )
        doc_ref = self.client.collection("billing_events").document(str(event.id))
        doc_ref.set(to_dict(event))
        self.client.collection("billing_event_index").document(
            f"{provider}:{external_event_id}"
        ).set({"event_id": str(event.id)})
        self.session.track(event, doc_ref)
        return event

    def mark_processed(self, event: BillingEvent) -> None:
        event.status = "processed"
        event.processed_at = datetime.now(UTC)
        self.session.flush()
