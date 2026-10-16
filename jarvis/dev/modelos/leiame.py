"""README do projeto criado: como instalar, rodar e testar cada peça escolhida."""

from __future__ import annotations

BACK = {
    "fastapi": {
        "nome": "FastAPI (Python)",
        "instalar": ["cd backend", "python -m venv .venv", ".venv\\Scripts\\activate", "pip install -r requirements.txt"],
        "rodar": ["uvicorn main:app --reload"],
        "testar": ["pytest"],
        "extra": "Documentação interativa da API: http://localhost:8000/docs",
    },
    "express": {
        "nome": "Express (Node.js)",
        "instalar": ["cd backend", "npm install"],
        "rodar": ["npm start"],
        "testar": ["npm test"],
        "extra": "Os dados ficam em backend/dados.json (troque por um banco quando crescer).",
    },
}
FRONT = {
    "react": {
        "nome": "React (Vite)",
        "instalar": ["cd frontend", "npm install"],
        "rodar": ["npm run dev"],
        "url": "http://localhost:5173",
        "extra": "Para apontar para outra API, crie frontend/.env com VITE_API_URL=http://servidor:porta",
    },
    "html": {
        "nome": "HTML + CSS + JavaScript",
        "instalar": ["cd frontend"],
        "rodar": ["python -m http.server 8080"],
        "url": "http://localhost:8080",
        "extra": "Sem build: edite index.html, styles.css e app.js e recarregue a página.",
    },
}


def _bloco(linhas: list[str]) -> str:
    return "```bash\n" + "\n".join(linhas) + "\n```"


def leiame(nome: str, descricao: str, back: str, front: str) -> str:
    pecas = [BACK[back]["nome"] if back else "", FRONT[front]["nome"] if front else ""]
    out = [f"# {nome}", "", descricao or "Projeto criado pela Jarvis a partir de um modelo pronto para rodar.", "",
           f"**Stack:** {' + '.join(p for p in pecas if p)}", ""]
    out += ["## Estrutura", ""]
    if back:
        out.append("- `backend/`: a API (rotas em `/api/itens`, exemplo completo de CRUD com testes).")
    if front:
        out.append("- `frontend/`: a tela de exemplo que usa a API.")
    out += ["", "## Como rodar", ""]
    if back:
        b = BACK[back]
        out += [f"### Back-end ({b['nome']})", "", _bloco(b["instalar"]), "", "Iniciar (API em http://localhost:8000):", "",
                _bloco(b["rodar"]), "", f"Testes: `{b['testar'][0]}`. {b['extra']}", ""]
    if front:
        f = FRONT[front]
        out += [f"### Front-end ({f['nome']})", "", _bloco(f["instalar"]), "", f"Iniciar ({f['url']}):", "",
                _bloco(f["rodar"]), "", f["extra"], ""]
    out += ["## Próximos passos", "",
            "- Troque a entidade de exemplo (`itens`) pelas entidades do seu sistema.",
            "- Faça um commit inicial: `git add . && git commit -m \"Projeto inicial\"`.",
            "- Peça à Jarvis: \"analisar\" ou \"planejar\" o próximo passo; ela usa o Claude Code para evoluir o projeto "
            "(e só altera arquivos depois que você aprova).", ""]
    return "\n".join(out)
