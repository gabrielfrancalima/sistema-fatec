import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { GraduationCap } from "lucide-react";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash;
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? match[1] : null;

    const process = async () => {
      if (!sessionId) {
        navigate("/");
        return;
      }
      try {
        const res = await api.post("/auth/session", { session_id: sessionId });
        setUser(res.data.user);
        window.history.replaceState(null, "", "/dashboard");
        navigate("/dashboard", { state: { user: res.data.user } });
      } catch (err) {
        const code = err.response?.status === 403 ? "domain" : "auth";
        navigate(`/?error=${code}`);
      }
    };
    process();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#273336] text-white">
      <div className="w-12 h-12 bg-[#FF161F] flex items-center justify-center mb-5 animate-pulse">
        <GraduationCap className="w-7 h-7" />
      </div>
      <p className="font-display font-bold text-lg">Autenticando...</p>
      <p className="text-white/50 text-sm mt-1">Validando sua conta institucional</p>
    </div>
  );
}
