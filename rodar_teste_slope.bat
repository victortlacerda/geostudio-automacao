@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
title Teste no modelo de exemplo do SLOPE/W
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Rode primeiro instalar_ambiente.bat
  pause & exit /b 1
)
set "MODELO=%~dp0docs\amostras_geostudio\slope\s00_talude5m.gsz"
set "LOG=%~dp0teste_slope_log.txt"
echo Teste iniciado em %date% %time% > "%LOG%"
echo [1/4] Testes automaticos...
"%PY%" -m pytest -q testes >> "%LOG%" 2>&1
echo [2/4] Resultados do SLOPE/W lidos do .gsz (modulo 02)...
"%PY%" modulos\02_resultados_slope\resultados_slope.py "%MODELO%" --fs-alvo 1.5 >> "%LOG%" 2>&1
echo [3/4] API do GeoStudio: tabelas de resultado (feche o modelo no GeoStudio antes)...
"%PY%" ferramentas\tabelas_resultados.py "%MODELO%" --amostra 8 >> "%LOG%" 2>&1
echo [4/4] API do GeoStudio: mapa de objetos...
"%PY%" ferramentas\mapa_objetos.py "%MODELO%" >> "%LOG%" 2>&1
echo FIM >> "%LOG%"
echo.
echo Pronto. Veja teste_slope_log.txt e a pasta docs\amostras_geostudio\slope\s00_talude5m_resultados
pause
