"""Test the PAYBACK Deutschland update coordinator."""

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.payback.api import PaybackAccount, PaybackCoupon, PaybackPoints
from custom_components.payback.const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from custom_components.payback.coordinator import PaybackDataUpdateCoordinator

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_coordinator_update_data_success(hass: HomeAssistant) -> None:
    """Test successful data update in coordinator."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "test_user@example.com", CONF_PASSWORD: "password"},
        unique_id="test_user@example.com",
    )
    entry.add_to_hass(hass)

    coordinator = PaybackDataUpdateCoordinator(hass, entry)

    mock_account = PaybackAccount(
        cardNumber="123456789",
        customerName="Max Mustermann",
        points=PaybackPoints(totalPoints=1500, availablePoints=1200, pendingPoints=300),
        coupons=[
            PaybackCoupon(couponId="c1", title="10x Points", activated=False),
            PaybackCoupon(couponId="c2", title="5x REWE", activated=True),
        ],
    )

    with (
        patch.object(coordinator.client, "login", return_value=True),
        patch.object(coordinator.client, "get_account", return_value=mock_account),
    ):
        data = await coordinator._async_update_data()

        assert data["card_number"] == "123456789"
        assert data["customer_name"] == "Max Mustermann"
        assert data["points"]["total"] == 1500
        assert data["points"]["available"] == 1200
        assert data["points"]["pending"] == 300
        assert len(data["coupons"]) == 2


async def test_coordinator_auto_activate_coupons(hass: HomeAssistant) -> None:
    """Test auto-activation of coupons during update when enabled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "test_user@example.com", CONF_PASSWORD: "password"},
        options={"auto_activate_coupons": True},
        unique_id="test_user@example.com",
    )
    entry.add_to_hass(hass)

    coordinator = PaybackDataUpdateCoordinator(hass, entry)

    mock_account = PaybackAccount(
        cardNumber="123456789",
        customerName="Max Mustermann",
        points=PaybackPoints(totalPoints=100),
        coupons=[PaybackCoupon(couponId="c1", title="10x Points", activated=False)],
    )

    with (
        patch.object(coordinator.client, "login", return_value=True),
        patch.object(coordinator.client, "get_account", return_value=mock_account),
        patch.object(
            coordinator.client, "activate_coupon", return_value=True
        ) as mock_activate,
    ):
        await coordinator._async_update_data()
        mock_activate.assert_called_once_with("c1")


async def test_coordinator_backoff_and_cache_fallback(hass: HomeAssistant) -> None:
    """Test rate-limit backoff and cache serving on API error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "test_user@example.com", CONF_PASSWORD: "password"},
        unique_id="test_user@example.com",
    )
    entry.add_to_hass(hass)

    coordinator = PaybackDataUpdateCoordinator(hass, entry)
    cached_data = {
        "card_number": "123456789",
        "customer_name": "Cached User",
        "points": {"total": 500, "available": 500, "pending": 0},
        "coupons": [],
    }

    with (
        patch.object(coordinator.store, "async_load", return_value=cached_data),
        patch.object(
            coordinator.client, "login", side_effect=Exception("Rate limit 429")
        ),
    ):
        data = await coordinator._async_update_data()
        assert data["customer_name"] == "Cached User"
        assert coordinator._consecutive_failures == 1
        assert coordinator._backoff_until is not None
