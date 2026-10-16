"""Checagens automáticas (heurísticas, sem IA) dos aspectos principais de um projeto.

Cada função recebe um `Projeto` (varredura somente leitura) e devolve um `Resultado`: nota de 0 a 100
(ou None se não se aplica), o que foi encontrado e o que melhorar. São sinais, não veredito: não
substituem a revisão feita por uma pessoa. Outras checagens: checagens_extras.py.
"""

from __future__ import annotations

import ast
import re
import subprocess

from jarvis.dev.habilidades.base import Resultado, codigo_de, limitar
from jarvis.dev.habilidades.checagens_design import arquitetura, design_de_interface
from jarvis.dev.habilidades.checagens_extras import acessibilidade, automacao, estrutura, observabilidade
from jarvis.dev.habilidades.varredura import Projeto, eh_modelo, eh_teste

LIMITE_LINHAS = 300
LIMITE_FUNCAO = 60
_SEGREDOS = [
    re.compile(r"AKIA[0-9A-Z]{16}"), re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"), re.compile(r"AIza[0-9A-Za-z_\-]{35}"), re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|passw(or)?d|senha)\w*\s*[:=]\s*[\"'][A-Za-z0-9_\-/+=.]{12,}[\"']"),
]
_PLACEHOLDER = re.compile(r"(?i)(changeme|exemplo|example|your|seu[_-]|xxx|<|\$\{|os\.environ|getenv|process\.env|placeholder|dummy)")
_SQL_PY = re.compile(r"""\.execute\(\s*(f["']|["'][^"']*["']\s*(%|\+)|[^)"']*\+\s*[a-zA-Z_])""")
_SQL_JS = re.compile(r"""\.query\(\s*`[^`]*\$\{""")
# Montados por partes para que este arquivo não seja marcado por ele mesmo.
_PENDENCIA = re.compile(r"\b(" + "|".join(("TO" + "DO", "FIX" + "ME", "X" + "XX")) + r")\b")
_SEM_VERIFICAR = re.compile("verify" + r"\s*=\s*" + "Fa" + "lse")


def testes(p: Projeto) -> Resultado:
    codigo = [c for c in p.textos if not c.endswith((".html", ".css", ".sql")) and not eh_modelo(c)]
    feitos = [c for c in codigo if eh_teste(c)]
    fontes = [c for c in codigo if not eh_teste(c)]
    if not fontes:
        return Resultado(None, ["Nenhum código-fonte encontrado."])
    razao = len(feitos) / len(fontes)
    pyproject = (p.raiz / "pyproject.toml").read_text(encoding="utf-8", errors="replace") if p.existe("pyproject.toml") else ""
    package = (p.raiz / "package.json").read_text(encoding="utf-8", errors="replace") if p.existe("package.json") else ""
    configurado = (p.existe("pytest.ini") or p.existe("conftest.py") or "tests/conftest.py" in p.arquivos or p.existe("jest.config.js")
                   or p.existe("vitest.config.js") or '"test"' in package or "[tool.pytest" in pyproject
                   or any(a.endswith("_test.go") for a in p.arquivos))
    nota = 0 if not feitos else 40 + min(40, razao / 0.3 * 40) + (20 if configurado else 0)
    achados = [f"{len(feitos)} arquivo(s) de teste para {len(fontes)} de código ({razao:.0%})."]
    ajuda = []
    if not feitos:
        ajuda.append("Crie a pasta tests/ e comece testando o caminho feliz de uma função (e o caso vazio).")
    elif razao < 0.15:
        ajuda.append("Poucos testes para o tamanho do código: cubra os módulos com mais regra de negócio primeiro.")
    if feitos and not configurado:
        ajuda.append("Configure como rodar os testes (pytest, npm test, go test) e documente no README.")
    return Resultado(limitar(nota), achados, ajuda)


def documentacao(p: Projeto) -> Resultado:
    leiame = next((a for a in p.arquivos if a.lower() in ("readme.md", "readme.rst", "readme.txt", "readme")), None)
    nota, achados, ajuda = 0, [], []
    if leiame is None:
        return Resultado(0, ["Não há README."], ["Crie um README com: o que é, como instalar, rodar e testar."])
    texto = (p.raiz / leiame).read_text(encoding="utf-8", errors="replace")
    linhas = len([l for l in texto.splitlines() if l.strip()])
    nota += 40
    achados.append(f"README com {linhas} linha(s) de conteúdo.")
    if linhas >= 20:
        nota += 30
    else:
        ajuda.append("README curto: explique o que é, como instalar, rodar, testar e contribuir.")
    if re.search(r"(?i)\b(instal|rodar|executar|run|npm|pip|uvicorn|docker|go run)\b", texto):
        nota += 15
    else:
        ajuda.append("O README não diz como rodar o projeto.")
    if any(a.lower().startswith(("docs/", "doc/")) or a.lower().startswith("changelog") for a in p.arquivos):
        nota += 15
    else:
        ajuda.append("Considere uma pasta docs/ ou um CHANGELOG para decisões e mudanças importantes.")
    return Resultado(limitar(nota), achados, ajuda)


