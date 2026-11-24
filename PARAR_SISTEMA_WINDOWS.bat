@echo off
setlocal
title Ponto Academico FATEC - Encerrar Sistema
cd /d "%~dp0"

if not exist "docker-compose.yml" goto err_missing

docker compose version >nul 2>&1
if not errorlevel 1 goto stop_v2

docker-compose down
goto done

:stop_v2
docker compose down

:done
echo.
echo Sistema encerrado com sucesso!
echo.
pause
exit /b 0

:err_missing
echo [ERRO] docker-compose.yml nao encontrado. Extraia o ZIP antes de executar.
echo.
pause
exit /b 1
