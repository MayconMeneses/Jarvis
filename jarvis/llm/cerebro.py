"""O cérebro "llm": um modelo generativo pequeno rodando no PC. Entra no roteador depois das IAs externas."""

from __future__ import annotations

from jarvis.brains.base import Answer, BrainUnavailable, Message
from jarvis.llm import catalogo, cliente, contexto, ferramentas, ferramentas_cinto, ferramentas_laco
from jarvis.llm.servidor import Servidor


class LLMLocal:
    name = "llm"

    def __init__(self, load_config, servidor: Servidor | None = None, motor=None) -> None:
        self._load_config = load_config
        self._motor = motor
        self._servidor: Servidor | None = servidor

    def _servidor_para(self, cfg) -> Servidor:
        s = self._servidor
        if s is None or (s.id_modelo, s.endpoint) != (cfg.llm_modelo, cfg.llm_endpoint.strip()):
            if s is not None:
                s.parar()
            s = self._servidor = Servidor(cfg.llm_modelo, cfg.llm_endpoint)
        return s

    def disponivel(self) -> bool:
        cfg = self._load_config()
        return cfg.llm_local and catalogo.estado(cfg.llm_modelo, cfg.llm_endpoint)["pronto"]

    def ask(self, messages: list[Message], system: str = "") -> Answer:
        cfg = self._load_config()
        if not cfg.llm_local:
            raise BrainUnavailable("o cérebro local está desligado")
        servidor = self._servidor_para(cfg)
        pergunta = messages[-1]["content"] if messages else ""
        from jarvis.local.engine import LocalEngine

        motor = self._motor or LocalEngine(self._load_config)
        com_ferramentas = ferramentas.modelo_usa_ferramentas(catalogo.modelo(cfg.llm_modelo).id) and getattr(cfg, "ferramentas_ia", True)
        dados = ferramentas.consultar_antes(pergunta, motor) or ""
        prompt = [{"role": "system", "content": contexto.sistema(system, pergunta, cfg, dados, com_ferramentas)},
                  *contexto.historico(list(messages))]
        url = servidor.garantir()

        def conversa(mensagens: list[dict]) -> str:
            return cliente.conversar(url, mensagens, modelo=cfg.llm_modelo)

        if com_ferramentas:  # cinto de ferramentas seguras (jarvis/llm/ferramentas_cinto.py), modo ReAct simples
            cinto = ferramentas_cinto.padrao(pergunta)
            prompt[0] = {"role": "system", "content": prompt[0]["content"] + "\n\n" + cinto.instrucao()}
            texto = ferramentas_laco.rodar(conversa, prompt, cinto).texto
        else:
            texto = conversa(prompt)
        if texto:
            from jarvis.conversa import critica

            anterior = next((m["content"] for m in reversed(messages[:-1]) if m["role"] == "assistant"), "")
            texto = critica.melhorar(texto, pergunta, prompt, conversa, anterior)  # curta, vaga ou repetida: tenta de novo uma vez
        servidor.marcar_uso()
        if not texto:
            raise BrainUnavailable("o modelo local não gerou resposta")
        return Answer(text=texto, brain=self.name)

    def stop(self) -> None:
        if self._servidor is not None:
            self._servidor.parar()


def conversa_local(cfg, servidor: Servidor | None = None):
    """Função `conversa(mensagens) -> texto` para as skills (pensar.criar) usarem o modelo local sem passar pelo roteador."""
    servidor = servidor or Servidor(cfg.llm_modelo, cfg.llm_endpoint)

    def conversa(mensagens: list[dict]) -> str:
        url = servidor.garantir()
        texto = cliente.conversar(url, mensagens, max_tokens=1200, temperatura=0.2, modelo=cfg.llm_modelo)
        servidor.marcar_uso()
        return texto

    conversa.servidor = servidor  # type: ignore[attr-defined]
    return conversa
