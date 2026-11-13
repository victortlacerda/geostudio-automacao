@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
rem Duplo clique roda o script; arrastar arquivos em cima deste .bat passa os arquivos para ele.
rem Usa o Python do ambiente .venv do repositorio, se existir (criado por instalar_ambiente.bat).
set "PY=python"
if exist "%~dp0..\.venv\Scripts\python.exe" set "PY=%~dp0..\.venv\Scripts\python.exe"
cd /d "%~dp0"
"%PY%" "%~dp0procurar_instalacao.py" %*
echo.
pause
