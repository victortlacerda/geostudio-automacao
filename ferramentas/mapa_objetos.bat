@echo off
rem Duplo clique roda o script; arrastar arquivos em cima deste .bat passa os arquivos para ele.
cd /d "%~dp0"
python "%~dp0mapa_objetos.py" %*
echo.
pause
