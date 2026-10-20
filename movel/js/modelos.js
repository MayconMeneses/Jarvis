// Projetos prontos (os mesmos do PC, gerados por gerar_dados.py em dados/modelos.json): FastAPI, Express, React e HTML, sozinhos ou combinados.
import { fold } from "./util.js";

export const PADRAO_DESCRICAO = "Projeto criado pela Jarvis a partir de um modelo pronto para rodar.";

export const slug = (nome) => fold(nome).replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "projeto";

// Sem aspas, <>, {}, $ ou barras: o nome vai para HTML, JSX, JSON e docstrings sem quebrar nem injetar nada.
export const nomeSeguro = (nome) => String(nome).replace(/[<>&"'`{}$\\]/g, "").trim() || "Projeto";

const trocar = (texto, pares) => pares.reduce((t, [de, para]) => t.split(de).join(para), texto);

export function listarModelos(modelos) {
  return Object.entries(modelos).map(([id, m]) => ({ id, descricao: m.descricao }));
}

// { "backend/main.py": "texto" } com nome, slug e descrição preenchidos; o README usa o nome cru (só com trim), como no PC.
export function arquivosDoModelo(modelos, id, nome, texto = "") {
  const modelo = modelos[id];
  if (!modelo) throw new Error(`não tenho o modelo "${id}"`);
  const seguro = nomeSeguro(nome), descricao = String(texto).trim();
  const comuns = [["__NOME__", seguro], ["__SLUG__", slug(nome)], ["__DESCRICAO__", descricao]];
  const leiame = [["__NOME__", String(nome).trim()], ["__DESCRICAO__", descricao || PADRAO_DESCRICAO]];
  return Object.fromEntries(Object.entries(modelo.arquivos).map(([c, t]) => [c, trocar(t, c === "README.md" ? leiame : comuns)]));
}
