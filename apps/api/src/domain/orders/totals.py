from dataclasses import dataclass


@dataclass(frozen=True)
class OrderItemTotal:
    quantity: int
    unit_price: float | None


def compute_total_amount(items: list[OrderItemTotal]) -> float:
    return sum((item.unit_price or 0.0) * item.quantity for item in items)
