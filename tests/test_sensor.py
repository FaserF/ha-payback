"""Test sensor platform for PAYBACK Deutschland integration."""

from unittest.mock import patch
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.payback.api import PaybackAccount, PaybackCoupon, PaybackPoints
from custom_components.payback.const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_sensors_creation_and_values(hass: HomeAssistant) -> None:
    """Test sensor entity values and attributes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "test_user@example.com", CONF_PASSWORD: "password"},
        unique_id="test_user@example.com",
    )
    entry.add_to_hass(hass)

    mock_account = PaybackAccount(
        cardNumber="987654321",
        customerName="Erika Mustermann",
        points=PaybackPoints(totalPoints=2500, availablePoints=2000, pendingPoints=500),
        coupons=[
            PaybackCoupon(couponId="c1", title="10x DM", activated=True),
            PaybackCoupon(couponId="c2", title="5x Aral", activated=False),
        ],
    )

    with patch(
        "custom_components.payback.api.PaybackAPIClient.login",
        return_value=True,
    ), patch(
        "custom_components.payback.api.PaybackAPIClient.get_account",
        return_value=mock_account,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Total points sensor
        state = hass.states.get("sensor.payback_test_user_example_com_total_points")
        assert state is not None
        assert state.state == "2500"

        # Available points sensor
        state = hass.states.get("sensor.payback_test_user_example_com_available_points")
        assert state is not None
        assert state.state == "2000"

        # Pending points sensor
        state = hass.states.get("sensor.payback_test_user_example_com_pending_points")
        assert state is not None
        assert state.state == "500"

        # Active coupons sensor
        state = hass.states.get("sensor.payback_test_user_example_com_active_coupons")
        assert state is not None
        assert state.state == "1"
        assert state.attributes["customer_name"] == "Erika Mustermann"
        assert state.attributes["card_number"] == "987654321"