def versionamento(p: Projeto) -> Resultado:
    achados, ajuda, nota = [], [], 0
    if p.existe(".git"):
        nota += 40
        try:
            saida = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=p.raiz, capture_output=True, text=True, timeout=10,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
            commits = int(saida) if saida.isdigit() else 0
        except (OSError, subprocess.TimeoutExpired, ValueError):
            commits = 0
        achados.append(f"Repositório git com {commits} commit(s).")
        nota += 15 if commits >= 5 else 0
        if commits < 5:
            ajuda.append("Faça commits pequenos e frequentes, com mensagens que expliquem o porquê.")
    else:
        ajuda.append("Inicie o controle de versão: git init, .gitignore e um primeiro commit.")
    if p.existe(".gitignore"):
        nota += 30
        ignorado = (p.raiz / ".gitignore").read_text(encoding="utf-8", errors="replace")
        if p.existe(".env") and ".env" not in ignorado:
            nota -= 20
            ajuda.append("Há um .env que NÃO está no .gitignore: ele pode vazar segredos.")
    else:
        ajuda.append("Crie um .gitignore (dependências, builds, .env e arquivos do editor).")
    if p.grandes:
        nota -= min(30, 15 * len(p.grandes))
        achados.append(f"{len(p.grandes)} arquivo(s) maior(es) que 5 MB (ex.: {p.grandes[0]}).")
        ajuda.append("Arquivos grandes pesam o repositório: gere-os no build ou use Git LFS.")
    elif p.existe(".git"):  # o bônus de "repositório enxuto" só vale para quem usa controle de versão
        nota += 15
    return Resultado(limitar(nota), achados, ajuda)


def seguranca(p: Projeto) -> Resultado:
    nota, achados, ajuda = 100, [], []
    vazados = []
    for caminho, texto in codigo_de(p).items():
        for padrao in _SEGREDOS:
            for achado in padrao.finditer(texto):
                if not _PLACEHOLDER.search(achado.group(0)):
                    vazados.append(caminho)
                    break
    if vazados:
        nota -= min(60, 30 * len(set(vazados)))
        achados.append("Possíveis segredos no código: " + ", ".join(sorted(set(vazados))[:5]) + ".")
        ajuda.append("Tire segredos do código: use variáveis de ambiente, revogue as chaves expostas e limpe o histórico se já houve commit.")
    perigos = {"eval/exec": 0, "SQL montado com texto": 0, "certificado sem verificação": 0}
    for caminho, texto in codigo_de(p).items():
        if caminho.endswith(".py"):
            perigos["eval/exec"] += len(re.findall(r"(?<![\w.])(eval|exec)\(", texto))
            perigos["SQL montado com texto"] += len(_SQL_PY.findall(texto))
            perigos["certificado sem verificação"] += len(_SEM_VERIFICAR.findall(texto))
        elif caminho.endswith((".js", ".jsx", ".ts", ".tsx")):
            perigos["eval/exec"] += len(re.findall(r"(?<![\w.])eval\(", texto))
            perigos["SQL montado com texto"] += len(_SQL_JS.findall(texto))
    for nome, qtd in perigos.items():
        if qtd:
            nota -= min(20, 10 * qtd)
            achados.append(f"{qtd} ocorrência(s) de {nome}.")
    if perigos["SQL montado com texto"]:
        ajuda.append("Use consultas parametrizadas (execute(sql, parametros)) em vez de montar SQL com texto.")
    if perigos["eval/exec"]:
        ajuda.append("Evite eval/exec com dados externos: prefira estruturas de dados e funções explícitas.")
    if perigos["certificado sem verificação"]:
        ajuda.append("Não desligue a verificação de certificados nas chamadas HTTPS.")
    if not achados:
        achados.append("Nenhum segredo nem padrão perigoso óbvio encontrado (isso não prova que está seguro).")
    return Resultado(limitar(nota), achados, ajuda)


def codigo_limpo(p: Projeto) -> Resultado:
    codigo = codigo_de(p)
    if not codigo:
        return Resultado(None, ["Nenhum código-fonte encontrado."])
    nota, achados, ajuda = 100, [], []
    grandes = [(c, len(t.splitlines())) for c, t in codigo.items() if len(t.splitlines()) > LIMITE_LINHAS]
    if grandes:
        nota -= min(40, 8 * len(grandes))
        pior = max(grandes, key=lambda g: g[1])
        achados.append(f"{len(grandes)} arquivo(s) com mais de {LIMITE_LINHAS} linhas (maior: {pior[0]}, {pior[1]}).")
        ajuda.append("Divida os arquivos grandes por assunto: cada arquivo, uma responsabilidade.")
    longas = 0
    for caminho, texto in codigo.items():
        if caminho.endswith(".py"):
            try:
                for no in ast.walk(ast.parse(texto)):
                    if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and (no.end_lineno or no.lineno) - no.lineno + 1 > LIMITE_FUNCAO:
                        longas += 1
            except SyntaxError:
                continue
    if longas:
        nota -= min(30, 5 * longas)
        achados.append(f"{longas} função(ões) com mais de {LIMITE_FUNCAO} linhas.")
        ajuda.append("Quebre funções longas em funções menores com nomes que dispensem comentário.")
    vazios = sum(len(re.findall(r"^\s*except\s*:", t, re.M)) for c, t in codigo.items() if c.endswith(".py"))
    if vazios:
        nota -= min(15, 5 * vazios)
        achados.append(f"{vazios} 'except:' sem tipo (engole qualquer erro).")
        ajuda.append("Capture exceções específicas e registre o erro em vez de escondê-lo.")
    pendencias = sum(len(_PENDENCIA.findall(t)) for t in codigo.values())
    if pendencias:
        nota -= min(10, 2 * pendencias)
        achados.append(f"{pendencias} marcador(es) de pendência esquecido(s).")
    if not achados:
        achados.append("Arquivos e funções dentro dos limites, sem except vazio nem pendências esquecidas.")
    return Resultado(limitar(nota), achados, ajuda)


CHECAGENS = {"testes": testes, "documentacao": documentacao, "versionamento": versionamento, "seguranca": seguranca,
             "codigo-limpo": codigo_limpo, "automacao": automacao, "observabilidade": observabilidade,
             "acessibilidade": acessibilidade, "estrutura": estrutura, "arquitetura": arquitetura,
             "design-de-interface": design_de_interface}
