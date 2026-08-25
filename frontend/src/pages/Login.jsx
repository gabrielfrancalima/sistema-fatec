import { GraduationCap, ShieldCheck, Clock } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";

const LOGIN_BG =
  "https://images.pexels.com/photos/17082393/pexels-photo-17082393.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

const ERROR_MESSAGES = {
  domain: "Acesso permitido apenas para contas institucionais da FATEC. Use seu e-mail @fatec.sp.gov.br ou @cps.sp.gov.br.",
  auth: "Falha ao entrar. Tente novamente.",
  ms_flow: "Sessão de login Microsoft expirada. Tente novamente.",
  ms_denied: "Login Microsoft cancelado.",
  ms_oauth: "Falha na autenticação Microsoft.",
  ms_token: "Não foi possível validar sua conta Microsoft.",
  ms_email: "Sua conta Microsoft não possui e-mail utilizável.",
  inactive: "Usuário desativado. Contate o ADM Master.",
};

export default function Login() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [msEnabled, setMsEnabled] = useState(false);

  useEffect(() => {
    if (!loading && user) navigate("/dashboard");
  }, [user, loading, navigate]);

  useEffect(() => {
    api.get("/auth/config").then((r) => setMsEnabled(r.data.microsoft_enabled)).catch(() => {});
    const params = new URLSearchParams(window.location.search);
    const err = params.get("error");
    if (err) {
      toast.error(ERROR_MESSAGES[err] || "Falha ao entrar. Tente novamente.");
      window.history.replaceState(null, "", "/");
    }
  }, []);

  const handleGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handleMicrosoft = () => {
    if (!msEnabled) {
      toast.error("Login Microsoft ainda não configurado. Peça ao administrador para cadastrar as credenciais do Azure.");
      return;
    }
    window.location.href = `${process.env.REACT_APP_BACKEND_URL}/api/auth/microsoft/login`;
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left brand panel */}
      <div className="relative hidden lg:block overflow-hidden grain">
        <img src={LOGIN_BG} alt="Arquitetura educacional" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-[#273336]/85" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#B20000]/40 to-transparent" />
        <div className="relative z-10 h-full flex flex-col justify-between p-12 text-white">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-[#FF161F] flex items-center justify-center">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <div className="leading-tight">
              <p className="font-display font-black text-lg tracking-tight">FATEC</p>
              <p className="text-[10px] uppercase tracking-[0.25em] text-white/70">Centro Paula Souza</p>
            </div>
          </div>
          <div className="max-w-md">
            <h1 className="font-display text-4xl xl:text-5xl font-black leading-[1.05] tracking-tight">
              Ponto Acadêmico<br />Automatizado
            </h1>
            <p className="mt-5 text-white/75 text-base leading-relaxed">
              Gestão de docentes, grade horária inteligente e geração de folhas de frequência em PDF — tudo em um só lugar.
            </p>
            <div className="mt-10 space-y-3 text-sm">
              <div className="flex items-center gap-3 text-white/80"><Clock className="w-4 h-4 text-[#FF161F]" /> Grade horária sem conflitos</div>
              <div className="flex items-center gap-3 text-white/80"><ShieldCheck className="w-4 h-4 text-[#FF161F]" /> Perfis: ADM, Operador e Coordenador</div>
            </div>
          </div>
          <p className="text-[11px] text-white/40 uppercase tracking-[0.2em]">Faculdade de Tecnologia do Estado de São Paulo</p>
        </div>
      </div>

      {/* Right auth panel */}
      <div className="flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-10 h-10 bg-[#FF161F] flex items-center justify-center">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <p className="font-display font-black text-lg">FATEC</p>
          </div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#808080]">Acesso ao sistema</p>
          <h2 className="font-display text-3xl font-black mt-2 text-[#273336]">Bem-vindo</h2>
          <p className="text-[#808080] mt-3 text-sm leading-relaxed">
            Entre com sua conta institucional (Google ou Microsoft) para acessar o painel de gestão de ponto acadêmico.
          </p>

          <button
            data-testid="google-login-button"
            onClick={handleGoogle}
            className="mt-8 w-full flex items-center justify-center gap-3 bg-white border border-[#BFBFBF] px-5 py-3.5 rounded-sm font-medium text-[#273336] hover:border-[#FF161F] hover:shadow-sm transition-[border-color,box-shadow] duration-200"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
              <path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84C6.71 7.3 9.14 5.38 12 5.38Z" />
            </svg>
            Entrar com Google
          </button>

          <button
            data-testid="microsoft-login-button"
            onClick={handleMicrosoft}
            className="mt-3 w-full flex items-center justify-center gap-3 bg-white border border-[#BFBFBF] px-5 py-3.5 rounded-sm font-medium text-[#273336] hover:border-[#FF161F] hover:shadow-sm transition-[border-color,box-shadow] duration-200"
          >
            <svg className="w-5 h-5" viewBox="0 0 23 23">
              <path fill="#F25022" d="M1 1h10v10H1z" />
              <path fill="#7FBA00" d="M12 1h10v10H12z" />
              <path fill="#00A4EF" d="M1 12h10v10H1z" />
              <path fill="#FFB900" d="M12 12h10v10H12z" />
            </svg>
            Entrar com Microsoft
          </button>

          <div className="mt-10 border-t border-[#BFBFBF]/40 pt-6">
            <p className="text-xs text-[#808080] leading-relaxed">
              Novos usuários recebem o perfil <span className="font-semibold text-[#273336]">Coordenador (consulta)</span> por padrão. Solicite ao ADM Master a alteração de perfil.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
