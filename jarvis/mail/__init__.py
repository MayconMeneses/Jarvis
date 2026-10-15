"""E-mail da Jarvis: Gmail e Outlook com a mesma interface."""

from __future__ import annotations

from collections import defaultdict

from jarvis.config import Config
from jarvis.mail.base import CATEGORIES, Mail, MailAccount, MailError, split_id
from jarvis.mail.rules import annotate


def accounts(cfg: Config) -> dict[str, MailAccount]:
    found: dict[str, MailAccount] = {}
    if cfg.email.gmail_ativo:
        from jarvis.mail.gmail import GmailAccount

        found["gmail"] = GmailAccount()
    if cfg.email.outlook_ativo:
        from jarvis.mail.outlook import OutlookAccount

        found["outlook"] = OutlookAccount(cfg.email.outlook_client_id, cfg.email.outlook_authority)
    return found


def recent(cfg: Config, limit: int = 20, unread_only: bool = False, found=None) -> dict:
    """E-mails recentes de todas as contas ativas, anotados com regras e alertas."""
    found = accounts(cfg) if found is None else found
    limit = max(1, min(int(limit), 50))
    result: dict = {"emails": [], "avisos": []}
    if not found:
        result["avisos"].append(
            "Nenhuma conta de e-mail conectada. Conecte com: python -m jarvis --conectar gmail "
            "(ou outlook)."
        )
    for name, account in found.items():
        try:
            mails = account.list_recent(limit, unread_only)
        except MailError as exc:
            result["avisos"].append(f"{name}: {exc}")
            continue
        result["emails"] += [annotate(m, cfg.email.regras) for m in mails]
    return result


def validate_items(items: list[dict], active: set[str]) -> list[dict]:
    clean = []
    for item in items:
        account, _ = split_id(str(item.get("id", "")))
        if account not in active:
            raise ValueError(f"a conta {account} não está conectada")
        if item.get("categoria") not in CATEGORIES:
            raise ValueError(f"categoria inválida: {item.get('categoria')!r}. Use uma de: {', '.join(CATEGORIES)}")
        clean.append({"id": item["id"], "categoria": item["categoria"]})
    if not clean:
        raise ValueError("nenhum e-mail informado")
    return clean


def organize(cfg: Config, items: list[dict], found=None) -> str:
    """Aplica as categorias aprovadas pelo usuário. Só adiciona marcadores."""
    found = accounts(cfg) if found is None else found
    items = validate_items(items, set(found))
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for item in items:
        account, native = split_id(item["id"])
        groups[(account, item["categoria"])].append(native)
    done, errors = 0, []
    for (account, category), natives in groups.items():
        try:
            found[account].apply_category(natives, category)
            done += len(natives)
        except MailError as exc:
            errors.append(f"{account}/{category}: {exc}")
    summary = f"{done} e-mail(s) marcados."
    return summary + (" Falhas: " + "; ".join(errors) if errors else "")


__all__ = ["CATEGORIES", "Mail", "MailAccount", "MailError", "accounts", "organize", "recent"]
