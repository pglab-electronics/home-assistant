"""Tests for Renault setup process."""

from collections.abc import Generator
from typing import Any
from unittest.mock import Mock, patch

import aiohttp
import pytest
from renault_api.gigya.exceptions import GigyaException, InvalidCredentialsException

from homeassistant.components.renault.const import DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant


@pytest.fixture(autouse=True)
def override_platforms() -> Generator[None, None, None]:
    """Override PLATFORMS."""
    with patch("homeassistant.components.renault.PLATFORMS", []):
        yield


@pytest.fixture(autouse=True, name="vehicle_type", params=["zoe_40"])
def override_vehicle_type(request) -> str:
    """Parametrize vehicle type."""
    return request.param


@pytest.mark.usefixtures("patch_renault_account", "patch_get_vehicles")
async def test_setup_unload_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Test entry setup and unload."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.LOADED

    # Unload the entry and verify that the data has been removed
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_bad_password(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Test entry setup and unload."""
    # Create a mock entry so we don't have to go through config flow
    with patch(
        "renault_api.renault_session.RenaultSession.login",
        side_effect=InvalidCredentialsException(403042, "invalid loginID or password"),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.parametrize("side_effect", [aiohttp.ClientConnectionError, GigyaException])
async def test_setup_entry_exception(
    hass: HomeAssistant, config_entry: ConfigEntry, side_effect: Any
) -> None:
    """Test ConfigEntryNotReady when API raises an exception during entry setup."""
    # In this case we are testing the condition where async_setup_entry raises
    # ConfigEntryNotReady.
    with patch(
        "renault_api.renault_session.RenaultSession.login",
        side_effect=side_effect,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("patch_renault_account")
async def test_setup_entry_kamereon_exception(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Test ConfigEntryNotReady when API raises an exception during entry setup."""
    # In this case we are testing the condition where renault_hub fails to retrieve
    # list of vehicles (see Gateway Time-out on #97324).
    with patch(
        "renault_api.renault_client.RenaultClient.get_api_account",
        side_effect=aiohttp.ClientResponseError(Mock(), (), status=504),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("patch_renault_account", "patch_get_vehicles")
@pytest.mark.parametrize("vehicle_type", ["missing_details"], indirect=True)
async def test_setup_entry_missing_vehicle_details(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Test ConfigEntryNotReady when vehicleDetails is missing."""
    # In this case we are testing the condition where renault_hub fails to retrieve
    # vehicle details (see #99127).
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
