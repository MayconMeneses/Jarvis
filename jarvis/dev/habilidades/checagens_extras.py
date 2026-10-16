"""Checagens automáticas (heurísticas, sem IA): automação, logs, acessibilidade e organização do projeto."""

from __future__ import annotations

import re

from jarvis.dev.habilidades.base import Resultado, codigo_de, limitar
from jarvis.dev.habilidades.varredura import Projeto, eh_modelo


def automacao(p: Projeto) -> Resultado:
    nota, achados, ajuda = 0, [], []
    ci = any(a.startswith(".github/workflows/") for a in p.arquivos) or p.existe(".gitlab-ci.yml") or p.existe("azure-pipelines.yml") or p.existe("Jenkinsfile")
    if ci:
        nota += 60
        achados.append("Integração contínua configurada.")
    else:
        ajuda.append("Crie uma integração contínua (ex.: GitHub Actions) que rode os testes a cada push.")
    if any(a.lower() in ("dockerfile", "docker-compose.yml", "compose.yaml") for a in p.arquivos):
        nota += 20
        achados.append("Dockerfile/compose presente.")
    if any(a.lower() in ("makefile", "justfile") or a.lower().endswith((".ps1", ".sh")) and "/" not in a for a in p.arquivos):
        nota += 20
        achados.append("Script de automação na raiz.")
    return Resultado(limitar(nota), achados or ["Nenhuma automação encontrada."], ajuda)


def observabilidade(p: Projeto) -> Resultado:
    codigo = codigo_de(p)
    if not codigo:
        return Resultado(None, ["Nenhum código-fonte encontrado."])
    juntos = "\n".join(codigo.values())
    com_log = bool(re.search(r"import logging|logging\.getLogger|console\.(error|warn)|from loguru|\blog\.(Printf|Println)|ILogger", juntos))
    prints = len(re.findall(r"^\s*print\(", juntos, re.M))
    tratamento = len(re.findall(r"\btry\s*:|\btry\s*\{|\bcatch\b|\bexcept\b", juntos))
    nota, achados, ajuda = 0, [], []
    if com_log:
        nota += 60
        achados.append("Usa logging com níveis.")
    else:
        ajuda.append("Use logging (com níveis e contexto) em vez de print para registrar o que acontece.")
    if tratamento:
        nota += 40 if tratamento >= 3 else 20
        achados.append(f"{tratamento} ponto(s) de tratamento de erro.")
    else:
        ajuda.append("Trate os erros previsíveis (entrada inválida, rede, arquivo) com mensagens úteis.")
    if prints > 20 and not com_log:
        achados.append(f"{prints} print() usados como log.")
    return Resultado(limitar(nota), achados, ajuda)


def acessibilidade(p: Projeto) -> Resultado:
    paginas = [c for c in p.textos if c.endswith(".html") and not eh_modelo(c)]
    paginas = paginas or [c for c in p.textos if c.endswith(".html")]
    if not paginas:
        return Resultado(None, ["Sem páginas HTML: não se aplica."])
    texto = "\n".join(p.textos[c] for c in paginas)
    nota, achados, ajuda = 0, [], []
    if re.search(r"<html[^>]*\blang=", texto, re.I):
        nota += 25
    else:
        ajuda.append("Declare o idioma: <html lang=\"pt-BR\">.")
    if re.search(r"name=[\"']viewport[\"']", texto, re.I):
        nota += 20
    else:
        ajuda.append("Adicione <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> para funcionar no celular.")
    imagens = re.findall(r"<img\b[^>]*>", texto, re.I)
    sem_alt = [i for i in imagens if not re.search(r"\balt=", i, re.I)]
    if not imagens or not sem_alt:
        nota += 30
    else:
        achados.append(f"{len(sem_alt)} imagem(ns) sem texto alternativo (alt).")
        ajuda.append("Toda imagem precisa de alt (vazio se for decorativa).")
    campos = len(re.findall(r"<(input|select|textarea)\b", texto, re.I))
    rotulos = len(re.findall(r"<label\b|aria-label=", texto, re.I))
    if not campos or rotulos >= campos:
        nota += 25
    else:
        achados.append(f"{campos} campo(s) de formulário para {rotulos} rótulo(s).")
        ajuda.append("Dê um <label> ou aria-label a cada campo de formulário.")
    return Resultado(limitar(nota), achados or [f"{len(paginas)} página(s) HTML verificada(s)."], ajuda)


def estrutura(p: Projeto) -> Resultado:
    nota, achados, ajuda = 0, [], []
    manifestos = [m for m in ("pyproject.toml", "requirements.txt", "package.json", "go.mod", "pom.xml", "composer.json", "Gemfile") if p.existe(m)]
    if manifestos:
        nota += 30
        achados.append("Dependências declaradas em " + ", ".join(manifestos) + ".")
    else:
        ajuda.append("Declare as dependências (requirements.txt, pyproject.toml, package.json ou go.mod).")
    if any(p.existe(t) for t in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock", "go.sum", "Pipfile.lock", "composer.lock")):
        nota += 20
    elif manifestos:
        ajuda.append("Trave as versões das dependências (arquivo de lock) para builds repetíveis.")
    pastas = {a.split("/")[0] for a in p.arquivos if "/" in a}
    if pastas & {"src", "app", "lib", "backend", "frontend", "jarvis", "cmd", "internal", "packages"} or len(pastas) >= 2:
        nota += 30
    else:
        ajuda.append("Organize o código em pastas por assunto (src/, tests/, docs/).")
    na_raiz = [a for a in p.arquivos if "/" not in a]
    if len(na_raiz) <= 15:
        nota += 20
    else:
        achados.append(f"{len(na_raiz)} arquivos soltos na raiz.")
        ajuda.append("Deixe a raiz enxuta: mova o que for código para pastas.")
    return Resultado(limitar(nota), achados, ajuda)
