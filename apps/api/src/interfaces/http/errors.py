from fastapi import HTTPException, status

from src.domain.shared.exceptions import (
    AIJobNotFoundError,
    CannotRemoveLastOwnerError,
    CostProfileNotFoundError,
    CustomerNotFoundError,
    EmailAlreadyRegisteredError,
    FileAssetNotFoundError,
    FileNotUploadedError,
    FinancialTransactionNotFoundError,
    InsufficientStockError,
    InvalidCostInputsError,
    InvalidCredentialsError,
    InvalidFinancialTransactionTypeError,
    InvalidImageInputError,
    InvalidInventoryMovementError,
    InvalidOrderTransitionError,
    InvalidSubscriptionTransitionError,
    InvalidWebhookPayloadError,
    InvalidWebhookSignatureError,
    InventoryItemNotFoundError,
    LimitExceededError,
    MachineNotFoundError,
    MaterialNotFoundError,
    OrderNotFoundError,
    OrganizationNotFoundError,
    PlanNotFoundError,
    ProductNotFoundError,
    ProjectNotFoundError,
    ProjectVersionNotFoundError,
    ProviderNotConfiguredError,
    QuoteNotFoundError,
    RefreshTokenInvalidError,
    StorageUnavailableError,
    SubscriptionNotFoundError,
    UnsupportedFileKindError,
    UserAlreadyMemberError,
    UserNotFoundError,
)

_STATUS_BY_ERROR = {
    EmailAlreadyRegisteredError: status.HTTP_409_CONFLICT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    RefreshTokenInvalidError: status.HTTP_401_UNAUTHORIZED,
    OrganizationNotFoundError: status.HTTP_404_NOT_FOUND,
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    UserAlreadyMemberError: status.HTTP_409_CONFLICT,
    CannotRemoveLastOwnerError: status.HTTP_409_CONFLICT,
    ProjectNotFoundError: status.HTTP_404_NOT_FOUND,
    ProjectVersionNotFoundError: status.HTTP_404_NOT_FOUND,
    FileAssetNotFoundError: status.HTTP_404_NOT_FOUND,
    FileNotUploadedError: status.HTTP_409_CONFLICT,
    UnsupportedFileKindError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidImageInputError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    StorageUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    AIJobNotFoundError: status.HTTP_404_NOT_FOUND,
    ProviderNotConfiguredError: status.HTTP_501_NOT_IMPLEMENTED,
    CostProfileNotFoundError: status.HTTP_404_NOT_FOUND,
    QuoteNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidCostInputsError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    MaterialNotFoundError: status.HTTP_404_NOT_FOUND,
    ProductNotFoundError: status.HTTP_404_NOT_FOUND,
    InventoryItemNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidInventoryMovementError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InsufficientStockError: status.HTTP_409_CONFLICT,
    CustomerNotFoundError: status.HTTP_404_NOT_FOUND,
    OrderNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidOrderTransitionError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    FinancialTransactionNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidFinancialTransactionTypeError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    MachineNotFoundError: status.HTTP_404_NOT_FOUND,
    PlanNotFoundError: status.HTTP_404_NOT_FOUND,
    SubscriptionNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidSubscriptionTransitionError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    LimitExceededError: status.HTTP_402_PAYMENT_REQUIRED,
    InvalidWebhookSignatureError: status.HTTP_400_BAD_REQUEST,
    InvalidWebhookPayloadError: status.HTTP_400_BAD_REQUEST,
}


def as_http_exception(exc: Exception) -> HTTPException:
    status_code = _STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, LimitExceededError):
        # Corpo estruturado, não só uma mensagem — o frontend precisa saber
        # qual chave/quanto/limite para renderizar "upgrade seu plano" sem
        # ter que fazer parsing de texto livre.
        return HTTPException(
            status_code=status_code,
            detail={
                "message": str(exc),
                "limit_key": exc.key,
                "current_usage": exc.current_usage,
                "limit": exc.limit,
            },
        )
    return HTTPException(status_code=status_code, detail=str(exc) or type(exc).__name__)
