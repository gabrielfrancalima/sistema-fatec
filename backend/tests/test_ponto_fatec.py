"""Backend tests for Ponto Acadêmico FATEC.
Covers: auth, RBAC, CRUDs (cursos/professores/disciplinas/feriados/aulas-remotas),
grade auto-generate (with professor conflict across courses), grade save/list/delete,
frequencia (professor + mapa), PDF generation (professor + curso), operadores mgmt.
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = "seed_session_admin_001"
OPERADOR = "seed_session_op_001"
COORD = "seed_session_co_001"


def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---- created ids to cleanup ----
created = {"cursos": [], "professores": [], "disciplinas": [], "feriados": [],
           "aulas-remotas": [], "grades": []}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for path, ids in created.items():
        for i in ids:
            try:
                requests.delete(f"{API}/{path}/{i}", headers=h(ADMIN), timeout=10)
            except Exception:
                pass


# ---------------- Auth ----------------
class TestAuth:
    def test_me_no_auth(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_me_admin(self):
        r = requests.get(f"{API}/auth/me", headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "adm_master"
        assert d["email"] == "gabrielpedra1999@gmail.com"

    def test_me_operador(self):
        r = requests.get(f"{API}/auth/me", headers=h(OPERADOR), timeout=10)
        assert r.status_code == 200
        assert r.json()["role"] == "operador"

    def test_me_coordenador(self):
        r = requests.get(f"{API}/auth/me", headers=h(COORD), timeout=10)
        assert r.status_code == 200
        assert r.json()["role"] == "coordenador"

    def test_invalid_token(self):
        r = requests.get(f"{API}/auth/me", headers=h("nope"), timeout=10)
        assert r.status_code == 401


# ---------------- RBAC on writes ----------------
class TestRBAC:
    def test_coord_blocked_on_write(self):
        r = requests.post(f"{API}/cursos", json={"nome": "X", "sigla": "X", "turno": "noturno"},
                          headers=h(COORD), timeout=10)
        assert r.status_code == 403

    def test_coord_can_read(self):
        r = requests.get(f"{API}/cursos", headers=h(COORD), timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_operador_can_write(self):
        r = requests.post(f"{API}/cursos", json={"nome": "TEST_OPWRITE", "sigla": "OPW", "turno": "noturno"},
                          headers=h(OPERADOR), timeout=10)
        assert r.status_code == 200
        cid = r.json()["id"]
        created["cursos"].append(cid)


# ---------------- CRUD Cursos ----------------
class TestCursos:
    def test_crud(self):
        r = requests.post(f"{API}/cursos", json={"nome": "TEST_ADS", "sigla": "TADS",
                                                 "turno": "noturno", "coordenador_nome": "Coord"},
                          headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        cid = r.json()["id"]
        created["cursos"].append(cid)

        # list
        r = requests.get(f"{API}/cursos", headers=h(ADMIN), timeout=10)
        assert any(c["id"] == cid for c in r.json())

        # update
        r = requests.put(f"{API}/cursos/{cid}", json={"nome": "TEST_ADS2", "sigla": "TADS",
                                                      "turno": "noturno"}, headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        assert r.json()["nome"] == "TEST_ADS2"

    def test_update_missing(self):
        r = requests.put(f"{API}/cursos/does-not-exist",
                         json={"nome": "x", "sigla": "x", "turno": "noturno"},
                         headers=h(ADMIN), timeout=10)
        assert r.status_code == 404


# ---------------- CRUD Professores ----------------
class TestProfessores:
    def test_create_list(self):
        r = requests.post(f"{API}/professores",
                          json={"nome": "TEST_ProfA", "email": "a@t.com", "titulacao": "Mestre"},
                          headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        created["professores"].append(r.json()["id"])
        r2 = requests.get(f"{API}/professores", headers=h(ADMIN), timeout=10)
        assert r2.status_code == 200


# ---------------- Full flow: curso -> professor -> disciplinas -> grade ----------------
@pytest.fixture(scope="module")
def flow_ids():
    # Course A
    ca = requests.post(f"{API}/cursos", json={"nome": "TEST_CursoA", "sigla": "CA",
                                              "turno": "noturno"}, headers=h(ADMIN), timeout=10).json()["id"]
    cb = requests.post(f"{API}/cursos", json={"nome": "TEST_CursoB", "sigla": "CB",
                                              "turno": "noturno"}, headers=h(ADMIN), timeout=10).json()["id"]
    created["cursos"].extend([ca, cb])

    # Shared professor
    p1 = requests.post(f"{API}/professores", json={"nome": "TEST_ProfShared"},
                       headers=h(ADMIN), timeout=10).json()["id"]
    p2 = requests.post(f"{API}/professores", json={"nome": "TEST_ProfOther"},
                       headers=h(ADMIN), timeout=10).json()["id"]
    created["professores"].extend([p1, p2])

    # Disciplinas for course A - many aulas so it fills week
    da1 = requests.post(f"{API}/disciplinas", json={"nome": "TEST_DA1", "codigo": "DA1",
                                                    "curso_id": ca, "professor_id": p1,
                                                    "aulas_por_semana": 4},
                        headers=h(ADMIN), timeout=10).json()["id"]
    da2 = requests.post(f"{API}/disciplinas", json={"nome": "TEST_DA2", "codigo": "DA2",
                                                    "curso_id": ca, "professor_id": p2,
                                                    "aulas_por_semana": 2},
                        headers=h(ADMIN), timeout=10).json()["id"]
    # Course B disciplina with the same professor p1
    db1 = requests.post(f"{API}/disciplinas", json={"nome": "TEST_DB1", "codigo": "DB1",
                                                    "curso_id": cb, "professor_id": p1,
                                                    "aulas_por_semana": 3},
                        headers=h(ADMIN), timeout=10).json()["id"]
    created["disciplinas"].extend([da1, da2, db1])
    return {"ca": ca, "cb": cb, "p1": p1, "p2": p2, "da1": da1, "da2": da2, "db1": db1}


class TestGradeFlow:
    def test_auto_generate_course_a(self, flow_ids):
        r = requests.post(f"{API}/grades/auto-generate",
                          json={"curso_id": flow_ids["ca"], "ano": 2026, "semestre": 1, "turno": "noturno"},
                          headers=h(ADMIN), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["entries"]) >= 1
        # Save the grade
        r2 = requests.post(f"{API}/grades",
                           json={"curso_id": flow_ids["ca"], "ano": 2026, "semestre": 1,
                                 "turno": "noturno", "entries": d["entries"]},
                           headers=h(ADMIN), timeout=10)
        assert r2.status_code == 200
        gid = r2.json()["id"]
        created["grades"].append(gid)
        flow_ids["grade_a_id"] = gid
        flow_ids["grade_a_entries"] = d["entries"]

    def test_no_double_booking_across_courses(self, flow_ids):
        """Prof p1 is already scheduled in course A. Auto-gen for course B must not double-book p1."""
        # Grab slots occupied by p1 in course A
        p1_slots_a = {(e["dia_semana"], e["hora_inicio"]) for e in flow_ids["grade_a_entries"]
                      if e["professor_id"] == flow_ids["p1"]}
        assert p1_slots_a, "expected p1 to have slots in curso A"

        r = requests.post(f"{API}/grades/auto-generate",
                          json={"curso_id": flow_ids["cb"], "ano": 2026, "semestre": 1, "turno": "noturno"},
                          headers=h(ADMIN), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        # Verify no p1 entry overlaps with p1 slots in curso A
        for e in d["entries"]:
            if e["professor_id"] == flow_ids["p1"]:
                assert (e["dia_semana"], e["hora_inicio"]) not in p1_slots_a, \
                    f"Double-booking detected for professor p1 at {e}"

    def test_auto_generate_no_disciplinas(self):
        empty = requests.post(f"{API}/cursos", json={"nome": "TEST_Empty", "sigla": "EMP",
                                                     "turno": "noturno"}, headers=h(ADMIN), timeout=10).json()["id"]
        created["cursos"].append(empty)
        r = requests.post(f"{API}/grades/auto-generate",
                          json={"curso_id": empty, "ano": 2026, "semestre": 1, "turno": "noturno"},
                          headers=h(ADMIN), timeout=10)
        assert r.status_code == 400

    def test_list_grades(self, flow_ids):
        r = requests.get(f"{API}/grades", params={"curso_id": flow_ids["ca"]},
                         headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        assert any(g["id"] == flow_ids["grade_a_id"] for g in r.json())

    def test_mapa(self, flow_ids):
        r = requests.get(f"{API}/frequencia/mapa/{flow_ids['grade_a_id']}",
                         headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "grid" in d and "slots" in d and "dias" in d

    def test_consulta_professor(self, flow_ids):
        r = requests.get(f"{API}/frequencia/professor/{flow_ids['p1']}",
                         headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ---------------- Feriados & Aulas remotas ----------------
class TestFeriadosRemotas:
    def test_feriado(self):
        r = requests.post(f"{API}/feriados",
                          json={"data": "2026-06-11", "descricao": "TEST Corpus", "tipo": "Nacional"},
                          headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        created["feriados"].append(r.json()["id"])

    def test_aula_remota(self, flow_ids):
        r = requests.post(f"{API}/aulas-remotas",
                          json={"data": "2026-06-15", "professor_id": flow_ids["p1"],
                                "descricao": "TEST remota"},
                          headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        created["aulas-remotas"].append(r.json()["id"])


# ---------------- PDF ----------------
class TestPDF:
    def test_pdf_professor(self, flow_ids):
        r = requests.get(f"{API}/pdf/professor/{flow_ids['p1']}",
                         params={"ano": 2026, "mes": 6}, headers=h(ADMIN), timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF")
        assert len(r.content) > 500

    def test_pdf_curso(self, flow_ids):
        r = requests.get(f"{API}/pdf/curso/{flow_ids['ca']}",
                         params={"ano": 2026, "mes": 6}, headers=h(ADMIN), timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF")

    def test_pdf_professor_not_found(self):
        r = requests.get(f"{API}/pdf/professor/nope",
                         params={"ano": 2026, "mes": 6}, headers=h(ADMIN), timeout=15)
        assert r.status_code == 404


# ---------------- Operadores mgmt ----------------
class TestOperadores:
    def test_list_users_admin(self):
        r = requests.get(f"{API}/users", headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_users_forbidden_op(self):
        r = requests.get(f"{API}/users", headers=h(OPERADOR), timeout=10)
        assert r.status_code == 403

    def test_list_users_forbidden_coord(self):
        r = requests.get(f"{API}/users", headers=h(COORD), timeout=10)
        assert r.status_code == 403

    def test_update_role(self):
        # Toggle op user active flag then restore
        r = requests.put(f"{API}/users/op_seed_01",
                         json={"role": "operador", "active": False},
                         headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        assert r.json()["active"] is False
        # restore
        r2 = requests.put(f"{API}/users/op_seed_01",
                          json={"role": "operador", "active": True},
                          headers=h(ADMIN), timeout=10)
        assert r2.status_code == 200
        assert r2.json()["active"] is True

    def test_update_invalid_role(self):
        r = requests.put(f"{API}/users/op_seed_01", json={"role": "hacker"},
                        headers=h(ADMIN), timeout=10)
        assert r.status_code == 400


# ---------------- Stats ----------------
class TestStats:
    def test_stats(self):
        r = requests.get(f"{API}/stats", headers=h(ADMIN), timeout=10)
        assert r.status_code == 200
        d = r.json()
        for k in ["cursos", "professores", "disciplinas", "feriados", "aulas_remotas", "grades", "operadores"]:
            assert k in d
