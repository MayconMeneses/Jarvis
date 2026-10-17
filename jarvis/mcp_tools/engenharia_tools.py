"""Engenharia de software, arquitetura, sistemas e UI/UX: tópicos, padrões de projeto, ferramentas de design e geradores."""

from __future__ import annotations

from jarvis.dev import gerar, logica, saber
from jarvis.dev.ux import cores
from jarvis.mcp_tools.core import server


@server.tool()
def explicar_topico_de_engenharia(nome: str, linguagem: str = "python") -> str:
    """Explica um tópico de engenharia de software, arquitetura, sistemas ou UI/UX (SOLID, DDD, hexagonal, microsserviços,
    CI/CD, observabilidade, cache, CAP, 12-factor, heurísticas de Nielsen, acessibilidade WCAG, tipografia, design system...)
    ou mostra um padrão de projeto (Strategy, Observer, Factory, Decorator, Adapter, Repository, Command, Builder) em
    Python ou JavaScript. Base curada e offline."""
    texto = saber.explicar(nome, logica.language_in(linguagem, "python") if linguagem else "python")
    return texto or f"Não tenho \"{nome}\". " + saber.resumo()


@server.tool()
def listar_o_que_a_jarvis_sabe() -> str:
    """Lista os conceitos de lógica, os tópicos de engenharia/arquitetura/sistemas, os padrões de projeto e os tópicos de UX."""
    return saber.resumo()


@server.tool()
def avaliar_contraste(cor_do_texto: str, cor_do_fundo: str) -> str:
    """Calcula o contraste WCAG entre duas cores hexadecimais (#rgb ou #rrggbb) e diz se passa em AA e AAA."""
    try:
        return cores.avaliar_contraste(cor_do_texto, cor_do_fundo)
    except ValueError as exc:
        return str(exc)


@server.tool()
def gerar_tokens_de_design(cor_principal: str, tamanho_base_px: float = 16, razao: float = 1.25) -> str:
    """Gera variáveis CSS (paleta de 10 tons, escala tipográfica, espaçamentos, tema escuro e movimento reduzido) a partir de uma cor."""
    try:
        return cores.tokens_css(cor_principal, tamanho_base_px, razao)
    except ValueError as exc:
        return str(exc)


@server.tool()
def gerar_artefato(tipo: str, nome: str = "item", detalhes: str = "") -> str:
    """Gera um artefato de engenharia em texto: 'sql' (tabela; detalhes "campo tipo, campo tipo"), 'adr' (nome = título),
    'historia' (detalhes "papel|quero|para"), 'openapi' (detalhes = recursos separados por vírgula), 'ci' (nome = python|node|go),
    'dockerfile' (nome = python|node) ou 'editorconfig'. Não grava nada em disco."""
    try:
        if tipo == "sql":
            campos = {}
            for parte in filter(None, (p.strip() for p in detalhes.split(","))):
                palavras = parte.split()
                campos[palavras[0]] = palavras[1] if len(palavras) > 1 else "texto"
            return gerar.esquema_sql(nome, campos)
        if tipo == "adr":
            return gerar.adr(nome, "Descreva o problema e as restrições.", "Descreva o que foi decidido.")
        if tipo == "historia":
            papel, quero, para = (detalhes.split("|") + ["", "", ""])[:3]
            return gerar.historia_usuario(papel or "usuário", quero or "realizar a ação", para or "alcançar o objetivo")
        if tipo == "openapi":
            return gerar.openapi(nome, [r.strip() for r in detalhes.split(",") if r.strip()] or ["itens"])
        if tipo == "ci":
            return gerar.workflow_ci(nome)
        if tipo == "dockerfile":
            return gerar.dockerfile(nome)
        if tipo == "editorconfig":
            return gerar.editorconfig()
    except ValueError as exc:
        return str(exc)
    return "Tipos: sql, adr, historia, openapi, ci, dockerfile, editorconfig."


@server.tool()
def revisar_codigo(texto: str) -> str:
    """Revisa um diff (git diff) ou um trecho de código colado, sem executar nada: aponta execução dinâmica, SQL montado com texto,
    shell perigoso, segredos no código, exceções engolidas, HTML sem filtro, pendências esquecidas, código sem teste e diffs grandes,
    com arquivo, linha e o que fazer. Em diff, só as linhas adicionadas são julgadas."""
    from jarvis.dev import revisao

    return revisao.relatorio(texto)
