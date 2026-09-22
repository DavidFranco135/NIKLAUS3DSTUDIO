from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.application.dashboard import use_cases as dashboard_use_cases
from src.domain.auth.roles import Role
from src.interfaces.http.dependencies import get_db, require_org_role
from src.interfaces.http.v1.schemas import DashboardResponse, FinancialSummaryResponse

router = APIRouter(prefix="/organizations/{organization_id}/dashboard", tags=["dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_dashboard(
    organization_id: UUID,
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> DashboardResponse:
    summary = dashboard_use_cases.get_dashboard_summary(
        db, organization_id=organization_id, start_date=start_date, end_date=end_date
    )
    return DashboardResponse(
        orders_by_status=summary.orders_by_status,
        low_stock_items_count=summary.low_stock_items_count,
        customers_count=summary.customers_count,
        projects_count=summary.projects_count,
        financial=FinancialSummaryResponse(
            total_revenue=summary.financial.total_revenue,
            total_cost=summary.financial.total_cost,
            total_expense=summary.financial.total_expense,
            profit=summary.financial.profit,
            pending_receivables=summary.financial.pending_receivables,
            pending_payables=summary.financial.pending_payables,
        ),
    )
