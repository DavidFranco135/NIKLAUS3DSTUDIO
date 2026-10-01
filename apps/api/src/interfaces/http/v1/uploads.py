from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.infrastructure.images.imgbb import upload_image
from src.interfaces.http.dependencies import require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import ImageUploadResponse

router = APIRouter(prefix="/organizations/{organization_id}/uploads", tags=["uploads"])


@router.post(
    "/image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
async def upload_image_route(
    organization_id: UUID, file: UploadFile = File(...)
) -> ImageUploadResponse:
    try:
        content = await file.read()
        url = upload_image(content, file.content_type or "")
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ImageUploadResponse(url=url)
