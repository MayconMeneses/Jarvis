// Monta o motor com o entendimento ligado (para os testes). Usa o autoconhecimento real quando existe; senão, a fixture pequena.
import { existsSync, readFileSync } from "node:fs";
import { sanear } from "../js/autoconhecimento.js";
import { Entendimento } from "../js/entendimento.js";
import { Memoria } from "../js/memoria.js";
import { Motor } from "../js/motor.js";
import { Saber } from "../js/saber.js";

const url = (c) => new URL(c, import.meta.url);
export const saber = new Saber(JSON.parse(readFileSync(url("../dados/saber.json"), "utf8")));
// Arquivo do app; enquanto o gerador não o copiou para movel/dados, vale a fonte do PC (mesmo conteúdo).
const CAMINHO_REAL = ["../dados/autoconhecimento.json", "../../jarvis/local/dados/autoconhecimento.json"].find((c) => existsSync(url(c)));
export const REAL = Boolean(CAMINHO_REAL);
export const entradasFixture = sanear(JSON.parse(readFileSync(url("./fixtures/autoconhecimento-exemplo.json"), "utf8")));
export const entradasReais = REAL ? sanear(JSON.parse(readFileSync(url(CAMINHO_REAL), "utf8"))) : [];
export const frasesReservadas = JSON.parse(readFileSync(url("./fixtures/frases-reservadas.json"), "utf8"));
export const frasesDoDono = JSON.parse(readFileSync(url("./fixtures/frases-dono.json"), "utf8"));

export function montar({ entradas = entradasFixture, estado = {}, aparelho = { plataforma: "desktop", nome: "computador", navegador: "navegador" }, relogio = () => new Date("2026-10-21T10:00:00"), memoria } = {}) {
  memoria ||= new Memoria(undefined, relogio);
  const motor = new Motor({ saber, memoria, buscar: async () => { throw new Error("offline"); }, agora: relogio });
  motor.entendimento = new Entendimento({
    memoria, entradas, aparelho, estado: async () => estado, relogio,
    executar: (f) => motor._porRegex(f), classificar: (t) => motor.classificar(t),
  });
  // O mesmo caminho do main.js: regras + entendimento; se nada, o fallback.
  const perguntar = async (texto) => {
    motor.entendimento.tomarWidget();
    let r = await motor.responder(texto);
    if (r === null) r = await motor.fallback(texto);
    return { texto: r, widget: motor.entendimento.tomarWidget() };
  };
  return { motor, memoria, e: motor.entendimento, perguntar };
}
