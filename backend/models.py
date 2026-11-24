from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "coordenador"
    active: bool = True
    created_at: str = Field(default_factory=now_utc)


class RoleUpdate(BaseModel):
    role: str
    active: Optional[bool] = None


class CursoCreate(BaseModel):
    nome: str = Field(..., min_length=1)
    sigla: str = Field(..., min_length=1)
    turno: str = "noturno"
    coordenador_nome: Optional[str] = ""


class Curso(CursoCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


class ProfessorCreate(BaseModel):
    nome: str = Field(..., min_length=1)
    email: Optional[str] = ""
    cpf: Optional[str] = ""
    titulacao: Optional[str] = "Especialista"
    registro: Optional[str] = ""


class Professor(ProfessorCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


class DisciplinaCreate(BaseModel):
    nome: str = Field(..., min_length=1)
    codigo: str = Field(..., min_length=1)
    curso_id: str = Field(..., min_length=1)
    professor_id: Optional[str] = None
    aulas_por_semana: int = Field(default=2, ge=1, le=20)
    carga_horaria: int = Field(default=40, ge=0)


class Disciplina(DisciplinaCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


class FeriadoCreate(BaseModel):
    data: str = Field(..., min_length=10)
    descricao: str = Field(..., min_length=1)
    tipo: str = "Nacional"


class Feriado(FeriadoCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


class AulaRemotaCreate(BaseModel):
    data: str = Field(..., min_length=10)
    curso_id: Optional[str] = None
    disciplina_id: Optional[str] = None
    professor_id: Optional[str] = None
    descricao: Optional[str] = ""


class AulaRemota(AulaRemotaCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)


class GradeEntry(BaseModel):
    dia_semana: int = Field(..., ge=0, le=4)
    slot_index: int = Field(..., ge=0)
    hora_inicio: str
    hora_fim: str
    disciplina_id: str
    professor_id: Optional[str] = None


class GradeCreate(BaseModel):
    curso_id: str
    ano: int = Field(..., ge=2000, le=2100)
    semestre: int = Field(default=1, ge=1, le=2)
    turno: str = "noturno"
    entries: List[GradeEntry] = []


class Grade(GradeCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_utc)
    updated_at: str = Field(default_factory=now_utc)


class AutoGenRequest(BaseModel):
    curso_id: str
    ano: int = Field(..., ge=2000, le=2100)
    semestre: int = Field(default=1, ge=1, le=2)
    turno: str = "noturno"
