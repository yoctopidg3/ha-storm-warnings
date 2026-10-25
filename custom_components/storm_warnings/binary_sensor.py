"""Binary sensor: on while a matching weather warning is active or due within lead_hours."""
from datetime import timedelta
import logging

import aiohttp

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from . import PARSERS, feed_url, matching

SCAN_INTERVAL = timedelta(minutes=15)
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([StormWarning(entry)], True)


class StormWarning(BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, entry):
        self._config = {**entry.data, **entry.options}
        self._url = feed_url(self._config)
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id

    async def async_update(self):
        c = self._config
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                self._url,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "home-assistant-storm-warnings"},  # NWS rejects requests without one
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
            warnings = PARSERS[c["source"]](data)
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, IndexError, TypeError) as err:
            # Keep the last state: the internet often drops mid-storm and we must not leave backup mode then.
            _LOGGER.warning("Warning feed %s failed, keeping last state: %s", self._url, err)
            return
        hits = matching(
            warnings, c["regions"], dt_util.utcnow(), timedelta(hours=c["lead_hours"]), c["min_level"], c["types"]
        )
        self._attr_is_on = bool(hits)
        self._attr_extra_state_attributes = {
            "warnings": [w["headline"] for w in hits],
            "until": max((dt_util.parse_datetime(w["expiry"]) for w in hits), default=None),
        }
