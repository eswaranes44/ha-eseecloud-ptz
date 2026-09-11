"""Camera entity backed by a configured go2rtc RTSP source."""

from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_GO2RTC_STREAM_URL, CONF_UID, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the camera entity when a go2rtc source is configured."""
    stream_url = entry.options.get(
        CONF_GO2RTC_STREAM_URL,
        entry.data.get(CONF_GO2RTC_STREAM_URL, ""),
    ).strip()
    if not stream_url:
        return

    async_add_entities([EseeCloudCamera(entry, stream_url)])


class EseeCloudCamera(Camera):
    """Live-view entity using the user's existing go2rtc stream."""

    _attr_has_entity_name = True
    _attr_name = "Live View"
    _attr_supported_features = CameraEntityFeature.STREAM
    _attr_use_stream_for_stills = True
    _attr_frame_interval = 0.5

    def __init__(self, entry: ConfigEntry, stream_url: str) -> None:
        """Initialize the live-view entity."""
        self._stream_url = stream_url
        uid = entry.data[CONF_UID]
        self._attr_unique_id = f"{uid}_live_view"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(uid))},
            name=entry.title,
            manufacturer="EseeCloud / Juan",
            model="EseeCloud PTZ camera",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    async def async_stream_source(self) -> str:
        """Return the RTSP source that Home Assistant/go2rtc will proxy."""
        return self._stream_url
