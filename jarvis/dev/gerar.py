"""Geradores de artefatos de engenharia: ADR, história de usuário, esquema SQL, OpenAPI, CI, Dockerfile e .editorconfig.

Texto determinístico a partir de poucos dados; nada é executado nem enviado. O esquema SQL e o OpenAPI são
validados nos testes (sqlite3 e PyYAML).
"""

from __future__ import annotations

import re
from datetime import date

TIPOS_SQL = {"texto": "TEXT", "inteiro": "INTEGER", "numero": "REAL", "decimal": "REAL", "data": "TEXT", "booleano": "INTEGER", "bool": "INTEGER"}


def _id(nome: str) -> str:
    limpo = re.sub(r"\W+", "_", nome.strip().lower(), flags=re.A).strip("_")
    if not limpo or limpo[0].isdigit():
        raise ValueError(f"nome inválido: {nome!r}")
    return limpo


def adr(titulo: str, contexto: str, decisao: str, consequencias: str = "", numero: int = 1) -> str:
    return (f"# ADR {numero:04d}: {titulo}\n\n- **Data:** {date.today().isoformat()}\n- **Status:** proposta\n\n"
            f"## Contexto\n{contexto}\n\n## Decisão\n{decisao}\n\n## Consequências\n{consequencias or 'A preencher: o que melhora, o que piora e o que passa a ser obrigatório.'}\n")


def historia_usuario(papel: str, quero: str, para: str, criterios: list[str] | None = None) -> str:
    criterios = criterios or ["Dado um contexto inicial, quando a ação acontece, então o resultado esperado é visível."]
    itens = "\n".join(f"- [ ] {c}" for c in criterios)
    return f"**Como** {papel}, **quero** {quero}, **para** {para}.\n\n**Critérios de aceite:**\n{itens}\n\n**Definição de pronto:** código revisado, testes passando, documentação atualizada."


def esquema_sql(tabela: str, campos: dict[str, str], relacoes: dict[str, str] | None = None) -> str:
    """CREATE TABLE (SQLite/SQL padrão) com chave primária, campos tipados, chaves estrangeiras e criado_em."""
    nome = _id(tabela)
    linhas = ["  id INTEGER PRIMARY KEY AUTOINCREMENT"]
    for campo, tipo in campos.items():
        linhas.append(f"  {_id(campo)} {TIPOS_SQL.get(tipo.lower(), 'TEXT')}")
    for campo, tabela_pai in (relacoes or {}).items():
        linhas.append(f"  {_id(campo)} INTEGER NOT NULL REFERENCES {_id(tabela_pai)}(id)")
    linhas.append("  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    sql = f"CREATE TABLE {nome} (\n" + ",\n".join(linhas) + "\n);"
    indices = "".join(f"\nCREATE INDEX idx_{nome}_{_id(c)} ON {nome}({_id(c)});" for c in (relacoes or {}))
    return sql + indices


def openapi(titulo: str, recursos: list[str]) -> str:
    """OpenAPI 3 (YAML) com listar/criar/buscar/remover para cada recurso."""
    linhas = ["openapi: 3.0.3", "info:", f"  title: {titulo}", "  version: 0.1.0", "paths:"]
    for recurso in recursos:
        nome = _id(recurso)
        linhas += [f"  /{nome}:", "    get:", f"      summary: Lista {nome}", "      responses:", "        '200': {description: Lista}",
                   "    post:", f"      summary: Cria em {nome}", "      responses:", "        '201': {description: Criado}",
                   "        '422': {description: Dados inválidos}",
                   f"  /{nome}/{{id}}:", "    parameters:", "      - {name: id, in: path, required: true, schema: {type: integer}}",
                   "    get:", f"      summary: Busca em {nome}", "      responses:", "        '200': {description: Encontrado}",
                   "        '404': {description: Não encontrado}",
                   "    delete:", f"      summary: Remove de {nome}", "      responses:", "        '204': {description: Removido}"]
    return "\n".join(linhas) + "\n"


def workflow_ci(linguagem: str = "python") -> str:
    base = {
        "python": ("actions/setup-python@v5", "python-version: '3.11'", "pip install -e .[dev]", "pytest -q"),
        "node": ("actions/setup-node@v4", "node-version: 20", "npm ci", "npm test"),
        "go": ("actions/setup-go@v5", "go-version: '1.22'", "go mod download", "go test ./..."),
    }
    chave = {"javascript": "node", "js": "node", "nodejs": "node", "py": "python", "golang": "go"}.get(linguagem.lower(), linguagem.lower())
    if chave not in base:
        raise ValueError(f"linguagem sem modelo de CI: {linguagem} (use python, node ou go)")
    acao, versao, instalar, testar = base[chave]
    return (f"name: CI\non:\n  push: {{branches: [main]}}\n  pull_request:\njobs:\n  testes:\n    runs-on: ubuntu-latest\n    steps:\n"
            f"      - uses: actions/checkout@v4\n      - uses: {acao}\n        with:\n          {versao}\n"
            f"      - run: {instalar}\n      - run: {testar}\n")


def dockerfile(linguagem: str = "python", porta: int = 8000) -> str:
    chave = {"javascript": "node", "js": "node", "nodejs": "node", "py": "python"}.get(linguagem.lower(), linguagem.lower())
    if chave == "python":
        return (f"FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\n"
                f"RUN useradd --create-home app\nUSER app\nEXPOSE {porta}\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"{porta}\"]\n")
    if chave == "node":
        return (f"FROM node:20-alpine\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci --omit=dev\nCOPY . .\nUSER node\nEXPOSE {porta}\n"
                "CMD [\"node\", \"index.js\"]\n")
    raise ValueError(f"linguagem sem modelo de Dockerfile: {linguagem} (use python ou node)")


def editorconfig() -> str:
    return ("root = true\n\n[*]\ncharset = utf-8\nend_of_line = lf\ninsert_final_newline = true\ntrim_trailing_whitespace = true\n"
            "indent_style = space\nindent_size = 4\n\n[*.{js,ts,json,html,css,yml,yaml}]\nindent_size = 2\n")
