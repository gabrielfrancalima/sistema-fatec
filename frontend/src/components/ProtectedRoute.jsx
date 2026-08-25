import { useAuth } from "@/context/AuthContext";
import { Navigate } from "react-router-dom";
import { GraduationCap } from "lucide-react";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#F3F4F6]">
        <div className="w-12 h-12 bg-[#FF161F] flex items-center justify-center animate-pulse">
          <GraduationCap className="w-7 h-7 text-white" />
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/" replace />;
  return children;
}
