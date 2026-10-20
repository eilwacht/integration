"""Config flow: one entry (breaking news) plus one subentry per news watch."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_KEYWORDS, CONF_REGIONS, DOMAIN, REGIONS, SUBENTRY_WATCH
from .watch import NATIONAL

REGION_OPTIONS = [str(NATIONAL), *(str(r) for r in REGIONS)]


class EilwachtConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the single Eilwacht entry (manifest: single_config_entry)."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Nothing to configure: breaking news work right away."""
        if user_input is not None:
            return self.async_create_entry(title="Eilwacht", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """News watches are subentries."""
        return {SUBENTRY_WATCH: WatchSubentryFlow}


class WatchSubentryFlow(ConfigSubentryFlow):
    """Add or change a news watch: name, federal states, keywords."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a news watch."""
        return await self._async_watch_step("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change a news watch."""
        return await self._async_watch_step("reconfigure", user_input)

    async def _async_watch_step(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            regions = sorted(int(r) for r in user_input.get(CONF_REGIONS, []))
            keywords = ", ".join(
                term.strip()
                for term in user_input.get(CONF_KEYWORDS, "").split(",")
                if term.strip()
            )
            if not name:
                errors[CONF_NAME] = "name_required"
            elif not regions:
                errors[CONF_REGIONS] = "no_regions"
            else:
                data = {CONF_REGIONS: regions, CONF_KEYWORDS: keywords}
                if self.source == SOURCE_RECONFIGURE:
                    return self.async_update_and_abort(
                        self._get_entry(),
                        self._get_reconfigure_subentry(),
                        title=name,
                        data=data,
                    )
                return self.async_create_entry(title=name, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): selector.TextSelector(),
                vol.Required(CONF_REGIONS): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=REGION_OPTIONS,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=CONF_REGIONS,
                    )
                ),
                vol.Optional(CONF_KEYWORDS): selector.TextSelector(),
            }
        )
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or self._defaults()
            ),
            errors=errors,
        )

    def _defaults(self) -> dict[str, Any]:
        if self.source == SOURCE_RECONFIGURE:
            subentry = self._get_reconfigure_subentry()
            return {
                CONF_NAME: subentry.title,
                CONF_REGIONS: [str(r) for r in subentry.data.get(CONF_REGIONS, [])],
                CONF_KEYWORDS: subentry.data.get(CONF_KEYWORDS, ""),
            }
        return {CONF_NAME: "", CONF_REGIONS: [], CONF_KEYWORDS: ""}
