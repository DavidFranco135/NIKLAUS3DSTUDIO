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
