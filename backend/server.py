from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import StreamingResponse, RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import secrets
import requests
import msal
from itsdangerous import URLSafeSerializer, BadSignature

from models import (
    User, RoleUpdate, Curso, CursoCreate, Professor, ProfessorCreate,
    Disciplina, DisciplinaCreate, Feriado, FeriadoCreate, AulaRemota, AulaRemotaCreate,
    Grade, GradeCreate, AutoGenRequest, now_utc, new_id,
)
from scheduling import auto_generate, get_slots, DIAS_SEMANA, TURNO_SLOTS
import pdf_generator as pdfg

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '').lower()

# Microsoft / Azure Entra ID OAuth
AZURE_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID', '')
AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET', '')
AZURE_TENANT_ID = os.environ.get('AZURE_TENANT_ID', 'organizations')
AZURE_REDIRECT_URI = os.environ.get('AZURE_REDIRECT_URI', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', '').rstrip('/')
APP_SECRET = os.environ.get('APP_SECRET', 'dev-secret')
MS_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
MS_SCOPES = ["User.Read"]
MS_ENABLED = bool(AZURE_CLIENT_ID and AZURE_CLIENT_SECRET and AZURE_REDIRECT_URI)
flow_signer = URLSafeSerializer(APP_SECRET, salt="ms-oauth-flow")
FLOW_COOKIE = "ms_oauth_flow"

# Institutional email domain allowlist (empty = allow any). Admin email is always allowed.
ALLOWED_EMAIL_DOMAINS = [d.strip().lower() for d in os.environ.get('ALLOWED_EMAIL_DOMAINS', '').split(',') if d.strip()]
_DOMAIN_MSG = ("Acesso permitido apenas para contas institucionais"
               + (f" ({', '.join('@' + d for d in ALLOWED_EMAIL_DOMAINS)})." if ALLOWED_EMAIL_DOMAINS else "."))


def _email_allowed(email: str) -> bool:
    email = (email or '').lower()
    if email == ADMIN_EMAIL:
        return True
    if not ALLOWED_EMAIL_DOMAINS:
        return True
    domain = email.split('@')[-1]
    return any(domain == d or domain.endswith('.' + d) for d in ALLOWED_EMAIL_DOMAINS)

app = FastAPI(title="Ponto Acadêmico FATEC")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


# ---------------- Auth helpers ----------------
async def get_current_user(request: Request) -> User:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")

    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Sessão inválida")

    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sessão expirada")

    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    user = User(**user_doc)
    if not user.active:
        raise HTTPException(status_code=403, detail="Usuário desativado")
    return user


def require_roles(*roles):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Acesso não autorizado para o seu perfil")
        return user
    return checker


# roles that can write
WRITE_ROLES = ("adm_master", "operador")


async def _create_session(user: User) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user.user_id, "session_token": token,
        "expires_at": expires.isoformat(), "created_at": now_utc(),
    })
    return token


async def _upsert_user(email: str, name: str, picture: Optional[str] = None) -> User:
    email = email.lower()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user = User(**existing)
        await db.users.update_one({"user_id": user.user_id}, {"$set": {"name": name or user.name}})
        return user
    role = "adm_master" if email == ADMIN_EMAIL else "coordenador"
    user = User(user_id=f"user_{uuid.uuid4().hex[:12]}", email=email, name=name or email,
                picture=picture, role=role)
    await db.users.insert_one(user.model_dump())
    return user


def _msal_app():
    return msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID, authority=MS_AUTHORITY, client_credential=AZURE_CLIENT_SECRET)


@api_router.get("/auth/config")
async def auth_config():
    return {"microsoft_enabled": MS_ENABLED, "google_enabled": True}


