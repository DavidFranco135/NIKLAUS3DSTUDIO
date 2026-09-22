from src.domain.dashboard.aggregation import count_by_status


def test_empty_list_gives_empty_counts():
    assert count_by_status([]) == {}


def test_counts_each_status_independently():
    statuses = ["quote", "quote", "paid", "completed", "paid", "paid"]
    assert count_by_status(statuses) == {"quote": 2, "paid": 3, "completed": 1}
