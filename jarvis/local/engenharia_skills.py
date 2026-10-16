"""Engenharia, arquitetura e UI/UX no motor próprio (sem IA): padrões de projeto, ferramentas de design e geradores.

Tudo calculado ou lido da base curada de jarvis/dev; nada é escrito em disco: os geradores devolvem o texto
para o usuário copiar ou pedir ao Claude Code para salvar.
"""

from __future__ import annotations

import re

from jarvis.dev import engenharia, gerar, logica, saber, topicos
from jarvis.dev.ux import cores

_COR = r"#?[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?"
_DUAS_CORES = re.compile(rf"(?<![\w#])({_COR})(?!\w)\D+?(?<![\w#])({_COR})(?!\w)")
_UMA_COR = re.compile(rf"(?<![\w])(#[0-9a-fA-F]{{3}}(?:[0-9a-fA-F]{{3}})?|[0-9a-fA-F]{{6}})(?!\w)")
_SQL_TIPOS = "texto|inteiro|numero|decimal|data|booleano|bool"


def explicar(tema: str, linguagem: str = "python") -> str | None:
    """Tópico de engenharia, arquitetura, UX, padrão ou algoritmo; None se não for algo que eu tenha na base."""
    return saber.explicar(tema, linguagem)


def comparar(texto: str) -> str | None:
    achados = [item for tipo, item in saber.citados(texto) if tipo != "logica"]
    if len(achados) >= 2:
        return topicos.comparar(achados[0], achados[1])
    return None


def padrao(texto: str) -> str:
    achado = engenharia.padrao(texto)
    if achado:
        return engenharia.mostrar_padrao(achado, logica.language_in(texto))
    return explicar("padroes de projeto") + "\n\n" + engenharia.visao_padroes() + "\n\nPeça por exemplo: \"mostre o padrão Observer em JavaScript\"."


def ux_ferramenta(texto: str) -> str:
    baixo = texto.lower()
    try:
        if "contraste" in baixo:
            duas = _DUAS_CORES.search(texto)
            if not duas:
                return "Diga as duas cores, por exemplo: \"contraste #767676 sobre #ffffff\"."
            return cores.avaliar_contraste(duas[1], duas[2])
        uma = _UMA_COR.search(texto)
        if "token" in baixo and uma:
            return "```css\n" + cores.tokens_css(uma[1]) + "\n```"
        if "paleta" in baixo:
            return cores.relatorio_paleta(uma[1]) if uma else "Diga a cor base, por exemplo: \"paleta a partir de #3b82f6\"."
        return cores.relatorio_escala()
    except ValueError as exc:
        return f"Não consegui: {exc}"


def _campos(trecho: str) -> dict[str, str]:
    campos = {}
    for parte in re.split(r"\s*(?:,|\be\b)\s*", trecho.strip()):
        palavras = parte.split()
        if palavras:
            tipo = palavras[1] if len(palavras) > 1 and re.fullmatch(_SQL_TIPOS, palavras[1], re.I) else "texto"
            campos[palavras[0]] = tipo
    return campos


def gerar_artefato(texto: str) -> str:
    baixo = texto.lower()
    try:
        if re.search(r"\b(tabela|esquema sql)\b", baixo):
            achado = re.search(r"(?:tabela|esquema sql)\s+(?:de\s+|do\s+|da\s+)?(?P<t>\w+)(?:\s+com\s+(?P<c>.+))?", texto, re.I)
            if not achado:
                return "Diga a tabela e os campos, por exemplo: \"crie uma tabela clientes com nome texto, idade inteiro\"."
            return "```sql\n" + gerar.esquema_sql(achado["t"], _campos(achado["c"] or "")) + "\n```"
        if re.search(r"\b(adr|decisao de arquitetura|registro de decisao)\b", baixo):
            titulo = re.sub(r"^.*?\b(adr|decisao de arquitetura|registro de decisao)\b\s*(?:sobre|para|de|:)?\s*", "", texto, flags=re.I).strip() or "Título da decisão"
            return "```markdown\n" + gerar.adr(titulo, "Descreva o problema e as restrições.", "Descreva o que foi decidido.") + "\n```"
        if re.search(r"\bhistoria de usuario\b", baixo):
            return gerar.historia_usuario("usuário", "realizar a ação desejada", "alcançar o objetivo")
        if re.search(r"\b(openapi|swagger)\b", baixo):
            recursos = re.findall(r"\b(?:de|para|com)\s+(\w+)", baixo.split("openapi")[-1].split("swagger")[-1]) or ["itens"]
            return "```yaml\n" + gerar.openapi("API", recursos) + "```"
        if re.search(r"\b(workflow|pipeline|ci)\b", baixo):
            return "```yaml\n" + gerar.workflow_ci(logica.language_in(texto, "python")) + "```"
        if "dockerfile" in baixo:
            return "```dockerfile\n" + gerar.dockerfile(logica.language_in(texto, "python")) + "```"
        if "editorconfig" in baixo:
            return "```ini\n" + gerar.editorconfig() + "```"
    except ValueError as exc:
        return f"Não consegui gerar: {exc}"
    return "Posso gerar: tabela SQL, ADR, história de usuário, OpenAPI, workflow de CI, Dockerfile e .editorconfig."
