import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Login from "@/pages/Login";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import Professores from "@/pages/Professores";
import Cursos from "@/pages/Cursos";
import Disciplinas from "@/pages/Disciplinas";
import Feriados from "@/pages/Feriados";
import AulasRemotas from "@/pages/AulasRemotas";
import GradeHoraria from "@/pages/GradeHoraria";
import FolhaPonto from "@/pages/FolhaPonto";
import Consultas from "@/pages/Consultas";
import Operadores from "@/pages/Operadores";

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;

  const P = (el) => <ProtectedRoute>{el}</ProtectedRoute>;

  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={P(<Dashboard />)} />
      <Route path="/professores" element={P(<Professores />)} />
      <Route path="/cursos" element={P(<Cursos />)} />
      <Route path="/disciplinas" element={P(<Disciplinas />)} />
      <Route path="/feriados" element={P(<Feriados />)} />
      <Route path="/aulas-remotas" element={P(<AulasRemotas />)} />
      <Route path="/grade" element={P(<GradeHoraria />)} />
      <Route path="/folha-ponto" element={P(<FolhaPonto />)} />
      <Route path="/consultas" element={P(<Consultas />)} />
      <Route path="/operadores" element={P(<Operadores />)} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <AppRouter />
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </div>
  );
}

export default App;
