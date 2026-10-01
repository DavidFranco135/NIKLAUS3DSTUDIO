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
            className="grid grid-cols-1 gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-2"
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

        <div className="rounded-xl border border-neutral-800 divide-y divide-neutral-800">
          {isLoading ? (
            <p className="px-4 py-6 text-center text-sm text-neutral-500">Carregando…</p>
          ) : filtered.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-neutral-500">Nenhum cliente encontrado.</p>
          ) : (
            filtered.map((c) => (
              <div key={c.id} className="flex flex-wrap items-start justify-between gap-2 p-4">
                <div className="min-w-0 space-y-1">
                  <p className="truncate font-medium">{c.name}</p>
                  <p className="text-sm text-neutral-400">{c.email ?? "—"}</p>
                  <p className="text-sm text-neutral-400">{c.phone ?? "—"}</p>
                  <p className="text-xs text-neutral-500">Cadastrado em {formatDate(c.created_at)}</p>
                </div>
                <div className="flex shrink-0 gap-3 text-sm">
                  <button onClick={() => startEdit(c)} className="text-blue-400 hover:underline">
                    Editar
                  </button>
                  <button onClick={() => handleDelete(c)} className="text-red-400 hover:underline">
                    Excluir
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
}
