"""Skill de criar sistemas "pensando": planeja os arquivos, escreve um por vez e confere cada um antes de propor.

Fluxo (cada passo é uma conversa curta com o modelo local, que é pequeno e erra menos em tarefas pequenas):
1. Plano: o modelo lista os arquivos (caminho: o que faz). Para Python, o conhecimento curado entra no prompt.
2. Cada arquivo: o modelo escreve só o conteúdo. Python é compilado, JSON é lido e JavaScript passa por `node --check`;
   se falhar, o erro volta ao modelo para corrigir (até 2 vezes).
3. O resultado vira um CARTÃO de aprovação com a lista de arquivos; nada é gravado antes de o usuário aprovar.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from jarvis.llm import arquivos as seguro
from jarvis.llm import contexto

Conversa = Callable[[list[dict]], str]
TENTATIVAS = 3
_LINHA_PLANO = re.compile(r"^[\s>*\-\d.)]*`?([\w][\w./\\-]*\.\w{1,5})`?\s*[:\-–—]\s*(.+)$")
_BLOCO = re.compile(r"```[\w+\-]*\n(.*?)```", re.S)


@dataclass
class Resultado:
    arquivos: dict[str, str] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)


def extrair_codigo(resposta: str) -> str:
    """O conteúdo do primeiro bloco ``` da resposta (ou a resposta inteira, sem cercas soltas)."""
    achado = _BLOCO.search(resposta)
    if achado:
        return achado.group(1).strip("\n")
    return re.sub(r"^```[\w+\-]*\n?|\n?```$", "", resposta.strip()).strip("\n")


def interpretar_plano(texto: str, limite: int = 8) -> list[tuple[str, str]]:
    plano: list[tuple[str, str]] = []
    for linha in texto.splitlines():
        achado = _LINHA_PLANO.match(linha.strip())
        if not achado:
            continue
        try:
            caminho = seguro.caminho_seguro(achado[1])
        except ValueError:
            continue
        if caminho.lower() != "readme.md" and caminho not in dict(plano):
            plano.append((caminho, achado[2].strip()))
    return plano[:limite]


def conferir(caminho: str, conteudo: str) -> str | None:
    """None se o arquivo parece válido; senão, o erro para devolver ao modelo."""
    if not conteudo.strip():
        return "o arquivo ficou vazio"
    sufixo = Path(caminho).suffix.lower()
    if sufixo == ".py":
        try:
            compile(conteudo, caminho, "exec")
        except SyntaxError as exc:
            return f"erro de sintaxe na linha {exc.lineno}: {exc.msg}"
    elif sufixo == ".json":
        try:
            json.loads(conteudo)
        except ValueError as exc:
            return f"JSON inválido: {exc}"
    elif sufixo == ".js" and (node := shutil.which("node")):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "t.js"
            arquivo.write_text(conteudo, encoding="utf-8")
            saida = subprocess.run([node, "--check", str(arquivo)], capture_output=True, text=True, timeout=30)
            if saida.returncode:
                return "erro de sintaxe JavaScript: " + saida.stderr.strip().splitlines()[-1][:200]
    return None


def planejar(descricao: str, conversa: Conversa, sistema: str) -> list[tuple[str, str]]:
    pedido = (f"Projeto: {descricao}\n\nListe os arquivos necessários (no máximo 7, simples, com testes se for Python). "
              "Uma linha por arquivo no formato `caminho: o que faz`. Sem explicações e sem README.")
    plano = interpretar_plano(conversa([{"role": "system", "content": sistema}, {"role": "user", "content": pedido}]))
    if not plano:
        raise ValueError("o modelo não conseguiu planejar os arquivos; descreva o sistema com mais detalhes")
    return plano


def escrever_arquivo(caminho: str, funcao: str, descricao: str, plano: list[tuple[str, str]], prontos: dict[str, str],
                     conversa: Conversa, sistema: str) -> tuple[str, str | None]:
    """(conteúdo, aviso). O aviso só existe se, mesmo após as tentativas, o arquivo continuou com problema."""
    visao = "\n".join(f"- {c}: {f}" for c, f in plano)
    contexto_prontos = "\n\n".join(f"Arquivo {c}:\n{t[:600]}" for c, t in list(prontos.items())[-2:])
    mensagens = [{"role": "system", "content": sistema},
                 {"role": "user", "content": f"Projeto: {descricao}\nArquivos do projeto:\n{visao}\n\n{contexto_prontos}\n\n"
                                             f"Escreva o arquivo {caminho} ({funcao}). Responda SÓ com o conteúdo, dentro de um bloco de código."}]
    erro = None
    for _ in range(TENTATIVAS):
        conteudo = extrair_codigo(conversa(mensagens))
        erro = conferir(caminho, conteudo)
        if erro is None:
            return conteudo, None
        mensagens += [{"role": "assistant", "content": f"```\n{conteudo}\n```"},
                      {"role": "user", "content": f"O arquivo tem um problema: {erro}. Corrija e envie o arquivo completo de novo, em um bloco de código."}]
    return conteudo, f"{caminho}: {erro} (revise antes de usar)"


def readme(nome: str, descricao: str, plano: list[tuple[str, str]]) -> str:
    itens = "\n".join(f"- `{c}`: {f}" for c, f in plano)
    return (f"# {nome}\n\n{descricao}\n\n## Arquivos\n{itens}\n\n"
            "> Gerado pela Jarvis com o modelo local. Leia o código e rode os testes antes de confiar nele.\n")


def criar(nome: str, descricao: str, conversa: Conversa, cfg=None, on_status: Callable[[str], None] | None = None) -> Resultado:
    dito = on_status or (lambda _: None)
    sistema = contexto.sistema("", descricao, cfg)
    dito("Planejando os arquivos…")
    plano = planejar(descricao, conversa, sistema)
    resultado = Resultado()
    for i, (caminho, funcao) in enumerate(plano, 1):
        dito(f"Escrevendo {caminho} ({i} de {len(plano)})…")
        conteudo, aviso = escrever_arquivo(caminho, funcao, descricao, plano, resultado.arquivos, conversa, sistema)
        resultado.arquivos[caminho] = conteudo
        if aviso:
            resultado.avisos.append(aviso)
    resultado.arquivos["README.md"] = readme(nome, descricao, plano)
    seguro.validar(resultado.arquivos)
    return resultado
