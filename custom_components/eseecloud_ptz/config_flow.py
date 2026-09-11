"""Config flow for EseeCloud Local PTZ."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import (
    CameraConfig,
    EseeCloudAuthenticationError,
    EseeCloudClient,
    EseeCloudError,
)
from .const import (
    CONF_DERIVED_CREDENTIAL,
    CONF_DURATION,
    CONF_PROFILE,
    CONF_UID,
    DEFAULT_DURATION,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
    MAX_DURATION,
    MIN_DURATION,
    PROFILE_W6_L2,
    PROFILES,
)


def _schema(defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "EseeCloud Camera")): str,
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Required(CONF_UID, default=defaults.get(CONF_UID, "")): int,
            vol.Required(
                CONF_USERNAME, default=defaults.get(CONF_USERNAME, DEFAULT_USERNAME)
            ): str,
            vol.Required(CONF_DERIVED_CREDENTIAL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Required(
                CONF_PROFILE, default=defaults.get(CONF_PROFILE, PROFILE_W6_L2)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(PROFILES), mode=SelectSelectorMode.DROPDOWN
                )
            ),
        }
    )


class EseeCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one camera."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            profile = PROFILES[user_input[CONF_PROFILE]]
            client = EseeCloudClient(
                CameraConfig(
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                    uid=user_input[CONF_UID],
                    username=user_input[CONF_USERNAME],
                    credential=user_input[CONF_DERIVED_CREDENTIAL],
                    marker=profile["marker"],
                    actions=profile["actions"],
                )
            )
            try:
                await self.hass.async_add_executor_job(client.authenticate)
            except EseeCloudAuthenticationError:
                errors["base"] = "invalid_auth"
            except (EseeCloudError, OSError, TimeoutError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(str(user_input[CONF_UID]))
                self._abort_if_unique_id_configured()
                data = dict(user_input)
                title = data.pop(CONF_NAME)
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return EseeCloudOptionsFlow(config_entry)


class EseeCloudOptionsFlow(config_entries.OptionsFlow):
    """Configure movement duration."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DURATION,
                        default=self.entry.options.get(CONF_DURATION, DEFAULT_DURATION),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_DURATION,
                            max=MAX_DURATION,
                            step=0.1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    )
                }
            ),
        )

