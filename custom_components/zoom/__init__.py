"""The Zoom integration."""
from logging import getLogger

from homeassistant.config_entries import ENTRY_STATE_LOADED, SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .api import ZoomAPI
from .common import (
    ZoomDataUpdateCoordinator,
    ZoomOAuth2Implementation,
    ZoomWebhookRequestView,
)
from .config_flow import OAuth2FlowHandler
from .const import (
    CONF_VERIFICATION_TOKEN,
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
    ZOOM_SCHEMA,
)

_LOGGER = getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: ZOOM_SCHEMA}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["binary_sensor", "sensor"]


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the Zoom component."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    OAuth2FlowHandler.async_register_implementation(
        hass,
        ZoomOAuth2Implementation(
            hass,
            DOMAIN,
            config[DOMAIN][CONF_CLIENT_ID],
            config[DOMAIN][CONF_CLIENT_SECRET],
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
            config[DOMAIN][CONF_VERIFICATION_TOKEN],
        ),
    )
    hass.data[DOMAIN][SOURCE_IMPORT] = True

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Zoom from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    try:
        implementation = (
            await config_entry_oauth2_flow.async_get_config_entry_implementation(
                hass, entry
            )
        )
    except ValueError:
        implementation = ZoomOAuth2Implementation(
            hass,
            DOMAIN,
            entry.data[CONF_CLIENT_ID],
            entry.data[CONF_CLIENT_SECRET],
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
            entry.data[CONF_VERIFICATION_TOKEN],
        )
        OAuth2FlowHandler.async_register_implementation(hass, implementation)

    if "coordinator" not in hass.data[DOMAIN]:
        coordinator = ZoomDataUpdateCoordinator(
            hass,
            ZoomAPI(
                config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
            ),
        )
        await coordinator.async_refresh()
        hass.data[DOMAIN]["coordinator"] = coordinator

        # Register view
        hass.http.register_view(
            ZoomWebhookRequestView(entry.data[CONF_VERIFICATION_TOKEN])
        )

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    hass.data[DOMAIN].pop(config_entry.entry_id)

    if (
        not any(
            entry.state == ENTRY_STATE_LOADED
            and entry.entry_id != config_entry.entry_id
            for entry in hass.config_entries.async_entries(DOMAIN)
        )
        and "coordinator" in hass.data[DOMAIN]
    ):
        hass.data[DOMAIN].pop("coordinator")

    return True