@api_router.get("/auth/microsoft/login")
async def ms_login():
    if not MS_ENABLED:
        raise HTTPException(status_code=503, detail="Login Microsoft não configurado")
    flow = _msal_app().initiate_auth_code_flow(scopes=MS_SCOPES, redirect_uri=AZURE_REDIRECT_URI)
    if "error" in flow:
        raise HTTPException(status_code=500, detail="Falha ao iniciar login Microsoft")
    payload = {"flow": flow, "exp": int(datetime.now(timezone.utc).timestamp()) + 600}
    redirect = RedirectResponse(flow["auth_uri"], status_code=302)
    redirect.set_cookie(FLOW_COOKIE, flow_signer.dumps(payload), max_age=600,
                        httponly=True, secure=True, samesite="lax", path="/api/auth/microsoft")
    return redirect


@api_router.get("/auth/microsoft/callback")
async def ms_callback(request: Request):
    def fail(code):
        return RedirectResponse(f"{FRONTEND_URL}/?error={code}", status_code=302)

    cookie = request.cookies.get(FLOW_COOKIE)
    if not cookie:
        return fail("ms_flow")
    try:
        saved = flow_signer.loads(cookie)
        if saved["exp"] < int(datetime.now(timezone.utc).timestamp()):
            raise BadSignature("expired")
    except BadSignature:
        return fail("ms_flow")

    if request.query_params.get("error"):
        return fail("ms_denied")
    try:
        result = _msal_app().acquire_token_by_auth_code_flow(saved["flow"], dict(request.query_params))
    except ValueError:
        return fail("ms_oauth")
    if "error" in result or "id_token_claims" not in result:
        return fail("ms_token")

    claims = result["id_token_claims"]
    email = (claims.get("email") or claims.get("preferred_username") or "").strip().lower()
    name = (claims.get("name") or "").strip()
    if not email:
        return fail("ms_email")

    if not _email_allowed(email):
        return fail("domain")

    user = await _upsert_user(email, name)
    if not user.active:
        return fail("inactive")
    token = await _create_session(user)
    redirect = RedirectResponse(f"{FRONTEND_URL}/dashboard", status_code=302)
    redirect.delete_cookie(FLOW_COOKIE, path="/api/auth/microsoft")
    redirect.set_cookie("session_token", token, max_age=7 * 24 * 3600,
                        httponly=True, secure=True, samesite="none", path="/")
    return redirect


# ---------------- Auth routes ----------------
@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id ausente")

    resp = requests.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": session_id}, timeout=15)
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Falha ao validar sessão")
    data = resp.json()
    email = data["email"].lower()

    if not _email_allowed(email):
        raise HTTPException(status_code=403, detail=_DOMAIN_MSG)

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user = User(**existing)
        await db.users.update_one({"user_id": user.user_id},
                                  {"$set": {"name": data.get("name", user.name),
                                            "picture": data.get("picture", user.picture)}})
    else:
        role = "adm_master" if email == ADMIN_EMAIL else "coordenador"
        user = User(user_id=f"user_{uuid.uuid4().hex[:12]}", email=email,
                    name=data.get("name", email), picture=data.get("picture"), role=role)
        await db.users.insert_one(user.model_dump())

    session_token = data["session_token"]
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user.user_id, "session_token": session_token,
        "expires_at": expires.isoformat(), "created_at": now_utc(),
    })
    response.set_cookie(key="session_token", value=session_token, httponly=True,
                        secure=True, samesite="none", path="/", max_age=7 * 24 * 3600)
    return {"user": user.model_dump()}


@api_router.get("/auth/me")
async def me(user: User = Depends(get_current_user)):
    return user.model_dump()


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


# ---------------- Users / Operadores (ADM only) ----------------
@api_router.get("/users")
async def list_users(user: User = Depends(require_roles("adm_master"))):
    docs = await db.users.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return docs


