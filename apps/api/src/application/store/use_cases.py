import time
from uuid import UUID

from sqlalchemy.orm import Session

from src.application.products.use_cases import list_products_costs
from src.domain.shared.exceptions import OrganizationNotFoundError
from src.infrastructure.repositories import (
    CostProfileRepository,
    OrganizationRepository,
    ProductRepository,
)
from src.interfaces.http.v1.schemas import (
    PublicProduct,
    PublicStoreResponse,
    PublicStoreSettings,
    StoreAdminResponse,
    StoreSettings,
)

_PUBLIC_CACHE_TTL_SECONDS = 30.0
_public_cache: dict[str, tuple[float, PublicStoreResponse]] = {}


def _load_settings(raw: dict | None) -> StoreSettings:
    try:
        return StoreSettings.model_validate((raw or {}).get("store") or {})
    except ValueError:
        return StoreSettings()


def get_store_settings(db: Session, *, organization_id: UUID) -> StoreAdminResponse:
    org = OrganizationRepository(db).get_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError(str(organization_id))
    return StoreAdminResponse(
        slug=org.slug, name=org.name, settings=_load_settings(org.settings)
    )


def save_store_settings(
    db: Session, *, organization_id: UUID, settings: StoreSettings
) -> StoreAdminResponse:
    org = OrganizationRepository(db).get_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError(str(organization_id))
    # Reassign the whole dict so SQLAlchemy sees the JSON column as changed.
    org.settings = {**(org.settings or {}), "store": settings.model_dump()}
    db.commit()
    _public_cache.pop(org.slug, None)
    return StoreAdminResponse(slug=org.slug, name=org.name, settings=settings)


def get_public_store(db: Session, *, slug: str) -> PublicStoreResponse:
    cached = _public_cache.get(slug)
    if cached is not None and time.monotonic() - cached[0] < _PUBLIC_CACHE_TTL_SECONDS:
        return cached[1]

    org = OrganizationRepository(db).get_by_slug(slug)
    if org is None:
        raise OrganizationNotFoundError(slug)
    settings = _load_settings(org.settings)

    default_profile = CostProfileRepository(db).get_default(org.id)
    computed = (
        list_products_costs(db, organization_id=org.id, cost_profile_id=default_profile.id)
        if default_profile is not None
        else {}
    )

    hidden = set(settings.hidden_product_ids)
    featured = set(settings.featured_product_ids)
    products: list[PublicProduct] = []
    for product in ProductRepository(db).list_for_org(org.id):
        if not product.is_active or str(product.id) in hidden:
            continue
        if product.manual_price is not None:
            price = product.manual_price
        elif product.id in computed:
            price = computed[product.id].suggested_price
        else:
            continue
        stock = product.stock_quantity
        products.append(
            PublicProduct(
                id=product.id,
                name=product.name,
                description=product.description,
                size=product.size,
                photo_urls=list(product.photo_urls or []),
                price=round(float(price), 2),
                stock_quantity=stock,
                available=stock is None or stock > 0,
                featured=str(product.id) in featured,
            )
        )

    response = PublicStoreResponse(
        slug=org.slug,
        name=org.name,
        settings=PublicStoreSettings(
            display_name=settings.display_name or org.name,
            tagline=settings.tagline,
            about=settings.about,
            whatsapp=settings.whatsapp,
            instagram=settings.instagram,
            hours=settings.hours,
            address=settings.address,
            accent=settings.accent,
            theme=settings.theme,
            slides=settings.slides,
            highlights=settings.highlights,
        ),
        products=products,
    )
    _public_cache[slug] = (time.monotonic(), response)
    return response
