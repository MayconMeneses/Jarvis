"""O cérebro "llm": um modelo generativo pequeno rodando no PC. Entra no roteador depois das IAs externas."""

from __future__ import annotations

from jarvis.brains.base import Answer, BrainUnavailable, Message
from jarvis.llm import catalogo, cliente, contexto
from jarvis.llm.servidor import Servidor


class LLMLocal:
    name = "llm"

    def __init__(self, load_config, servidor: Servidor | None = None) -> None:
        self._load_config = load_config
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
        prompt = [{"role": "system", "content": contexto.sistema(system, pergunta, cfg)}, *contexto.historico(list(messages))]
        url = servidor.garantir()
        texto = cliente.conversar(url, prompt, modelo=cfg.llm_modelo)
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
