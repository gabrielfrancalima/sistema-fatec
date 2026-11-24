@echo off
setlocal
title Ponto Academico FATEC - Inicializador Docker
cd /d "%~dp0"

echo ====================================================================
echo   PONTO ACADEMICO FATEC - GERENCIAMENTO DE PONTO DOCENTE - EQUIPE N7
echo ====================================================================
echo.
echo Pasta atual: %CD%
echo.

if not exist "docker-compose.yml" goto err_not_extracted

where docker >nul 2>&1
if errorlevel 1 goto err_no_docker

echo [1/4] Verificando se o Docker Desktop esta em execucao...
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready

echo [INFO] Docker Desktop nao esta rodando. Tentando iniciar automaticamente...
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if exist "%LocalAppData%\Docker\Docker Desktop.exe" start "" "%LocalAppData%\Docker\Docker Desktop.exe"

set /a tries=0

:wait_docker
set /a tries=%tries%+1
echo Aguardando motor do Docker iniciar... tentativa %tries% de 30
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready
if %tries% geq 30 goto err_docker_timeout
goto wait_docker

:docker_ready
echo [OK] Docker esta ativo!
echo.
echo [2/4] Detectando comando Docker Compose...
set "COMPOSE_CMD="
docker compose version >nul 2>&1
if not errorlevel 1 set "COMPOSE_CMD=docker compose"
if defined COMPOSE_CMD goto run_compose

docker-compose version >nul 2>&1
if not errorlevel 1 set "COMPOSE_CMD=docker-compose"
if defined COMPOSE_CMD goto run_compose
goto err_no_compose

:run_compose
echo [OK] Comando detectado: %COMPOSE_CMD%
echo.
echo [3/4] Construindo e subindo containers MongoDB, Backend e Frontend...
echo Aviso: na primeira execucao o download e compilacao levam de 2 a 5 minutos.
echo.
%COMPOSE_CMD% up --build -d
if errorlevel 1 goto err_compose_fail

echo.
echo [4/4] Aguardando aplicacao responder em http://localhost:3000 ...
set /a w=0

:wait_http
set /a w=%w%+1
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:3000/api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto open_browser
echo Aguardando resposta do servidor... tentativa %w% de 30
if %w% geq 30 goto open_browser_warn
goto wait_http

:open_browser_warn
echo [AVISO] O servidor demorou para responder ao healthcheck. Tentando abrir o navegador mesmo assim...

:open_browser
echo.
echo ====================================================================
echo   SISTEMA NO AR E PRONTO PARA USO!
echo   - Aplicacao Web:    http://localhost:3000
echo   - API Swagger UI:   http://localhost:8000/docs
echo   - Healthcheck:      http://localhost:3000/api/health
echo   - Rodar 24 testes:  RODAR_TESTES_WINDOWS.bat
echo   - Encerrar sistema: PARAR_SISTEMA_WINDOWS.bat
echo ====================================================================
echo.
start "" "http://localhost:3000"
pause
exit /b 0

:err_not_extracted
echo [ERRO] Arquivo docker-compose.yml nao encontrado nesta pasta!
echo Voce provavelmente clicou no arquivo diretamente dentro do ZIP sem extrair.
echo Solucao: clique com o botao direito no ZIP, escolha "Extrair Tudo..." e execute o arquivo dentro da pasta extraida.
echo.
pause
exit /b 1

:err_no_docker
echo [ERRO] O Docker nao foi encontrado neste computador.
echo Instale o Docker Desktop em: https://www.docker.com/products/docker-desktop/
echo Se voce estiver em um computador corporativo bloqueado sem Docker, rode pelo GitHub Codespaces no navegador.
echo.
pause
exit /b 1

:err_no_compose
echo [ERRO] Docker Compose nao encontrado. Atualize o Docker Desktop e tente novamente.
echo.
pause
exit /b 1

:err_docker_timeout
echo [ERRO] O motor do Docker nao iniciou a tempo.
echo Abra o programa Docker Desktop manualmente pelo Menu Iniciar, aguarde ficar verde/ativo e execute este arquivo novamente.
echo.
pause
exit /b 1

:err_compose_fail
echo.
echo [ERRO] Falha ao construir ou iniciar os containers Docker.
echo Leia a mensagem de erro acima para identificar a causa - ex: porta 3000, 8000 ou 27017 ja em uso.
echo.
pause
exit /b 1
