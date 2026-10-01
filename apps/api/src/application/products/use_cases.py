from uuid import UUID

from sqlalchemy.orm import Session

from src.application.calculator.use_cases import get_cost_profile
from src.application.inventory.use_cases import get_material
from src.application.machines.use_cases import get_machine
from src.domain.calculator.engine import calculate_quote
from src.domain.calculator.inputs import QuoteInputs
from src.domain.calculator.profile import CostProfileValues
from src.domain.calculator.report import CostBreakdown
from src.domain.shared.exceptions import ProductNotFoundError
from src.infrastructure.db.models import Product
from src.infrastructure.repositories import (
    MachineRepository,
    MaterialRepository,
    ProductMaterialRepository,
    ProductRepository,
)


def create_product(
    db: Session,
    *,
    organization_id: UUID,
    name: str,
    description: str | None,
    print_time_hours: float | None,
    machine_id: UUID | None,
    manual_price: float | None = None,
    size: str | None = None,
    photo_url: str | None = None,
    materials: list[dict],
) -> Product:
    """`materials` is a list of {"material_id": UUID, "quantity_g": float} —

    the product's bill of materials (BOM): how much of each raw material one
    unit consumes. Validated against the org's own material/machine catalog
    so a product can never reference another org's rows or a typo'd id.

    `manual_price` is the escape hatch for a "simple" product: just a name
    and a fixed sale price, no machine/BOM/cost-profile needed. When set,
    `compute_product_cost` returns it directly instead of running the BOM
    through the pricing formula.
    """
    if machine_id is not None:
        get_machine(db, organization_id=organization_id, machine_id=machine_id)
    for line in materials:
        get_material(db, organization_id=organization_id, material_id=line["material_id"])

    product = ProductRepository(db).create(
        organization_id=organization_id,
        name=name,
        description=description,
        print_time_hours=print_time_hours,
        machine_id=machine_id,
        manual_price=manual_price,
        size=size,
        photo_url=photo_url,
    )
    material_repo = ProductMaterialRepository(db)
    for line in materials:
        material_repo.create(
            organization_id=organization_id,
            product_id=product.id,
            material_id=line["material_id"],
            quantity_g=line["quantity_g"],
        )
    db.commit()
    return product


def list_products(db: Session, *, organization_id: UUID) -> list[Product]:
    return ProductRepository(db).list_for_org(organization_id)


def get_product(db: Session, *, organization_id: UUID, product_id: UUID) -> Product:
    product = ProductRepository(db).get(organization_id, product_id)
    if product is None:
        raise ProductNotFoundError(str(product_id))
    return product


def list_product_materials(
    db: Session, *, organization_id: UUID, product_id: UUID
) -> list[dict]:
    lines = ProductMaterialRepository(db).list_for_product(organization_id, product_id)
    return [{"material_id": line.material_id, "quantity_g": line.quantity_g} for line in lines]


def update_product(
    db: Session,
    *,
    organization_id: UUID,
    product_id: UUID,
    name: str | None,
    description: str | None,
    print_time_hours: float | None,
    machine_id: UUID | None,
    manual_price: float | None = None,
    size: str | None = None,
    photo_url: str | None = None,
    materials: list[dict] | None,
) -> Product:
    """`materials`, when provided, fully replaces the product's BOM (the

    frontend always sends the complete, current list of lines — there is no
    partial line-level update).
    """
    product = get_product(db, organization_id=organization_id, product_id=product_id)
    if name is not None:
        product.name = name
    if description is not None:
        product.description = description
    if print_time_hours is not None:
        product.print_time_hours = print_time_hours
    if machine_id is not None:
        get_machine(db, organization_id=organization_id, machine_id=machine_id)
        product.machine_id = machine_id
    if manual_price is not None:
        product.manual_price = manual_price
    if size is not None:
        product.size = size
    if photo_url is not None:
        product.photo_url = photo_url
    if materials is not None:
        for line in materials:
            get_material(db, organization_id=organization_id, material_id=line["material_id"])
        material_repo = ProductMaterialRepository(db)
        material_repo.delete_for_product(organization_id, product.id)
        for line in materials:
            material_repo.create(
                organization_id=organization_id,
                product_id=product.id,
                material_id=line["material_id"],
                quantity_g=line["quantity_g"],
            )
    db.commit()
    return product


def delete_product(db: Session, *, organization_id: UUID, product_id: UUID) -> None:
    product = get_product(db, organization_id=organization_id, product_id=product_id)
    ProductRepository(db).soft_delete(product)
    db.commit()


