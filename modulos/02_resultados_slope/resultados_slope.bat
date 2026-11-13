@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
rem Duplo clique: escolhe o .gsz numa janela. Arrastar .gsz em cima deste .bat: processa direto.
set "PY=python"
if exist "%~dp0..\..\.venv\Scripts\python.exe" set "PY=%~dp0..\..\.venv\Scripts\python.exe"
cd /d "%~dp0"
"%PY%" "%~dp0resultados_slope.py" %*
echo.
pause
