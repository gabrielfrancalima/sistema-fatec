# PRD — Ponto Acadêmico FATEC (Centro Paula Souza)

## Problem Statement
Plataforma web responsiva (desktop + mobile) para automatizar a geração de ponto/folha de frequência acadêmica da FATEC. ADM Master cadastra operadores; operador/coordenador consultam. Geração de folha de ponto (PDF) por curso, por professor e por período (mês). CRUDs de Professores, Cursos, Disciplinas, Feriados, Aulas Remotas. Geração automática de grade horária, associação professor↔grade, folha de frequência, consulta e mapa de frequências. Identidade visual FATEC.

## Architecture
- Backend: FastAPI + MongoDB (motor). Modules: server.py (rotas/auth/RBAC), models.py, scheduling.py (auto-geração sem conflito), pdf_generator.py (reportlab).
- Frontend: React (CRA/craco), TailwindCSS, shadcn/ui, lucide-react, sonner. Fonts: Chivo + IBM Plex Sans.
- Auth: Emergent-managed Google OAuth (cookie session_token httpOnly, 7 dias).

## User Personas & Roles
- **ADM Master** (adm_master): acesso total + gestão de operadores (/operadores).
- **Operador** (operador): todos os CRUDs + geração de PDF (escrita).
- **Coordenador** (coordenador): somente consulta (perfil padrão de novos logins).
Admin/owner: gabrielpedra1999@gmail.com (adm_master automático no 1º login).

## Core Requirements (static)
- CRUDs: Professores, Cursos, Disciplinas, Feriados, Aulas Remotas.
- Grade horária automática evitando conflito de horário do professor entre cursos.
- Folha de ponto PDF: por professor, por curso (geral), por mês; marca feriados e aulas remotas (EAD); campos de assinatura.
- Consulta de frequência do professor; Mapa de frequência (grade em grid).
- Responsivo desktop/mobile; identidade FATEC (vermelho #FF161F / cinza #273336).

## Implemented (2026-08-25)
- Auth Google + RBAC (adm/operador/coordenador) — testado 100%.
- CRUD completo das 5 entidades com componente genérico (dialog + tabela + a11y).
- Auto-geração de grade (slots por turno: noturno 4 / matutino-vespertino 6) com detecção de conflitos e preview em grid; salvar/listar/excluir grades.
- Geração de PDF (professor e curso) — layout institucional verificado visualmente.
- Consultas: frequência por professor + mapa de frequência.
- Gestão de operadores (mudar perfil, ativar/desativar, remover).
- Dashboard com estatísticas + ações rápidas. Login responsivo.
- Backend 28/28 testes; frontend 100%.

## Backlog / Próximos (P1/P2)
- P1: Edição visual manual da grade (drag/ajuste de células) além da auto-geração.
- P1: Exportar mapa de frequência do curso em PDF landscape (grid completo).
- P2: Filtro de período por intervalo de datas (não só mês).
- P2: Assinatura digital / registro de conferência da folha.
- P2: Importação em lote (CSV) de professores/disciplinas.
- P2: Logo oficial FATEC (imagem) no cabeçalho do PDF.

## Notes
- PDF endpoints atualmente acessíveis a qualquer usuário autenticado (coordenador pode baixar) — decisão de produto pendente se deve ser restrito a escrita.
