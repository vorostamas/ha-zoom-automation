"""Sensor platform for Zoom."""
from logging import getLogger
from typing import Any, Dict, List, Optional

from homeassistant.components.binary_sensor import DEVICE_CLASS_OCCUPANCY
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event
from homeassistant.helpers.typing import HomeAssistantType

from .common import ZoomBaseEntity
from .const import (
    ATTR_EVENT,
    HA_ZOOM_EVENT,
    OCCUPANCY_EVENT,
    OCCUPANCY_ID,
    OCCUPANCY_STATUS,
    OCCUPANCY_STATUS_OFF,
)

_LOGGER = getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up a Zoom presence sensor entry."""
    async_add_entities(
        [ZoomOccupancySensor(hass, config_entry)],
        update_before_add=True,
    )


def get_data_from_path(data: Dict[str, Any], path: List[str]) -> Optional[str]:
    """Get value from dictionary using path list."""
    for val in path:
        data = data.get(val, {})

    if isinstance(data, str):
        return data
    return None


class ZoomOccupancySensor(ZoomBaseEntity):
    """Class for a Zoom user profile sensor."""

    def __init__(self, hass: HomeAssistantType, config_entry: ConfigEntry) -> None:
        """Initialize base sensor."""
        super().__init__(hass, config_entry)
        self._zoom_presence_status = None

    async def async_update_status(self, event: Event):
        """Update status if event received for this entity."""
        if (
            event.data[ATTR_EVENT] == OCCUPANCY_EVENT
            and get_data_from_path(event.data, OCCUPANCY_ID).lower()
            == self._coordinator.data.get("id", "").lower()
        ):
            self._zoom_presence_status = get_data_from_path(
                event.data, OCCUPANCY_STATUS
            ).lower()
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        # Register callback for webhook event
        self._async_unsub_listeners.append(
            self.hass.bus.async_listen(HA_ZOOM_EVENT, self.async_update_status)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect callbacks when entity is removed."""
        for listener in self._async_unsub_listeners:
            listener()

        self._async_unsub_listeners.clear()

    @property
    def name(self) -> str:
        """Entity name."""
        return f"Zoom {self._name}"

    @property
    def state(self) -> str:
        """Entity state."""
        return (
            STATE_OFF
            if not self._zoom_presence_status
            or self._zoom_presence_status == OCCUPANCY_STATUS_OFF.lower()
            else STATE_ON
        )

    @property
    def should_poll(self) -> bool:
        """Should entity be polled."""
        return False

    @property
    def assumed_state(self) -> bool:
        """Return True if unable to access real state of the entity."""
        return True

    @property
    def icon(self) -> str:
        """Entity icon."""
        return "mdi:do-not-disturb"

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_OCCUPANCY