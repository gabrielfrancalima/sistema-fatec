from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Query
from fastapi.responses import StreamingResponse, RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from urllib.parse import urlencode
import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
import secrets
import requests
import msal
from itsdangerous import URLSafeSerializer, BadSignature

from models import (
    User, RoleUpdate, Curso, CursoCreate, Professor, ProfessorCreate,
    Disciplina, DisciplinaCreate, Feriado, FeriadoCreate, AulaRemota, AulaRemotaCreate,
    Grade, GradeCreate, AutoGenRequest, now_utc,
)
from scheduling import auto_generate, get_slots, DIAS_SEMANA, TURNO_SLOTS
import pdf_generator as pdfg

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ponto_fatec")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongo:27017")
DB_NAME = os.environ.get("DB_NAME", "ponto_fatec")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "gabrielpedra1999@gmail.com").lower()

AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "organizations")
AZURE_REDIRECT_URI = os.environ.get("AZURE_REDIRECT_URI", "")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
APP_SECRET = os.environ.get("APP_SECRET", "fatec-ponto-academico-dev-secret")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "none" if COOKIE_SECURE else "lax")
ALLOW_LOCAL_DEMO_LOGIN = os.environ.get("ALLOW_LOCAL_DEMO_LOGIN", "false").lower() == "true"

MS_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
MS_SCOPES = ["User.Read"]
MS_ENABLED = bool(AZURE_CLIENT_ID and AZURE_CLIENT_SECRET and AZURE_REDIRECT_URI)
GOOGLE_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI)

flow_signer = URLSafeSerializer(APP_SECRET, salt="ms-oauth-flow")
google_signer = URLSafeSerializer(APP_SECRET, salt="google-oauth-state")
FLOW_COOKIE = "ms_oauth_flow"
GOOGLE_STATE_COOKIE = "google_oauth_state"

ALLOWED_EMAIL_DOMAINS = [
    d.strip().lower()
    for d in os.environ.get("ALLOWED_EMAIL_DOMAINS", "").split(",")
    if d.strip()
]
_DOMAIN_MSG = (
    "Acesso permitido apenas para contas institucionais"
    + (f" ({', '.join('@' + d for d in ALLOWED_EMAIL_DOMAINS)})." if ALLOWED_EMAIL_DOMAINS else ".")
)

WRITE_ROLES = ("adm_master", "operador")

client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]


def _email_allowed(email: str) -> bool:
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False
    if ADMIN_EMAIL and email == ADMIN_EMAIL:
        return True
    if not ALLOWED_EMAIL_DOMAINS:
        return True
    domain = email.split("@")[-1]
    return any(domain == d or domain.endswith("." + d) for d in ALLOWED_EMAIL_DOMAINS)


async def _ensure_indexes():
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.user_sessions.create_index("user_id")
    for coll in ("cursos", "professores", "disciplinas", "feriados", "aulas_remotas", "grades"):
        await db[coll].create_index("id", unique=True)


