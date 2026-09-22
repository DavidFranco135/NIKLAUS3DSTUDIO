from src.domain.shared.exceptions import InsufficientStockError, InvalidInventoryMovementError

# "quantity NUMERIC NOT NULL -- positivo ou negativo conforme tipo" (DATABASE.md):
# the stored quantity's sign must already match what the type means. `ajuste`
# (a correction) is the one type allowed to go either way — it's meant to fix
# a count that drifted, in whichever direction.
_REQUIRED_SIGN_BY_TYPE = {
    "entrada": 1,
    "saida": -1,
    "consumo": -1,
    "perda": -1,
    "ajuste": 0,
}


def validate_movement_type(movement_type: str) -> None:
    if movement_type not in _REQUIRED_SIGN_BY_TYPE:
        raise InvalidInventoryMovementError(
            f"Tipo de movimento inválido: {movement_type!r}. "
            f"Esperado um de {sorted(_REQUIRED_SIGN_BY_TYPE)}."
        )


def validate_quantity_sign(movement_type: str, quantity: float) -> None:
    if quantity == 0:
        raise InvalidInventoryMovementError("quantity não pode ser zero.")
    required_sign = _REQUIRED_SIGN_BY_TYPE[movement_type]
    if required_sign == 1 and quantity < 0:
        raise InvalidInventoryMovementError(f"Movimento '{movement_type}' exige quantity > 0.")
    if required_sign == -1 and quantity > 0:
        raise InvalidInventoryMovementError(f"Movimento '{movement_type}' exige quantity < 0.")


def apply_movement(quantity_on_hand: float, quantity: float) -> float:
    """Estoque nunca fica negativo — inclusive para `ajuste`: se a correção

    resultaria num total negativo, é sinal de um número errado sendo
    aplicado, não de estoque "devendo" ficar negativo (rastrear
    encomendas em falta é responsabilidade de outro módulo, não deste
    contador físico).
    """
    new_quantity = quantity_on_hand + quantity
    if new_quantity < 0:
        raise InsufficientStockError(
            f"Estoque insuficiente: {quantity_on_hand} disponível, "
            f"movimento de {quantity} resultaria em {new_quantity}."
        )
    return new_quantity
