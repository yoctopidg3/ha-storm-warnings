"""Binary sensor: on while a matching weather warning is active or due within lead_hours."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import highest_level


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([StormWarning(entry)])


class StormWarning(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, entry):
        super().__init__(entry.runtime_data)
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id

    @property
    def is_on(self):
        return bool(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        hits = self.coordinator.data
        return {
            "level": highest_level(hits),
            "warnings": [w["headline"] for w in hits],
            "until": max((dt_util.parse_datetime(w["expiry"]) for w in hits), default=None),
        }
