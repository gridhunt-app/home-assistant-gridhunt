"""Config flow: pairing code or pasted token."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ApiError, AuthError, GridhuntClient, account_id_of
from .const import (
    CONF_BASE_URL,
    CONF_SHOW_PANEL,
    CONF_TOKEN,
    DEFAULT_BASE_URL,
    DEFAULT_SHOW_PANEL,
    DOMAIN,
    PAIR_NAME,
)


def _norm(url: str) -> str:
    return url.strip().rstrip("/")


def _is_legacy_uid(uid: str) -> bool:
    """unique_id of versions before 0.1.18: 12 hex chars of the token hash."""
    return re.fullmatch(r"[0-9a-f]{12}", uid) is not None


def unique_id_for(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:12]


class GridhuntConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 3

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GridhuntOptionsFlow:
        return GridhuntOptionsFlow()

    def __init__(self) -> None:
        self._base_url = DEFAULT_BASE_URL
        self._device_code = ""
        self._user_code = ""
        self._verification_url = ""
        self._reauth = False

    # -- helpers ---------------------------------------------------------------
    def _default_base(self) -> str:
        if self._reauth:
            return self._get_reauth_entry().data.get(CONF_BASE_URL, self._base_url)
        return self._base_url

    def _client(self, token: str | None = None) -> GridhuntClient:
        return GridhuntClient(async_get_clientsession(self.hass), self._base_url, token)

    async def _finish(self, token: str) -> ConfigFlowResult:
        """Validate the token and create or update the entry."""
        try:
            me = await self._client(token).me()
        except AuthError:
            return self.async_abort(reason="invalid_auth")
        except ApiError:
            return self.async_abort(reason="cannot_connect")
        return await self._create(token, me)

    async def _create(self, token: str, me: dict[str, Any]) -> ConfigFlowResult:
        account_id = account_id_of(me)
        uid = account_id or unique_id_for(token)  # token hash only for servers without an account id
        data = {CONF_BASE_URL: self._base_url, CONF_TOKEN: token}
        if self._reauth:
            entry = self._get_reauth_entry()
            if not account_id:
                return self.async_update_reload_and_abort(entry, data_updates=data)
            if entry.unique_id and not _is_legacy_uid(entry.unique_id):
                # the new token must belong to the same account
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
            return self.async_update_reload_and_abort(entry, unique_id=uid, data_updates=data)
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=me.get("name") or "Gridhunt", data=data)

    # -- entry points ----------------------------------------------------------
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["pair", "token"])

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        self._reauth = True
        self._base_url = entry_data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="reauth_confirm", menu_options=["pair", "token"])

    # -- pairing code ----------------------------------------------------------
    async def async_step_pair(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._base_url = _norm(user_input[CONF_BASE_URL])
            try:
                result = await self._client().pair_start(PAIR_NAME)
                self._device_code = result["deviceCode"]
                self._user_code = result["userCode"]
                self._verification_url = result["verificationUrl"]
            except (ApiError, KeyError):
                errors["base"] = "cannot_connect"
            else:
                return await self.async_step_pair_wait()
        return self.async_show_form(
            step_id="pair",
            data_schema=vol.Schema(
                {vol.Optional(CONF_BASE_URL, default=self._default_base()): str}
            ),
            errors=errors,
        )

    async def async_step_pair_wait(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                result = await self._client().pair_poll(self._device_code)
            except ApiError as err:
                if err.code == "invalid_code":
                    return self.async_show_form(
                        step_id="pair",
                        data_schema=vol.Schema(
                            {vol.Optional(CONF_BASE_URL, default=self._base_url): str}
                        ),
                        errors={"base": "code_expired"},
                    )
                errors["base"] = "cannot_connect"
            else:
                token = result.get("token")
                if not token:
                    errors["base"] = "authorization_pending"
                else:
                    return await self._finish(token)
        return self.async_show_form(
            step_id="pair_wait",
            data_schema=vol.Schema({}),
            description_placeholders={
                "user_code": self._user_code,
                "verification_url": self._verification_url,
                # QR z adresem zatwierdzenia (GIF z serwera Gridhunt): telefon z zalogowanym Gridhuntem zatwierdza kod
                "qr_url": f"{self._base_url}/api/ha/pair/qr?{urlencode({'code': self._user_code})}",
            },
            errors=errors,
        )

    # -- pasted token ----------------------------------------------------------
    async def async_step_token(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._base_url = _norm(user_input[CONF_BASE_URL])
            token = user_input[CONF_TOKEN].strip()
            try:
                me = await self._client(token).me()
            except AuthError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            else:
                return await self._create(token, me)
        return self.async_show_form(
            step_id="token",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOKEN): str,
                    vol.Optional(CONF_BASE_URL, default=self._default_base()): str,
                }
            ),
            errors=errors,
        )


class GridhuntOptionsFlow(OptionsFlow):
    """Account options: sidebar panel on/off (applied without a restart)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={**self.config_entry.options, **user_input})
        current = self.config_entry.options.get(CONF_SHOW_PANEL, DEFAULT_SHOW_PANEL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_SHOW_PANEL, default=current): bool}),
        )
