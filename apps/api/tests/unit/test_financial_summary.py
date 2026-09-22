import pytest

from src.domain.financial.summary import TransactionAmount, compute_summary
from src.domain.shared.exceptions import InvalidFinancialTransactionTypeError


def test_empty_transactions_gives_zero_summary():
    summary = compute_summary([])
    assert summary.total_revenue == 0.0
    assert summary.profit == 0.0
    assert summary.pending_receivables == 0.0
    assert summary.pending_payables == 0.0


def test_profit_is_revenue_minus_cost_minus_expense():
    transactions = [
        TransactionAmount(type="receita", amount=1000.0, is_paid=True),
        TransactionAmount(type="custo", amount=300.0, is_paid=True),
        TransactionAmount(type="despesa", amount=100.0, is_paid=True),
    ]
    summary = compute_summary(transactions)
    assert summary.total_revenue == 1000.0
    assert summary.total_cost == 300.0
    assert summary.total_expense == 100.0
    assert summary.profit == 600.0


def test_unpaid_revenue_counts_as_pending_receivable():
    transactions = [
        TransactionAmount(type="receita", amount=500.0, is_paid=False),
        TransactionAmount(type="receita", amount=200.0, is_paid=True),
    ]
    summary = compute_summary(transactions)
    assert summary.total_revenue == 700.0
    assert summary.pending_receivables == 500.0
    assert summary.pending_payables == 0.0


def test_unpaid_cost_and_expense_count_as_pending_payable():
    transactions = [
        TransactionAmount(type="custo", amount=150.0, is_paid=False),
        TransactionAmount(type="despesa", amount=80.0, is_paid=False),
    ]
    summary = compute_summary(transactions)
    assert summary.pending_payables == 230.0
    assert summary.pending_receivables == 0.0


def test_types_are_never_mixed_in_the_same_total():
    transactions = [
        TransactionAmount(type="receita", amount=100.0, is_paid=True),
        TransactionAmount(type="custo", amount=100.0, is_paid=True),
        TransactionAmount(type="despesa", amount=100.0, is_paid=True),
    ]
    summary = compute_summary(transactions)
    assert summary.total_revenue == 100.0
    assert summary.total_cost == 100.0
    assert summary.total_expense == 100.0


def test_rejects_unknown_transaction_type():
    with pytest.raises(InvalidFinancialTransactionTypeError):
        compute_summary([TransactionAmount(type="bonus", amount=10.0, is_paid=True)])
