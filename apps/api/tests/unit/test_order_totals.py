from src.domain.orders.totals import OrderItemTotal, compute_total_amount


def test_empty_items_totals_zero():
    assert compute_total_amount([]) == 0.0


def test_sums_quantity_times_unit_price():
    items = [
        OrderItemTotal(quantity=2, unit_price=10.0),
        OrderItemTotal(quantity=1, unit_price=5.5),
    ]
    assert compute_total_amount(items) == 25.5


def test_treats_missing_unit_price_as_zero():
    items = [OrderItemTotal(quantity=3, unit_price=None)]
    assert compute_total_amount(items) == 0.0
