import secrets

from sqlalchemy.orm import Session

from src.domain.shared.slug import slugify
from src.infrastructure.db.repositories import OrganizationRepository


def unique_org_slug(db: Session, name: str) -> str:
    org_repo = OrganizationRepository(db)
    base_slug = slugify(name)
    slug = base_slug
    while org_repo.slug_exists(slug):
        slug = f"{base_slug}-{secrets.token_hex(2)}"
    return slug
