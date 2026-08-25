"""Sensor platform for PAYBACK Deutschland integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PaybackDataUpdateCoordinator

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="total_points",
        name="Total Points",
        icon="mdi:hand-coin",
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="available_points",
        name="Available Points",
        icon="mdi:piggy-bank",
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="pending_points",
        name="Pending Points",
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="active_coupons",
        name="Active Coupons",
        icon="mdi:ticket-percent",
        state_class=SensorStateClass.TOTAL,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PAYBACK sensors based on config entry."""
    coordinator: PaybackDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PaybackSensorEntity(coordinator, description) for description in SENSOR_TYPES
    ]
    async_add_entities(entities)


class PaybackSensorEntity(
    CoordinatorEntity[PaybackDataUpdateCoordinator], SensorEntity
):
    """Representation of a PAYBACK Sensor."""

    def __init__(
        self,
        coordinator: PaybackDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.username}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.username)},
            "name": f"PAYBACK ({coordinator.username})",
            "manufacturer": "PAYBACK",
            "model": "Account Status",
            "configuration_url": "https://www.payback.de/coupons",
        }

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        points = self.coordinator.data.get("points", {})
        coupons = self.coordinator.data.get("coupons", [])

        if self.entity_description.key == "total_points":
            return points.get("total", 0)
        if self.entity_description.key == "available_points":
            return points.get("available", 0)
        if self.entity_description.key == "pending_points":
            return points.get("pending", 0)
        if self.entity_description.key == "active_coupons":
            return len([c for c in coupons if c.get("activated")])

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        if not self.coordinator.data:
            return {}

        return {
            "customer_name": self.coordinator.data.get("customer_name"),
            "card_number": self.coordinator.data.get("card_number"),
            "last_updated": self.coordinator.data.get("last_updated"),
        }
