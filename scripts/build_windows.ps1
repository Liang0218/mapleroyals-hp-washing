# Build MapleRoyalsHpWash Windows GUI (run in PowerShell / cmd on Windows)
# Requires: Python 3.11+, pip

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -m pip install -U pip
python -m pip install -e ".[gui,build]"
python -m PyInstaller --noconfirm --clean hp_wash_thief.spec

Write-Host ""
Write-Host "Done. Folder: dist\MapleRoyalsHpWash\"
Write-Host "Run:     dist\MapleRoyalsHpWash\MapleRoyalsHpWash.exe"
Write-Host "Zip that folder and share it with others (keep DLLs next to the exe)."
