@echo off
REM Build MapleRoyalsHpWash Windows GUI (run on Windows)
cd /d "%~dp0\.."
python -m pip install -U pip
python -m pip install -e ".[gui,build]"
python -m PyInstaller --noconfirm --clean hp_wash_thief.spec
echo.
echo Done. Folder: dist\MapleRoyalsHpWash\
echo Run: dist\MapleRoyalsHpWash\MapleRoyalsHpWash.exe
pause
