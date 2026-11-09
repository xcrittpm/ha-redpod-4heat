"""Config flow for the Red-Pod 4Heat (local) integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from .api import FourHeatClient, FourHeatError
from .const import CODE_STATE, DEFAULT_NAME, DEFAULT_PORT, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(int, vol.Range(1, 65535)),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


class FourHeatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the module's IP address and check it answers."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()
            try:
                readings = await FourHeatClient(host, port).read_all()
            except FourHeatError:
                errors["base"] = "cannot_connect"
            else:
                if CODE_STATE not in readings:
                    errors["base"] = "unsupported"
                else:
                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME) or DEFAULT_NAME,
                        data={CONF_HOST: host, CONF_PORT: port},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
            errors=errors,
        )
