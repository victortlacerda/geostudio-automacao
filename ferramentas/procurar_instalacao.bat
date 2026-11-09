@echo off
rem Duplo clique roda o script; arrastar arquivos em cima deste .bat passa os arquivos para ele.
cd /d "%~dp0"
python "%~dp0procurar_instalacao.py" %*
echo.
pause
