"""Config flow for Napco iBridge."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import NapcoIbridgeApiClient, NapcoIbridgeApiClientCommunicationError, async_discover_panel
from .const import CONF_CODE, CONF_HOST, DOMAIN, LOGGER

DISCOVER_OPTION = "discover"
MANUAL_OPTION = "manual"


def _details_schema(host_default: str = "", code_default: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host_default): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT),
            ),
            vol.Optional(CONF_CODE, default=code_default): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD),
            ),
        },
    )


async def _async_probe(host: str) -> None:
    """Open a short-lived connection to verify we can talk to the panel."""
    client = NapcoIbridgeApiClient(host=host)
    try:
        await client.async_connect()
    finally:
        await client.async_disconnect()


class NapcoIbridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow that picks between discovery and manual entry, then validates."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_host: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NapcoIbridgeOptionsFlow:
        return NapcoIbridgeOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_menu(
                step_id="user",
                menu_options=[DISCOVER_OPTION, MANUAL_OPTION],
            )
        return await self.async_step_manual()

    async def async_step_discover(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        try:
            host = await async_discover_panel()
        except NapcoIbridgeApiClientCommunicationError as err:
            LOGGER.warning("Discovery failed: %s", err)
            return self.async_show_form(
                step_id="user",
                errors={"base": "no_discovery"},
            )
        self._discovered_host = host
        return await self.async_step_details()

    async def async_step_manual(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        self._discovered_host = None
        return await self.async_step_details()

    async def async_step_details(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        host_default = self._discovered_host or ""
        if user_input is not None:
            host = user_input[CONF_HOST]
            code = (user_input.get(CONF_CODE) or "").strip()
            if code and not code.isdigit():
                errors[CONF_CODE] = "invalid_code"
            else:
                try:
                    await _async_probe(host)
                except NapcoIbridgeApiClientCommunicationError as err:
                    LOGGER.warning("Probe of %s failed: %s", host, err)
                    errors["base"] = "cannot_connect"

            if not errors:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                data: dict[str, Any] = {CONF_HOST: host}
                if code:
                    data[CONF_CODE] = code
                return self.async_create_entry(title=f"Napco iBridge ({host})", data=data)

            host_default = host

        return self.async_show_form(
            step_id="details",
            data_schema=_details_schema(
                host_default=host_default,
                code_default=(user_input or {}).get(CONF_CODE, ""),
            ),
            errors=errors,
        )


class NapcoIbridgeOptionsFlow(OptionsFlow):
    """Allow updating the stored user code after setup."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            code = (user_input.get(CONF_CODE) or "").strip()
            if code and not code.isdigit():
                errors[CONF_CODE] = "invalid_code"
            else:
                data = {**self.config_entry.data}
                if code:
                    data[CONF_CODE] = code
                else:
                    data.pop(CONF_CODE, None)
                self.hass.config_entries.async_update_entry(self.config_entry, data=data)
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=self._schema(),
            errors=errors,
        )

    def _schema(self) -> vol.Schema:
        data = self.config_entry.data
        return vol.Schema(
            {
                vol.Optional(CONF_CODE, default=data.get(CONF_CODE, "")): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD),
                ),
            },
        )
