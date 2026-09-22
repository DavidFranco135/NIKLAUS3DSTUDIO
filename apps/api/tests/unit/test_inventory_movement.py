import pytest

from src.domain.inventory.alerts import is_low_stock
from src.domain.inventory.movement import (
    apply_movement,
    validate_movement_type,
    validate_quantity_sign,
)
from src.domain.shared.exceptions import InsufficientStockError, InvalidInventoryMovementError


def test_validate_movement_type_rejects_unknown_type():
    with pytest.raises(InvalidInventoryMovementError):
        validate_movement_type("devolucao")


@pytest.mark.parametrize("movement_type", ["entrada", "saida", "ajuste", "consumo", "perda"])
def test_validate_movement_type_accepts_known_types(movement_type):
    validate_movement_type(movement_type)


def test_entrada_requires_positive_quantity():
    validate_quantity_sign("entrada", 10)
    with pytest.raises(InvalidInventoryMovementError):
        validate_quantity_sign("entrada", -10)


@pytest.mark.parametrize("movement_type", ["saida", "consumo", "perda"])
def test_outgoing_types_require_negative_quantity(movement_type):
    validate_quantity_sign(movement_type, -5)
    with pytest.raises(InvalidInventoryMovementError):
        validate_quantity_sign(movement_type, 5)


def test_ajuste_accepts_either_sign():
    validate_quantity_sign("ajuste", 5)
    validate_quantity_sign("ajuste", -5)


def test_zero_quantity_is_always_rejected():
    with pytest.raises(InvalidInventoryMovementError):
        validate_quantity_sign("ajuste", 0)


def test_apply_movement_adds_signed_quantity():
    assert apply_movement(10, 5) == 15
    assert apply_movement(10, -5) == 5


def test_apply_movement_rejects_going_negative():
    with pytest.raises(InsufficientStockError):
        apply_movement(10, -15)


def test_apply_movement_allows_reaching_exactly_zero():
    assert apply_movement(10, -10) == 0


def test_is_low_stock():
    assert is_low_stock(5, 10) is True
    assert is_low_stock(10, 10) is True
    assert is_low_stock(15, 10) is False
