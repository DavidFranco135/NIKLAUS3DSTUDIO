"""Backend-agnostic repository facade.

Re-exports either the SQL (`infrastructure.db.repositories`) or Firestore
(`infrastructure.firestore.repositories`) classes depending on
`settings.db_backend` (see config.py) - this is the Phase 5 cutover switch
from the Firebase migration plan. `application/*/use_cases.py` (and a
couple of `interfaces/` files) import repository classes from here instead
of a specific backend module, so flipping the switch doesn't require
touching any of them.

AI job repositories are deliberately excluded - `application/ai/*` still
imports `AIJobRepository`/`AIJobAttemptRepository` directly from
`infrastructure.db.repositories` regardless of this flag, since AI
generation has no Firestore-backed path yet (see the plan's guiding
decision #5 and Phase 6).
"""
from src.config import get_settings

_settings = get_settings()

if _settings.db_backend == "firestore":
    from src.infrastructure.firestore.repositories import (
        BillingEventRepository,
        CostProfileRepository,
        CustomerRepository,
        FileAssetRepository,
        FinancialTransactionRepository,
        InventoryItemRepository,
        InventoryMovementRepository,
        MachineRepository,
        MaterialRepository,
        OrderItemRepository,
        OrderRepository,
        OrganizationRepository,
        OrgMemberRepository,
        PlanEntitlementRepository,
        PlanRepository,
        ProductMaterialRepository,
        ProductRepository,
        ProjectRepository,
        ProjectVersionRepository,
        QuoteRepository,
        RefreshTokenRepository,
        SubscriptionRepository,
        UserRepository,
    )
else:
    from src.infrastructure.db.repositories import (
        BillingEventRepository,
        CostProfileRepository,
        CustomerRepository,
        FileAssetRepository,
        FinancialTransactionRepository,
        InventoryItemRepository,
        InventoryMovementRepository,
        MachineRepository,
        MaterialRepository,
        OrderItemRepository,
        OrderRepository,
        OrganizationRepository,
        OrgMemberRepository,
        PlanEntitlementRepository,
        PlanRepository,
        ProductMaterialRepository,
        ProductRepository,
        ProjectRepository,
        ProjectVersionRepository,
        QuoteRepository,
        RefreshTokenRepository,
        SubscriptionRepository,
        UserRepository,
    )

__all__ = [
    "BillingEventRepository",
    "CostProfileRepository",
    "CustomerRepository",
    "FileAssetRepository",
    "FinancialTransactionRepository",
    "InventoryItemRepository",
    "InventoryMovementRepository",
    "MachineRepository",
    "MaterialRepository",
    "OrderItemRepository",
    "OrderRepository",
    "OrganizationRepository",
    "OrgMemberRepository",
    "PlanEntitlementRepository",
    "PlanRepository",
    "ProductMaterialRepository",
    "ProductRepository",
    "ProjectRepository",
    "ProjectVersionRepository",
    "QuoteRepository",
    "RefreshTokenRepository",
    "SubscriptionRepository",
    "UserRepository",
]
