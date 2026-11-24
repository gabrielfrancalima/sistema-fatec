# Ponto Acadêmico FATEC — Gerenciamento de Ponto Docente

Aplicação web fullstack em arquitetura containerizada (**React + Nginx + FastAPI + MongoDB 7**) com controle de acesso baseado em papéis (**RBAC**), autenticação OAuth 2.0 (**Google** e **Microsoft Azure Entra ID**), restrição por domínio institucional (`@fatec.sp.gov.br`, `@cps.sp.gov.br`), montagem automática de grade horária sem conflito docente entre cursos e geração de folhas de ponto em PDF.

## Arquitetura dos Containers

| Serviço | Imagem / Stack | Porta | Função |
| :--- | :--- | :--- | :--- |
| `frontend` | Node 20 (build) → Nginx 1.27 Alpine | `3000 → 80` | SPA React otimizada + Proxy Reverso `/api/` |
| `backend` | Python 3.11 Slim + FastAPI + Uvicorn (non-root) | `8000 → 8000` | API REST, OAuth 2.0, RBAC, Grade e PDFs |
| `mongo` | MongoDB 7 | `27017 → 27017` | Persistência em volume nomeado (`mongo_data`) |

## Como Executar em Qualquer Máquina

### Opção 1 — Windows (1 clique)
1. Extraia o arquivo ZIP.
2. Dê duplo clique em **`INICIAR_SISTEMA_WINDOWS.bat`**.
3. O sistema abre automaticamente em **`http://localhost:3000`**.
4. Para encerrar: **`PARAR_SISTEMA_WINDOWS.bat`**.
5. Para rodar os 24 testes automatizados: **`RODAR_TESTES_WINDOWS.bat`**.

### Opção 2 — Linux / macOS
```bash
./INICIAR_SISTEMA_LINUX_MAC.sh
```
Para rodar os testes: `./RODAR_TESTES_LINUX_MAC.sh`  
Para encerrar: `./PARAR_SISTEMA_LINUX_MAC.sh`

### Opção 3 — Terminal (ou GitHub Codespaces no navegador)
```bash
docker compose up --build
```
No **GitHub Codespaces** (para máquinas sem Docker Desktop / sem permissão de administrador): suba esta pasta em um repositório no GitHub, clique em **Code → Codespaces → Create codespace on main**, rode `docker compose up --build` no terminal e abra o link automático da porta `3000`.

## Endpoints Principais

- **Aplicação Web:** `http://localhost:3000`
- **Documentação interativa (Swagger UI):** `http://localhost:8000/docs`
- **Healthcheck (API + MongoDB):** `http://localhost:3000/api/health`
