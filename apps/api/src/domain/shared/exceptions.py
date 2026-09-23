class DomainError(Exception):
    pass


class InvalidCredentialsError(DomainError):
    pass


class EmailAlreadyRegisteredError(DomainError):
    pass


class UserNotFoundError(DomainError):
    pass


class OrganizationNotFoundError(DomainError):
    pass


class NotOrgMemberError(DomainError):
    pass


class InsufficientRoleError(DomainError):
    pass


class RefreshTokenInvalidError(DomainError):
    pass


class CannotRemoveLastOwnerError(DomainError):
    pass


class UserAlreadyMemberError(DomainError):
    pass


class ProjectNotFoundError(DomainError):
    pass


class ProjectVersionNotFoundError(DomainError):
    pass


class FileAssetNotFoundError(DomainError):
    pass


class FileNotUploadedError(DomainError):
    pass


class UnsupportedFileKindError(DomainError):
    pass


class StorageUnavailableError(DomainError):
    pass


class ProviderUnavailableError(DomainError):
    pass


class AllProvidersFailedError(DomainError):
    pass


class AIJobNotFoundError(DomainError):
    pass


class ProviderNotConfiguredError(DomainError):
    """Raised by a real-vendor provider stub (Hunyuan3D, TRELLIS, ...) that

    implements the port but has no working engine behind it yet — pending
    GPU infra and/or license confirmation (see docs/AI-LICENSES.md).
    """

    pass


class InvalidImageInputError(DomainError):
    pass


class GenerationValidationFailedError(DomainError):
    pass


class InvalidCADParametersError(DomainError):
    pass


class CostProfileNotFoundError(DomainError):
    pass


class QuoteNotFoundError(DomainError):
    pass


class InvalidCostInputsError(DomainError):
    pass


class CannotDeleteDefaultCostProfileError(DomainError):
    pass


class MaterialNotFoundError(DomainError):
    pass


class ProductNotFoundError(DomainError):
    pass


class InventoryItemNotFoundError(DomainError):
    pass


class InvalidInventoryMovementError(DomainError):
    pass


class InsufficientStockError(DomainError):
    pass


class CustomerNotFoundError(DomainError):
    pass


class OrderNotFoundError(DomainError):
    pass


class InvalidOrderTransitionError(DomainError):
    pass


class FinancialTransactionNotFoundError(DomainError):
    pass


class InvalidFinancialTransactionTypeError(DomainError):
    pass


class MachineNotFoundError(DomainError):
    pass


class PlanNotFoundError(DomainError):
    pass


class SubscriptionNotFoundError(DomainError):
    pass


class InvalidSubscriptionTransitionError(DomainError):
    pass


class LimitExceededError(DomainError):
    def __init__(self, *, key: str, current_usage: float, limit: float, message: str) -> None:
        super().__init__(message)
        self.key = key
        self.current_usage = current_usage
        self.limit = limit


class InvalidEntitlementError(DomainError):
    pass


class InvalidWebhookSignatureError(DomainError):
    pass


class InvalidWebhookPayloadError(DomainError):
    pass