async def _seed_local_environment():
    if not ALLOW_LOCAL_DEMO_LOGIN:
        return

    seed_users = [
        ("admin_seed_01", ADMIN_EMAIL or "gabrielpedra1999@gmail.com", "Gabriel de França Lima", "adm_master", "seed_session_admin_001"),
        ("op_seed_01", "operador.secretaria@fatec.sp.gov.br", "Secretaria Acadêmica (Operador)", "operador", "seed_session_op_001"),
        ("coord_seed_01", "coordenador.ads@fatec.sp.gov.br", "Coordenação ADS", "coordenador", "seed_session_co_001"),
    ]
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    for uid, email, name, role, token in seed_users:
        existing_by_id = await db.users.find_one({"user_id": uid})
        existing_by_email = await db.users.find_one({"email": email.lower()})
        if not existing_by_id and not existing_by_email:
            await db.users.insert_one(
                User(user_id=uid, email=email.lower(), name=name, role=role, active=True).model_dump()
            )
            target_uid = uid
        else:
            target_uid = (existing_by_id or existing_by_email)["user_id"]
        await db.user_sessions.update_one(
            {"session_token": token},
            {"$set": {"user_id": target_uid, "session_token": token, "expires_at": expires, "created_at": now_utc()}},
            upsert=True,
        )

    if await db.cursos.count_documents({}) == 0:
        c_ads = Curso(nome="Análise e Desenvolvimento de Sistemas", sigla="ADS", turno="noturno", coordenador_nome="Prof. Dr. Carlos Henrique").model_dump()
        c_dsm = Curso(nome="Desenvolvimento de Software Multiplataforma", sigla="DSM", turno="noturno", coordenador_nome="Profa. Dra. Fernanda Costa").model_dump()
        c_ge = Curso(nome="Gestão Empresarial", sigla="GE", turno="matutino", coordenador_nome="Profa. Me. Ana Paula Oliveira").model_dump()
        await db.cursos.insert_many([c_ads, c_dsm, c_ge])

        p1 = Professor(nome="Prof. Dr. Carlos Eduardo Silva", email="carlos.silva@fatec.sp.gov.br", cpf="284.910.388-12", titulacao="Doutor", registro="MAT-10492").model_dump()
        p2 = Professor(nome="Profa. Dra. Fernanda Costa", email="fernanda.costa@fatec.sp.gov.br", cpf="402.119.838-45", titulacao="Doutor", registro="MAT-10219").model_dump()
        p3 = Professor(nome="Profa. Me. Ana Paula Oliveira", email="ana.oliveira@fatec.sp.gov.br", cpf="319.482.118-04", titulacao="Mestre", registro="MAT-10841").model_dump()
        p4 = Professor(nome="Prof. Esp. Roberto Almeida", email="roberto.almeida@fatec.sp.gov.br", cpf="192.847.558-90", titulacao="Especialista", registro="MAT-11205").model_dump()
        await db.professores.insert_many([p1, p2, p3, p4])

        d1 = Disciplina(nome="Laboratório de Engenharia de Software", codigo="IES300", curso_id=c_ads["id"], professor_id=p1["id"], aulas_por_semana=4, carga_horaria=80).model_dump()
        d2 = Disciplina(nome="Banco de Dados Relacional", codigo="IBD002", curso_id=c_ads["id"], professor_id=p2["id"], aulas_por_semana=4, carga_horaria=80).model_dump()
        d3 = Disciplina(nome="Estrutura de Dados", codigo="IED001", curso_id=c_ads["id"], professor_id=p4["id"], aulas_por_semana=4, carga_horaria=80).model_dump()
        d4 = Disciplina(nome="Interação Humano-Computador", codigo="IHC001", curso_id=c_ads["id"], professor_id=p3["id"], aulas_por_semana=2, carga_horaria=40).model_dump()
        d5 = Disciplina(nome="Programação Web II", codigo="DSM201", curso_id=c_dsm["id"], professor_id=p1["id"], aulas_por_semana=4, carga_horaria=80).model_dump()
        d6 = Disciplina(nome="Gestão de Projetos Ágeis", codigo="AGE102", curso_id=c_ge["id"], professor_id=p3["id"], aulas_por_semana=4, carga_horaria=80).model_dump()
        await db.disciplinas.insert_many([d1, d2, d3, d4, d5, d6])

        feriados_seed = [
            Feriado(data="2026-11-02", descricao="Finados", tipo="Nacional").model_dump(),
            Feriado(data="2026-11-15", descricao="Proclamação da República", tipo="Nacional").model_dump(),
            Feriado(data="2026-11-20", descricao="Dia da Consciência Negra", tipo="Nacional").model_dump(),
        ]
        await db.feriados.insert_many(feriados_seed)

        remotas_seed = [
            AulaRemota(data="2026-11-12", curso_id=c_ads["id"], disciplina_id=d1["id"], professor_id=p1["id"], descricao="Semana de Tecnologia via Microsoft Teams").model_dump(),
            AulaRemota(data="2026-11-18", curso_id=c_ads["id"], disciplina_id=d2["id"], professor_id=p2["id"], descricao="Atividade síncrona EAD").model_dump(),
        ]
        await db.aulas_remotas.insert_many(remotas_seed)

        entries_ads, _ = auto_generate([d1, d2, d3, d4], set(), "noturno")
        grade_ads = Grade(curso_id=c_ads["id"], ano=2026, semestre=2, turno="noturno", entries=entries_ads).model_dump()
        await db.grades.insert_one(grade_ads)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await _ensure_indexes()
        await _seed_local_environment()
        logger.info("Ponto Acadêmico FATEC API pronta e conectada ao MongoDB.")
    except Exception as exc:
        logger.warning("Aviso durante inicialização: %s", exc)
    yield
    client.close()


app = FastAPI(title="Ponto Acadêmico FATEC", version="1.0.0", lifespan=lifespan)
api_router = APIRouter(prefix="/api")


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


async def _create_session(user: User) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user.user_id,
        "session_token": token,
        "expires_at": expires.isoformat(),
        "created_at": now_utc(),
    })
    return token


