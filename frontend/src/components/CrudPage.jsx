import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle,
  AlertDialogDescription, AlertDialogFooter, AlertDialogCancel, AlertDialogAction,
} from "@/components/ui/alert-dialog";
import { Plus, Pencil, Trash2, Inbox } from "lucide-react";
import { toast } from "sonner";

export default function CrudPage({ title, endpoint, fields, columns, testid }) {
  const { canWrite } = useAuth();
  const [items, setItems] = useState([]);
  const [refs, setRefs] = useState({});
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({});
  const [deleteId, setDeleteId] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/${endpoint}`);
      setItems(res.data);
      const refFields = fields.filter((f) => f.type === "ref");
      const refData = {};
      await Promise.all(
        refFields.map(async (f) => {
          if (!refData[f.refEndpoint]) {
            const r = await api.get(`/${f.refEndpoint}`);
            refData[f.refEndpoint] = r.data;
          }
        })
      );
      setRefs(refData);
    } catch {
      toast.error("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  }, [endpoint, fields]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    const init = {};
    fields.forEach((f) => (init[f.name] = f.default ?? ""));
    setForm(init);
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = (item) => {
    const init = {};
    fields.forEach((f) => (init[f.name] = item[f.name] ?? f.default ?? ""));
    setForm(init);
    setEditing(item);
    setDialogOpen(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    const payload = { ...form };
    fields.forEach((f) => {
      if (f.type === "number") payload[f.name] = Number(payload[f.name]) || 0;
      if (f.type === "ref" && payload[f.name] === "") payload[f.name] = null;
    });
    try {
      if (editing) {
        await api.put(`/${endpoint}/${editing.id}`, payload);
        toast.success("Registro atualizado");
      } else {
        await api.post(`/${endpoint}`, payload);
        toast.success("Registro criado");
      }
      setDialogOpen(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    try {
      await api.delete(`/${endpoint}/${deleteId}`);
      toast.success("Registro removido");
      load();
    } catch {
      toast.error("Erro ao remover");
    } finally {
      setDeleteId(null);
    }
  };

  const refLabel = (col, value) => {
    const data = refs[col.refEndpoint] || [];
    const found = data.find((d) => d.id === value);
    return found ? found[col.refLabel] : "—";
  };

  const renderCell = (col, item) => {
    const value = item[col.key];
    if (col.type === "ref") return refLabel(col, value);
    if (col.type === "date") return value ? new Date(value + "T00:00:00").toLocaleDateString("pt-BR") : "—";
    if (col.render) return col.render(item);
    return value || "—";
  };

  return (
    <Layout title={title}>
      <div className="max-w-6xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#808080]">Cadastro</p>
            <h2 className="font-display text-2xl font-black text-[#273336] mt-1">{title}</h2>
          </div>
          {canWrite && (
            <Button data-testid={`add-${testid}-button`} onClick={openCreate}
              className="bg-[#FF161F] hover:bg-[#B20000] rounded-sm gap-2">
              <Plus className="w-4 h-4" /> Novo
            </Button>
          )}
        </div>

        <div className="bg-white border border-[#BFBFBF]/40 rounded-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid={`${testid}-table`}>
              <thead>
                <tr className="bg-[#273336] text-white text-left">
                  {columns.map((c) => (
                    <th key={c.key} className="px-4 py-3 font-semibold text-xs uppercase tracking-wider whitespace-nowrap">{c.label}</th>
                  ))}
                  {canWrite && <th className="px-4 py-3 text-right text-xs uppercase tracking-wider">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  [...Array(4)].map((_, i) => (
                    <tr key={i} className="border-b border-[#BFBFBF]/20">
                      {columns.map((c) => (
                        <td key={c.key} className="px-4 py-3"><div className="h-4 bg-[#F3F4F6] rounded animate-pulse" /></td>
                      ))}
                      {canWrite && <td className="px-4 py-3" />}
                    </tr>
                  ))
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length + 1} className="px-4 py-16 text-center">
                      <Inbox className="w-10 h-10 mx-auto text-[#BFBFBF] mb-3" />
                      <p className="text-[#808080]">Nenhum registro cadastrado.</p>
                    </td>
                  </tr>
                ) : (
                  items.map((item, idx) => (
                    <tr key={item.id} data-testid={`${testid}-row-${idx}`}
                      className="border-b border-[#BFBFBF]/20 hover:bg-[#F3F4F6] transition-colors">
                      {columns.map((c) => (
                        <td key={c.key} className="px-4 py-3 text-[#273336] whitespace-nowrap">{renderCell(c, item)}</td>
                      ))}
                      {canWrite && (
                        <td className="px-4 py-3 text-right whitespace-nowrap">
                          <button data-testid={`edit-${testid}-${idx}`} onClick={() => openEdit(item)}
                            className="p-1.5 text-[#808080] hover:text-[#273336] transition-colors">
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button data-testid={`delete-${testid}-${idx}`} onClick={() => setDeleteId(item.id)}
                            className="p-1.5 text-[#808080] hover:text-[#FF161F] transition-colors">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="rounded-sm bg-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-display">{editing ? "Editar" : "Novo"} — {title}</DialogTitle>
            <DialogDescription className="text-[#808080]">Preencha os campos e clique em salvar.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="space-y-4">
            {fields.map((f) => (
              <div key={f.name} className="space-y-1.5">
                <Label className="text-xs font-bold uppercase tracking-wider text-[#808080]">{f.label}</Label>
                {f.type === "select" ? (
                  <select data-testid={`field-${f.name}`} required={f.required}
                    value={form[f.name] ?? ""} onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                    className="w-full h-10 px-3 rounded-sm border border-[#BFBFBF] bg-white text-sm focus:ring-2 focus:ring-[#FF161F] focus:border-transparent outline-none">
                    <option value="">Selecione...</option>
                    {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                ) : f.type === "ref" ? (
                  <select data-testid={`field-${f.name}`} required={f.required}
                    value={form[f.name] ?? ""} onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                    className="w-full h-10 px-3 rounded-sm border border-[#BFBFBF] bg-white text-sm focus:ring-2 focus:ring-[#FF161F] focus:border-transparent outline-none">
                    <option value="">Selecione...</option>
                    {(refs[f.refEndpoint] || []).map((o) => <option key={o.id} value={o.id}>{o[f.refLabel]}</option>)}
                  </select>
                ) : (
                  <Input data-testid={`field-${f.name}`} type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
                    required={f.required} value={form[f.name] ?? ""}
                    onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                    className="rounded-sm border-[#BFBFBF] focus-visible:ring-[#FF161F]" />
                )}
              </div>
            ))}
            <DialogFooter className="gap-2">
              <Button type="button" variant="outline" className="rounded-sm" onClick={() => setDialogOpen(false)}>Cancelar</Button>
              <Button type="submit" data-testid="save-form-button" disabled={saving}
                className="bg-[#FF161F] hover:bg-[#B20000] rounded-sm">{saving ? "Salvando..." : "Salvar"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteId} onOpenChange={(o) => !o && setDeleteId(null)}>
        <AlertDialogContent className="rounded-sm bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar exclusão</AlertDialogTitle>
            <AlertDialogDescription>Esta ação não pode ser desfeita.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-sm">Cancelar</AlertDialogCancel>
            <AlertDialogAction data-testid="confirm-delete-button" onClick={confirmDelete}
              className="bg-[#FF161F] hover:bg-[#B20000] rounded-sm">Excluir</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
}
