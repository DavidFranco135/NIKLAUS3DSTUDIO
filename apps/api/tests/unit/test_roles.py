import pytest

from src.domain.auth.roles import Role, role_at_least


@pytest.mark.parametrize(
    "role,minimum,expected",
    [
        (Role.OWNER, Role.VIEWER, True),
        (Role.OWNER, Role.OWNER, True),
        (Role.VIEWER, Role.OWNER, False),
        (Role.MANAGER, Role.ADMIN, False),
        (Role.ADMIN, Role.MANAGER, True),
        (Role.OPERATOR, Role.OPERATOR, True),
    ],
)
def test_role_at_least(role: Role, minimum: Role, expected: bool):
    assert role_at_least(role, minimum) is expected
