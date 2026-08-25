from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ---------- Auth ----------
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "coordenador"  # adm_master | operador | coordenador
    active: bool = True
    created_at: str = Field(default_factory=now_utc)


class RoleUpdate(BaseModel):
    role: str
    active: Optional[bool] = None


# ---------- Curso ----------
class CursoCreate(BaseModel):
    nome: str
    sigla: str
    turno: str = "noturno"  # matutino | vespertino | noturno
    coordenador_nome: Optional[str] = ""


class Curso(CursoCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


# ---------- Professor ----------
class ProfessorCreate(BaseModel):
    nome: str
    email: Optional[str] = ""
    cpf: Optional[str] = ""
    titulacao: Optional[str] = "Especialista"
    registro: Optional[str] = ""


class Professor(ProfessorCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


# ---------- Disciplina ----------
class DisciplinaCreate(BaseModel):
    nome: str
    codigo: str
    curso_id: str
    professor_id: Optional[str] = None
    aulas_por_semana: int = 2
    carga_horaria: int = 40


class Disciplina(DisciplinaCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


# ---------- Feriado ----------
class FeriadoCreate(BaseModel):
    data: str  # YYYY-MM-DD
    descricao: str
    tipo: str = "Nacional"  # Nacional | Estadual | Institucional


class Feriado(FeriadoCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


# ---------- Aula Remota ----------
class AulaRemotaCreate(BaseModel):
    data: str  # YYYY-MM-DD
    curso_id: Optional[str] = None
    disciplina_id: Optional[str] = None
    professor_id: Optional[str] = None
    descricao: Optional[str] = ""


class AulaRemota(AulaRemotaCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


# ---------- Grade Horária ----------
class GradeEntry(BaseModel):
    dia_semana: int  # 0=Segunda ... 4=Sexta
    slot_index: int
    hora_inicio: str
    hora_fim: str
    disciplina_id: str
    professor_id: Optional[str] = None


class GradeCreate(BaseModel):
    curso_id: str
    ano: int
    semestre: int = 1
    turno: str = "noturno"
    entries: List[GradeEntry] = []


class Grade(GradeCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)
    updated_at: str = Field(default_factory=now_utc)


class AutoGenRequest(BaseModel):
    curso_id: str
    ano: int
    semestre: int = 1
    turno: str = "noturno"
