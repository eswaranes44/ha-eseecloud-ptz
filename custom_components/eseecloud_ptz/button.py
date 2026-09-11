"""PTZ direction buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DURATION, CONF_UID, DEFAULT_DURATION, DOMAIN

ICONS = {
    "up": "mdi:arrow-up-bold",
    "down": "mdi:arrow-down-bold",
    "left": "mdi:arrow-left-bold",
    "right": "mdi:arrow-right-bold",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create four directional buttons."""
    async_add_entities(EseeCloudDirectionButton(entry, direction) for direction in ICONS)


class EseeCloudDirectionButton(ButtonEntity):
    """Momentary bounded PTZ movement button."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, direction: str) -> None:
        self._entry = entry
        self._direction = direction
        self._attr_name = direction.title()
        self._attr_icon = ICONS[direction]
        self._attr_unique_id = f"{entry.data[CONF_UID]}_{direction}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.data[CONF_UID]))},
            name=entry.title,
            manufacturer="EseeCloud / Juan",
            model=entry.data.get(CONF_NAME, entry.data.get("profile", "PTZ Camera")),
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    async def async_press(self) -> None:
        runtime = self._entry.runtime_data
        duration = self._entry.options.get(CONF_DURATION, DEFAULT_DURATION)
        await runtime.move(self.hass, self._direction, duration)

