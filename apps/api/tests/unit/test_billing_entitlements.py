import pytest

from src.domain.billing.entitlements import Entitlement, get_numeric_limit, is_feature_enabled
from src.domain.shared.exceptions import InvalidEntitlementError


def test_boolean_entitlement_enabled():
    entitlement = Entitlement(key="feature.x", limit_type="boolean", bool_value=True)
    assert is_feature_enabled(entitlement) is True


def test_boolean_entitlement_disabled():
    entitlement = Entitlement(key="feature.x", limit_type="boolean", bool_value=False)
    assert is_feature_enabled(entitlement) is False


def test_numeric_entitlement_is_not_a_feature_flag():
    entitlement = Entitlement(key="max_projects", limit_type="numeric", numeric_value=10)
    assert is_feature_enabled(entitlement) is False


def test_numeric_limit_returns_value():
    entitlement = Entitlement(key="max_projects", limit_type="numeric", numeric_value=10)
    assert get_numeric_limit(entitlement) == 10


def test_unlimited_limit_returns_none():
    entitlement = Entitlement(key="max_projects", limit_type="unlimited")
    assert get_numeric_limit(entitlement) is None


def test_boolean_entitlement_has_no_numeric_limit():
    entitlement = Entitlement(key="feature.x", limit_type="boolean", bool_value=True)
    assert get_numeric_limit(entitlement) is None


def test_rejects_invalid_limit_type():
    with pytest.raises(InvalidEntitlementError):
        Entitlement(key="x", limit_type="bogus")
