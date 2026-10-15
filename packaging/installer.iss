; Instalador da Super Jarvis (Inno Setup 6).
; Gere antes a pasta do app:  python -m PyInstaller packaging/jarvis.spec --noconfirm --distpath dist --workpath build
; Depois compile:              ISCC packaging\installer.iss
;
; Instala só para o usuário atual (sem administrador). A desinstalação remove o
; programa, mas mantém configurações, chaves e as notas da Jarvis no Obsidian.

#define AppName "Super Jarvis"
#define AppVersion "0.8.0"
#define AppExe "Jarvis.exe"

[Setup]
AppId={{6E2B7C4A-3F1D-4C8E-9A5B-2D7E1F0C9B31}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Maycon
DefaultDirName={localappdata}\Programs\SuperJarvis
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=SuperJarvis-Setup-{#AppVersion}
SetupIconFile=jarvis.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked
Name: "autostart"; Description: "Abrir a Jarvis quando o Windows iniciar"

[Files]
Source: "..\dist\SuperJarvis\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SuperJarvis"; ValueData: """{app}\{#AppExe}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir a Jarvis agora"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM {#AppExe} /F"; Flags: runhidden; RunOnceId: "FecharJarvis"

[Code]
function ClaudeInstalled(): Boolean;
begin
  Result := FileExists(ExpandConstant('{%USERPROFILE}\.local\bin\claude.exe'))
    or (FileSearch('claude.exe', GetEnv('PATH')) <> '');
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpReady) and not ClaudeInstalled() then
    MsgBox('O Claude Code não foi encontrado neste PC. A Jarvis usa o Claude Code (com a sua assinatura) '
      + 'como cérebro principal.' + #13#10#13#10
      + 'Você pode instalar a Jarvis agora e o Claude Code depois (https://claude.com/claude-code). '
      + 'Enquanto isso, ela usa o Gemini ou a NVIDIA se as chaves estiverem configuradas.',
      mbInformation, MB_OK);
end;
