"""Test the PAYBACK Deutschland config flow."""

from unittest.mock import patch
import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.payback.const import (
    CONF_AUTO_ACTIVATE_COUPONS,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_flow_user_success(hass: HomeAssistant) -> None:
    """Test successful user login step of config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch(
        "custom_components.payback.api.PaybackAPIClient.login",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test_user@example.com",
                CONF_PASSWORD: "secret_password",
            },
        )
        assert result["type"] == "create_entry"
        assert result["title"] == "PAYBACK (test_user@example.com)"
        assert result["data"] == {
            CONF_USERNAME: "test_user@example.com",
            CONF_PASSWORD: "secret_password",
        }


async def test_flow_user_auth_failed(hass: HomeAssistant) -> None:
    """Test authentication failure handling in config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.payback.api.PaybackAPIClient.login",
        side_effect=Exception("Invalid credentials"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test_user@example.com",
                CONF_PASSWORD: "wrong_password",
            },
        )
        assert result["type"] == "form"
        assert result["errors"] == {"base": "auth_failed"}


async def test_flow_already_configured(hass: HomeAssistant) -> None:
    """Test config flow aborts when the same user is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PAYBACK (test_user@example.com)",
        data={CONF_USERNAME: "test_user@example.com", CONF_PASSWORD: "password"},
        unique_id="test_user@example.com",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.payback.api.PaybackAPIClient.login",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test_user@example.com",
                CONF_PASSWORD: "password",
            },
        )
        assert result["type"] == "abort"
        assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow to update interval and auto-activation."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PAYBACK (test_user@example.com)",
        data={CONF_USERNAME: "test_user@example.com", CONF_PASSWORD: "password"},
        unique_id="test_user@example.com",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_INTERVAL: 8,
            CONF_AUTO_ACTIVATE_COUPONS: True,
        },
    )
    assert result["data"] == {
        CONF_UPDATE_INTERVAL: 8,
        CONF_AUTO_ACTIVATE_COUPONS: True,
    }
