import { useState, useEffect } from "react";
import api, { API } from "@/lib/api";
import Layout from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { FileText, Download, User, GraduationCap } from "lucide-react";
import { toast } from "sonner";

const MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
const now = new Date();

export default function FolhaPonto() {
  const [tab, setTab] = useState("professor");
  const [professores, setProfessores] = useState([]);
  const [cursos, setCursos] = useState([]);
  const [profId, setProfId] = useState("");
  const [profCursoId, setProfCursoId] = useState("");
  const [cursoId, setCursoId] = useState("");
  const [mes, setMes] = useState(now.getMonth() + 1);
  const [ano, setAno] = useState(now.getFullYear());
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    api.get("/professores").then((r) => setProfessores(r.data));
    api.get("/cursos").then((r) => setCursos(r.data));
  }, []);

  const download = async () => {
    let url, filename;
    if (tab === "professor") {
      if (!profId) { toast.error("Selecione um professor"); return; }
      url = `${API}/pdf/professor/${profId}?ano=${ano}&mes=${mes}${profCursoId ? `&curso_id=${profCursoId}` : ""}`;
      filename = "folha_ponto.pdf";
    } else {
      if (!cursoId) { toast.error("Selecione um curso"); return; }
      url = `${API}/pdf/curso/${cursoId}?ano=${ano}&mes=${mes}`;
      filename = "mapa_frequencia.pdf";
    }
    setDownloading(true);
    try {
      const res = await api.get(url.replace(API, ""), { responseType: "blob" });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      window.URL.revokeObjectURL(link.href);
      toast.success("PDF gerado");
    } catch (err) {
      toast.error("Erro ao gerar PDF");
    } finally {
      setDownloading(false);
    }
  };

  const selectCls = "w-full h-10 px-3 rounded-sm border border-[#BFBFBF] bg-white text-sm focus:ring-2 focus:ring-[#FF161F] outline-none";

  return (
    <Layout title="Folha de Ponto">
      <div className="max-w-3xl">
        <div className="mb-6">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#808080]">Geração de documentos</p>
          <h2 className="font-display text-2xl font-black text-[#273336] mt-1">Folha de Ponto / Frequência (PDF)</h2>
        </div>

        <div className="flex gap-2 mb-6">
          <button data-testid="tab-professor" onClick={() => setTab("professor")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-sm text-sm font-medium transition-colors ${tab === "professor" ? "bg-[#FF161F] text-white" : "bg-white border border-[#BFBFBF]/40 text-[#273336] hover:border-[#FF161F]/40"}`}>
            <User className="w-4 h-4" /> Por Professor
          </button>
          <button data-testid="tab-curso" onClick={() => setTab("curso")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-sm text-sm font-medium transition-colors ${tab === "curso" ? "bg-[#FF161F] text-white" : "bg-white border border-[#BFBFBF]/40 text-[#273336] hover:border-[#FF161F]/40"}`}>
            <GraduationCap className="w-4 h-4" /> Por Curso (geral)
          </button>
        </div>

        <div className="bg-white border border-[#BFBFBF]/40 rounded-sm p-6 space-y-4">
          {tab === "professor" ? (
            <>
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-[#808080]">Professor</label>
                <select data-testid="folha-professor-select" value={profId} onChange={(e) => setProfId(e.target.value)} className={selectCls}>
                  <option value="">Selecione...</option>
                  {professores.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-[#808080]">Curso (opcional — todos se vazio)</label>
                <select data-testid="folha-prof-curso-select" value={profCursoId} onChange={(e) => setProfCursoId(e.target.value)} className={selectCls}>
                  <option value="">Todos os cursos</option>
                  {cursos.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
                </select>
              </div>
            </>
          ) : (
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#808080]">Curso</label>
              <select data-testid="folha-curso-select" value={cursoId} onChange={(e) => setCursoId(e.target.value)} className={selectCls}>
                <option value="">Selecione...</option>
                {cursos.map((c) => <option key={c.id} value={c.id}>{c.nome} ({c.sigla})</option>)}
              </select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#808080]">Mês</label>
              <select data-testid="folha-mes-select" value={mes} onChange={(e) => setMes(Number(e.target.value))} className={selectCls}>
                {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#808080]">Ano</label>
              <input data-testid="folha-ano-input" type="number" value={ano} onChange={(e) => setAno(Number(e.target.value))} className={selectCls} />
            </div>
          </div>

          <div className="pt-2">
            <Button data-testid="generate-pdf-button" onClick={download} disabled={downloading}
              className="w-full bg-[#FF161F] hover:bg-[#B20000] rounded-sm gap-2 h-11">
              <Download className="w-4 h-4" /> {downloading ? "Gerando PDF..." : "Gerar e baixar PDF"}
            </Button>
          </div>
        </div>

        <div className="mt-6 flex items-start gap-3 text-sm text-[#808080] bg-[#F3F4F6] border border-[#BFBFBF]/40 rounded-sm p-4">
          <FileText className="w-5 h-5 text-[#FF161F] shrink-0 mt-0.5" />
          <p>A folha considera a grade horária salva, marca <b>feriados</b> e <b>aulas remotas (EAD)</b> automaticamente, e inclui campos de assinatura do docente e da coordenação.</p>
        </div>
      </div>
    </Layout>
  );
}
