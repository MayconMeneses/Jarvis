# Gera o instalador e deixa a versão mais nova na raiz do projeto (a antiga é substituída).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& "$env:USERPROFILE\.venvs\super-jarvis\Scripts\python.exe" -m PyInstaller packaging\jarvis.spec --noconfirm --distpath dist --workpath build
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" packaging\installer.iss
$novo = Get-ChildItem dist\SuperJarvis-Setup-*.exe | Sort-Object LastWriteTime | Select-Object -Last 1
Get-ChildItem . -Filter "SuperJarvis-Setup-*.exe" | Remove-Item -Force
Copy-Item $novo.FullName .
Write-Host "Instalador pronto na raiz: $($novo.Name)"