async def _upsert_user(email: str, name: str, picture: Optional[str] = None) -> User:
    email = email.strip().lower()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user = User(**existing)
        updates = {"name": name or user.name}
        if picture:
            updates["picture"] = picture
        await db.users.update_one({"user_id": user.user_id}, {"$set": updates})
        user.name = updates["name"]
        if picture:
            user.picture = picture
        return user
    role = "adm_master" if (ADMIN_EMAIL and email == ADMIN_EMAIL) else "coordenador"
    user = User(
        user_id=f"user_{uuid.uuid4().hex[:12]}",
        email=email,
        name=name or email,
        picture=picture,
        role=role,
    )
    await db.users.insert_one(user.model_dump())
    return user


def _msal_app():
    return msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID,
        authority=MS_AUTHORITY,
        client_credential=AZURE_CLIENT_SECRET,
    )


@api_router.get("/health")
async def health():
    try:
        await db.command("ping")
        return {
            "status": "ok",
            "database": "connected",
            "service": "ponto-academico-fatec",
            "timestamp": now_utc(),
        }
    except Exception as exc:
        logger.error("Healthcheck DB failure: %s", exc)
        raise HTTPException(status_code=503, detail="Banco de dados indisponível")


@api_router.get("/auth/config")
async def auth_config():
    return {
        "microsoft_enabled": MS_ENABLED,
        "google_enabled": GOOGLE_ENABLED,
        "demo_login_enabled": ALLOW_LOCAL_DEMO_LOGIN,
    }


@api_router.post("/auth/demo-login")
async def demo_login(request: Request, response: Response):
    if not ALLOW_LOCAL_DEMO_LOGIN:
        raise HTTPException(status_code=403, detail="Login local de demonstração desativado")
    body = await request.json()
    role = body.get("role", "adm_master")
    role_map = {
        "adm_master": ("admin_seed_01", ADMIN_EMAIL or "gabrielpedra1999@gmail.com", "Gabriel de França Lima"),
        "operador": ("op_seed_01", "operador.secretaria@fatec.sp.gov.br", "Secretaria Acadêmica (Operador)"),
        "coordenador": ("coord_seed_01", "coordenador.ads@fatec.sp.gov.br", "Coordenação ADS"),
    }
    if role not in role_map:
        raise HTTPException(status_code=400, detail="Perfil de demonstração inválido")

    uid, email, name = role_map[role]
    existing = await db.users.find_one({"user_id": uid}, {"_id": 0})
    if not existing:
        existing = await db.users.find_one({"email": email.lower()}, {"_id": 0})
    if not existing:
        user = User(user_id=uid, email=email.lower(), name=name, role=role, active=True)
        await db.users.insert_one(user.model_dump())
    else:
        user = User(**existing)
        if not user.active:
            raise HTTPException(status_code=403, detail="Usuário desativado")

    token = await _create_session(user)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
        max_age=7 * 24 * 3600,
    )
    return {"user": user.model_dump()}


@api_router.get("/auth/google/login")
async def google_login():
    if not GOOGLE_ENABLED:
        raise HTTPException(status_code=503, detail="Login Google não configurado neste ambiente")
    state = secrets.token_urlsafe(24)
    params = urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
    payload = {"state": state, "exp": int(datetime.now(timezone.utc).timestamp()) + 600}
    redirect = RedirectResponse(auth_url, status_code=302)
    redirect.set_cookie(
        GOOGLE_STATE_COOKIE,
        google_signer.dumps(payload),
        max_age=600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/api/auth/google",
    )
    return redirect


