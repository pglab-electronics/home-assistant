"""Switch platform for Ecoforest."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pyecoforest.api import EcoforestApi
from pyecoforest.models.device import Device

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EcoforestConfigEntry
from .entity import EcoforestEntity


@dataclass(frozen=True, kw_only=True)
class EcoforestSwitchEntityDescription(SwitchEntityDescription):
    """Describes an Ecoforest switch entity."""

    value_fn: Callable[[Device], bool]
    switch_fn: Callable[[EcoforestApi, bool], Awaitable[Device]]


SWITCH_TYPES: tuple[EcoforestSwitchEntityDescription, ...] = (
    EcoforestSwitchEntityDescription(
        key="status",
        name=None,
        value_fn=lambda data: data.on,
        switch_fn=lambda api, status: api.turn(status),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EcoforestConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ecoforest switch platform."""
    coordinator = config_entry.runtime_data

    entities = [
        EcoforestSwitchEntity(coordinator, description) for description in SWITCH_TYPES
    ]

    async_add_entities(entities)


class EcoforestSwitchEntity(EcoforestEntity, SwitchEntity):
    """Representation of an Ecoforest switch entity."""

    entity_description: EcoforestSwitchEntityDescription

    @property
    def is_on(self) -> bool:
        """Return the state of the ecoforest device."""
        return self.entity_description.value_fn(self.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the ecoforest device."""
        await self.entity_description.switch_fn(self.coordinator.api, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the ecoforest device."""
        await self.entity_description.switch_fn(self.coordinator.api, False)
        await self.coordinator.async_request_refresh()
