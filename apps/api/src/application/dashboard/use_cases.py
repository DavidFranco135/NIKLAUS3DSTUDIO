from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from src.application.financial.use_cases import get_financial_summary
from src.application.inventory.use_cases import list_inventory_items
from src.domain.dashboard.aggregation import count_by_status
from src.domain.financial.summary import FinancialSummary
from src.infrastructure.db.repositories import (
    CustomerRepository,
    OrderRepository,
    ProjectRepository,
)


@dataclass(frozen=True)
class DashboardSummary:
    orders_by_status: dict[str, int]
    low_stock_items_count: int
    customers_count: int
    projects_count: int
    financial: FinancialSummary


def get_dashboard_summary(
    db: Session,
    *,
    organization_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> DashboardSummary:
    orders = OrderRepository(db).list_for_org(organization_id)
    low_stock_items = list_inventory_items(
        db, organization_id=organization_id, low_stock_only=True
    )
    customers = CustomerRepository(db).list_for_org(organization_id)
    projects = ProjectRepository(db).list_for_org(organization_id)
    financial = get_financial_summary(
        db, organization_id=organization_id, start_date=start_date, end_date=end_date
    )

    return DashboardSummary(
        orders_by_status=count_by_status([o.status for o in orders]),
        low_stock_items_count=len(low_stock_items),
        customers_count=len(customers),
        projects_count=len(projects),
        financial=financial,
    )
