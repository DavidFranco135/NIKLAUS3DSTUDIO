from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.db.models import (
    AIJob,
    AIJobAttempt,
    CostProfile,
    FileAsset,
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

    def create(
        self, *, organization_id: UUID, name: str, description: str | None, created_by: UUID
    ) -> Project:
        project = Project(
            organization_id=organization_id,
            name=name,
            description=description,
            created_by=created_by,
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
