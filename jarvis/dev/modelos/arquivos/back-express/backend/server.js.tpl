// __NOME__: API de exemplo (Express). Troque "itens" pelas suas entidades.
// Rodar:   npm start        Testar: npm test
import cors from "cors";
import express from "express";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const AQUI = path.dirname(fileURLToPath(import.meta.url));

/** Guarda os itens em um arquivo JSON (simples para começar; troque por um banco quando crescer). */
export function criarArmazem(arquivo = path.join(AQUI, "dados.json")) {
  const ler = () => (fs.existsSync(arquivo) ? JSON.parse(fs.readFileSync(arquivo, "utf-8")) : { proximo: 1, itens: [] });
  const gravar = (dados) => fs.writeFileSync(arquivo, JSON.stringify(dados, null, 2));
  return { ler, gravar };
}

export function criarApp(armazem = criarArmazem()) {
  const app = express();
  app.use(cors({ origin: ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080", "http://127.0.0.1:8080"] }));
  app.use(express.json());

  app.get("/api/saude", (_req, res) => res.json({ status: "ok" }));

  app.get("/api/itens", (_req, res) => res.json(armazem.ler().itens));

  app.post("/api/itens", (req, res) => {
    const titulo = String(req.body?.titulo ?? "").trim();
    if (!titulo || titulo.length > 200) return res.status(422).json({ erro: "titulo é obrigatório (até 200 caracteres)" });
    const dados = armazem.ler();
    const item = { id: dados.proximo++, titulo, concluido: false };
    dados.itens.push(item);
    armazem.gravar(dados);
    res.status(201).json(item);
  });

  app.patch("/api/itens/:id", (req, res) => {
    const dados = armazem.ler();
    const item = dados.itens.find((i) => i.id === Number(req.params.id));
    if (!item) return res.status(404).json({ erro: "item não encontrado" });
    item.concluido = Boolean(req.body?.concluido);
    armazem.gravar(dados);
    res.json(item);
  });

  app.delete("/api/itens/:id", (req, res) => {
    const dados = armazem.ler();
    const antes = dados.itens.length;
    dados.itens = dados.itens.filter((i) => i.id !== Number(req.params.id));
    if (dados.itens.length === antes) return res.status(404).json({ erro: "item não encontrado" });
    armazem.gravar(dados);
    res.status(204).end();
  });

  return app;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const porta = Number(process.env.PORT ?? 8000);
  criarApp().listen(porta, () => console.log(`__NOME__ em http://localhost:${porta}`));
}
