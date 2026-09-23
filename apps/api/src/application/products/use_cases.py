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
from src.infrastructure.db.repositories import (
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
    materials: list[dict],
) -> Product:
    """`materials` is a list of {"material_id": UUID, "quantity_g": float} —

    the product's bill of materials (BOM): how much of each raw material one
    unit consumes. Validated against the org's own material/machine catalog
    so a product can never reference another org's rows or a typo'd id.
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
    )
    material_repo = ProductMaterialRepository(db)
    for line in materials:
        material_repo.create(
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


def list_product_materials(db: Session, *, product_id: UUID) -> list[dict]:
    lines = ProductMaterialRepository(db).list_for_product(product_id)
    return [{"material_id": line.material_id, "quantity_g": line.quantity_g} for line in lines]


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
    by hand or derived from a product's recipe.
    """
    product = get_product(db, organization_id=organization_id, product_id=product_id)
    profile = get_cost_profile(db, organization_id=organization_id, cost_profile_id=cost_profile_id)

    material_cost = 0.0
    for line in ProductMaterialRepository(db).list_for_product(product.id):
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
        CostProfileValues(
            energy_cost_per_kwh=profile.energy_cost_per_kwh,
            labor_cost_per_hour=profile.labor_cost_per_hour,
            packaging_cost_flat=profile.packaging_cost_flat,
            waste_percentage=profile.waste_percentage,
            fees_percentage=profile.fees_percentage,
            profit_margin_percentage=profile.profit_margin_percentage,
            tax_percentage=profile.tax_percentage or 0.0,
        ),
    )
