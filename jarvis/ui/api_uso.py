"""Ponte da aba "Uso de IA": resumo, configuração, preços, calibração da cota, exportar e importar."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import webview

from jarvis.uso import agentes, configuracao, cota, exportar, precos, resumo, servico

log = logging.getLogger(__name__)


class UsoMixin:
    def uso_resumo(self, periodo: str = "mes", filtros: dict | None = None) -> dict:
        try:
            reg = servico.atualizar(intervalo=5)
            return resumo.resumo(reg, str(periodo), time.time(), filtros if isinstance(filtros, dict) else None)
        except Exception:
            log.exception("falha ao montar o resumo de uso")
            return {"error": "Não foi possível ler o uso de IA. Detalhes no log da Jarvis."}

    def uso_precos(self) -> dict:
        return precos.carregar()

    def uso_salvar_precos(self, dados: dict) -> dict:
        return precos.salvar(dados if isinstance(dados, dict) else {})

    def uso_salvar_config(self, dados: dict) -> dict:
        return configuracao.salvar(servico.registro(), dados if isinstance(dados, dict) else {})

    def uso_calibrar(self, janela: str, pct: float) -> dict:
        """"Estou em X% da janela agora" (100 = bati o limite): ajusta o teto estimado."""
        try:
            return cota.calibrar(servico.atualizar(intervalo=0), time.time(), str(janela), float(pct))
        except (ValueError, TypeError) as exc:
            return {"error": str(exc)}

    def uso_sessao(self, session_id: str) -> dict:
        """Contrato do Painel de Agentes: {tokens_in, tokens_out, cache, custo_usd, estimado, origem}."""
        return agentes.uso_por_sessao(str(session_id))

    def uso_exportar(self, formato: str = "json") -> dict:
        if getattr(self, "_window", None) is None:
            return {"error": "janela indisponível"}
        csv_ = formato == "csv"
        local = self._window.create_file_dialog(webview.FileDialog.SAVE, save_filename="uso-ia." + ("csv" if csv_ else "json"))
        if not local:
            return {"cancelado": True}
        reg = servico.atualizar(intervalo=5)
        try:
            Path(local if isinstance(local, str) else local[0]).write_text(
                exportar.exportar_csv(reg) if csv_ else exportar.exportar_json(reg), encoding="utf-8")
        except OSError as exc:
            return {"error": f"Não foi possível gravar: {exc}"}
        return {"text": "Exportado (só números e rótulos, sem conteúdo de conversas)."}

    def uso_importar(self) -> dict:
        if getattr(self, "_window", None) is None:
            return {"error": "janela indisponível"}
        escolha = self._window.create_file_dialog(webview.FileDialog.OPEN)
        if not escolha:
            return {"cancelado": True}
        try:
            if Path(escolha if isinstance(escolha, str) else escolha[0]).stat().st_size > 50_000_000:
                return {"error": "Arquivo grande demais (mais de 50 MB)."}
            texto = Path(escolha if isinstance(escolha, str) else escolha[0]).read_text(encoding="utf-8")
            return {"text": f"{exportar.importar_json(servico.registro(), texto)['linhas']} linha(s) importadas."}
        except (OSError, ValueError) as exc:
            return {"error": f"Não consegui importar: {exc}"}
