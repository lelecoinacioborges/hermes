@echo off
title Hermes Agent - Terminal Chat
cls
echo ========================================================
echo   Iniciando Hermes Agent (Interface Interativa)...
echo   Para sair digite /exit ou pressione Ctrl+C
echo ========================================================
echo.
docker exec -it hermes hermes
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Modo de fallback REPL]
    docker exec -it hermes hermes --cli
)
echo.
pause
