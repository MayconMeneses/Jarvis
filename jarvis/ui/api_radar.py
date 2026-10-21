"""Janela "📰 Radar": nicho, horário, interruptores, fontes e botões de gerar, ouvir e abrir o boletim."""

from __future__ import annotations

from dataclasses import asdict

from jarvis import config
from jarvis.radar import servico
from jarvis.radar.agendador import hora_de
from jarvis.radar.historico import Historico


class RadarMixin:
    """Tudo aqui lê e grava o config.json e chama o mesmo serviço dos comandos de voz/texto."""

    def radar_estado(self) -> dict:
        cfg = config.load()
        h = Historico()
        try:
            fontes = [{"nome": f.nome, "tipo": f.tipo, "idioma": f.idioma, "nota": f.nota, "ativa": f.ativa, "medida": f.medida}
                      for f in h.fontes()]
            ultima = h.ultima_execucao()
        finally:
            h.fechar()
        r = asdict(cfg.radar)
        return {"nicho": r["nicho"], "ativo": r["ativo"], "hora": r["hora"], "dias_uteis": r["dias_uteis"], "usar_ia": r["usar_ia"],
                "audio": r["audio"], "ia_disponivel": not cfg.somente_independente, "fontes": fontes, "rodando": servico.rodando(cfg),
                "ultima": ({k: ultima[k] for k in ("dia", "escolhidos", "varridos", "novos", "falhas", "resultado")} if ultima else None)}

    def radar_salvar(self, campos: dict) -> dict:
        """Só campos conhecidos e já validados: o texto vem da tela, mas nunca é confiado cegamente."""
        if not isinstance(campos, dict):
            return {"error": "dados inválidos"}
        cfg = config.load()
        r = cfg.radar
        if "nicho" in campos:
            nicho = " ".join(str(campos["nicho"]).split())[:120]
            if nicho != r.nicho:
                servico.definir_nicho(nicho, cfg)
                cfg = config.load()
                r = cfg.radar
        if "hora" in campos:
            h, m = hora_de(str(campos["hora"]))
            r.hora = f"{h:02d}:{m:02d}"
        for chave in ("ativo", "dias_uteis", "usar_ia", "audio"):
            if chave in campos:
                r.__dict__[chave] = bool(campos[chave])
        if r.ativo and not r.nicho.strip():
            r.ativo = False
            config.save(cfg)
            return {"error": "Defina o nicho antes de ligar o Radar."}
        config.save(cfg)
        self._diary("Radar: configuração alterada na janela")
        return {"ok": True}

    def radar_rodar(self, so_texto: bool = False) -> dict:
        return {"text": servico.rodar(config.load(), bool(so_texto))}

    def radar_ouvir(self) -> dict:
        try:
            return {"text": servico.ouvir(config.load())}
        except Exception as exc:  # sem placa de som, por exemplo
            return {"error": f"Não consegui tocar o áudio: {exc}"}

    def radar_parar(self) -> dict:
        try:
            return {"text": servico.parar()}
        except Exception as exc:
            return {"error": str(exc)}

    def radar_abrir(self) -> dict:
        return {"text": servico.abrir(config.load())}

    def radar_fonte_adicionar(self, url: str) -> dict:
        return {"text": servico.adicionar(str(url), config.load())}

    def radar_fonte_ativar(self, nome: str, ativa: bool) -> dict:
        h = Historico()
        try:
            return {"ok": h.ativar(str(nome), bool(ativa))}
        finally:
            h.fechar()
