from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.inventory.alerts import is_low_stock
from src.domain.inventory.movement import (
    apply_movement,
    validate_movement_type,
    validate_quantity_sign,
)
from src.domain.shared.exceptions import (
    InventoryItemNotFoundError,
    MaterialNotFoundError,
    OrderNotFoundError,
)
from src.infrastructure.db.models import InventoryItem, InventoryMovement, Material
from src.infrastructure.db.repositories import (
    InventoryItemRepository,
    InventoryMovementRepository,
    MaterialRepository,
    OrderRepository,
)


def create_material(
    db: Session,
    *,
    organization_id: UUID,
    name: str,
    type: str,
    color: str | None,
    density_g_cm3: float | None,
    cost_per_kg: float | None,
    supplier: str | None,
) -> Material:
    material = MaterialRepository(db).create(
        organization_id=organization_id,
        name=name,
        type=type,
        color=color,
        density_g_cm3=density_g_cm3,
        cost_per_kg=cost_per_kg,
        supplier=supplier,
    )
    db.commit()
    return material


def list_materials(db: Session, *, organization_id: UUID) -> list[Material]:
    return MaterialRepository(db).list_for_org(organization_id)


def get_material(db: Session, *, organization_id: UUID, material_id: UUID) -> Material:
    material = MaterialRepository(db).get(organization_id, material_id)
    if material is None:
        raise MaterialNotFoundError(str(material_id))
    return material


def create_inventory_item(
    db: Session,
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
    if material_id is not None:
        get_material(db, organization_id=organization_id, material_id=material_id)
    item = InventoryItemRepository(db).create(
        organization_id=organization_id,
        material_id=material_id,
        name=name,
        category=category,
        unit=unit,
        minimum_stock=minimum_stock,
        unit_cost=unit_cost,
        supplier=supplier,
        initial_quantity=initial_quantity,
    )
    db.commit()
    return item


def list_inventory_items(
    db: Session, *, organization_id: UUID, low_stock_only: bool = False
) -> list[InventoryItem]:
    items = InventoryItemRepository(db).list_for_org(organization_id)
    if low_stock_only:
        items = [i for i in items if is_low_stock(i.quantity_on_hand, i.minimum_stock)]
    return items


def get_inventory_item(db: Session, *, organization_id: UUID, item_id: UUID) -> InventoryItem:
    item = InventoryItemRepository(db).get(organization_id, item_id)
    if item is None:
        raise InventoryItemNotFoundError(str(item_id))
    return item


def create_movement(
    db: Session,
    *,
    organization_id: UUID,
    item_id: UUID,
    movement_type: str,
    quantity: float,
    unit_cost: float | None,
    notes: str | None,
    created_by: UUID | None,
    reference_order_id: UUID | None = None,
) -> InventoryMovement:
    item = get_inventory_item(db, organization_id=organization_id, item_id=item_id)

    if reference_order_id is not None and OrderRepository(db).get(
        organization_id, reference_order_id
    ) is None:
        raise OrderNotFoundError(str(reference_order_id))

    validate_movement_type(movement_type)
    validate_quantity_sign(movement_type, quantity)
    new_quantity = apply_movement(item.quantity_on_hand, quantity)

    movement = InventoryMovementRepository(db).create(
        inventory_item_id=item.id,
        organization_id=organization_id,
        type=movement_type,
        quantity=quantity,
        unit_cost=unit_cost,
        notes=notes,
        created_by=created_by,
        reference_order_id=reference_order_id,
    )
    InventoryItemRepository(db).update_quantity(item, new_quantity=new_quantity)
    db.commit()
    return movement


def list_movements(db: Session, *, organization_id: UUID, item_id: UUID) -> list[InventoryMovement]:
    get_inventory_item(db, organization_id=organization_id, item_id=item_id)
    return InventoryMovementRepository(db).list_for_item(item_id)
