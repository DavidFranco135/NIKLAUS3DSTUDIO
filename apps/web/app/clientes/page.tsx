"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import type { Customer } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

export default function ClientesPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [document, setDocument] = useState("");

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const data = await apiFetch<Customer[]>(`${orgPath}/customers`, { accessToken });
      setCustomers(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar clientes.");
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
    setEmail("");
    setPhone("");
    setDocument("");
    setEditingId(null);
    setShowForm(false);
  }

  function startEdit(c: Customer) {
    setEditingId(c.id);
    setName(c.name);
    setEmail(c.email ?? "");
    setPhone(c.phone ?? "");
    setDocument(c.document ?? "");
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
        email: email || null,
        phone: phone || null,
        document: document || null,
      });
      if (editingId) {
        await apiFetch(`${orgPath}/customers/${editingId}`, { method: "PATCH", accessToken, body });
      } else {
        await apiFetch(`${orgPath}/customers`, { method: "POST", accessToken, body });
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar cliente.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(c: Customer) {
    if (!accessToken) return;
    if (!window.confirm(`Excluir o cliente "${c.name}"?`)) return;
    setError(null);
    try {
      await apiFetch(`${orgPath}/customers/${c.id}`, { method: "DELETE", accessToken });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao excluir cliente.");
    }
  }

  const filtered = customers.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    (c.email ?? "").toLowerCase().includes(search.toLowerCase()) ||
    (c.phone ?? "").includes(search)
  );

  if (status !== "authenticated") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-neutral-400">Carregando…</p>
      </main>
    );
  }

  return (
    <AppShell title="Clientes">
      <div className="mx-auto max-w-5xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <input
            placeholder="Buscar por nome, e-mail ou telefone…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 sm:max-w-xs"
          />
          <button
            onClick={() => (showForm ? resetForm() : setShowForm(true))}
            className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
          >
            {showForm ? "Cancelar" : "+ Novo cliente"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="grid gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-2"
          >
            <input required placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input type="email" placeholder="E-mail" value={email} onChange={(e) => setEmail(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input placeholder="Telefone" value={phone} onChange={(e) => setPhone(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input placeholder="CPF/CNPJ" value={document} onChange={(e) => setDocument(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <button type="submit" disabled={isSaving} className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50 sm:col-span-2">
              {isSaving ? "Salvando…" : editingId ? "Salvar alterações" : "Salvar cliente"}
            </button>
          </form>
        )}

        <div className="overflow-x-auto rounded-xl border border-neutral-800">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead className="border-b border-neutral-800 bg-neutral-950/50 text-neutral-400">
              <tr>
                <th className="px-4 py-3 font-medium">Nome</th>
                <th className="px-4 py-3 font-medium">E-mail</th>
                <th className="px-4 py-3 font-medium">Telefone</th>
                <th className="px-4 py-3 font-medium">Cadastrado em</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-neutral-500">Carregando…</td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-neutral-500">Nenhum cliente encontrado.</td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-neutral-900/50">
                    <td className="px-4 py-3">{c.name}</td>
                    <td className="px-4 py-3">{c.email ?? "—"}</td>
                    <td className="px-4 py-3">{c.phone ?? "—"}</td>
                    <td className="px-4 py-3">{formatDate(c.created_at)}</td>
                    <td className="px-4 py-3 text-right space-x-3">
                      <button onClick={() => startEdit(c)} className="text-sm text-blue-400 hover:underline">
                        Editar
                      </button>
                      <button onClick={() => handleDelete(c)} className="text-sm text-red-400 hover:underline">
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
