"""Diagnostics for EseeCloud Local PTZ."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DERIVED_CREDENTIAL


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return redacted configuration diagnostics."""
    data = dict(entry.data)
    data[CONF_DERIVED_CREDENTIAL] = "**REDACTED**"
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "data": data,
        "options": dict(entry.options),
    }

