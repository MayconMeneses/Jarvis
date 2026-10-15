"""Outlook / Hotmail pelo Microsoft Graph (OAuth via MSAL).

Aplica categorias "Jarvis: <categoria>" sem mover nem apagar mensagens. Exige um
registro de aplicativo próprio no Microsoft Entra (client_id no config.json).
"""

from __future__ import annotations

from jarvis import vault
from jarvis.mail.base import Mail, MailError

SCOPES = ["Mail.ReadWrite"]
API = "https://graph.microsoft.com/v1.0/me"
TOKEN = "outlook"
CATEGORY_PREFIX = "Jarvis: "


def _app(client_id: str, authority: str):
    import msal

    if not client_id:
        raise MailError("falta o outlook_client_id no config.json (veja o guia de configuração)")
    cache = msal.SerializableTokenCache()
    saved = vault.load(TOKEN)
    if saved:
        cache.deserialize(saved)
    app = msal.PublicClientApplication(
        client_id, authority=f"https://login.microsoftonline.com/{authority}", token_cache=cache
    )
    return app, cache


def _persist(cache) -> None:
    if cache.has_state_changed:
        vault.save(TOKEN, cache.serialize())


def connect(client_id: str, authority: str = "consumers") -> str:
    app, cache = _app(client_id, authority)
    result = app.acquire_token_interactive(SCOPES, prompt="select_account")
    if "access_token" not in result:
        raise MailError(f"Microsoft recusou o login: {result.get('error_description', result)}")
    _persist(cache)
    return result.get("id_token_claims", {}).get("preferred_username", "")


class OutlookAccount:
    name = "outlook"

    def __init__(self, client_id: str, authority: str = "consumers", session=None, token=None) -> None:
        self.client_id = client_id
        self.authority = authority
        self._session = session  # injetáveis nos testes
        self._token = token

    def _access_token(self) -> str:
        if self._token:
            return self._token
        app, cache = _app(self.client_id, self.authority)
        accounts = app.get_accounts()
        result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
        if not result or "access_token" not in result:
            raise MailError("Outlook não conectado (rode: python -m jarvis --conectar outlook)")
        _persist(cache)
        return result["access_token"]

    def _request(self, method: str, path: str, **kwargs) -> dict:
        if self._session is None:
            import requests

            self._session = requests.Session()
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        try:
            resp = self._session.request(method, API + path, headers=headers, timeout=30, **kwargs)
        except Exception as exc:
            raise MailError(f"Outlook sem conexão: {exc}") from exc
        if resp.status_code >= 400:
            raise MailError(f"Outlook respondeu HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json() if resp.content else {}

    def list_recent(self, limit: int = 20, unread_only: bool = False) -> list[Mail]:
        params = {
            "$top": str(limit),
            "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead",
        }
        if unread_only:
            params["$filter"] = "isRead eq false"
        else:  # o Graph rejeita $orderby junto com esse $filter
            params["$orderby"] = "receivedDateTime desc"
        data = self._request("GET", "/mailFolders/inbox/messages", params=params)
        mails = []
        for msg in data.get("value", []):
            sender = (msg.get("from") or {}).get("emailAddress", {})
            mails.append(Mail(
                id=f"outlook:{msg['id']}",
                conta="outlook",
                remetente=f"{sender.get('name', '')} <{sender.get('address', '')}>".strip(),
                assunto=msg.get("subject") or "(sem assunto)",
                data=msg.get("receivedDateTime", ""),
                previa=(msg.get("bodyPreview") or "")[:300],
                nao_lido=not msg.get("isRead", True),
            ))
        return mails

    def apply_category(self, native_ids: list[str], category: str) -> None:
        name = CATEGORY_PREFIX + category
        for native in native_ids:
            current = self._request("GET", f"/messages/{native}", params={"$select": "categories"})
            categories = current.get("categories", [])
            if name not in categories:
                self._request("PATCH", f"/messages/{native}", json={"categories": categories + [name]})
