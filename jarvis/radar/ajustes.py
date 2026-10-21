"""Configuração do Radar (vai em config.json, na chave "radar"). Padrões seguros: IA e voz automática desligadas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RadarConfig:
    ativo: bool = False  # liga o agendamento diário (só depois de definir o nicho)
    nicho: str = ""  # sem nicho o Radar não existe: a Jarvis pergunta
    palavras_chave: list[str] = field(default_factory=list)
    bloqueios: list[str] = field(default_factory=lambda: [
        "publieditorial", "patrocinado", "oferta", "cupom", "promocao", "black friday", "sorteio"])
    entidades_seguidas: list[str] = field(default_factory=list)  # pessoas/empresas que dão "impacto"
    principais: int = 5
    radar: int = 2  # itens do "radar secundário"
    janela_horas: int = 24
    max_por_fonte: int = 2
    nota_minima: int = 30
    ler_artigos: int = 3  # quantos dos melhores itens têm a página aberta (os outros ficam só no RSS)
    hora: str = "07:00"
    dias_uteis: bool = True
    usar_ia: bool = False  # IA só melhora o texto (sem ferramentas) e nunca roda em modo somente_independente
    audio: bool = True  # gera o áudio (.wav) do boletim; tocar é sempre sob comando
    palavras_por_minuto: int = 180
    max_palavras: int = 900
    pasta: str = ""  # vazio = Documentos\Jarvis\Radar
