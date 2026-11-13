@echo off
chcp 65001 >nul
rem Testa se a API do GeoStudio abre um .gsz (somente leitura). Feche o modelo no GeoStudio antes.
rem Sem argumento, usa a amostra docs\amostras_geostudio\slope\s00_talude5m.gsz.
set "PY=python"
if exist "%~dp0..\.venv\Scripts\python.exe" set "PY=%~dp0..\.venv\Scripts\python.exe"
set "ARQ=%~1"
if "%ARQ%"=="" set "ARQ=%~dp0..\docs\amostras_geostudio\slope\s00_talude5m.gsz"
set "LOG=%~dp0..\teste_abrir_api_log.txt"
echo Rodada 1: modo UTF-8 do Python ligado > "%LOG%"
set "PYTHONUTF8=1"
"%PY%" "%~dp0teste_abrir_api.py" "%ARQ%" >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo ================================================== >> "%LOG%"
echo Rodada 2: modo UTF-8 do Python desligado >> "%LOG%"
set "PYTHONUTF8=0"
set "PYTHONIOENCODING=utf-8"
"%PY%" "%~dp0teste_abrir_api.py" "%ARQ%" >> "%LOG%" 2>&1
type "%LOG%"
echo.
echo Resultado gravado em teste_abrir_api_log.txt
pause
