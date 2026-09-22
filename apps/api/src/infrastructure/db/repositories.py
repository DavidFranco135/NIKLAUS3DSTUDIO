from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.db.models import (
    AIJob,
    AIJobAttempt,
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
    Project,
    ProjectVersion,
    Quote,
    RefreshToken,
    User,
)


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip even for DateTime(timezone=True); Postgres keeps it."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def create(self, *, email: str, password_hash: str, full_name: str | None) -> User:
        user = User(email=email, password_hash=password_hash, full_name=full_name)
        self.session.add(user)
        self.session.flush()
        return user


class OrganizationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, organization_id: UUID) -> Organization | None:
        return self.session.get(Organization, organization_id)

    def slug_exists(self, slug: str) -> bool:
        stmt = select(Organization).where(Organization.slug == slug)
        return self.session.scalar(stmt) is not None

    def create(self, *, name: str, slug: str) -> Organization:
        organization = Organization(name=name, slug=slug)
        self.session.add(organization)
        self.session.flush()
        return organization

    def list_for_user(self, user_id: UUID) -> list[Organization]:
        return list(
            self.session.scalars(
                select(Organization)
                .join(OrgMember, OrgMember.organization_id == Organization.id)
                .where(OrgMember.user_id == user_id)
                .order_by(Organization.created_at)
            )
        )


class OrgMemberRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, user_id: UUID) -> OrgMember | None:
        return self.session.scalar(
            select(OrgMember).where(
                OrgMember.organization_id == organization_id,
                OrgMember.user_id == user_id,
            )
        )

    def list_for_org(self, organization_id: UUID) -> list[OrgMember]:
        return list(
            self.session.scalars(
                select(OrgMember)
                .where(OrgMember.organization_id == organization_id)
                .order_by(OrgMember.created_at)
            )
        )

    def count_owners(self, organization_id: UUID) -> int:
        return len(
            [
                m
                for m in self.list_for_org(organization_id)
                if m.role == "OWNER"
            ]
        )

    def create(
        self, *, organization_id: UUID, user_id: UUID, role: str, invited_by: UUID | None = None
    ) -> OrgMember:
        member = OrgMember(
            organization_id=organization_id, user_id=user_id, role=role, invited_by=invited_by
        )
        self.session.add(member)
        self.session.flush()
        return member

    def delete(self, member: OrgMember) -> None:
        self.session.delete(member)
        self.session.flush()


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(token)
        self.session.flush()
        return token

    def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        token = self.session.scalar(stmt)
        if token is None or token.revoked_at is not None:
            return None
        if _as_aware_utc(token.expires_at) < datetime.now(UTC):
            return None
        return token

    def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        self.session.flush()


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, project_id: UUID) -> Project | None:
        return self.session.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
                Project.deleted_at.is_(None),
            )
        )

    def list_for_org(self, organization_id: UUID) -> list[Project]:
        return list(
            self.session.scalars(
                select(Project)
                .where(Project.organization_id == organization_id, Project.deleted_at.is_(None))
                .order_by(Project.created_at.desc())
            )
        )

    def list_for_customer(self, organization_id: UUID, customer_id: UUID) -> list[Project]:
        return list(
            self.session.scalars(
                select(Project)
                .where(
                    Project.organization_id == organization_id,
                    Project.customer_id == customer_id,
                    Project.deleted_at.is_(None),
                )
                .order_by(Project.created_at.desc())
            )
        )

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
        self.session.add(project)
        self.session.flush()
        return project

    def soft_delete(self, project: Project) -> None:
        project.deleted_at = datetime.now(UTC)
        self.session.flush()


class ProjectVersionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, project_id: UUID, version_id: UUID) -> ProjectVersion | None:
        return self.session.scalar(
            select(ProjectVersion).where(
                ProjectVersion.id == version_id, ProjectVersion.project_id == project_id
            )
        )

    def list_for_project(self, project_id: UUID) -> list[ProjectVersion]:
        return list(
            self.session.scalars(
                select(ProjectVersion)
                .where(ProjectVersion.project_id == project_id)
                .order_by(ProjectVersion.version_number.desc())
            )
        )

    def next_version_number(self, project_id: UUID) -> int:
        current_max = self.session.scalar(
            select(ProjectVersion.version_number)
            .where(ProjectVersion.project_id == project_id)
            .order_by(ProjectVersion.version_number.desc())
            .limit(1)
        )
        return (current_max or 0) + 1

    def create(
        self,
        *,
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
        self.session.add(version)
        self.session.flush()
        return version


class FileAssetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, file_id: UUID) -> FileAsset | None:
        return self.session.scalar(
            select(FileAsset).where(
                FileAsset.id == file_id, FileAsset.organization_id == organization_id
            )
        )

    def list_for_version(self, project_version_id: UUID) -> list[FileAsset]:
        return list(
            self.session.scalars(
                select(FileAsset)
                .where(FileAsset.project_version_id == project_version_id)
                .order_by(FileAsset.created_at)
            )
        )

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
        self.session.add(file_asset)
        self.session.flush()
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
        """For server-side writes (e.g. AI worker output) that skip the

        pending -> confirm dance a browser upload needs: the caller already
        holds the bytes, so there is nothing left to confirm.
        """
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
        self.session.add(file_asset)
        self.session.flush()
        return file_asset


class AIJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, job_id: UUID) -> AIJob | None:
        return self.session.scalar(
            select(AIJob).where(AIJob.id == job_id, AIJob.organization_id == organization_id)
        )

    def get_active_by_idempotency_key(
        self, organization_id: UUID, idempotency_key: str
    ) -> AIJob | None:
        return self.session.scalar(
            select(AIJob).where(
                AIJob.organization_id == organization_id,
                AIJob.idempotency_key == idempotency_key,
                AIJob.status.in_(["QUEUED", "PROCESSING", "VALIDATING", "COMPLETED"]),
            )
        )

    def get_by_idempotency_key(self, organization_id: UUID, idempotency_key: str) -> AIJob | None:
        """Regardless of status — used to find a previously `FAILED` job for

        the same request so a retry can reuse (reset) that row instead of
        crashing on the `UNIQUE(organization_id, idempotency_key)` constraint.
        """
        return self.session.scalar(
            select(AIJob).where(
                AIJob.organization_id == organization_id,
                AIJob.idempotency_key == idempotency_key,
            )
        )

    def reset_for_retry(self, job: AIJob) -> None:
        job.status = "QUEUED"
        job.error_message = None
        job.result_file_id = None
        job.result_project_version_id = None
        job.result_metadata = None
        job.started_at = None
        job.finished_at = None
        self.session.flush()

    def list_for_org(self, organization_id: UUID, *, project_id: UUID | None = None) -> list[AIJob]:
        stmt = select(AIJob).where(AIJob.organization_id == organization_id)
        if project_id is not None:
            stmt = stmt.where(AIJob.project_id == project_id)
        return list(self.session.scalars(stmt.order_by(AIJob.created_at.desc())))

    def create(
        self,
        *,
        organization_id: UUID,
        project_id: UUID | None,
        requested_by: UUID | None,
        task_type: str,
        input_spec: dict,
        queue_name: str,
        idempotency_key: str,
        source_image_file_id: UUID | None = None,
    ) -> AIJob:
        job = AIJob(
            organization_id=organization_id,
            project_id=project_id,
            requested_by=requested_by,
            task_type=task_type,
            input_spec=input_spec,
            queue_name=queue_name,
            idempotency_key=idempotency_key,
            source_image_file_id=source_image_file_id,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def mark_processing(self, job: AIJob) -> None:
        job.status = "PROCESSING"
        job.started_at = datetime.now(UTC)
        self.session.flush()

    def mark_validating(self, job: AIJob) -> None:
        job.status = "VALIDATING"
        self.session.flush()

    def mark_completed(
        self,
        job: AIJob,
        *,
        result_file_id: UUID,
        result_project_version_id: UUID | None,
        result_metadata: dict | None,
    ) -> None:
        job.status = "COMPLETED"
        job.result_file_id = result_file_id
        job.result_project_version_id = result_project_version_id
        job.result_metadata = result_metadata
        job.finished_at = datetime.now(UTC)
        self.session.flush()

    def mark_failed(self, job: AIJob, *, error_message: str) -> None:
        job.status = "FAILED"
        job.error_message = error_message
        job.finished_at = datetime.now(UTC)
        self.session.flush()


class AIJobAttemptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_job(self, ai_job_id: UUID) -> list[AIJobAttempt]:
        return list(
            self.session.scalars(
                select(AIJobAttempt)
                .where(AIJobAttempt.ai_job_id == ai_job_id)
                .order_by(AIJobAttempt.attempt_number)
            )
        )

    def create(
        self,
        *,
        ai_job_id: UUID,
        provider_name: str,
        attempt_number: int,
        status: str,
        error_detail: str | None,
        duration_ms: int,
    ) -> AIJobAttempt:
        attempt = AIJobAttempt(
            ai_job_id=ai_job_id,
            provider_name=provider_name,
            attempt_number=attempt_number,
            status=status,
            error_detail=error_detail,
            duration_ms=duration_ms,
        )
        self.session.add(attempt)
        self.session.flush()
        return attempt


class CostProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, cost_profile_id: UUID) -> CostProfile | None:
        return self.session.scalar(
            select(CostProfile).where(
                CostProfile.id == cost_profile_id,
                CostProfile.organization_id == organization_id,
            )
        )

    def list_for_org(self, organization_id: UUID) -> list[CostProfile]:
        return list(
            self.session.scalars(
                select(CostProfile)
                .where(CostProfile.organization_id == organization_id)
                .order_by(CostProfile.created_at)
            )
        )

    def get_default(self, organization_id: UUID) -> CostProfile | None:
        return self.session.scalar(
            select(CostProfile).where(
                CostProfile.organization_id == organization_id,
                CostProfile.is_default.is_(True),
            )
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
        self.session.add(profile)
        self.session.flush()
        return profile


class QuoteRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, quote_id: UUID) -> Quote | None:
        return self.session.scalar(
            select(Quote).where(Quote.id == quote_id, Quote.organization_id == organization_id)
        )

    def list_for_org(self, organization_id: UUID) -> list[Quote]:
        return list(
            self.session.scalars(
                select(Quote)
                .where(Quote.organization_id == organization_id)
                .order_by(Quote.created_at.desc())
            )
        )

    def list_for_customer(self, organization_id: UUID, customer_id: UUID) -> list[Quote]:
        return list(
            self.session.scalars(
                select(Quote)
                .where(
                    Quote.organization_id == organization_id, Quote.customer_id == customer_id
                )
                .order_by(Quote.created_at.desc())
            )
        )

    def create(
        self,
        *,
        organization_id: UUID,
        cost_profile_id: UUID,
        project_version_id: UUID | None,
        customer_id: UUID | None,
        created_by: UUID | None,
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
            cost_breakdown_snapshot=cost_breakdown_snapshot,
            production_cost=production_cost,
            suggested_price=suggested_price,
        )
        self.session.add(quote)
        self.session.flush()
        return quote


class MaterialRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, material_id: UUID) -> Material | None:
        return self.session.scalar(
            select(Material).where(
                Material.id == material_id, Material.organization_id == organization_id
            )
        )

    def list_for_org(self, organization_id: UUID) -> list[Material]:
        return list(
            self.session.scalars(
                select(Material)
                .where(Material.organization_id == organization_id)
                .order_by(Material.created_at)
            )
        )

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
        self.session.add(material)
        self.session.flush()
        return material


class InventoryItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, item_id: UUID) -> InventoryItem | None:
        return self.session.scalar(
            select(InventoryItem).where(
                InventoryItem.id == item_id, InventoryItem.organization_id == organization_id
            )
        )

    def list_for_org(self, organization_id: UUID) -> list[InventoryItem]:
        return list(
            self.session.scalars(
                select(InventoryItem)
                .where(InventoryItem.organization_id == organization_id)
                .order_by(InventoryItem.created_at)
            )
        )

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
        self.session.add(item)
        self.session.flush()
        return item

    def update_quantity(self, item: InventoryItem, *, new_quantity: float) -> None:
        item.quantity_on_hand = new_quantity
        self.session.flush()


class InventoryMovementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_item(self, inventory_item_id: UUID) -> list[InventoryMovement]:
        return list(
            self.session.scalars(
                select(InventoryMovement)
                .where(InventoryMovement.inventory_item_id == inventory_item_id)
                .order_by(InventoryMovement.created_at.desc())
            )
        )

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
        self.session.add(movement)
        self.session.flush()
        return movement


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, customer_id: UUID) -> Customer | None:
        return self.session.scalar(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.organization_id == organization_id,
                Customer.deleted_at.is_(None),
            )
        )

    def list_for_org(self, organization_id: UUID) -> list[Customer]:
        return list(
            self.session.scalars(
                select(Customer)
                .where(Customer.organization_id == organization_id, Customer.deleted_at.is_(None))
                .order_by(Customer.created_at.desc())
            )
        )

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
        self.session.add(customer)
        self.session.flush()
        return customer

    def soft_delete(self, customer: Customer) -> None:
        customer.deleted_at = datetime.now(UTC)
        self.session.flush()


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, order_id: UUID) -> Order | None:
        return self.session.scalar(
            select(Order).where(Order.id == order_id, Order.organization_id == organization_id)
        )

    def list_for_org(self, organization_id: UUID) -> list[Order]:
        return list(
            self.session.scalars(
                select(Order)
                .where(Order.organization_id == organization_id)
                .order_by(Order.created_at.desc())
            )
        )

    def list_for_customer(self, organization_id: UUID, customer_id: UUID) -> list[Order]:
        return list(
            self.session.scalars(
                select(Order)
                .where(
                    Order.organization_id == organization_id, Order.customer_id == customer_id
                )
                .order_by(Order.created_at.desc())
            )
        )

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
        self.session.add(order)
        self.session.flush()
        return order

    def update_status(self, order: Order, *, new_status: str) -> None:
        order.status = new_status
        self.session.flush()

    def update_total_amount(self, order: Order, *, total_amount: float) -> None:
        order.total_amount = total_amount
        self.session.flush()


class OrderItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, order_id: UUID, item_id: UUID) -> OrderItem | None:
        return self.session.scalar(
            select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
        )

    def list_for_order(self, order_id: UUID) -> list[OrderItem]:
        return list(
            self.session.scalars(
                select(OrderItem)
                .where(OrderItem.order_id == order_id)
                .order_by(OrderItem.created_at)
            )
        )

    def create(
        self,
        *,
        order_id: UUID,
        organization_id: UUID,
        project_version_id: UUID | None,
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
            machine_id=machine_id,
            material_id=material_id,
            quantity=quantity,
            unit_cost=unit_cost,
            unit_price=unit_price,
        )
        self.session.add(item)
        self.session.flush()
        return item


class FinancialTransactionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, transaction_id: UUID) -> FinancialTransaction | None:
        return self.session.scalar(
            select(FinancialTransaction).where(
                FinancialTransaction.id == transaction_id,
                FinancialTransaction.organization_id == organization_id,
            )
        )

    def list_for_org(
        self,
        organization_id: UUID,
        *,
        type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[FinancialTransaction]:
        stmt = select(FinancialTransaction).where(
            FinancialTransaction.organization_id == organization_id
        )
        if type is not None:
            stmt = stmt.where(FinancialTransaction.type == type)
        if start_date is not None:
            stmt = stmt.where(FinancialTransaction.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(FinancialTransaction.created_at <= end_date)
        return list(self.session.scalars(stmt.order_by(FinancialTransaction.created_at.desc())))

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
            due_date=due_date,
            paid_at=paid_at,
            created_by=created_by,
        )
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def mark_paid(self, transaction: FinancialTransaction) -> None:
        transaction.paid_at = datetime.now(UTC)
        self.session.flush()


class MachineRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, machine_id: UUID) -> Machine | None:
        return self.session.scalar(
            select(Machine).where(
                Machine.id == machine_id, Machine.organization_id == organization_id
            )
        )

    def list_for_org(self, organization_id: UUID) -> list[Machine]:
        return list(
            self.session.scalars(
                select(Machine)
                .where(Machine.organization_id == organization_id)
                .order_by(Machine.created_at)
            )
        )

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
        self.session.add(machine)
        self.session.flush()
        return machine
