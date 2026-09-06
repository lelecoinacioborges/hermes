@echo off
if "%~1"=="" (
    docker exec -it hermes hermes
) else (
    docker exec -it hermes hermes %*
)
