"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { Material } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

export default function MateriaisPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [materials, setMaterials] = useState<Material[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [color, setColor] = useState("");
  const [costPerKg, setCostPerKg] = useState("");
  const [supplier, setSupplier] = useState("");

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const data = await apiFetch<Material[]>(`${orgPath}/materials`, { accessToken });
      setMaterials(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar materiais.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, currentOrganizationId, orgPath]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status !== "authenticated") return;
    const timeoutId = setTimeout(load, 0);
    return () => clearTimeout(timeoutId);
  }, [status, router, load]);

  function resetForm() {
    setName("");
    setType("");
    setColor("");
    setCostPerKg("");
    setSupplier("");
    setEditingId(null);
    setShowForm(false);
  }

  function startEdit(m: Material) {
    setEditingId(m.id);
    setName(m.name);
    setType(m.type);
    setColor(m.color ?? "");
    setCostPerKg(m.cost_per_kg != null ? String(m.cost_per_kg) : "");
    setSupplier(m.supplier ?? "");
    setShowForm(true);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    setIsSaving(true);
    setError(null);
    try {
      const body = JSON.stringify({
        name,
        type,
        color: color || null,
        cost_per_kg: costPerKg ? Number(costPerKg) : null,
        supplier: supplier || null,
      });
      if (editingId) {
        await apiFetch(`${orgPath}/materials/${editingId}`, { method: "PATCH", accessToken, body });
      } else {
        await apiFetch(`${orgPath}/materials`, { method: "POST", accessToken, body });
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar material.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(m: Material) {
    if (!accessToken) return;
    if (!window.confirm(`Excluir o material "${m.name}"?`)) return;
    setError(null);
    try {
      await apiFetch(`${orgPath}/materials/${m.id}`, { method: "DELETE", accessToken });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao excluir material.");
    }
  }

  if (status !== "authenticated") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-neutral-400">Carregando…</p>
      </main>
    );
  }

  return (
    <AppShell title="Materiais">
      <div className="mx-auto max-w-5xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        <div className="flex items-center justify-between">
          <p className="text-sm text-neutral-500">{materials.length} material(is) cadastrado(s)</p>
          <button
            onClick={() => (showForm ? resetForm() : setShowForm(true))}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
          >
            {showForm ? "Cancelar" : "+ Novo material"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="grid grid-cols-1 gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-2"
          >
            <input required placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input required placeholder="Tipo (ex: PLA, PETG)" value={type} onChange={(e) => setType(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input placeholder="Cor" value={color} onChange={(e) => setColor(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input type="number" step="0.01" placeholder="Custo por kg (R$)" value={costPerKg} onChange={(e) => setCostPerKg(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input placeholder="Fornecedor" value={supplier} onChange={(e) => setSupplier(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <button type="submit" disabled={isSaving} className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50 sm:col-span-2">
              {isSaving ? "Salvando…" : editingId ? "Salvar alterações" : "Salvar material"}
            </button>
          </form>
        )}

        <div className="overflow-x-auto rounded-xl border border-neutral-800">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead className="border-b border-neutral-800 bg-neutral-950/50 text-neutral-400">
              <tr>
                <th className="px-4 py-3 font-medium">Nome</th>
                <th className="px-4 py-3 font-medium">Tipo</th>
                <th className="px-4 py-3 font-medium">Cor</th>
                <th className="px-4 py-3 font-medium">Custo/kg</th>
                <th className="px-4 py-3 font-medium">Fornecedor</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-neutral-500">Carregando…</td>
                </tr>
              ) : materials.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-neutral-500">Nenhum material cadastrado.</td>
                </tr>
              ) : (
                materials.map((m) => (
                  <tr key={m.id} className="hover:bg-neutral-900/50">
                    <td className="px-4 py-3">{m.name}</td>
                    <td className="px-4 py-3">{m.type}</td>
                    <td className="px-4 py-3">{m.color ?? "—"}</td>
                    <td className="px-4 py-3">{formatCurrency(m.cost_per_kg)}</td>
                    <td className="px-4 py-3">{m.supplier ?? "—"}</td>
                    <td className="px-4 py-3 text-right space-x-3">
                      <button onClick={() => startEdit(m)} className="text-sm text-blue-400 hover:underline">
                        Editar
                      </button>
                      <button onClick={() => handleDelete(m)} className="text-sm text-red-400 hover:underline">
                        Excluir
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
