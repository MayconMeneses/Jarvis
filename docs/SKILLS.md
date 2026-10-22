# Como a Jarvis ganha habilidades (skills) e ferramentas

A regra de ouro: **nada de terceiros é baixado ou executado sozinho**. Tudo entra por arquivo versionado, com teste, e por cartão de aprovação quando mexe no PC.

## 1. Habilidade de programador (declarativa)
1. Copie `jarvis/dev/habilidades/dados/modelo.json` e cole o objeto em `jarvis/dev/habilidades/dados/habilidades.json`.
2. Preencha `id`, `nome`, `resumo`, 3 `niveis`, `praticas`, `estudar` (ids da base curada) e `treino`.
3. Rode `python -m pytest tests/test_skill_modelo.py tests/test_habilidades.py -q` (o validador é `jarvis/dev/habilidades/modelo.py`).
4. Se ela também for **medida** em projetos, escreva a checagem em `checagens*.py`, registre em `CHECAGENS` e ponha `"medida": true`.

## 2. Comando novo no motor local (sem IA)
Copie o desenho de `jarvis/local/mcp_skills.py`: `PADROES` (regex em português, sem acento), `MODULOS` (intenção -> função `(texto, cfg) -> str`),
e registre em `jarvis/local/padroes.py` e `jarvis/local/engine.py`. Ação que muda algo = **cartão** (`jarvis/pc/actions.py`), nunca execução direta.

## 3. Ferramenta para o cérebro generativo (cinto)
Uma `Ferramenta` em `jarvis/llm/ferramentas_*.py` (nome, esquema JSON, função, `externo=True` se o resultado vem de terceiros).
Só leitura ou `propor_*`. Teste: argumentos inválidos, limite de tamanho, resultado marcado como dado, injeção em resultado.

## 4. Ferramenta externa (MCP)
Só pelo catálogo curado `jarvis/mcp_catalogo/catalogo.json`: versão exata, hash do registro, licença, permissões, riscos e motivo.
Instalar é um cartão; o `mcp.json` do Claude CLI sai só dos itens aprovados. Para propor um item novo: pesquise (mantenedor, licença, último commit,
dependências, scripts de instalação), preencha todos os campos e rode `python -m pytest tests/test_mcp_catalogo.py -q`.
