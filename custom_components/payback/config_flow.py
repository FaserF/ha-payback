"""Config flow for PAYBACK Deutschland integration."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api import PaybackAPIClient
from .const import (
    CONF_AUTO_ACTIVATE_COUPONS,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
)


class PaybackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PAYBACK Deutschland."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD].strip()

            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            # Test credentials
            client = PaybackAPIClient(
                username=username,
                password=password,
                session_cookie=user_input.get(CONF_SESSION_COOKIE, "").strip() or None,
            )
            try:
                valid = await self.hass.async_add_executor_job(client.login)
                if valid:
                    return self.async_create_entry(
                        title=f"PAYBACK ({username})",
                        data={
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_SESSION_COOKIE: user_input.get(CONF_SESSION_COOKIE, "").strip(),
                        },
                    )
                errors["base"] = "auth_failed"
            except Exception:
                errors["base"] = "auth_failed"

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_SESSION_COOKIE, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow handler."""
        return PaybackOptionsFlowHandler()


class PaybackOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for PAYBACK Deutschland."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        config = {**self.config_entry.data, **self.config_entry.options}

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=168)),
                vol.Optional(
                    CONF_AUTO_ACTIVATE_COUPONS,
                    default=config.get(CONF_AUTO_ACTIVATE_COUPONS, False),
                ): bool,
                vol.Optional(
                    CONF_SESSION_COOKIE,
                    default=config.get(CONF_SESSION_COOKIE, ""),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