@api_router.put("/users/{user_id}")
async def update_user_role(user_id: str, upd: RoleUpdate, user: User = Depends(require_roles("adm_master"))):
    if upd.role not in ("adm_master", "operador", "coordenador"):
        raise HTTPException(status_code=400, detail="Perfil inválido")
    changes = {"role": upd.role}
    if upd.active is not None:
        changes["active"] = upd.active
    res = await db.users.update_one({"user_id": user_id}, {"$set": changes})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return doc


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: User = Depends(require_roles("adm_master"))):
    if user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Não é possível remover o próprio usuário")
    await db.users.delete_one({"user_id": user_id})
    await db.user_sessions.delete_many({"user_id": user_id})
    return {"ok": True}


# ---------------- Generic CRUD factory ----------------
def crud_routes(path, coll, CreateModel, DocModel):
    @api_router.get(f"/{path}", name=f"list_{path}")
    async def _list(user: User = Depends(get_current_user)):
        return await db[coll].find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)

    @api_router.post(f"/{path}", name=f"create_{path}")
    async def _create(payload: CreateModel, user: User = Depends(require_roles(*WRITE_ROLES))):
        obj = DocModel(**payload.model_dump())
        await db[coll].insert_one(obj.model_dump())
        return obj.model_dump()

    @api_router.put(f"/{path}/{{item_id}}", name=f"update_{path}")
    async def _update(item_id: str, payload: CreateModel, user: User = Depends(require_roles(*WRITE_ROLES))):
        res = await db[coll].update_one({"id": item_id}, {"$set": payload.model_dump()})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Registro não encontrado")
        return await db[coll].find_one({"id": item_id}, {"_id": 0})

    @api_router.delete(f"/{path}/{{item_id}}", name=f"delete_{path}")
    async def _delete(item_id: str, user: User = Depends(require_roles(*WRITE_ROLES))):
        await db[coll].delete_one({"id": item_id})
        return {"ok": True}


crud_routes("cursos", "cursos", CursoCreate, Curso)
crud_routes("professores", "professores", ProfessorCreate, Professor)
crud_routes("disciplinas", "disciplinas", DisciplinaCreate, Disciplina)
crud_routes("feriados", "feriados", FeriadoCreate, Feriado)
crud_routes("aulas-remotas", "aulas_remotas", AulaRemotaCreate, AulaRemota)


# ---------------- Grade Horária ----------------
@api_router.get("/config/slots")
async def config_slots(user: User = Depends(get_current_user)):
    return {"turnos": {k: [{"hora_inicio": s[0], "hora_fim": s[1]} for s in v] for k, v in TURNO_SLOTS.items()},
            "dias": DIAS_SEMANA}


@api_router.get("/grades")
async def list_grades(curso_id: Optional[str] = None, user: User = Depends(get_current_user)):
    q = {"curso_id": curso_id} if curso_id else {}
    return await db.grades.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)


