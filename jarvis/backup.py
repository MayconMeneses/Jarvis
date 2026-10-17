"""Cópia de segurança CRIPTOGRAFADA da memória, no mesmo formato do app do celular (movel/js/cripto.js).

Só sai do aparelho quando o usuário pede e escolhe onde guardar. O arquivo é protegido por uma senha que só o usuário sabe:
AES-256-GCM, com a chave derivada da senha por PBKDF2-HMAC-SHA256 (600 mil iterações, sal e nonce aleatórios). Sem a senha
(que a Jarvis nunca guarda nem registra) o conteúdo não abre. Senha perdida = cópia perdida.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

FORMATO = "jarvis-backup-1"
FORMATO_MEMORIA = "jarvis-movel-1"  # o mesmo do app do celular: notas com ref, titulo, tipo, corpo, criada, atualizada
ITERACOES = 600_000
MIN_SENHA = 8


def _chave(senha: str, sal: bytes, iteracoes: int) -> bytes:
    return PBKDF2HMAC(hashes.SHA256(), 32, sal, iteracoes).derive(senha.encode("utf-8"))


def _b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode("ascii")


def cifrar(texto: str, senha: str, iteracoes: int = ITERACOES) -> str:
    if len(senha) < MIN_SENHA:
        raise ValueError(f"use uma senha de pelo menos {MIN_SENHA} caracteres")
    sal, nonce = os.urandom(16), os.urandom(12)
    dados = AESGCM(_chave(senha, sal, iteracoes)).encrypt(nonce, texto.encode("utf-8"), None)
    return json.dumps({"formato": FORMATO, "kdf": "PBKDF2-SHA256", "iteracoes": iteracoes, "sal": _b64(sal), "nonce": _b64(nonce), "dados": _b64(dados)})


def eh_cifrado(conteudo: str) -> bool:
    try:
        return json.loads(conteudo).get("formato") == FORMATO
    except (ValueError, AttributeError):
        return False


def decifrar(conteudo: str, senha: str) -> str:
    try:
        c = json.loads(conteudo)
        if c.get("formato") != FORMATO or not 1 <= int(c["iteracoes"]) <= 5_000_000:
            raise ValueError("arquivo de cópia inválido")
        chave = _chave(senha, base64.b64decode(c["sal"]), int(c["iteracoes"]))
        return AESGCM(chave).decrypt(base64.b64decode(c["nonce"]), base64.b64decode(c["dados"]), None).decode("utf-8")
    except InvalidTag as exc:
        raise ValueError("senha incorreta ou arquivo alterado") from exc
    except (KeyError, TypeError, ValueError, base64.binascii.Error) as exc:
        raise ValueError("arquivo de cópia inválido") from exc


def memoria_para_texto(mem) -> tuple[str, int]:
    """Todas as notas da memória no formato compartilhado com o celular."""
    notas = []
    for n in mem.list_notes(limit=100_000):
        corpo = mem.get(n["ref"]) or ""
        notas.append({"ref": n["ref"], "titulo": n["ref"].rsplit("/", 1)[-1], "tipo": n["tipo"], "corpo": corpo, "criada": n["criado"], "atualizada": n["atualizado"]})
    texto = json.dumps({"formato": FORMATO_MEMORIA, "exportado": datetime.now().isoformat(timespec="seconds"), "notas": notas, "meta": {}}, ensure_ascii=False)
    return texto, len(notas)


def importar_texto(mem, texto: str) -> tuple[int, int]:
    """Funde as notas da cópia na memória: a versão mais recente de cada nota vence. Devolve (novas, atualizadas)."""
    dados = json.loads(texto)
    if dados.get("formato") != FORMATO_MEMORIA or not isinstance(dados.get("notas"), list):
        raise ValueError("a cópia não está no formato da Jarvis")
    atuais = {n["ref"]: n["atualizado"] for n in mem.list_notes(limit=100_000)}
    novas = atualizadas = 0
    for n in dados["notas"]:
        ref = str(n["ref"])[:120]
        depois = str(n.get("atualizada", ""))
        if ref in atuais and (depois <= atuais[ref] or mem.get(ref) == n["corpo"]):
            continue
        mem.put(ref, str(n["corpo"]), str(n.get("tipo", "nota")), title=str(n.get("titulo", "")), created=str(n.get("criada", "")), updated=depois)
        novas, atualizadas = (novas + 1, atualizadas) if ref not in atuais else (novas, atualizadas + 1)
    return novas, atualizadas


def exportar_arquivo(mem, caminho: str, senha: str, iteracoes: int = ITERACOES) -> int:
    texto, total = memoria_para_texto(mem)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(cifrar(texto, senha, iteracoes))
    return total


def importar_arquivo(mem, caminho: str, senha: str) -> tuple[int, int]:
    with open(caminho, encoding="utf-8") as f:
        conteudo = f.read()
    return importar_texto(mem, decifrar(conteudo, senha) if eh_cifrado(conteudo) else conteudo)
