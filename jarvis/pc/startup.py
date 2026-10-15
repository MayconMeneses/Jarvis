"""Programas que iniciam com o Windows.

Desativar usa o mesmo mecanismo do Gerenciador de Tarefas (chave
StartupApproved): o programa continua instalado e pode ser reativado em
Gerenciador de Tarefas > Aplicativos de inicialização. Só itens do usuário atual
(HKCU e pasta Inicializar do usuário) podem ser desativados sem administrador.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_WOW = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
DISABLED_FLAG = bytes([3]) + bytes(11)


class Registry(Protocol):
    def values(self, hive: str, path: str) -> dict[str, object]: ...
    def set_binary(self, hive: str, path: str, name: str, data: bytes) -> None: ...


class WinRegistry:
    def _root(self, hive: str):
        import winreg

        return {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}[hive]

    def values(self, hive: str, path: str) -> dict[str, object]:
        import winreg

        result: dict[str, object] = {}
        try:
            with winreg.OpenKey(self._root(hive), path) as key:
                i = 0
                while True:
                    try:
                        name, value, _kind = winreg.EnumValue(key, i)
                    except OSError:
                        break
                    result[name] = value
                    i += 1
        except OSError:
            pass
        return result

    def set_binary(self, hive: str, path: str, name: str, data: bytes) -> None:
        import winreg

        with winreg.CreateKeyEx(self._root(hive), path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, data)


@dataclass
class StartupItem:
    nome: str
    comando: str
    origem: str  # "usuario" ou "todos_usuarios"
    ativo: bool
    approved_hive: str
    approved_path: str

    @property
    def pode_desativar(self) -> bool:
        return self.origem == "usuario"

    def to_dict(self) -> dict:
        data = asdict(self)
        del data["approved_hive"], data["approved_path"]
        data["pode_desativar"] = self.pode_desativar
        return data


def _is_enabled(approved: dict[str, object], name: str) -> bool:
    flag = approved.get(name)
    if not isinstance(flag, (bytes, bytearray)) or not flag:
        return True  # sem registro de aprovação = ativo
    return flag[0] % 2 == 0  # 02/06 ativo, 03/07 desativado


def _startup_folders() -> list[tuple[str, str, Path]]:
    appdata = os.environ.get("APPDATA", "")
    programdata = os.environ.get("ProgramData", "")
    tail = Path("Microsoft/Windows/Start Menu/Programs/Startup")
    return [("usuario", "HKCU", Path(appdata) / tail), ("todos_usuarios", "HKLM", Path(programdata) / tail)]


def list_items(reg: Registry | None = None, folders=None) -> list[StartupItem]:
    reg = reg or WinRegistry()
    items: list[StartupItem] = []
    sources = [
        ("usuario", "HKCU", RUN, "Run"),
        ("todos_usuarios", "HKLM", RUN, "Run"),
        ("todos_usuarios", "HKLM", RUN_WOW, "Run32"),
    ]
    for origem, hive, path, approved_name in sources:
        approved_path = f"{APPROVED}\\{approved_name}"
        approved = reg.values(hive, approved_path)
        for name, command in reg.values(hive, path).items():
            items.append(StartupItem(name, str(command), origem, _is_enabled(approved, name), hive, approved_path))

    for origem, hive, folder in (folders if folders is not None else _startup_folders()):
        if not folder.is_dir():
            continue
        approved_path = f"{APPROVED}\\StartupFolder"
        approved = reg.values(hive, approved_path)
        for entry in folder.iterdir():
            if entry.name.lower() == "desktop.ini":
                continue
            items.append(StartupItem(entry.name, str(entry), origem, _is_enabled(approved, entry.name), hive, approved_path))
    return items


def find_disableable(name: str, reg: Registry | None = None, folders=None) -> StartupItem:
    matches = [i for i in list_items(reg, folders) if i.nome.lower() == name.strip().lower()]
    if not matches:
        raise ValueError(f"programa de inicialização '{name}' não encontrado")
    item = matches[0]
    if not item.pode_desativar:
        raise ValueError(
            f"'{item.nome}' vale para todos os usuários e exige administrador; "
            "desative em Gerenciador de Tarefas > Aplicativos de inicialização"
        )
    if not item.ativo:
        raise ValueError(f"'{item.nome}' já está desativado")
    return item


def disable(name: str, reg: Registry | None = None, folders=None) -> str:
    reg = reg or WinRegistry()
    item = find_disableable(name, reg, folders)
    reg.set_binary(item.approved_hive, item.approved_path, item.nome, DISABLED_FLAG)
    return (
        f"'{item.nome}' não vai mais iniciar com o Windows. Para reativar: "
        "Gerenciador de Tarefas > Aplicativos de inicialização."
    )
