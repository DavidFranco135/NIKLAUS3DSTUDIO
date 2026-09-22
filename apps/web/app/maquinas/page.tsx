"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { Machine } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

const STATUS_LABELS: Record<string, string> = {
  active: "Ativa",
  maintenance: "Manutenção",
  inactive: "Inativa",
};

const STATUS_TONE: Record<string, string> = {
  active: "bg-green-950 text-green-300",
  maintenance: "bg-yellow-950 text-yellow-300",
  inactive: "bg-neutral-800 text-neutral-400",
};

export default function MaquinasPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [machines, setMachines] = useState<Machine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [brand, setBrand] = useState("");
  const [model, setModel] = useState("");
  const [technology, setTechnology] = useState("FDM");
  const [costPerHour, setCostPerHour] = useState("");
  const [volX, setVolX] = useState("");
  const [volY, setVolY] = useState("");
  const [volZ, setVolZ] = useState("");

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const data = await apiFetch<Machine[]>(`${orgPath}/machines`, { accessToken });
      setMachines(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar máquinas.");
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

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    setIsCreating(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/machines`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({
          name,
          brand: brand || null,
          model: model || null,
          technology,
          cost_per_hour: costPerHour ? Number(costPerHour) : null,
          build_volume_x_mm: volX ? Number(volX) : null,
          build_volume_y_mm: volY ? Number(volY) : null,
          build_volume_z_mm: volZ ? Number(volZ) : null,
        }),
      });
      setName("");
      setBrand("");
      setModel("");
      setTechnology("FDM");
      setCostPerHour("");
      setVolX("");
      setVolY("");
      setVolZ("");
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao criar máquina.");
    } finally {
      setIsCreating(false);
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
    <AppShell title="Máquinas">
      <div className="mx-auto max-w-5xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        <div className="flex items-center justify-between">
          <p className="text-sm text-neutral-500">{machines.length} máquina(s) cadastrada(s)</p>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
          >
            {showForm ? "Cancelar" : "+ Nova máquina"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleCreate}
            className="grid gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-2"
          >
            <input required placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <select value={technology} onChange={(e) => setTechnology(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2">
              <option value="FDM">FDM</option>
              <option value="SLA">SLA</option>
              <option value="MSLA">MSLA</option>
            </select>
            <input placeholder="Marca" value={brand} onChange={(e) => setBrand(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input placeholder="Modelo" value={model} onChange={(e) => setModel(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input type="number" step="0.01" placeholder="Custo por hora (R$)" value={costPerHour} onChange={(e) => setCostPerHour(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <div className="grid grid-cols-3 gap-2">
              <input type="number" placeholder="X mm" value={volX} onChange={(e) => setVolX(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <input type="number" placeholder="Y mm" value={volY} onChange={(e) => setVolY(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <input type="number" placeholder="Z mm" value={volZ} onChange={(e) => setVolZ(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            </div>
            <button type="submit" disabled={isCreating} className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50 sm:col-span-2">
              {isCreating ? "Salvando…" : "Salvar máquina"}
            </button>
          </form>
        )}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {isLoading ? (
            <p className="text-neutral-500">Carregando…</p>
          ) : machines.length === 0 ? (
            <p className="text-neutral-500">Nenhuma máquina cadastrada.</p>
          ) : (
            machines.map((m) => (
              <div key={m.id} className="space-y-2 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">{m.name}</h3>
                  <span className={`rounded px-2 py-0.5 text-xs ${STATUS_TONE[m.status] ?? "bg-neutral-800 text-neutral-400"}`}>
                    {STATUS_LABELS[m.status] ?? m.status}
                  </span>
                </div>
                <p className="text-xs text-neutral-500">
                  {m.brand ?? "—"} {m.model ?? ""} · {m.technology}
                </p>
                {(m.build_volume_x_mm || m.build_volume_y_mm || m.build_volume_z_mm) && (
                  <p className="text-xs text-neutral-500">
                    Volume: {m.build_volume_x_mm ?? "—"} x {m.build_volume_y_mm ?? "—"} x {m.build_volume_z_mm ?? "—"} mm
                  </p>
                )}
                <p className="text-sm text-neutral-300">{formatCurrency(m.cost_per_hour)}/h</p>
              </div>
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
}
