"""Support for Peblar selects."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from peblar import PeblarEVInterface

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import (
    PeblarConfigEntry,
    PeblarData,
    PeblarDataUpdateCoordinator,
    PeblarRuntimeData,
)
from .entity import PeblarEntity
from .helpers import peblar_exception_handler

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class PeblarSwitchEntityDescription(SwitchEntityDescription):
    """Class describing Peblar switch entities."""

    has_fn: Callable[[PeblarRuntimeData], bool] = lambda x: True
    is_on_fn: Callable[[PeblarData], bool]
    set_fn: Callable[[PeblarDataUpdateCoordinator, bool], Awaitable[Any]]


def _async_peblar_charge(
    coordinator: PeblarDataUpdateCoordinator, on: bool
) -> Awaitable[PeblarEVInterface]:
    """Set the charge state."""
    charge_current_limit = 0
    if on:
        charge_current_limit = (
            coordinator.config_entry.runtime_data.last_known_charging_limit * 1000
        )
    return coordinator.api.ev_interface(charge_current_limit=charge_current_limit)


DESCRIPTIONS = [
    PeblarSwitchEntityDescription(
        key="force_single_phase",
        translation_key="force_single_phase",
        entity_category=EntityCategory.CONFIG,
        has_fn=lambda x: (
            x.data_coordinator.data.system.force_single_phase_allowed
            and x.user_configuration_coordinator.data.connected_phases > 1
        ),
        is_on_fn=lambda x: x.ev.force_single_phase,
        set_fn=lambda x, on: x.api.ev_interface(force_single_phase=on),
    ),
    PeblarSwitchEntityDescription(
        key="charge",
        translation_key="charge",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda x: (x.ev.charge_current_limit >= 6000),
        set_fn=_async_peblar_charge,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Peblar switch based on a config entry."""
    async_add_entities(
        PeblarSwitchEntity(
            entry=entry,
            coordinator=entry.runtime_data.data_coordinator,
            description=description,
        )
        for description in DESCRIPTIONS
        if description.has_fn(entry.runtime_data)
    )


class PeblarSwitchEntity(
    PeblarEntity[PeblarDataUpdateCoordinator],
    SwitchEntity,
):
    """Defines a Peblar switch entity."""

    entity_description: PeblarSwitchEntityDescription

    @property
    def is_on(self) -> bool:
        """Return state of the switch."""
        return self.entity_description.is_on_fn(self.coordinator.data)

    @peblar_exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.entity_description.set_fn(self.coordinator, True)
        await self.coordinator.async_request_refresh()

    @peblar_exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.entity_description.set_fn(self.coordinator, False)
        await self.coordinator.async_request_refresh()