def _manual_price_breakdown(manual_price: float) -> CostBreakdown:
    """A "simple" product (name + fixed price, no BOM/machine/cost profile)

    skips the pricing formula entirely — the manual price IS the sale price.
    """
    return CostBreakdown(
        material_cost=0.0,
        waste_cost=0.0,
        energy_cost=0.0,
        machine_cost=0.0,
        labor_cost=0.0,
        packaging_cost=0.0,
        fees=0.0,
        production_cost=manual_price,
        tax_amount=0.0,
        suggested_price=manual_price,
    )


def _profile_values(profile) -> CostProfileValues:
    return CostProfileValues(
        energy_cost_per_kwh=profile.energy_cost_per_kwh,
        labor_cost_per_hour=profile.labor_cost_per_hour,
        packaging_cost_flat=profile.packaging_cost_flat,
        waste_percentage=profile.waste_percentage,
        fees_percentage=profile.fees_percentage,
        profit_margin_percentage=profile.profit_margin_percentage,
        tax_percentage=profile.tax_percentage or 0.0,
    )


def compute_product_cost(
    db: Session,
    *,
    organization_id: UUID,
    product_id: UUID,
    cost_profile_id: UUID,
    energy_kwh: float = 0.0,
    labor_hours: float = 0.0,
) -> CostBreakdown:
    """Sums the product's BOM against each material's cost_per_kg to get

    material_cost, then runs it through the same deterministic pricing
    engine the standalone calculator uses (domain/calculator/engine.py) —
    one formula, one source of truth, whether the material cost was typed
    by hand or derived from a product's recipe. A product with a
    manual_price (a "simple" product with no BOM) skips this entirely.
    """
    product = get_product(db, organization_id=organization_id, product_id=product_id)
    if product.manual_price is not None:
        return _manual_price_breakdown(product.manual_price)

    profile = get_cost_profile(db, organization_id=organization_id, cost_profile_id=cost_profile_id)

    material_cost = 0.0
    for line in ProductMaterialRepository(db).list_for_product(organization_id, product.id):
        material = get_material(db, organization_id=organization_id, material_id=line.material_id)
        cost_per_kg = material.cost_per_kg or 0.0
        material_cost += (line.quantity_g / 1000.0) * cost_per_kg

    if product.machine_id is not None:
        machine = get_machine(db, organization_id=organization_id, machine_id=product.machine_id)
        machine_cost_per_hour = machine.cost_per_hour or 0.0
    else:
        machine_cost_per_hour = 0.0

    print_time_hours = product.print_time_hours or 0.0

    return calculate_quote(
        QuoteInputs(
            material_cost=material_cost,
            print_time_hours=print_time_hours,
            machine_cost_per_hour=machine_cost_per_hour,
            energy_kwh=energy_kwh,
            labor_hours=labor_hours,
        ),
        _profile_values(profile),
    )


def list_products_costs(
    db: Session, *, organization_id: UUID, cost_profile_id: UUID
) -> dict[UUID, CostBreakdown]:
    """Same formula as `compute_product_cost`, but for every product in the

    org in one pass — one cost-profile fetch, one materials/machines list
    (not one query per product per BOM line), instead of the frontend
    firing a separate request per product (which used to make the Produtos
    page noticeably slow once there were more than a handful of products).
    """
    profile = get_cost_profile(db, organization_id=organization_id, cost_profile_id=cost_profile_id)
    profile_values = _profile_values(profile)

    products = ProductRepository(db).list_for_org(organization_id)
    materials_by_id = {m.id: m for m in MaterialRepository(db).list_for_org(organization_id)}
    machines_by_id = {m.id: m for m in MachineRepository(db).list_for_org(organization_id)}
    bom_repo = ProductMaterialRepository(db)

    result: dict[UUID, CostBreakdown] = {}
    for product in products:
        if product.manual_price is not None:
            result[product.id] = _manual_price_breakdown(product.manual_price)
            continue

        material_cost = 0.0
        for line in bom_repo.list_for_product(organization_id, product.id):
            material = materials_by_id.get(line.material_id)
            cost_per_kg = (material.cost_per_kg if material else 0.0) or 0.0
            material_cost += (line.quantity_g / 1000.0) * cost_per_kg

        machine = machines_by_id.get(product.machine_id) if product.machine_id else None
        machine_cost_per_hour = (machine.cost_per_hour or 0.0) if machine else 0.0

        result[product.id] = calculate_quote(
            QuoteInputs(
                material_cost=material_cost,
                print_time_hours=product.print_time_hours or 0.0,
                machine_cost_per_hour=machine_cost_per_hour,
                energy_kwh=0.0,
                labor_hours=0.0,
            ),
            profile_values,
        )
    return result
