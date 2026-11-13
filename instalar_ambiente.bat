@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
title Instalar o ambiente Python da automacao do GeoStudio
set "LOG=%~dp0instalar_ambiente_log.txt"
echo Instalacao iniciada em %date% %time% > "%LOG%"

rem ---- Python 3.12 (a API do GeoStudio exige 3.12.1 ate antes do 3.13) ----
set "PY312="
py -3.12 -c "import sys; print(sys.version)" >> "%LOG%" 2>&1 && set "PY312=py -3.12"
if not defined PY312 if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY312 (
  echo Python 3.12 nao encontrado. Instale em https://www.python.org/downloads/ e rode de novo.
  echo ERRO: Python 3.12 nao encontrado >> "%LOG%"
  pause & exit /b 1
)

echo [1/4] Criando o ambiente .venv com Python 3.12...
if not exist ".venv\Scripts\python.exe" %PY312% -m venv .venv >> "%LOG%" 2>&1 || goto erro
set "PY=%~dp0.venv\Scripts\python.exe"

echo [2/4] Instalando as bibliotecas do projeto...
"%PY%" -m pip install -r requirements.txt pytest >> "%LOG%" 2>&1 || goto erro

echo [3/4] Instalando a API do GeoStudio (gsi)...
set "APIREQ=C:\Program Files\Seequent\GeoStudio 2026.1\API\requirements.txt"
if not exist "%APIREQ%" (
  echo Nao achei "%APIREQ%". Rode ferramentas\procurar_instalacao.bat. >> "%LOG%"
  echo Nao achei a pasta API do GeoStudio 2026.1.
  goto erro
)
"%PY%" -m pip install -r "%APIREQ%" >> "%LOG%" 2>&1 || goto erro
"%PY%" -c "import gsi, sys; print('gsi ok', sys.version)" >> "%LOG%" 2>&1 || goto erro

echo [4/4] Rodando os testes automaticos (sem GeoStudio)...
"%PY%" -m pytest -q testes >> "%LOG%" 2>&1

echo.
echo Pronto. Detalhes em instalar_ambiente_log.txt
echo FIM OK >> "%LOG%"
pause
exit /b 0

:erro
echo FIM COM ERRO >> "%LOG%"
echo.
echo Algo deu errado. Veja instalar_ambiente_log.txt
pause
exit /b 1
