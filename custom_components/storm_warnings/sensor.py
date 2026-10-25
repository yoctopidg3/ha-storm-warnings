"""Sensor: highest level among the matching warnings (none, yellow, orange, red)."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LEVELS, highest_level

ICONS = {"none": "mdi:weather-partly-cloudy", "yellow": "mdi:weather-windy", "orange": "mdi:weather-lightning-rainy",
         "red": "mdi:weather-hurricane"}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([StormLevel(entry)])


class StormLevel(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["none", *LEVELS]
    _attr_translation_key = "level"

    def __init__(self, entry):
        super().__init__(entry.runtime_data)
        self._attr_name = f"{entry.title} level"
        self._attr_unique_id = f"{entry.entry_id}_level"

    @property
    def native_value(self):
        return highest_level(self.coordinator.data)

    @property
    def icon(self):
        return ICONS[self.native_value]
