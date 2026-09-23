from fastapi import APIRouter

from src.interfaces.http.v1.ai import router as ai_router
from src.interfaces.http.v1.auth import router as auth_router
from src.interfaces.http.v1.billing import global_router as billing_global_router
from src.interfaces.http.v1.billing import router as billing_router
from src.interfaces.http.v1.calculator import router as calculator_router
from src.interfaces.http.v1.customers import router as customers_router
from src.interfaces.http.v1.dashboard import router as dashboard_router
from src.interfaces.http.v1.finance import router as finance_router
from src.interfaces.http.v1.health import router as health_router
from src.interfaces.http.v1.inventory import router as inventory_router
from src.interfaces.http.v1.machines import router as machines_router
from src.interfaces.http.v1.materials import router as materials_router
from src.interfaces.http.v1.orders import router as orders_router
from src.interfaces.http.v1.organizations import router as organizations_router
from src.interfaces.http.v1.products import router as products_router
from src.interfaces.http.v1.projects import router as projects_router
from src.interfaces.http.v1.users import router as users_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(organizations_router)
router.include_router(customers_router)
router.include_router(projects_router)
router.include_router(ai_router)
router.include_router(calculator_router)
router.include_router(materials_router)
router.include_router(products_router)
router.include_router(inventory_router)
router.include_router(orders_router)
router.include_router(finance_router)
router.include_router(dashboard_router)
router.include_router(machines_router)
router.include_router(billing_router)
router.include_router(billing_global_router)
