"""Fetch the warning feed every 15 minutes and keep the warnings that match this entry."""
from datetime import timedelta
import logging

import aiohttp

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import DOMAIN, PARSERS, feed_url, matching

_LOGGER = logging.getLogger(__name__)


class StormCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=15), config_entry=entry)
        self.config = {**entry.data, **entry.options}
        self.url = feed_url(self.config)

    async def _async_update_data(self):
        c = self.config
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                self.url,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "home-assistant-storm-warnings"},  # NWS rejects requests without one
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
            warnings = PARSERS[c["source"]](data)
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, IndexError, TypeError) as err:
            if self.data is None:
                raise UpdateFailed(f"Warning feed {self.url} failed: {err}") from err
            # Keep the last result: the internet often drops mid-storm and we must not leave backup mode then.
            _LOGGER.warning("Warning feed %s failed, keeping last state: %s", self.url, err)
            return self.data
        return matching(
            warnings, c["regions"], dt_util.utcnow(), timedelta(hours=c["lead_hours"]), c["min_level"], c["types"]
        )
