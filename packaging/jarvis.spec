# PyInstaller: gera dist/SuperJarvis/ com dois executáveis que compartilham as bibliotecas.
#   Jarvis.exe      janela + bandeja (sem console)
#   jarvis-cli.exe  terminal: --conectar, --chave, perguntas e o servidor MCP (--mcp-server)
#
#   python -m PyInstaller packaging/jarvis.spec --noconfirm --distpath dist --workpath build

from PyInstaller.utils.hooks import (
    collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata,
)

datas = []
datas += collect_data_files("jarvis", includes=["**/*.html", "**/*.json", "**/*.css", "**/*.js"])
datas += collect_data_files("openwakeword")       # modelo "hey jarvis" e de áudio
datas += collect_data_files("faster_whisper")     # VAD silero
datas += collect_data_files("webview")
datas += collect_data_files("certifi")
datas += collect_data_files("docx")               # modelo padrão do Word
datas += collect_data_files("pptx")               # modelo padrão do PowerPoint
datas += collect_data_files("fpdf")
for dist in ("mcp", "pydantic", "pydantic_core", "keyring", "google-auth", "google-auth-oauthlib",
             "msal", "edge-tts", "faster-whisper", "openwakeword", "onnxruntime", "ctranslate2"):
    datas += copy_metadata(dist)

binaries = collect_dynamic_libs("ctranslate2") + collect_dynamic_libs("onnxruntime")

hiddenimports = (
    collect_submodules("jarvis")
    + collect_submodules("mcp", filter=lambda name: not name.startswith("mcp.cli"))  # cli exige typer
    + ["keyring.backends.Windows", "webview.platforms.edgechromium", "pystray._win32"]
)

a = Analysis(
    ["entry.py"],
    pathex=[".."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "torch", "tensorflow", "tflite_runtime", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

common = dict(exclude_binaries=True, icon="jarvis.ico", upx=False)
gui = EXE(pyz, a.scripts, [], name="Jarvis", console=False, **common)
cli = EXE(pyz, a.scripts, [], name="jarvis-cli", console=True, **common)

COLLECT(gui, cli, a.binaries, a.datas, name="SuperJarvis", upx=False)
