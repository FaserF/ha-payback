"""Data Update Coordinator for PAYBACK Deutschland integration with complete anti-ban safeguards."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import storage
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import PaybackAPIClient, PaybackAccount
from .const import (
    CONF_AUTO_ACTIVATE_COUPONS,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Global request lock per domain to ensure serial processing across components (ANTI-BAN)
_GLOBAL_FETCH_LOCK = asyncio.Lock()
ISSUE_ID_CONNECTION = "connection_error"


class PaybackDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage fetching PAYBACK data safely without triggering anti-bot bans."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        config = {**entry.data, **entry.options}
        self.username: str = config[CONF_USERNAME]
        self.password: str = config[CONF_PASSWORD]
        self.auto_activate_coupons: bool = config.get(CONF_AUTO_ACTIVATE_COUPONS, False)
        self.config_entry = entry

        # Anti-ban state
        self._backoff_until: datetime | None = None
        self._consecutive_failures = 0
        self._last_success: datetime | None = None
        self._issue_created = False

        session_cookie = config.get(CONF_SESSION_COOKIE, "").strip() or None
        self.store: storage.Store = storage.Store(hass, 1, f"{DOMAIN}_{self.username}")
        self.client = PaybackAPIClient(
            username=self.username,
            password=self.password,
            session_cookie=session_cookie,
        )

        interval_hours = max(
            MIN_UPDATE_INTERVAL,
            config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"PAYBACK ({self.username})",
            update_interval=timedelta(hours=interval_hours),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Payback API with full anti-ban protections."""
        now = dt_util.utcnow()

        # 1. Backoff Check (ANTI-BAN)
        if self._backoff_until and now < self._backoff_until:
            remaining = int((self._backoff_until - now).total_seconds())
            _LOGGER.warning(
                "PAYBACK rate-limit backoff active for %s (%ds remaining). Serving cached data.",
                self.username,
                remaining,
            )
            cached = await self._load_cached_data()
            if cached:
                return cached
            raise UpdateFailed(f"Rate limited (backoff for {remaining}s)")

        # 2. Acquire Global Lock (ANTI-BAN - zero concurrent requests)
        async with _GLOBAL_FETCH_LOCK:
            # Jitter delay (5 to 15s) to avoid timing signatures
            jitter = random.uniform(5.0, 15.0)
            _LOGGER.debug("PAYBACK anti-ban delay: sleeping %.1fs before API call", jitter)
            await asyncio.sleep(jitter)

            try:
                # Execute async login & fetch
                await self.hass.async_add_executor_job(self.client.login)
                account: PaybackAccount = await self.hass.async_add_executor_job(self.client.get_account)

                # Process auto-activation if requested
                if self.auto_activate_coupons:
                    for coupon in account.coupons:
                        if not coupon.activated:
                            await self.hass.async_add_executor_job(self.client.activate_coupon, coupon.coupon_id)
                            await asyncio.sleep(random.uniform(2.0, 4.0))

                data = {
                    "card_number": account.card_number,
                    "customer_name": account.customer_name,
                    "points": {
                        "total": account.points.total_points,
                        "available": account.points.available_points,
                        "pending": account.points.pending_points,
                    },
                    "coupons": [
                        {
                            "id": c.coupon_id,
                            "title": c.title,
                            "description": c.description,
                            "partner": c.partner_name,
                            "activated": c.activated,
                        }
                        for c in account.coupons
                    ],
                    "last_updated": dt_util.utcnow().isoformat(),
                }

                # Reset failure state on success
                self._consecutive_failures = 0
                self._backoff_until = None
                self._last_success = now

                if self._issue_created:
                    ir.async_delete_issue(self.hass, DOMAIN, ISSUE_ID_CONNECTION)
                    self._issue_created = False

                # Save to persistent storage to survive restarts
                await self.store.async_save(data)
                return data

            except Exception as exc:
                self._consecutive_failures += 1

                # Calculate exponential backoff (e.g., 30m, 1h, 2h, up to 12h)
                backoff_minutes = min(720, 30 * (2 ** (self._consecutive_failures - 1)))
                self._backoff_until = now + timedelta(minutes=backoff_minutes)

                _LOGGER.error(
                    "Error fetching PAYBACK data (attempt %d): %s. Backing off until %s",
                    self._consecutive_failures,
                    exc,
                    self._backoff_until,
                )

                if not self._issue_created:
                    ir.async_create_issue(
                        self.hass,
                        DOMAIN,
                        ISSUE_ID_CONNECTION,
                        is_fixable=False,
                        severity=ir.IssueSeverity.WARNING,
                        translation_key="connection_error",
                    )
                    self._issue_created = True

                # Serve cached data if available rather than breaking entities
                cached = await self._load_cached_data()
                if cached:
                    return cached
                raise UpdateFailed(f"Error communicating with PAYBACK API: {exc}") from exc

    async def _load_cached_data(self) -> dict[str, Any] | None:
        """Load persistent cache from disk."""
        try:
            return await self.store.async_load()
        except Exception as exc:
            _LOGGER.debug("Could not load PAYBACK cache: %s", exc)
            return None