@api_router.get("/auth/google/callback")
async def google_callback(request: Request):
    def fail(code):
        return RedirectResponse(f"{FRONTEND_URL}/?error={code}", status_code=302)

    cookie = request.cookies.get(GOOGLE_STATE_COOKIE)
    if not cookie:
        return fail("google_flow")
    try:
        saved = google_signer.loads(cookie)
        if saved["exp"] < int(datetime.now(timezone.utc).timestamp()):
            raise BadSignature("expired")
    except BadSignature:
        return fail("google_flow")

    if request.query_params.get("error"):
        return fail("google_denied")
    if request.query_params.get("state") != saved.get("state"):
        return fail("google_flow")

    code = request.query_params.get("code")
    if not code:
        return fail("google_oauth")

    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if token_resp.status_code != 200:
        return fail("google_token")

    access_token = token_resp.json().get("access_token")
    if not access_token:
        return fail("google_token")

    info_resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if info_resp.status_code != 200:
        return fail("google_token")

    profile = info_resp.json()
    email = (profile.get("email") or "").strip().lower()
    name = (profile.get("name") or "").strip()
    picture = profile.get("picture")
    if not email:
        return fail("auth")

    if not _email_allowed(email):
        return fail("domain")

    user = await _upsert_user(email, name, picture)
    if not user.active:
        return fail("inactive")

    token = await _create_session(user)
    redirect = RedirectResponse(f"{FRONTEND_URL}/dashboard", status_code=302)
    redirect.delete_cookie(GOOGLE_STATE_COOKIE, path="/api/auth/google")
    redirect.set_cookie(
        "session_token",
        token,
        max_age=7 * 24 * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    return redirect


@api_router.get("/auth/microsoft/login")
async def ms_login():
    if not MS_ENABLED:
        raise HTTPException(status_code=503, detail="Login Microsoft não configurado")
    flow = _msal_app().initiate_auth_code_flow(scopes=MS_SCOPES, redirect_uri=AZURE_REDIRECT_URI)
    if "error" in flow:
        raise HTTPException(status_code=500, detail="Falha ao iniciar login Microsoft")
    payload = {"flow": flow, "exp": int(datetime.now(timezone.utc).timestamp()) + 600}
    redirect = RedirectResponse(flow["auth_uri"], status_code=302)
    redirect.set_cookie(
        FLOW_COOKIE,
        flow_signer.dumps(payload),
        max_age=600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/api/auth/microsoft",
    )
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
    redirect.set_cookie(
        "session_token",
        token,
        max_age=7 * 24 * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    return redirect


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


@api_router.get("/users")
async def list_users(user: User = Depends(require_roles("adm_master"))):
    return await db.users.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


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
    return await db.users.find_one({"user_id": user_id}, {"_id": 0})


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: User = Depends(require_roles("adm_master"))):
    if user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Não é possível remover o próprio usuário")
    await db.users.delete_one({"user_id": user_id})
    await db.user_sessions.delete_many({"user_id": user_id})
    return {"ok": True}


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


@api_router.get("/config/slots")
async def config_slots(user: User = Depends(get_current_user)):
    return {
        "turnos": {k: [{"hora_inicio": s[0], "hora_fim": s[1]} for s in v] for k, v in TURNO_SLOTS.items()},
        "dias": DIAS_SEMANA,
    }


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

    other = await db.grades.find(
        {
            "curso_id": {"$ne": req.curso_id},
            "ano": req.ano,
            "semestre": req.semestre,
        },
        {"_id": 0},
    ).to_list(2000)
    busy = set()
    for g in other:
        for e in g.get("entries", []):
            if e.get("professor_id"):
                busy.add((e["professor_id"], e["dia_semana"], e["hora_inicio"]))

    entries, conflicts = auto_generate(disciplinas, busy, req.turno)
    return {
        "entries": entries,
        "conflicts": conflicts,
        "curso_id": req.curso_id,
        "ano": req.ano,
        "semestre": req.semestre,
        "turno": req.turno,
    }


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
                dia_idx = e["dia_semana"]
                dia_nome = DIAS_SEMANA[dia_idx] if 0 <= dia_idx < len(DIAS_SEMANA) else "-"
                result.append({
                    "dia_semana": dia_idx,
                    "dia_nome": dia_nome,
                    "hora_inicio": e["hora_inicio"],
                    "hora_fim": e["hora_fim"],
                    "disciplina": disc.get("nome", "-"),
                    "curso": curso.get("nome", "-"),
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
            "disciplina": disc.get("nome", "-"),
            "codigo": disc.get("codigo", ""),
            "professor": prof.get("nome", "-"),
        }
    return {
        "turno": grade.get("turno"),
        "slots": [{"hora_inicio": s[0], "hora_fim": s[1]} for s in slots],
        "dias": DIAS_SEMANA,
        "grid": grid,
    }


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
async def pdf_professor(
    professor_id: str,
    ano: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
    curso_id: Optional[str] = None,
    user: User = Depends(get_current_user),
):
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
    safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in prof["nome"].replace(" ", "_"))
    fname = f"folha_ponto_{safe_name}_{mes:02d}_{ano}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@api_router.get("/pdf/curso/{curso_id}")
async def pdf_curso(
    curso_id: str,
    ano: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
    user: User = Depends(get_current_user),
):
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

    professores_entries = [
        (professores.get(pid, {"id": pid, "nome": "?"}), ents)
        for pid, ents in per_prof.items()
    ]
    professores_entries.sort(key=lambda x: x[0].get("nome", ""))

    remotas_por_prof = {}
    for r in remotas_docs:
        if r.get("curso_id") not in (None, curso_id):
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
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


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
    return {"message": "Ponto Acadêmico FATEC API", "version": "1.0.0"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
