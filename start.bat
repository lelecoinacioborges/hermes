@echo off
echo Iniciando Hermes Agent e OmniRoute no Docker...
docker compose up -d
echo.
echo ========================================================
echo  OmniRoute Dashboard: http://localhost:20128
echo  Hermes Dashboard:   http://localhost:9119
echo ========================================================
echo.
echo Para abrir o chat interativo no terminal: execute chat.bat
pause
