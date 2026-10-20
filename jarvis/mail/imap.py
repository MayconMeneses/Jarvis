"""Conta IMAP opcional (Yahoo, iCloud, provedor próprio). SOMENTE LEITURA: SSL, caixa em modo readonly, BODY.PEEK.

A senha de app fica no Gerenciador de Credenciais (chave "imap:<apelido>"), nunca no config.json. O host precisa
estar na lista permitida. Marcar categorias não é suportado (o protocolo aqui só lê).
"""

from __future__ import annotations

import email
import email.header
import email.policy
import email.utils
import imaplib
import re

from jarvis import keys
from jarvis.config import Config
from jarvis.mail.base import Mail, MailError

HOSTS_PERMITIDOS = {
    "imap.mail.yahoo.com", "imap.mail.me.com", "imap.gmail.com", "outlook.office365.com", "imap-mail.outlook.com",
    "imap.aol.com", "imap.zoho.com", "imap.fastmail.com", "imap.uol.com.br", "imap.terra.com.br", "imap.bol.com.br",
    "imap.ig.com.br", "imap.hostinger.com", "imap.titan.email", "imap.mail.com", "imap.yandex.com", "imap.gmx.com",
}


def nome_da_conta(apelido: str) -> str:
    return "imap-" + re.sub(r"[^a-z0-9_-]+", "-", apelido.lower()).strip("-")[:20]


def validar_host(host: str) -> str:
    host = host.strip().lower()
    if host not in HOSTS_PERMITIDOS:
        raise ValueError(f"servidor IMAP não permitido: {host}. Permitidos: {', '.join(sorted(HOSTS_PERMITIDOS))}")
    return host


def conectar(cfg: Config, apelido: str, host: str, usuario: str, senha: str, porta: int = 993) -> None:
    """Guarda a senha de app no cofre e o resto no config (quem chama salva o config)."""
    apelido = " ".join(apelido.split())[:30]
    if not apelido or not usuario.strip() or not senha.strip():
        raise ValueError("informe apelido, usuário e senha de app")
    host = validar_host(host)
    keys.set_key(f"imap:{apelido}", senha)
    cfg.email.imap = [c for c in cfg.email.imap if c.get("apelido") != apelido] + [
        {"apelido": apelido, "host": host, "porta": int(porta), "usuario": usuario.strip()}]


def desconectar(cfg: Config, apelido: str) -> None:
    keys.delete_key(f"imap:{apelido}")
    cfg.email.imap = [c for c in cfg.email.imap if c.get("apelido") != apelido]


def _decodificar(valor: str | None) -> str:
    if not valor:
        return ""
    try:
        return str(email.header.make_header(email.header.decode_header(valor)))
    except (ValueError, LookupError):
        return valor


def _previa(msg) -> str:
    parte = msg.get_body(preferencelist=("plain", "html")) if hasattr(msg, "get_body") else None
    try:
        texto = parte.get_content() if parte is not None else ""
    except (LookupError, ValueError):
        texto = ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texto)).strip()[:300]


class ImapAccount:
    def __init__(self, conf: dict, senha: str | None = None, fabrica=imaplib.IMAP4_SSL) -> None:
        self.conf, self._senha, self._fabrica = conf, senha, fabrica
        self.name = nome_da_conta(conf["apelido"])

    def _abrir(self):
        senha = self._senha or keys.get_key(f"imap:{self.conf['apelido']}")
        if not senha:
            raise MailError(f"sem senha de app para {self.conf['apelido']} no cofre")
        host = validar_host(self.conf["host"])
        try:
            box = self._fabrica(host, int(self.conf.get("porta", 993)), timeout=20)
            box.login(self.conf["usuario"], senha)
            box.select("INBOX", readonly=True)  # nada é marcado, movido ou apagado
        except (imaplib.IMAP4.error, OSError) as exc:
            raise MailError(f"IMAP {self.conf['apelido']}: não consegui entrar ({type(exc).__name__})") from None
        return box

    def list_recent(self, limit: int, unread_only: bool) -> list[Mail]:
        box = self._abrir()
        try:
            _, dados = box.uid("SEARCH", None, "UNSEEN" if unread_only else "ALL")
            uids = (dados[0] or b"").split()[-limit:][::-1]
            mails = []
            for uid in uids:
                tipo, partes = box.uid("FETCH", uid, "(FLAGS BODY.PEEK[HEADER] BODY.PEEK[TEXT]<0.2000>)")
                if tipo != "OK":
                    continue
                cabecalho = next((p[1] for p in partes if isinstance(p, tuple) and b"HEADER" in p[0]), b"")
                corpo = next((p[1] for p in partes if isinstance(p, tuple) and b"TEXT" in p[0]), b"")
                msg = email.message_from_bytes(cabecalho + b"\r\n" + corpo, policy=email.policy.default)
                flags = b" ".join(p[0] if isinstance(p, tuple) else p for p in partes if isinstance(p, (tuple, bytes)))
                mails.append(Mail(
                    id=f"{self.name}:{uid.decode()}", conta=self.name,
                    remetente=_decodificar(msg.get("From")), assunto=_decodificar(msg.get("Subject")) or "(sem assunto)",
                    data=msg.get("Date", ""), previa=_previa(msg), nao_lido=b"\\Seen" not in flags,
                    lista=msg.get("List-Unsubscribe") is not None))
            return mails
        except (imaplib.IMAP4.error, OSError) as exc:
            raise MailError(f"IMAP {self.conf['apelido']}: falha ao ler ({type(exc).__name__})") from None
        finally:
            try:
                box.logout()
            except Exception:
                pass

    def apply_category(self, native_ids: list[str], category: str) -> None:
        raise MailError("contas IMAP são somente leitura: a Jarvis não marca e-mails nelas")
