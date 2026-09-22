from dataclasses import dataclass

from src.domain.shared.exceptions import InvalidFinancialTransactionTypeError

_VALID_TYPES = {"receita", "custo", "despesa"}


def validate_transaction_type(transaction_type: str) -> None:
    if transaction_type not in _VALID_TYPES:
        raise InvalidFinancialTransactionTypeError(
            f"Tipo de transação inválido: {transaction_type!r}. "
            f"Esperado um de {sorted(_VALID_TYPES)}."
        )


@dataclass(frozen=True)
class TransactionAmount:
    type: str
    amount: float
    is_paid: bool


@dataclass(frozen=True)
class FinancialSummary:
    total_revenue: float
    total_cost: float
    total_expense: float
    profit: float
    pending_receivables: float
    pending_payables: float


def compute_summary(transactions: list[TransactionAmount]) -> FinancialSummary:
    """Lucro = Σreceita − Σcusto − Σdespesa (DATABASE.md, regra explícita de

    `financial_transactions`) — sem lógica condicional escondida: cada tipo
    é somado isoladamente, nunca misturado na mesma conta. `pending_*` soma
    o que ainda não tem `paid_at` — receita não recebida é "a receber",
    custo/despesa não pago é "a pagar" (ambos ficam no mesmo lado do fluxo
    de caixa: dinheiro que ainda vai sair, seja para fornecedor ou despesa).
    """
    total_revenue = total_cost = total_expense = 0.0
    pending_receivables = pending_payables = 0.0

    for transaction in transactions:
        validate_transaction_type(transaction.type)
        if transaction.type == "receita":
            total_revenue += transaction.amount
            if not transaction.is_paid:
                pending_receivables += transaction.amount
        elif transaction.type == "custo":
            total_cost += transaction.amount
            if not transaction.is_paid:
                pending_payables += transaction.amount
        else:
            total_expense += transaction.amount
            if not transaction.is_paid:
                pending_payables += transaction.amount

    profit = total_revenue - total_cost - total_expense
    return FinancialSummary(
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_expense=total_expense,
        profit=profit,
        pending_receivables=pending_receivables,
        pending_payables=pending_payables,
    )
