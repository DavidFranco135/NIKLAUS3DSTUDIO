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
"""
from datetime import UTC, datetime
from uuid import UUID

from google.cloud.firestore import Client
from google.cloud.firestore_v1.base_query import FieldFilter

from src.infrastructure.firestore.entities import (
    CostProfile,
    Material,
    Organization,
    OrgMember,
    RefreshToken,
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
