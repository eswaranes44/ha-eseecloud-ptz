"""EseeCloud Local PTZ integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .client import CameraConfig, EseeCloudClient, EseeCloudError
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DIRECTION,
    ATTR_DURATION,
    CONF_DERIVED_CREDENTIAL,
    CONF_DURATION,
    CONF_PROFILE,
    CONF_UID,
    DEFAULT_DURATION,
    DOMAIN,
    MAX_DURATION,
    MIN_DURATION,
    PLATFORMS,
    PROFILES,
    SERVICE_MOVE,
)


@dataclass(slots=True)
class EseeCloudRuntime:
    """Per-entry runtime state."""

    client: EseeCloudClient
    lock: asyncio.Lock

    async def move(self, hass: HomeAssistant, direction: str, duration: float) -> None:
        async with self.lock:
            await hass.async_add_executor_job(self.client.move, direction, duration)


def _client_from_entry(entry: ConfigEntry) -> EseeCloudClient:
    profile = PROFILES[entry.data[CONF_PROFILE]]
    return EseeCloudClient(
        CameraConfig(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            uid=entry.data[CONF_UID],
            username=entry.data[CONF_USERNAME],
            credential=entry.data[CONF_DERIVED_CREDENTIAL],
            marker=profile["marker"],
            actions=profile["actions"],
        )
    )


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Set up the integration and global move action."""

    schema = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_DIRECTION): vol.In(["up", "down", "left", "right"]),
            vol.Optional(ATTR_DURATION, default=DEFAULT_DURATION): vol.All(
                vol.Coerce(float), vol.Range(min=MIN_DURATION, max=MAX_DURATION)
            ),
        }
    )

    async def handle_move(call: ServiceCall) -> None:
        entry = hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY_ID])
        if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
            raise HomeAssistantError("EseeCloud PTZ configuration entry not found")
        runtime: EseeCloudRuntime = entry.runtime_data
        await runtime.move(
            hass, call.data[ATTR_DIRECTION], call.data[ATTR_DURATION]
        )

    hass.services.async_register(DOMAIN, SERVICE_MOVE, handle_move, schema=schema)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one camera entry."""
    client = _client_from_entry(entry)
    try:
        await hass.async_add_executor_job(client.authenticate)
    except (EseeCloudError, OSError, TimeoutError, ValueError) as exc:
        raise ConfigEntryNotReady("Unable to authenticate with the camera") from exc
    entry.runtime_data = EseeCloudRuntime(client, asyncio.Lock())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one camera entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
