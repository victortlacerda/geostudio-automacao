@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
rem Auditoria do projeto GeoStudio: duplo clique escolhe o .gsz; arrastar o .gsz em cima deste .bat tambem funciona.
set "PY=python"
if exist "%~dp0..\..\.venv\Scripts\python.exe" set "PY=%~dp0..\..\.venv\Scripts\python.exe"
"%PY%" "%~dp0auditoria.py" %*
echo.
pause
