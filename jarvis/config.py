"""Configuração da Jarvis.

Fica em %APPDATA%\\SuperJarvis\\config.json. Na primeira execução o arquivo é
criado com os valores padrão para o usuário editar.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

APP_NAME = "SuperJarvis"


def config_dir() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / APP_NAME


def data_dir() -> Path:
    """Dados locais que não devem sincronizar (logs, banco técnico)."""
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME


@dataclass
class ClaudeConfig:
    executable: str = "claude"
    model: str = ""  # vazio = modelo padrão da assinatura
    timeout_seconds: int = 180
    # Mantém um Claude aberto entre perguntas (~2 s por resposta em vez de ~11 s).
    sessao_continua: bool = True
    # Pesquisar na internet e ler sites (WebSearch/WebFetch da assinatura).
    web: bool = True


@dataclass
class ProviderConfig:
    """Provedor com API compatível com OpenAI. A chave fica no cofre do Windows."""

    base_url: str = ""
    model: str = ""
    timeout_seconds: int = 60


def _gemini() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        model="gemini-flash-latest",
    )


def _nvidia() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://integrate.api.nvidia.com/v1",
        model="nvidia/llama-3.1-nemotron-70b-instruct",  # o catálogo da NVIDIA muda: ao salvar a chave, a Jarvis testa e troca se preciso
    )


@dataclass
class EmailConfig:
    gmail_ativo: bool = False
    outlook_ativo: bool = False
    outlook_client_id: str = ""
    # "consumers" = contas pessoais (Hotmail/Outlook.com); "common" aceita também as de empresa.
    outlook_authority: str = "consumers"
    # Regras fixas: {"campo": "remetente"|"assunto", "contem": "...", "categoria": "..."}
    regras: list[dict] = field(default_factory=list)
    # Contas IMAP opcionais (só leitura): {"apelido", "host", "porta", "usuario"}. A senha de app fica no cofre do Windows.
    imap: list[dict] = field(default_factory=list)
    # Triagem AÇÃO/INFO/RUÍDO: só envia trechos de e-mail para IA na nuvem (Gemini/NVIDIA/Claude) se o usuário consentir.
    triagem_nuvem: bool = False


@dataclass
class VoiceConfig:
    ativa: bool = True
    falar_respostas: bool = True
    # "small" errou ~11% das palavras com ruído neste PC; "base" ~60%, mas é ~4 s mais rápido.
    modelo_transcricao: str = "small"
    voz: str = "pt-BR-FranciscaNeural"   # nome da voz online (edge-tts)
    # "local" = Piper offline, sem depender de terceiros (padrão) | "online" = edge-tts (Microsoft).
    voz_motor: str = "local"
    voz_efeito: bool = True      # reverb sutil na voz local
    atraso_visual_ms: int = 80   # atraso do som (alto-falante/Bluetooth) para o orbe acompanhar a fala
    # 0 a 1: menor = ativa mais fácil (e com mais alarmes falsos).
    sensibilidade: float = 0.5


def _only_known(kind: type, raw: dict) -> dict:
    known = {f.name for f in fields(kind)}
    return {k: v for k, v in raw.items() if k in known}


@dataclass
class Config:
    user_name: str = "Maycon"
    language: str = "pt-BR"
    city: str = ""
    obsidian_vault: str = ""  # opcional: só para importar/exportar a memória
    memoria_db: str = ""  # vazio = %APPDATA%\SuperJarvis\memoria.db
    # Ordem de tentativa; quem falhar ou estiver sem chave é pulado.
    brains: list[str] = field(default_factory=lambda: ["claude", "gemini", "nvidia"])
    # Ferramentas do PC (leitura + propostas com aprovação). Só o Claude as usa.
    ferramentas_pc: bool = True
    # Quando usar o Gemini: "reserva" (só se o Claude falhar) ou "simples" (conversa curta
    # sem ferramentas vai para o Gemini). Pedir "Gemini, ..." funciona nos dois modos.
    uso_gemini: str = "reserva"
    # Motor local sem IA: comandos diretos na hora e reserva final quando nenhuma IA responde.
    modo_independente: bool = True
    # True = usa só o motor próprio (nenhuma IA, nenhuma chave, nenhum limite): comandos, memória,
    # dashboards, pesquisa na internet com resumo extrativo. Muda na hora, sem reiniciar.
    somente_independente: bool = False
    # Jarvis instalada: procura, baixa e instala versões novas do GitHub sozinha (SHA-256 conferido).
    atualizacao_automatica: bool = True
    # Cérebro generativo local (jarvis/llm): um modelo pequeno rodando no PC, sem API. Instalado por cartão aprovado.
    llm_local: bool = False
    # Iniciativa própria: avisos sem ser chamada (bom dia, treino da semana, memória alta, projeto parado).
    proativo: bool = True
    # Aprendizado autônomo: estuda sozinha, na internet, os assuntos que o usuário mais pergunta. Desligado por padrão.
    autonomo: bool = False
    autonomo_max_por_dia: int = 3
    autonomo_minimo: int = 3  # quantas vezes o assunto precisa aparecer nos pedidos dos últimos 14 dias
    # Jarvis no celular (app web instalável): desligado por padrão. "rede" True = alcançável na rede local/Tailscale.
    celular_ativo: bool = False
    celular_porta: int = 8765
    celular_rede: bool = True
    # Como o celular alcança o PC: "auto" (Tailscale se estiver ligado, senão o Wi-Fi), "tailscale" (de qualquer lugar,
    # criptografado) ou "rede" (só no mesmo Wi-Fi).
    celular_acesso: str = "auto"
    celular_certificado: str = ""  # opcional: HTTPS (ex.: certificado do Tailscale); vazio = HTTP
    celular_chave: str = ""
    # Origem (esquema+host) do app autônomo do celular que pode LER agenda/e-mails/bom dia deste PC (CORS). Nada além disso.
    celular_origem_app: str = "https://mayconmeneses.github.io"
    proativo_hora: int = 8       # a partir de que hora o "bom dia" pode aparecer (se a Jarvis já estiver aberta)
    proativo_voz: bool = False   # falar sozinha (nunca entre 22h e 7h)
    instagram_lembrete: bool = False  # lembrete semanal (segunda) da análise de Instagram, FALADO; ligado por cartão aprovado
    # Orbe da janela: "completo" | "suave" (sem rotação nem pulso de escala) | "desligado".
    efeitos_visuais: str = "completo"
    face_ao_abrir: bool = False  # abrir a tela FACE (HUD em tela cheia dentro da janela) ao iniciar; opt-in
    # Tema da janela: "hud" | "ambar" | "esmeralda" | "contraste" (alto contraste). Ver jarvis/ui/api_tema.py.
    tema: str = "hud"
    llm_modelo: str = "qwen2.5-coder-1.5b"
    llm_endpoint: str = ""  # opcional: servidor já rodando (Ollama/LM Studio), ex.: http://127.0.0.1:11434
    # Agendas iCal: {"apelido", "cor"}. O link secreto de cada uma fica no cofre do Windows, nunca aqui.
    agendas: list[dict] = field(default_factory=list)
    # Perfil de custo do Claude: "economico" | "equilibrado" | "maximo". Cada perfil aponta para um modelo editável
    # em perfis_modelo; vazio = o modelo padrão da assinatura (ver jarvis/brains/perfis.py).
    perfil_modelo: str = "equilibrado"
    perfis_modelo: dict[str, str] = field(default_factory=lambda: {"economico": "", "equilibrado": "", "maximo": ""})
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    gemini: ProviderConfig = field(default_factory=_gemini)
    nvidia: ProviderConfig = field(default_factory=_nvidia)
    email: EmailConfig = field(default_factory=EmailConfig)
    voz: VoiceConfig = field(default_factory=VoiceConfig)
    # Projetos de código que a Jarvis pode analisar: {"nome": "C:\\caminho\\da\\pasta"}
    projetos: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict) -> "Config":
        values = _only_known(cls, raw)
        nested = {
            "claude": ClaudeConfig, "gemini": ProviderConfig,
            "nvidia": ProviderConfig, "email": EmailConfig, "voz": VoiceConfig,
        }
        defaults = cls()
        for name, kind in nested.items():
            if isinstance(values.get(name), dict):
                base = asdict(getattr(defaults, name))
                base.update(_only_known(kind, values[name]))
                values[name] = kind(**base)
        return cls(**values)


def load(path: Path | None = None) -> Config:
    path = path or config_dir() / "config.json"
    if not path.exists():
        cfg = Config()
        save(cfg, path)
        return cfg
    raw = json.loads(path.read_text(encoding="utf-8"))
    cfg = Config.from_dict(raw)
    if not cfg.obsidian_vault or not Path(cfg.obsidian_vault).is_dir():
        cfg.obsidian_vault = detect_obsidian_vault() or cfg.obsidian_vault
    if asdict(cfg) != raw:  # completa o arquivo com campos novos (ou o cofre detectado)
        save(cfg, path)
    return cfg


def detect_obsidian_vault(obsidian_json: Path | None = None) -> str:
    """Cofre aberto no Obsidian deste usuário (o mais recente), ou "" se não houver."""
    obsidian_json = obsidian_json or Path(os.environ.get("APPDATA", "")) / "obsidian" / "obsidian.json"
    try:
        vaults = json.loads(obsidian_json.read_text(encoding="utf-8")).get("vaults", {}).values()
    except (OSError, ValueError, AttributeError):
        return ""
    existing = [v for v in vaults if isinstance(v, dict) and Path(v.get("path", "")).is_dir()]
    if not existing:
        return ""
    best = max(existing, key=lambda v: (bool(v.get("open")), v.get("ts", 0)))
    return best["path"]


def save(cfg: Config, path: Path | None = None) -> None:
    path = path or config_dir() / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    new = asdict(cfg)
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    changed = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    if changed:
        import logging
        import sys

        # Registro para rastrear quem altera a configuração (ex.: cidade apagada sem querer).
        logging.getLogger(__name__).info(
            "config.json alterado por pid %s (%s): %s", os.getpid(), " ".join(sys.argv[:2])[-80:],
            ", ".join(f"{k}: {old.get(k)!r:.40} -> {new.get(k)!r:.40}" for k in changed if k not in ("claude",)))
    # ensure_ascii: acentos viram á etc., então o arquivo nunca fica com texto corrompido.
    path.write_text(json.dumps(new, ensure_ascii=True, indent=2), encoding="utf-8")
