import { useState, useEffect } from "react";
import api from "@/lib/api";
import Layout from "@/components/Layout";
import { Search, User, LayoutGrid } from "lucide-react";

export default function Consultas() {
  const [tab, setTab] = useState("professor");
  const [professores, setProfessores] = useState([]);
  const [grades, setGrades] = useState([]);
  const [cursos, setCursos] = useState([]);
  const [profId, setProfId] = useState("");
  const [gradeId, setGradeId] = useState("");
  const [freq, setFreq] = useState([]);
  const [mapa, setMapa] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/professores").then((r) => setProfessores(r.data));
    api.get("/grades").then((r) => setGrades(r.data));
    api.get("/cursos").then((r) => setCursos(r.data));
  }, []);

  const loadFreq = async (id) => {
    setProfId(id); setFreq([]);
    if (!id) return;
    setLoading(true);
    try { const r = await api.get(`/frequencia/professor/${id}`); setFreq(r.data); }
    finally { setLoading(false); }
  };

  const loadMapa = async (id) => {
    setGradeId(id); setMapa(null);
    if (!id) return;
    setLoading(true);
    try { const r = await api.get(`/frequencia/mapa/${id}`); setMapa(r.data); }
    finally { setLoading(false); }
  };

  const selectCls = "w-full sm:w-80 h-10 px-3 rounded-sm border border-[#BFBFBF] bg-white text-sm focus:ring-2 focus:ring-[#FF161F] outline-none";
  const gradeLabel = (g) => {
    const c = cursos.find((x) => x.id === g.curso_id);
    return `${c?.nome || "Curso"} — ${g.ano}/${g.semestre}º (${g.turno})`;
  };
  const cellFor = (si, di) => mapa?.grid[`${si}_${di}`];

  return (
    <Layout title="Consultas">
      <div className="max-w-5xl">
        <div className="mb-6">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#808080]">Consulta</p>
          <h2 className="font-display text-2xl font-black text-[#273336] mt-1">Frequência & Mapa</h2>
        </div>

        <div className="flex gap-2 mb-6">
          <button data-testid="consulta-tab-professor" onClick={() => setTab("professor")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-sm text-sm font-medium transition-colors ${tab === "professor" ? "bg-[#FF161F] text-white" : "bg-white border border-[#BFBFBF]/40 text-[#273336]"}`}>
            <User className="w-4 h-4" /> Frequência do Professor
          </button>
          <button data-testid="consulta-tab-mapa" onClick={() => setTab("mapa")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-sm text-sm font-medium transition-colors ${tab === "mapa" ? "bg-[#FF161F] text-white" : "bg-white border border-[#BFBFBF]/40 text-[#273336]"}`}>
            <LayoutGrid className="w-4 h-4" /> Mapa de Frequência
          </button>
        </div>

        {tab === "professor" ? (
          <div>
            <select data-testid="consulta-professor-select" value={profId} onChange={(e) => loadFreq(e.target.value)} className={selectCls}>
              <option value="">Selecione um professor...</option>
              {professores.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
            </select>
            <div className="mt-5 bg-white border border-[#BFBFBF]/40 rounded-sm overflow-hidden">
              <table className="w-full text-sm" data-testid="freq-table">
                <thead>
                  <tr className="bg-[#273336] text-white text-left">
                    <th className="px-4 py-3 text-xs uppercase tracking-wider">Dia</th>
                    <th className="px-4 py-3 text-xs uppercase tracking-wider">Horário</th>
                    <th className="px-4 py-3 text-xs uppercase tracking-wider">Disciplina</th>
                    <th className="px-4 py-3 text-xs uppercase tracking-wider">Curso</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan={4} className="px-4 py-10 text-center text-[#808080]">Carregando...</td></tr>
                  ) : !profId ? (
                    <tr><td colSpan={4} className="px-4 py-10 text-center text-[#808080]"><Search className="w-8 h-8 mx-auto mb-2 text-[#BFBFBF]" />Selecione um professor.</td></tr>
                  ) : freq.length === 0 ? (
                    <tr><td colSpan={4} className="px-4 py-10 text-center text-[#808080]">Nenhuma aula na grade.</td></tr>
                  ) : freq.map((f, i) => (
                    <tr key={i} className="border-b border-[#BFBFBF]/20 hover:bg-[#F3F4F6] transition-colors">
                      <td className="px-4 py-3 font-medium">{f.dia_nome.replace("-feira", "")}</td>
                      <td className="px-4 py-3">{f.hora_inicio}–{f.hora_fim}</td>
                      <td className="px-4 py-3">{f.disciplina}</td>
                      <td className="px-4 py-3 text-[#808080]">{f.curso}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div>
            <select data-testid="consulta-grade-select" value={gradeId} onChange={(e) => loadMapa(e.target.value)} className={selectCls}>
              <option value="">Selecione uma grade...</option>
              {grades.map((g) => <option key={g.id} value={g.id}>{gradeLabel(g)}</option>)}
            </select>
            <div className="mt-5">
              {!mapa ? (
                <div className="bg-white border border-[#BFBFBF]/40 rounded-sm px-4 py-14 text-center text-[#808080]">
                  <LayoutGrid className="w-8 h-8 mx-auto mb-2 text-[#BFBFBF]" />Selecione uma grade para ver o mapa.
                </div>
              ) : (
                <div className="bg-white border border-[#BFBFBF]/40 rounded-sm overflow-x-auto" data-testid="mapa-grid">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-[#273336] text-white">
                        <th className="px-3 py-2.5 text-left">Horário</th>
                        {mapa.dias.map((d) => <th key={d} className="px-3 py-2.5 text-left min-w-[130px]">{d.replace("-feira", "")}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {mapa.slots.map((s, si) => (
                        <tr key={si} className="border-b border-[#BFBFBF]/20">
                          <td className="px-3 py-2 font-medium text-[#808080] whitespace-nowrap">{s.hora_inicio}–{s.hora_fim}</td>
                          {mapa.dias.map((_, di) => {
                            const cell = cellFor(si, di);
                            return (
                              <td key={di} className="px-2 py-1.5 align-top">
                                {cell ? (
                                  <div className="bg-[#FF161F]/10 border-l-2 border-[#FF161F] px-2 py-1.5 rounded-sm">
                                    <p className="font-semibold text-[#273336] leading-tight">{cell.disciplina}</p>
                                    <p className="text-[10px] text-[#808080] mt-0.5">{cell.professor}</p>
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
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
