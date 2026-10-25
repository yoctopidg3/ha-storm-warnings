"""UI setup: pick a source, then the area and warning filters."""
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import COUNTIES, DOMAIN, LEVELS, PARSERS, feed_url, nearest_county

DEFAULT_TYPES = ["wind", "rain", "thunder", "snow", "ice", "storm", "tornado", "hurricane", "blizzard", "winter"]


def _filters_schema(current):
    return {
        vol.Required("lead_hours", default=current.get("lead_hours", 24)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=96, unit_of_measurement="h", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required("min_level", default=current.get("min_level", "yellow")): selector.SelectSelector(
            selector.SelectSelectorConfig(options=LEVELS, translation_key="level")
        ),
        vol.Required("types", default=current.get("types", DEFAULT_TYPES)): selector.SelectSelector(
            selector.SelectSelectorConfig(options=DEFAULT_TYPES, multiple=True, custom_value=True)
        ),
    }


def _clean_types(user_input):
    user_input["types"] = [t.strip().lower() for t in user_input["types"] if t.strip()]
    return user_input


class StormWarningsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._source = user_input["source"]
            return await getattr(self, f"async_step_{self._source}")()
        schema = vol.Schema(
            {
                vol.Required("source", default="met_eireann"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=list(PARSERS), translation_key="source")
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_met_eireann(self, user_input=None):
        errors = {}
        if user_input is not None:
            regions = sorted(user_input["regions"])
            if regions:
                title = "Storm warning " + ", ".join(COUNTIES[r][0] for r in regions)
                return await self._create(title, f"met_eireann:{','.join(regions)}", {**user_input, "regions": regions})
            errors["regions"] = "no_counties"
        counties = [
            selector.SelectOptionDict(value=k, label=v[0]) for k, v in sorted(COUNTIES.items(), key=lambda kv: kv[1])
        ]
        home = nearest_county(self.hass.config.latitude, self.hass.config.longitude)
        schema = vol.Schema(
            {
                vol.Required("regions", default=[home] if home else []): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=counties, multiple=True)
                ),
                **_filters_schema({}),
            }
        )
        return self.async_show_form(step_id="met_eireann", data_schema=schema, errors=errors)

    async def async_step_meteoalarm(self, user_input=None):
        errors = {}
        if user_input is not None:
            country = user_input["country"].strip().lower().replace(" ", "-")
            regions = sorted({r.strip().upper() for r in user_input["regions"].split(",") if r.strip()})
            if not regions:
                errors["regions"] = "no_regions"
            else:
                errors.update(await self._check_feed({"source": "meteoalarm", "country": country}))
            if not errors:
                data = {**user_input, "country": country, "regions": regions}
                title = f"Storm warning {country} {', '.join(regions)}"
                return await self._create(title, f"meteoalarm:{country}:{','.join(regions)}", data)
        schema = vol.Schema(
            {
                vol.Required("country", default="ireland"): str,
                vol.Required("regions"): str,
                **_filters_schema({}),
            }
        )
        return self.async_show_form(
            step_id="meteoalarm", data_schema=self.add_suggested_values_to_schema(schema, user_input), errors=errors
        )

    async def async_step_nws(self, user_input=None):
        if user_input is not None:
            loc = user_input.pop("location")
            data = {**user_input, "regions": [], "latitude": loc["latitude"], "longitude": loc["longitude"]}
            title = f"Storm warning {loc['latitude']:.2f}, {loc['longitude']:.2f}"
            return await self._create(title, f"nws:{loc['latitude']:.4f},{loc['longitude']:.4f}", data)
        home = {"latitude": self.hass.config.latitude, "longitude": self.hass.config.longitude}
        schema = vol.Schema(
            {
                vol.Required("location", default=home): selector.LocationSelector(),
                **_filters_schema({}),
            }
        )
        return self.async_show_form(step_id="nws", data_schema=schema)

    async def _check_feed(self, config):
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(feed_url(config), timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 404:
                    return {"country": "unknown_country"}
                resp.raise_for_status()
        except (aiohttp.ClientError, TimeoutError):
            return {"base": "cannot_connect"}
        return {}

    async def _create(self, title, unique_id, data):
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data={"source": self._source, **_clean_types(data)})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return StormWarningsOptionsFlow()


class StormWarningsOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=_clean_types(user_input))
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=vol.Schema(_filters_schema(current)))
