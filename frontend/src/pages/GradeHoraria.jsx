import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Sparkles, Save, Trash2, AlertTriangle, CheckCircle2, CalendarClock } from "lucide-react";
import { toast } from "sonner";

const CURRENT_YEAR = new Date().getFullYear();

export default function GradeHoraria() {
  const { canWrite } = useAuth();
  const [cursos, setCursos] = useState([]);
  const [disciplinas, setDisciplinas] = useState([]);
  const [professores, setProfessores] = useState([]);
  const [grades, setGrades] = useState([]);
  const [slotsCfg, setSlotsCfg] = useState({ turnos: {}, dias: [] });

  const [cursoId, setCursoId] = useState("");
  const [ano, setAno] = useState(CURRENT_YEAR);
  const [semestre, setSemestre] = useState(1);
  const [preview, setPreview] = useState(null);
  const [conflicts, setConflicts] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);

  const curso = cursos.find((c) => c.id === cursoId);
  const turno = curso?.turno || "noturno";
  const discMap = Object.fromEntries(disciplinas.map((d) => [d.id, d]));
  const profMap = Object.fromEntries(professores.map((p) => [p.id, p]));

  const loadAll = useCallback(async () => {
    const [c, d, p, g, s] = await Promise.all([
      api.get("/cursos"), api.get("/disciplinas"), api.get("/professores"),
      api.get("/grades"), api.get("/config/slots"),
    ]);
    setCursos(c.data); setDisciplinas(d.data); setProfessores(p.data);
    setGrades(g.data); setSlotsCfg(s.data);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const generate = async () => {
    if (!cursoId) { toast.error("Selecione um curso"); return; }
    setGenerating(true);
    try {
      const res = await api.post("/grades/auto-generate", { curso_id: cursoId, ano: Number(ano), semestre: Number(semestre), turno });
      setPreview(res.data.entries);
      setConflicts(res.data.conflicts);
      if (res.data.conflicts.length) toast.warning(`${res.data.conflicts.length} disciplina(s) com conflito`);
      else toast.success("Grade gerada sem conflitos");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erro ao gerar grade");
    } finally {
      setGenerating(false);
    }
  };

  const save = async () => {
    if (!preview) return;
    setSaving(true);
    try {
      await api.post("/grades", { curso_id: cursoId, ano: Number(ano), semestre: Number(semestre), turno, entries: preview });
      toast.success("Grade salva");
      setPreview(null); setConflicts([]);
      loadAll();
    } catch {
      toast.error("Erro ao salvar grade");
    } finally {
      setSaving(false);
    }
  };

  const deleteGrade = async (id) => {
    try { await api.delete(`/grades/${id}`); toast.success("Grade removida"); loadAll(); }
    catch { toast.error("Erro ao remover"); }
  };

  const slots = slotsCfg.turnos[turno] || [];
  const dias = slotsCfg.dias || [];
  const cellFor = (slotIdx, dayIdx) =>
    (preview || []).find((e) => e.slot_index === slotIdx && e.dia_semana === dayIdx);

  return (
    <Layout title="Grade Horária">
      <div className="max-w-6xl">
        <div className="mb-6">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#808080]">Operação</p>
          <h2 className="font-display text-2xl font-black text-[#273336] mt-1">Montagem Automática de Grade</h2>
          <p className="text-sm text-[#808080] mt-1">O sistema distribui as disciplinas evitando conflitos de horário do professor entre todos os cursos.</p>
        </div>

        {/* Controls */}
        <div className="bg-white border border-[#BFBFBF]/40 rounded-sm p-5 mb-6">
          <div className="grid sm:grid-cols-4 gap-4 items-end">
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#808080]">Curso</label>
              <select data-testid="grade-curso-select" value={cursoId} onChange={(e) => { setCursoId(e.target.value); setPreview(null); }}
                className="w-full h-10 px-3 rounded-sm border border-[#BFBFBF] bg-white text-sm focus:ring-2 focus:ring-[#FF161F] outline-none">
                <option value="">Selecione...</option>
                {cursos.map((c) => <option key={c.id} value={c.id}>{c.nome} ({c.turno})</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#808080]">Ano</label>
              <input data-testid="grade-ano" type="number" value={ano} onChange={(e) => setAno(e.target.value)}
                className="w-full h-10 px-3 rounded-sm border border-[#BFBFBF] bg-white text-sm focus:ring-2 focus:ring-[#FF161F] outline-none" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#808080]">Semestre</label>
              <select data-testid="grade-semestre" value={semestre} onChange={(e) => setSemestre(e.target.value)}
                className="w-full h-10 px-3 rounded-sm border border-[#BFBFBF] bg-white text-sm focus:ring-2 focus:ring-[#FF161F] outline-none">
                <option value={1}>1º Semestre</option>
                <option value={2}>2º Semestre</option>
              </select>
            </div>
            {canWrite && (
              <Button data-testid="generate-grade-button" onClick={generate} disabled={generating}
                className="bg-[#FF161F] hover:bg-[#B20000] rounded-sm gap-2 h-10">
                <Sparkles className="w-4 h-4" /> {generating ? "Gerando..." : "Gerar automaticamente"}
              </Button>
            )}
          </div>
        </div>

        {/* Conflicts */}
        {conflicts.length > 0 && (
          <div className="bg-[#FDE8E8] border border-[#FF161F]/30 rounded-sm p-4 mb-6" data-testid="conflicts-panel">
            <div className="flex items-center gap-2 text-[#B20000] font-semibold mb-2">
              <AlertTriangle className="w-4 h-4" /> Conflitos não resolvidos
            </div>
            <ul className="text-sm text-[#273336] space-y-1">
              {conflicts.map((c, i) => (
                <li key={i}>• <b>{c.disciplina_nome}</b>: alocado {c.alocado}/{c.solicitado} — {c.motivo}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Preview grid */}
        {preview && (
          <div className="bg-white border border-[#BFBFBF]/40 rounded-sm overflow-hidden mb-8 animate-fade-up">
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#BFBFBF]/40">
              <div className="flex items-center gap-2">
                {conflicts.length === 0
                  ? <CheckCircle2 className="w-5 h-5 text-green-600" />
                  : <AlertTriangle className="w-5 h-5 text-[#FF161F]" />}
                <span className="font-display font-bold text-[#273336]">Pré-visualização — {curso?.nome}</span>
              </div>
              {canWrite && (
                <Button data-testid="save-grade-button" onClick={save} disabled={saving}
                  className="bg-[#273336] hover:bg-[#0A0A0A] rounded-sm gap-2">
                  <Save className="w-4 h-4" /> {saving ? "Salvando..." : "Salvar grade"}
                </Button>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-[#273336] text-white">
                    <th className="px-3 py-2.5 text-left">Horário</th>
                    {dias.map((d) => <th key={d} className="px-3 py-2.5 text-left min-w-[130px]">{d.replace("-feira", "")}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {slots.map((s, si) => (
                    <tr key={si} className="border-b border-[#BFBFBF]/20">
                      <td className="px-3 py-2 font-medium text-[#808080] whitespace-nowrap">{s.hora_inicio}–{s.hora_fim}</td>
                      {dias.map((_, di) => {
                        const cell = cellFor(si, di);
                        return (
                          <td key={di} className="px-2 py-1.5 align-top">
                            {cell ? (
                              <div className="bg-[#FF161F]/10 border-l-2 border-[#FF161F] px-2 py-1.5 rounded-sm">
                                <p className="font-semibold text-[#273336] leading-tight">{discMap[cell.disciplina_id]?.nome || "—"}</p>
                                <p className="text-[10px] text-[#808080] mt-0.5">{profMap[cell.professor_id]?.nome || "Sem professor"}</p>
                              </div>
                            ) : <div className="h-8" />}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Saved grades */}
        <div>
          <h3 className="font-display font-bold text-[#273336] mb-3 flex items-center gap-2">
            <CalendarClock className="w-4 h-4 text-[#FF161F]" /> Grades salvas
          </h3>
          <div className="bg-white border border-[#BFBFBF]/40 rounded-sm overflow-hidden">
            <table className="w-full text-sm" data-testid="grades-table">
              <thead>
                <tr className="bg-[#273336] text-white text-left">
                  <th className="px-4 py-3 text-xs uppercase tracking-wider">Curso</th>
                  <th className="px-4 py-3 text-xs uppercase tracking-wider">Período</th>
                  <th className="px-4 py-3 text-xs uppercase tracking-wider">Turno</th>
                  <th className="px-4 py-3 text-xs uppercase tracking-wider">Aulas</th>
                  {canWrite && <th className="px-4 py-3 text-right text-xs uppercase tracking-wider">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {grades.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-10 text-center text-[#808080]">Nenhuma grade salva.</td></tr>
                ) : grades.map((g, i) => {
                  const c = cursos.find((x) => x.id === g.curso_id);
                  return (
                    <tr key={g.id} className="border-b border-[#BFBFBF]/20 hover:bg-[#F3F4F6] transition-colors" data-testid={`grade-row-${i}`}>
                      <td className="px-4 py-3 font-medium">{c?.nome || "—"}</td>
                      <td className="px-4 py-3">{g.ano} / {g.semestre}º sem.</td>
                      <td className="px-4 py-3 capitalize">{g.turno}</td>
                      <td className="px-4 py-3">{g.entries?.length || 0}</td>
                      {canWrite && (
                        <td className="px-4 py-3 text-right">
                          <button data-testid={`delete-grade-${i}`} onClick={() => deleteGrade(g.id)} className="p-1.5 text-[#808080] hover:text-[#FF161F] transition-colors">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  );
}
