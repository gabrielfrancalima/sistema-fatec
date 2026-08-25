import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth, ROLE_LABELS } from "@/context/AuthContext";
import {
  LayoutDashboard, Users, BookOpen, GraduationCap, CalendarOff, Wifi,
  CalendarClock, FileText, Search, UserCog, LogOut, Menu, X,
} from "lucide-react";

const NAV = [
  { to: "/dashboard", label: "Painel", icon: LayoutDashboard },
  { to: "/professores", label: "Professores", icon: Users },
  { to: "/cursos", label: "Cursos", icon: GraduationCap },
  { to: "/disciplinas", label: "Disciplinas", icon: BookOpen },
  { to: "/feriados", label: "Feriados", icon: CalendarOff },
  { to: "/aulas-remotas", label: "Aulas Remotas", icon: Wifi },
  { to: "/grade", label: "Grade Horária", icon: CalendarClock },
  { to: "/folha-ponto", label: "Folha de Ponto", icon: FileText },
  { to: "/consultas", label: "Consultas", icon: Search },
];

export default function Layout({ children, title }) {
  const { user, logout, isAdmin } = useAuth();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const nav = [...NAV];
  if (isAdmin) nav.push({ to: "/operadores", label: "Operadores", icon: UserCog });

  const Sidebar = (
    <aside className="flex flex-col h-full w-64 bg-[#273336] text-white">
      <div className="flex items-center gap-3 px-6 h-16 border-b border-white/10 shrink-0">
        <div className="w-9 h-9 bg-[#FF161F] flex items-center justify-center">
          <GraduationCap className="w-5 h-5" />
        </div>
        <div className="leading-tight">
          <p className="font-display font-black tracking-tight">FATEC</p>
          <p className="text-[9px] uppercase tracking-[0.2em] text-white/50">Ponto Acadêmico</p>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {nav.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              data-testid={`nav-${item.to.replace("/", "")}`}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-sm text-sm font-medium transition-colors duration-150 ${
                  isActive ? "bg-[#FF161F] text-white" : "text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Icon className="w-4.5 h-4.5 shrink-0" style={{ width: 18, height: 18 }} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
      <div className="p-3 border-t border-white/10 shrink-0">
        <div className="flex items-center gap-3 px-2 py-2">
          {user?.picture ? (
            <img src={user.picture} alt="" className="w-9 h-9 rounded-full object-cover" />
          ) : (
            <div className="w-9 h-9 rounded-full bg-[#FF161F] flex items-center justify-center text-sm font-bold">
              {user?.name?.[0]?.toUpperCase()}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium truncate">{user?.name}</p>
            <p className="text-[10px] uppercase tracking-wider text-[#FF161F] font-bold">{ROLE_LABELS[user?.role]}</p>
          </div>
        </div>
        <button
          data-testid="logout-button"
          onClick={logout}
          className="mt-2 w-full flex items-center gap-2 px-3 py-2 text-sm text-white/60 hover:text-white hover:bg-white/5 rounded-sm transition-colors"
        >
          <LogOut className="w-4 h-4" /> Sair
        </button>
      </div>
    </aside>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="hidden lg:block shrink-0">{Sidebar}</div>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-[#273336]/80 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-0 h-full">{Sidebar}</div>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-[#BFBFBF]/40 flex items-center justify-between px-4 lg:px-8 shrink-0">
          <div className="flex items-center gap-3">
            <button className="lg:hidden" data-testid="mobile-menu-button" onClick={() => setOpen(true)}>
              <Menu className="w-6 h-6 text-[#273336]" />
            </button>
            <h1 className="font-display text-xl font-black text-[#273336] tracking-tight">{title}</h1>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs text-[#808080]">
            <span className="w-2 h-2 rounded-full bg-green-500" /> Sistema ativo
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
