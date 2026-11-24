@echo off
setlocal
title Ponto Academico FATEC - Suite Automatizada Pytest
cd /d "%~dp0"

if not exist "docker-compose.yml" goto err_missing

echo Executando a suite completa de 24 testes de integracao Pytest...
echo.
docker compose version >nul 2>&1
if not errorlevel 1 goto run_v2

docker-compose exec -e REACT_APP_BACKEND_URL=http://127.0.0.1:8000 backend pytest -v
goto done

:run_v2
docker compose exec -e REACT_APP_BACKEND_URL=http://127.0.0.1:8000 backend pytest -v

:done
echo.
pause
exit /b 0

:err_missing
echo [ERRO] docker-compose.yml nao encontrado. Extraia o ZIP antes de executar.
echo.
pause
exit /b 1
