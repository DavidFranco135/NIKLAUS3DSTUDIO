from src.domain.billing.enforcement import check_feature_flag, check_numeric_limit
from src.domain.billing.entitlements import Entitlement


def test_usage_below_limit_is_allowed():
    entitlement = Entitlement(key="max_projects", limit_type="numeric", numeric_value=10)
    result = check_numeric_limit(current_usage=5, entitlement=entitlement)
    assert result.allowed is True
    assert result.limit == 10


def test_usage_at_limit_is_blocked():
    entitlement = Entitlement(key="max_projects", limit_type="numeric", numeric_value=10)
    result = check_numeric_limit(current_usage=10, entitlement=entitlement)
    assert result.allowed is False
    assert result.reason is not None


def test_usage_over_limit_is_blocked():
    entitlement = Entitlement(key="max_projects", limit_type="numeric", numeric_value=10)
    result = check_numeric_limit(current_usage=11, entitlement=entitlement)
    assert result.allowed is False


def test_unlimited_entitlement_always_allows():
    entitlement = Entitlement(key="max_projects", limit_type="unlimited")
    result = check_numeric_limit(current_usage=99999, entitlement=entitlement)
    assert result.allowed is True
    assert result.limit is None


def test_enabled_feature_flag_is_allowed():
    entitlement = Entitlement(key="feature.x", limit_type="boolean", bool_value=True)
    result = check_feature_flag(entitlement)
    assert result.allowed is True


def test_disabled_feature_flag_is_blocked():
    entitlement = Entitlement(key="feature.x", limit_type="boolean", bool_value=False)
    result = check_feature_flag(entitlement)
    assert result.allowed is False
    assert result.reason is not None
