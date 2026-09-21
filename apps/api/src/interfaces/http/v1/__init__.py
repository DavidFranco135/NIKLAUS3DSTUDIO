from fastapi import APIRouter

from src.interfaces.http.v1.ai import router as ai_router
from src.interfaces.http.v1.auth import router as auth_router
from src.interfaces.http.v1.health import router as health_router
from src.interfaces.http.v1.organizations import router as organizations_router
from src.interfaces.http.v1.projects import router as projects_router
from src.interfaces.http.v1.users import router as users_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(organizations_router)
router.include_router(projects_router)
router.include_router(ai_router)
