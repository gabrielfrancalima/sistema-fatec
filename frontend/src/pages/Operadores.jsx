import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { useAuth, ROLE_LABELS } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import {
  AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle,
  AlertDialogDescription, AlertDialogFooter, AlertDialogCancel, AlertDialogAction,
} from "@/components/ui/alert-dialog";
import { UserCog, Trash2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

const ROLES = [
  { value: "coordenador", label: "Coordenador (consulta)" },
  { value: "operador", label: "Operador (CRUD + PDF)" },
  { value: "adm_master", label: "ADM Master" },
];

export default function Operadores() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await api.get("/users"); setUsers(r.data); }
    catch { toast.error("Erro ao carregar usuários"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const changeRole = async (u, role) => {
    try { await api.put(`/users/${u.user_id}`, { role }); toast.success("Perfil atualizado"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Erro"); }
  };

  const toggleActive = async (u) => {
    try { await api.put(`/users/${u.user_id}`, { role: u.role, active: !u.active }); toast.success("Status atualizado"); load(); }
    catch { toast.error("Erro"); }
  };

  const confirmDelete = async () => {
    try { await api.delete(`/users/${deleteId}`); toast.success("Usuário removido"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Erro"); }
    finally { setDeleteId(null); }
  };

  return (
    <Layout title="Operadores">
      <div className="max-w-5xl">
        <div className="mb-6">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#808080]">Configuração do sistema</p>
          <h2 className="font-display text-2xl font-black text-[#273336] mt-1 flex items-center gap-2">
            <UserCog className="w-6 h-6 text-[#FF161F]" /> Gestão de Operadores
          </h2>
          <p className="text-sm text-[#808080] mt-1">Como ADM Master, defina o perfil de acesso de cada usuário autenticado.</p>
        </div>

        <div className="bg-white border border-[#BFBFBF]/40 rounded-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="users-table">
              <thead>
                <tr className="bg-[#273336] text-white text-left">
                  <th className="px-4 py-3 text-xs uppercase tracking-wider">Usuário</th>
                  <th className="px-4 py-3 text-xs uppercase tracking-wider">E-mail</th>
                  <th className="px-4 py-3 text-xs uppercase tracking-wider">Perfil</th>
                  <th className="px-4 py-3 text-xs uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-right text-xs uppercase tracking-wider">Ações</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={5} className="px-4 py-10 text-center text-[#808080]">Carregando...</td></tr>
                ) : users.map((u, i) => (
                  <tr key={u.user_id} className="border-b border-[#BFBFBF]/20 hover:bg-[#F3F4F6] transition-colors" data-testid={`user-row-${i}`}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 font-medium">
                        {u.email === user.email && <ShieldCheck className="w-4 h-4 text-[#FF161F]" title="Você" />}
                        {u.name}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[#808080]">{u.email}</td>
                    <td className="px-4 py-3">
                      <select data-testid={`role-select-${i}`} value={u.role} disabled={u.user_id === user.user_id}
                        onChange={(e) => changeRole(u, e.target.value)}
                        className="h-9 px-2 rounded-sm border border-[#BFBFBF] bg-white text-xs focus:ring-2 focus:ring-[#FF161F] outline-none disabled:opacity-50">
                        {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <button data-testid={`toggle-active-${i}`} onClick={() => toggleActive(u)} disabled={u.user_id === user.user_id}
                        className={`px-2.5 py-1 rounded-sm text-xs font-semibold disabled:opacity-50 ${u.active ? "bg-green-100 text-green-700" : "bg-red-100 text-[#B20000]"}`}>
                        {u.active ? "Ativo" : "Inativo"}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button data-testid={`delete-user-${i}`} onClick={() => setDeleteId(u.user_id)} disabled={u.user_id === user.user_id}
                        className="p-1.5 text-[#808080] hover:text-[#FF161F] transition-colors disabled:opacity-30">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <AlertDialog open={!!deleteId} onOpenChange={(o) => !o && setDeleteId(null)}>
        <AlertDialogContent className="rounded-sm bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Remover usuário</AlertDialogTitle>
            <AlertDialogDescription>O usuário perderá o acesso ao sistema.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-sm">Cancelar</AlertDialogCancel>
            <AlertDialogAction data-testid="confirm-delete-user" onClick={confirmDelete} className="bg-[#FF161F] hover:bg-[#B20000] rounded-sm">Remover</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
}
