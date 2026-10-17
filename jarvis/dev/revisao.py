"""Revisão de código e de diffs (sem IA): lê só o que foi colado, acha problemas conhecidos e diz o que fazer.

Aceita um diff unificado (revisa só as linhas ADICIONADAS) ou um trecho de código. Não executa nada nem altera arquivos.
São sinais para a revisão, não um veredito: confirme cada achado lendo o código.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from jarvis.dev.habilidades.checagens import _PLACEHOLDER, _SEGREDOS

ALTA, MEDIA, BAIXA = "alta", "média", "baixa"
LIMITE_LINHA = 140
LIMITE_DIFF = 400


@dataclass
class Achado:
    gravidade: str
    arquivo: str
    linha: int
    regra: str
    sugestao: str
    trecho: str


# (regex, gravidade, regra, sugestão). Padrões de risco montados por partes para este próprio arquivo não ser acusado.
_RISCOS = [
    (re.compile(r"\b(eval|ex" + r"ec)\s*\("), ALTA, "Execução de código dinâmico",
     "Evite eval/exec; use um parser (json.loads, ast.literal_eval) ou uma tabela de funções permitidas."),
    (re.compile(r"shell\s*=\s*True"), ALTA, "Comando de shell montado como texto",
     "Passe uma lista de argumentos e shell=False, para o texto do usuário não virar comando."),
    (re.compile(r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false"), ALTA, "Verificação de certificado desligada",
     "Mantenha a verificação TLS ligada; trate o certificado em vez de ignorá-lo."),
    (re.compile(r"(?i)\bf[\"'][^\"'\n]*\b(select\b.*\bfrom|insert\s+into|update\s+\w+\s+set|delete\s+from)\b"
                r"|\b(select\b.*\bfrom|insert\s+into|delete\s+from)\b[^\n]*([\"']\s*\+\s*\w|\.format\(|[\"']\s*%\s*\w)"), ALTA, "SQL montado com texto",
     "Use consultas parametrizadas (?, %s ou :nome) em vez de juntar o valor no texto da consulta."),
    (re.compile(r"\.innerHTML\s*=|document\.write\s*\(|dangerouslySetInnerHTML"), MEDIA, "HTML inserido sem filtro",
     "Use textContent ou crie os elementos pelo DOM; HTML de fora pode carregar script (XSS)."),
    (re.compile(r"^\s*except\s*:\s*$|except\s+Exception\s*:\s*(pass)?\s*$"), MEDIA, "Exceção engolida",
     "Capture o erro específico e registre ou trate; um except vazio esconde defeitos."),
    (re.compile(r"(?i)(password|senha|token|secret)\w*\s*[,)]?\s*[\"'].*%s|log\w*\.\w+\(.*(password|senha|token)"), MEDIA, "Possível dado sensível no log",
     "Nunca registre senhas, tokens ou chaves; registre só identificadores."),
    (re.compile(r"\b(breakpoint\(\)|pdb\.set_trace|debugger;)"), MEDIA, "Depurador esquecido", "Remova a parada de depuração antes de integrar."),
    (re.compile(r"\b(TODO|FIXME|XXX|HACK)\b"), BAIXA, "Pendência marcada", "Resolva ou transforme em uma tarefa rastreável antes de integrar."),
    (re.compile(r"^\s*(print\(|console\.log\()"), BAIXA, "Saída de depuração", "Use o sistema de logs (logging/console.error) ou remova."),
]
_ARQUIVO = re.compile(r"^\+\+\+ (?:b/)?(.+?)(?:\t.*)?$")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")
_TESTE = re.compile(r"(^|/)(tests?|__tests__|spec)/|test_[^/]*\.py$|_test\.(py|go)$|\.(test|spec)\.[jt]sx?$")
_CODIGO = re.compile(r"\.(py|js|jsx|ts|tsx|go|java|cs|php|rb|rs|kt)$")


def _linhas_adicionadas(texto: str) -> tuple[list[tuple[str, int, str]], set[str]]:
    """[(arquivo, nº da linha, conteúdo)] e o conjunto de arquivos do diff; para código solto, tudo conta como adicionado."""
    if not any(l.startswith(("@@", "+++ ")) for l in texto.splitlines()):
        return [("trecho", n, l) for n, l in enumerate(texto.splitlines(), 1)], set()
    adicionadas, arquivos, arquivo, numero = [], set(), "?", 0
    for linha in texto.splitlines():
        if (m := _ARQUIVO.match(linha)):
            arquivo = m[1]
            arquivos.add(arquivo)
        elif (m := _HUNK.match(linha)):
            numero = int(m[1])
        elif linha.startswith("+") and not linha.startswith("+++"):
            adicionadas.append((arquivo, numero, linha[1:]))
            numero += 1
        elif not linha.startswith(("-", "\\")):
            numero += 1
    return adicionadas, arquivos


def revisar(texto: str) -> tuple[list[Achado], dict]:
    linhas, arquivos = _linhas_adicionadas(texto)
    achados: list[Achado] = []
    for arquivo, numero, conteudo in linhas:
        for regex, gravidade, regra, sugestao in _RISCOS:
            if regex.search(conteudo):
                achados.append(Achado(gravidade, arquivo, numero, regra, sugestao, conteudo.strip()[:100]))
        if any(r.search(conteudo) for r in _SEGREDOS) and not _PLACEHOLDER.search(conteudo):
            achados.append(Achado(ALTA, arquivo, numero, "Possível segredo no código",
                                  "Tire a chave do código: use variável de ambiente ou cofre, e troque a chave se ela já foi enviada.", "(valor oculto)"))
        if len(conteudo) > LIMITE_LINHA:
            achados.append(Achado(BAIXA, arquivo, numero, f"Linha com {len(conteudo)} caracteres", "Quebre a linha ou extraia uma função.", conteudo.strip()[:60] + "…"))
    resumo = {"adicionadas": len(linhas), "arquivos": sorted(arquivos)}
    if arquivos:
        codigo = [a for a in arquivos if _CODIGO.search(a) and not _TESTE.search(a)]
        if codigo and not any(_TESTE.search(a) for a in arquivos):
            achados.append(Achado(MEDIA, "(diff)", 0, "Código alterado sem teste", "Inclua ou atualize um teste que cubra a mudança.", ", ".join(codigo[:3])))
        if len(linhas) > LIMITE_DIFF:
            achados.append(Achado(BAIXA, "(diff)", 0, f"Diff grande ({len(linhas)} linhas adicionadas)",
                                  "Mudanças pequenas são revisadas melhor: divida em partes com um objetivo cada.", ""))
    ordem = {ALTA: 0, MEDIA: 1, BAIXA: 2}
    return sorted(achados, key=lambda a: (ordem[a.gravidade], a.arquivo, a.linha)), resumo


def relatorio(texto: str) -> str:
    achados, resumo = revisar(texto)
    cabeca = (f"**Revisão do diff** ({len(resumo['arquivos'])} arquivo(s), {resumo['adicionadas']} linhas adicionadas)" if resumo["arquivos"]
              else f"**Revisão do trecho** ({resumo['adicionadas']} linhas)")
    if not achados:
        return cabeca + "\nNão achei problemas conhecidos nas regras que eu verifico. Isso não substitui ler o código: confira a lógica, os casos de borda e os testes."
    marca = {ALTA: "🔴", MEDIA: "🟠", BAIXA: "⚪"}
    linhas = [cabeca, f"{len(achados)} ponto(s) para olhar:"]
    for a in achados[:25]:
        onde = f"{a.arquivo}:{a.linha}" if a.linha else a.arquivo
        linhas.append(f"- {marca[a.gravidade]} **{a.regra}** ({a.gravidade}) em `{onde}`" + (f": `{a.trecho}`" if a.trecho else "") + f"\n  → {a.sugestao}")
    if len(achados) > 25:
        linhas.append(f"- … e mais {len(achados) - 25} ponto(s).")
    linhas.append("\n_São sinais automáticos, não um veredito: confirme cada um lendo o código._")
    return "\n".join(linhas)
