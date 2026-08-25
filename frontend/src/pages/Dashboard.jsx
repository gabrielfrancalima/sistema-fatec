import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth, ROLE_LABELS } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import {
  Users, BookOpen, GraduationCap, CalendarOff, Wifi, CalendarClock, FileText, ArrowRight,
} from "lucide-react";

const ACCENT = "https://images.unsplash.com/photo-1725354282080-cf7e4b7325bc?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1ODR8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBhYnN0cmFjdCUyMHJlZCUyMGdyYXklMjBiYWNrZ3JvdW5kfGVufDB8fHx8MTc4NzY2NTUwOHww&ixlib=rb-4.1.0&q=85";

const CARDS = [
  { key: "professores", label: "Professores", icon: Users, to: "/professores" },
  { key: "cursos", label: "Cursos", icon: GraduationCap, to: "/cursos" },
  { key: "disciplinas", label: "Disciplinas", icon: BookOpen, to: "/disciplinas" },
  { key: "grades", label: "Grades Horárias", icon: CalendarClock, to: "/grade" },
  { key: "feriados", label: "Feriados", icon: CalendarOff, to: "/feriados" },
  { key: "aulas_remotas", label: "Aulas Remotas", icon: Wifi, to: "/aulas-remotas" },
];

const QUICK = [
  { label: "Criar Grade Horária", desc: "Montagem automática sem conflitos", to: "/grade", icon: CalendarClock },
  { label: "Gerar Folha de Ponto", desc: "PDF por professor, curso ou período", to: "/folha-ponto", icon: FileText },
];

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/stats").then((r) => setStats(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <Layout title="Painel">
      {/* Hero banner */}
      <div className="relative overflow-hidden rounded-sm grain mb-8">
        <img src={ACCENT} alt="" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-[#273336]/85" />
        <div className="relative z-10 p-8 lg:p-10 text-white">
          <p className="text-xs font-bold uppercase tracking-[0.25em] text-white/60">
            {ROLE_LABELS[user?.role]}
          </p>
          <h2 className="font-display text-3xl lg:text-4xl font-black mt-2 tracking-tight">
            Olá, {user?.name?.split(" ")[0]}
          </h2>
          <p className="text-white/70 mt-2 max-w-xl">
            Gerencie docentes, grade horária e gere folhas de frequência do Centro Paula Souza — FATEC.
          </p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {CARDS.map((c) => {
          const Icon = c.icon;
          return (
            <Link key={c.key} to={c.to} data-testid={`stat-${c.key}`}
              className="group bg-white border border-[#BFBFBF]/40 rounded-sm p-5 hover:shadow-sm hover:-translate-y-[1px] hover:border-[#FF161F]/40 transition-[transform,box-shadow,border-color] duration-200">
              <Icon className="w-6 h-6 text-[#FF161F]" />
              <p className="font-display text-3xl font-black text-[#273336] mt-4">
                {loading ? <span className="inline-block w-8 h-7 bg-[#F3F4F6] rounded animate-pulse" /> : (stats[c.key] ?? 0)}
              </p>
              <p className="text-xs text-[#808080] mt-1 uppercase tracking-wider font-medium">{c.label}</p>
            </Link>
          );
        })}
      </div>

      {/* Quick actions */}
      <div className="grid md:grid-cols-2 gap-4">
        {QUICK.map((q) => {
          const Icon = q.icon;
          return (
            <Link key={q.to} to={q.to} data-testid={`quick-${q.to.replace("/", "")}`}
              className="group flex items-center gap-5 bg-white border border-[#BFBFBF]/40 rounded-sm p-6 hover:shadow-sm hover:border-[#FF161F]/40 transition-[box-shadow,border-color] duration-200">
              <div className="w-12 h-12 bg-[#273336] flex items-center justify-center shrink-0">
                <Icon className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <p className="font-display font-bold text-[#273336]">{q.label}</p>
                <p className="text-sm text-[#808080]">{q.desc}</p>
              </div>
              <ArrowRight className="w-5 h-5 text-[#BFBFBF] group-hover:text-[#FF161F] group-hover:translate-x-1 transition-[color,transform] duration-200" />
            </Link>
          );
        })}
      </div>
    </Layout>
  );
}
