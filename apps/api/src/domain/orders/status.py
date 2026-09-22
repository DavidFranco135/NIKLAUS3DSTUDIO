from src.domain.shared.exceptions import InvalidOrderTransitionError

# Sequência linear do funil (DATABASE.md) — cada estágio implica que os
# anteriores já aconteceram. `cancelled` é um terminal lateral, alcançável de
# qualquer estágio não-terminal, nunca a partir de `completed` (já entregue,
# não há o que cancelar) nem de `cancelled` (já é terminal).
_SEQUENCE = [
    "quote",
    "order",
    "paid",
    "production",
    "printing",
    "finishing",
    "packaging",
    "delivered",
    "completed",
]
_TERMINAL = "cancelled"


def validate_transition(current: str, new: str) -> None:
    """Só permite avançar no funil (não necessariamente um passo por vez —

    pular um estágio que não se aplica a um pedido específico é permitido),
    nunca voltar, e `cancelled` só é alcançável enquanto o pedido não tiver
    sido concluído nem já cancelado.
    """
    if current not in _SEQUENCE:
        raise InvalidOrderTransitionError(f"Status atual desconhecido: {current!r}.")

    if new == _TERMINAL:
        if current in (_TERMINAL, "completed"):
            raise InvalidOrderTransitionError(
                f"Não é possível cancelar um pedido em '{current}'."
            )
        return

    if new not in _SEQUENCE:
        raise InvalidOrderTransitionError(f"Status inválido: {new!r}.")

    if current == _TERMINAL:
        raise InvalidOrderTransitionError("Pedido cancelado não pode mudar de status.")

    if _SEQUENCE.index(new) <= _SEQUENCE.index(current):
        raise InvalidOrderTransitionError(
            f"Não é possível ir de '{current}' para '{new}' — só é permitido avançar."
        )