@api_router.get("/grades/{grade_id}")
async def get_grade(grade_id: str, user: User = Depends(get_current_user)):
    doc = await db.grades.find_one({"id": grade_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Grade não encontrada")
    return doc


@api_router.post("/grades")
async def save_grade(payload: GradeCreate, user: User = Depends(require_roles(*WRITE_ROLES))):
    obj = Grade(**payload.model_dump())
    await db.grades.insert_one(obj.model_dump())
    return obj.model_dump()


@api_router.put("/grades/{grade_id}")
async def update_grade(grade_id: str, payload: GradeCreate, user: User = Depends(require_roles(*WRITE_ROLES))):
    changes = payload.model_dump()
    changes["updated_at"] = now_utc()
    res = await db.grades.update_one({"id": grade_id}, {"$set": changes})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Grade não encontrada")
    return await db.grades.find_one({"id": grade_id}, {"_id": 0})


@api_router.delete("/grades/{grade_id}")
async def delete_grade(grade_id: str, user: User = Depends(require_roles(*WRITE_ROLES))):
    await db.grades.delete_one({"id": grade_id})
    return {"ok": True}


@api_router.post("/grades/auto-generate")
async def grade_auto_generate(req: AutoGenRequest, user: User = Depends(require_roles(*WRITE_ROLES))):
    disciplinas = await db.disciplinas.find({"curso_id": req.curso_id}, {"_id": 0}).to_list(500)
    if not disciplinas:
        raise HTTPException(status_code=400, detail="Nenhuma disciplina cadastrada para este curso")

    # professor busy set from OTHER grades (all grades not of this curso/period combination)
    other = await db.grades.find({"$or": [
        {"curso_id": {"$ne": req.curso_id}},
        {"ano": {"$ne": req.ano}},
        {"semestre": {"$ne": req.semestre}},
    ]}, {"_id": 0}).to_list(2000)
    busy = set()
    for g in other:
        for e in g.get("entries", []):
            if e.get("professor_id"):
                busy.add((e["professor_id"], e["dia_semana"], e["hora_inicio"]))

    entries, conflicts = auto_generate(disciplinas, busy, req.turno)
    return {"entries": entries, "conflicts": conflicts,
            "curso_id": req.curso_id, "ano": req.ano, "semestre": req.semestre, "turno": req.turno}


# ---------------- Consultas / Mapa de Frequência ----------------
@api_router.get("/frequencia/professor/{professor_id}")
async def consulta_professor(professor_id: str, user: User = Depends(get_current_user)):
    grades = await db.grades.find({}, {"_id": 0}).to_list(2000)
    disciplinas = {d["id"]: d for d in await db.disciplinas.find({}, {"_id": 0}).to_list(2000)}
    cursos = {c["id"]: c for c in await db.cursos.find({}, {"_id": 0}).to_list(2000)}
    result = []
    for g in grades:
        for e in g.get("entries", []):
            if e.get("professor_id") == professor_id:
                disc = disciplinas.get(e["disciplina_id"], {})
                curso = cursos.get(g["curso_id"], {})
                result.append({
                    "dia_semana": e["dia_semana"], "dia_nome": DIAS_SEMANA[e["dia_semana"]],
                    "hora_inicio": e["hora_inicio"], "hora_fim": e["hora_fim"],
                    "disciplina": disc.get("nome", "-"), "curso": curso.get("nome", "-"),
                    "turno": g.get("turno"),
                })
    result.sort(key=lambda x: (x["dia_semana"], x["hora_inicio"]))
    return result


@api_router.get("/frequencia/mapa/{grade_id}")
async def mapa_frequencia(grade_id: str, user: User = Depends(get_current_user)):
    grade = await db.grades.find_one({"id": grade_id}, {"_id": 0})
    if not grade:
        raise HTTPException(status_code=404, detail="Grade não encontrada")
    disciplinas = {d["id"]: d for d in await db.disciplinas.find({}, {"_id": 0}).to_list(2000)}
    professores = {p["id"]: p for p in await db.professores.find({}, {"_id": 0}).to_list(2000)}
    slots = get_slots(grade.get("turno", "noturno"))
    grid = {}
    for e in grade.get("entries", []):
        disc = disciplinas.get(e["disciplina_id"], {})
        prof = professores.get(e.get("professor_id"), {})
        grid[f'{e["slot_index"]}_{e["dia_semana"]}'] = {
            "disciplina": disc.get("nome", "-"), "codigo": disc.get("codigo", ""),
            "professor": prof.get("nome", "-"),
        }
    return {"turno": grade.get("turno"), "slots": [{"hora_inicio": s[0], "hora_fim": s[1]} for s in slots],
            "dias": DIAS_SEMANA, "grid": grid}


# ---------------- PDF ----------------
async def _build_context(ano: int, mes: int):
    feriados_docs = await db.feriados.find({}, {"_id": 0}).to_list(2000)
    feriados = {}
    for f in feriados_docs:
        d = f["data"]
        try:
            dt = datetime.fromisoformat(d)
            if dt.year == ano and dt.month == mes:
                feriados[d[:10]] = f["descricao"]
        except Exception:
            pass
    remotas_docs = await db.aulas_remotas.find({}, {"_id": 0}).to_list(2000)
    disciplinas = {d["id"]: d for d in await db.disciplinas.find({}, {"_id": 0}).to_list(2000)}
    return feriados, remotas_docs, disciplinas


@api_router.get("/pdf/professor/{professor_id}")
async def pdf_professor(professor_id: str, ano: int, mes: int, curso_id: Optional[str] = None,
                        user: User = Depends(get_current_user)):
    prof = await db.professores.find_one({"id": professor_id}, {"_id": 0})
    if not prof:
        raise HTTPException(status_code=404, detail="Professor não encontrado")
    curso = await db.cursos.find_one({"id": curso_id}, {"_id": 0}) if curso_id else None
    feriados, remotas_docs, disciplinas = await _build_context(ano, mes)

    q = {"curso_id": curso_id} if curso_id else {}
    grades = await db.grades.find(q, {"_id": 0}).to_list(2000)
    entries_prof = []
    for g in grades:
        for e in g.get("entries", []):
            if e.get("professor_id") == professor_id:
                entries_prof.append(e)

    remotas = set()
    for r in remotas_docs:
        if r.get("professor_id") in (None, professor_id) and (curso_id is None or r.get("curso_id") in (None, curso_id)):
            try:
                dt = datetime.fromisoformat(r["data"])
                if dt.year == ano and dt.month == mes:
                    remotas.add(r["data"][:10])
            except Exception:
                pass

    buf = pdfg.gerar_folha_professor(prof, curso, entries_prof, ano, mes, feriados, remotas, disciplinas)
    fname = f"folha_ponto_{prof['nome'].replace(' ', '_')}_{mes:02d}_{ano}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@api_router.get("/pdf/curso/{curso_id}")
async def pdf_curso(curso_id: str, ano: int, mes: int, user: User = Depends(get_current_user)):
    curso = await db.cursos.find_one({"id": curso_id}, {"_id": 0})
    if not curso:
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    feriados, remotas_docs, disciplinas = await _build_context(ano, mes)
    professores = {p["id"]: p for p in await db.professores.find({}, {"_id": 0}).to_list(2000)}

    grades = await db.grades.find({"curso_id": curso_id}, {"_id": 0}).to_list(2000)
    per_prof = {}
    for g in grades:
        for e in g.get("entries", []):
            pid = e.get("professor_id")
            if pid:
                per_prof.setdefault(pid, []).append(e)

    professores_entries = [(professores.get(pid, {"id": pid, "nome": "?"}), ents)
                           for pid, ents in per_prof.items()]
    professores_entries.sort(key=lambda x: x[0].get("nome", ""))

    remotas_por_prof = {}
    for r in remotas_docs:
        if curso_id is not None and r.get("curso_id") not in (None, curso_id):
            continue
        try:
            dt = datetime.fromisoformat(r["data"])
            if dt.year == ano and dt.month == mes:
                pid = r.get("professor_id")
                if pid:
                    remotas_por_prof.setdefault(pid, set()).add(r["data"][:10])
                else:
                    for p in per_prof:
                        remotas_por_prof.setdefault(p, set()).add(r["data"][:10])
        except Exception:
            pass

    buf = pdfg.gerar_folha_curso(curso, professores_entries, ano, mes, feriados, remotas_por_prof, disciplinas)
    fname = f"mapa_frequencia_{curso['sigla']}_{mes:02d}_{ano}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ---------------- Dashboard stats ----------------
@api_router.get("/stats")
async def stats(user: User = Depends(get_current_user)):
    return {
        "cursos": await db.cursos.count_documents({}),
        "professores": await db.professores.count_documents({}),
        "disciplinas": await db.disciplinas.count_documents({}),
        "feriados": await db.feriados.count_documents({}),
        "aulas_remotas": await db.aulas_remotas.count_documents({}),
        "grades": await db.grades.count_documents({}),
        "operadores": await db.users.count_documents({}),
    }


@api_router.get("/")
async def root():
    return {"message": "Ponto Acadêmico FATEC API"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
