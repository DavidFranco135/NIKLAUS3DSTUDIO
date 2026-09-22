from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.shared.exceptions import MachineNotFoundError
from src.infrastructure.db.models import Machine
from src.infrastructure.db.repositories import MachineRepository


def create_machine(
    db: Session,
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
    machine = MachineRepository(db).create(
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
    db.commit()
    return machine


def list_machines(db: Session, *, organization_id: UUID) -> list[Machine]:
    return MachineRepository(db).list_for_org(organization_id)


def get_machine(db: Session, *, organization_id: UUID, machine_id: UUID) -> Machine:
    machine = MachineRepository(db).get(organization_id, machine_id)
    if machine is None:
        raise MachineNotFoundError(str(machine_id))
    return machine


def update_machine(
    db: Session,
    *,
    organization_id: UUID,
    machine_id: UUID,
    name: str | None,
    brand: str | None,
    model: str | None,
    cost_per_hour: float | None,
    status: str | None,
) -> Machine:
    machine = get_machine(db, organization_id=organization_id, machine_id=machine_id)
    if name is not None:
        machine.name = name
    if brand is not None:
        machine.brand = brand
    if model is not None:
        machine.model = model
    if cost_per_hour is not None:
        machine.cost_per_hour = cost_per_hour
    if status is not None:
        machine.status = status
    db.commit()
    return machine
