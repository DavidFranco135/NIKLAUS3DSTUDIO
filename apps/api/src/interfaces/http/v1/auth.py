from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.application.auth import use_cases
from src.config import get_settings
from src.domain.auth.dto import TokenPair
from src.domain.shared.exceptions import DomainError
from src.interfaces.http.dependencies import get_db
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

settings = get_settings()


def _set_refresh_cookie(response: Response, tokens: TokenPair) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.api_env != "development",
        samesite="none",
        path=REFRESH_COOKIE_PATH,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, response: Response, db: Session = Depends(get_db)
) -> AuthResponse:
    try:
        user, _organization, tokens = use_cases.register(
            db,
            organization_name=payload.organization_name,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc

    _set_refresh_cookie(response, tokens)
    return AuthResponse(access_token=tokens.access_token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        user, tokens = use_cases.login(db, email=payload.email, password=payload.password)
    except DomainError as exc:
        raise as_http_exception(exc) from exc

    _set_refresh_cookie(response, tokens)
    return AuthResponse(access_token=tokens.access_token, user=UserResponse.model_validate(user))


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> AuthResponse:
    if refresh_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")

    try:
        user, tokens = use_cases.refresh_session(db, refresh_token_plaintext=refresh_token)
    except DomainError as exc:
        raise as_http_exception(exc) from exc

    _set_refresh_cookie(response, tokens)
    return AuthResponse(access_token=tokens.access_token, user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> None:
    if refresh_token is not None:
        use_cases.logout(db, refresh_token_plaintext=refresh_token)
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
