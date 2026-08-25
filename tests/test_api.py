"""Test API client for PAYBACK Deutschland."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.payback.api import (
    PaybackAPIClient,
    PaybackCoupon,
    PaybackPoints,
)


def test_payback_models():
    """Test data model instantiation and field aliases."""
    pts = PaybackPoints(totalPoints=100, availablePoints=80, pendingPoints=20)
    assert pts.total_points == 100
    assert pts.available_points == 80
    assert pts.pending_points == 20

    c = PaybackCoupon(couponId="123", title="Test", partnerName="DM", activated=True)
    assert c.coupon_id == "123"
    assert c.partner_name == "DM"
    assert c.activated is True


def test_api_client_login():
    """Test API client login method."""
    client = PaybackAPIClient("user@test.com", "pass")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"token": "xyz123"}'
    mock_resp.json.return_value = {"token": "xyz123"}

    with patch.object(client.session, "request", return_value=mock_resp):
        assert client.login() is True
        assert client._auth_token == "xyz123"


def test_api_activate_coupon_failure():
    """Test coupon activation error handling."""
    client = PaybackAPIClient("user@test.com", "pass")
    with patch.object(client.session, "request", side_effect=RuntimeError("API Error")):
        with pytest.raises(RuntimeError):
            client.activate_coupon("invalid_id")
