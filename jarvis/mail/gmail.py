"""Gmail pela API oficial (OAuth). Lê e aplica marcadores "Jarvis/<categoria>".

A permissão gmail.modify é a menor que permite criar e aplicar marcadores. A
Jarvis não chama nenhuma rota de envio, lixeira ou exclusão.
"""

from __future__ import annotations

import json
from pathlib import Path

from jarvis import vault
from jarvis.config import config_dir
from jarvis.mail.base import Mail, MailError

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN = "gmail"
LABEL_PREFIX = "Jarvis/"


def client_secret_path() -> Path:
    return config_dir() / "gmail_client_secret.json"


def connect() -> str:
    """Abre o navegador para o usuário autorizar. Retorna o e-mail conectado."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    secret = client_secret_path()
    if not secret.exists():
        raise MailError(f"arquivo de credenciais do Google não encontrado em {secret}")
    flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
    creds = flow.run_local_server(
        port=0,
        authorization_prompt_message="Abrindo o navegador para você autorizar o Gmail…",
        success_message="Gmail conectado à Jarvis. Pode fechar esta aba.",
    )
    vault.save(TOKEN, creds.to_json())
    return GmailAccount().profile_email()


class GmailAccount:
    name = "gmail"

    def __init__(self, session=None) -> None:
        self._session = session  # injetável nos testes
        self._creds = None
        self._saved_token = None

    def _http(self):
        if self._session is None:
            from google.auth.transport.requests import AuthorizedSession
            from google.oauth2.credentials import Credentials

            token = vault.load(TOKEN)
            if not token:
                raise MailError("Gmail não conectado (rode: python -m jarvis --conectar gmail)")
            self._creds = Credentials.from_authorized_user_info(json.loads(token), SCOPES)
            self._saved_token = self._creds.token
            self._session = AuthorizedSession(self._creds)
        return self._session

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            resp = self._http().request(method, API + path, timeout=30, **kwargs)
        except Exception as exc:  # rede ou falha ao renovar o token
            raise MailError(f"Gmail sem conexão: {exc}") from exc
        if self._creds is not None and self._creds.token != self._saved_token:
            vault.save(TOKEN, self._creds.to_json())  # o token foi renovado
            self._saved_token = self._creds.token
        if resp.status_code >= 400:
            raise MailError(f"Gmail respondeu HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json() if resp.content else {}

    def profile_email(self) -> str:
        return self._request("GET", "/profile").get("emailAddress", "")

    def list_recent(self, limit: int = 20, unread_only: bool = False) -> list[Mail]:
        query = "in:inbox" + (" is:unread" if unread_only else "")
        listed = self._request("GET", "/messages", params={"maxResults": limit, "q": query})
        mails = []
        for ref in listed.get("messages", []):
            msg = self._request(
                "GET", f"/messages/{ref['id']}",
                params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
            )
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            mails.append(Mail(
                id=f"gmail:{msg['id']}",
                conta="gmail",
                remetente=headers.get("from", ""),
                assunto=headers.get("subject", "(sem assunto)"),
                data=headers.get("date", ""),
                previa=msg.get("snippet", "")[:300],
                nao_lido="UNREAD" in msg.get("labelIds", []),
            ))
        return mails

    def _label_id(self, category: str) -> str:
        name = LABEL_PREFIX + category
        for label in self._request("GET", "/labels").get("labels", []):
            if label["name"] == name:
                return label["id"]
        created = self._request("POST", "/labels", json={
            "name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show",
        })
        return created["id"]

    def apply_category(self, native_ids: list[str], category: str) -> None:
        if native_ids:
            self._request("POST", "/messages/batchModify", json={
                "ids": native_ids, "addLabelIds": [self._label_id(category)],
            })
