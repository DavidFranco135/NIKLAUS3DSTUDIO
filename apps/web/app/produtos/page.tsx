"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { CostProfile, Machine, Material, Product, ProductCost } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

type BomLine = { material_id: string; quantity_g: string };

export default function ProdutosPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [costProfiles, setCostProfiles] = useState<CostProfile[]>([]);
  const [costs, setCosts] = useState<Record<string, ProductCost | null>>({});
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [printTimeHours, setPrintTimeHours] = useState("");
  const [machineId, setMachineId] = useState("");
  const [bomLines, setBomLines] = useState<BomLine[]>([{ material_id: "", quantity_g: "" }]);

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const materialName = useCallback(
    (id: string) => materials.find((m) => m.id === id)?.name ?? "—",
    [materials]
  );

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const [productsData, materialsData, machinesData, profilesData] = await Promise.all([
        apiFetch<Product[]>(`${orgPath}/products`, { accessToken }),
        apiFetch<Material[]>(`${orgPath}/materials`, { accessToken }),
        apiFetch<Machine[]>(`${orgPath}/machines`, { accessToken }),
        apiFetch<CostProfile[]>(`${orgPath}/cost-profiles`, { accessToken }),
      ]);
      setProducts(productsData);
      setMaterials(materialsData);
      setMachines(machinesData);
      setCostProfiles(profilesData);

      const defaultProfile = profilesData.find((p) => p.is_default) ?? profilesData[0];
      if (defaultProfile) {
        const entries = await Promise.all(
          productsData.map(async (p) => {
            try {
              const cost = await apiFetch<ProductCost>(
                `${orgPath}/products/${p.id}/cost?cost_profile_id=${defaultProfile.id}`,
                { accessToken }
              );
              return [p.id, cost] as const;
            } catch {
              return [p.id, null] as const;
            }
          })
        );
        setCosts(Object.fromEntries(entries));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar produtos.");
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

  function updateBomLine(index: number, patch: Partial<BomLine>) {
    setBomLines((lines) => lines.map((l, i) => (i === index ? { ...l, ...patch } : l)));
  }

  function addBomLine() {
    setBomLines((lines) => [...lines, { material_id: "", quantity_g: "" }]);
  }

  function removeBomLine(index: number) {
    setBomLines((lines) => lines.filter((_, i) => i !== index));
  }

  function resetForm() {
    setName("");
    setDescription("");
    setPrintTimeHours("");
    setMachineId("");
    setBomLines([{ material_id: "", quantity_g: "" }]);
    setEditingId(null);
    setShowForm(false);
  }

  function startEdit(product: Product) {
    setEditingId(product.id);
    setName(product.name);
    setDescription(product.description ?? "");
    setPrintTimeHours(product.print_time_hours != null ? String(product.print_time_hours) : "");
    setMachineId(product.machine_id ?? "");
    setBomLines(
      product.materials.length > 0
        ? product.materials.map((l) => ({
            material_id: l.material_id,
            quantity_g: String(l.quantity_g),
          }))
        : [{ material_id: "", quantity_g: "" }]
    );
    setShowForm(true);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    const validLines = bomLines.filter((l) => l.material_id && l.quantity_g);
    setIsSaving(true);
    setError(null);
    try {
      const body = JSON.stringify({
        name,
        description: description || null,
        print_time_hours: printTimeHours ? Number(printTimeHours) : null,
        machine_id: machineId || null,
        materials: validLines.map((l) => ({
          material_id: l.material_id,
          quantity_g: Number(l.quantity_g),
        })),
      });
      if (editingId) {
        await apiFetch(`${orgPath}/products/${editingId}`, { method: "PATCH", accessToken, body });
      } else {
        await apiFetch(`${orgPath}/products`, { method: "POST", accessToken, body });
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar produto.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(product: Product) {
    if (!accessToken) return;
    if (!window.confirm(`Excluir o produto "${product.name}"?`)) return;
    setError(null);
    try {
      await apiFetch(`${orgPath}/products/${product.id}`, { method: "DELETE", accessToken });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao excluir produto.");
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
    <AppShell title="Produtos">
      <div className="mx-auto max-w-5xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        {materials.length === 0 && !isLoading && (
          <p className="rounded-lg border border-yellow-800 bg-yellow-950/40 px-4 py-3 text-sm text-yellow-300">
            Cadastre pelo menos um material na aba Materiais antes de criar um produto.
          </p>
        )}
        {costProfiles.length === 0 && !isLoading && (
          <p className="rounded-lg border border-yellow-800 bg-yellow-950/40 px-4 py-3 text-sm text-yellow-300">
            Cadastre um perfil de custo na aba Precificação (Perfil de custo) para ver o custo/preço calculado aqui.
          </p>
        )}

        <div className="flex items-center justify-between">
          <p className="text-sm text-neutral-500">{products.length} produto(s) cadastrado(s)</p>
          <button
            onClick={() => (showForm ? resetForm() : setShowForm(true))}
            disabled={materials.length === 0}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
          >
            {showForm ? "Cancelar" : "+ Novo produto"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4"
          >
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <input required placeholder="Nome do produto" value={name} onChange={(e) => setName(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 sm:col-span-2" />
              <input placeholder="Descrição (opcional)" value={description} onChange={(e) => setDescription(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 sm:col-span-2" />
              <input type="number" step="0.01" placeholder="Tempo de impressão (h)" value={printTimeHours} onChange={(e) => setPrintTimeHours(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <select value={machineId} onChange={(e) => setMachineId(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2">
                <option value="">Máquina (opcional)</option>
                {machines.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <p className="text-xs text-neutral-500">
                Quanto material esse produto consome por unidade
              </p>
              {bomLines.map((line, index) => (
                <div key={index} className="flex flex-col gap-2 sm:flex-row">
                  <select
                    value={line.material_id}
                    onChange={(e) => updateBomLine(index, { material_id: e.target.value })}
                    className="w-full min-w-0 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm sm:flex-1"
                  >
                    <option value="">Selecione o material…</option>
                    {materials.map((m) => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Gramas"
                      value={line.quantity_g}
                      onChange={(e) => updateBomLine(index, { quantity_g: e.target.value })}
                      className="w-full min-w-0 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm sm:w-28"
                    />
                    <button
                      type="button"
                      onClick={() => removeBomLine(index)}
                      disabled={bomLines.length === 1}
                      className="shrink-0 rounded border border-neutral-700 px-3 py-2 text-sm text-neutral-400 hover:border-red-700 hover:text-red-400 disabled:opacity-30"
                    >
                      Remover
                    </button>
                  </div>
                </div>
              ))}
              <button
                type="button"
                onClick={addBomLine}
                className="text-sm text-blue-400 hover:underline"
              >
                + Adicionar material
              </button>
            </div>

            <button type="submit" disabled={isSaving} className="w-full rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50">
              {isSaving ? "Salvando…" : editingId ? "Salvar alterações" : "Salvar produto"}
            </button>
          </form>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {isLoading ? (
            <p className="text-neutral-500">Carregando…</p>
          ) : products.length === 0 ? (
            <p className="text-neutral-500">Nenhum produto cadastrado ainda.</p>
          ) : (
            products.map((product) => {
              const cost = costs[product.id];
              return (
                <div key={product.id} className="space-y-2 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-medium">{product.name}</h3>
                      {product.description && (
                        <p className="text-xs text-neutral-500">{product.description}</p>
                      )}
                    </div>
                    {product.print_time_hours != null && (
                      <span className="shrink-0 rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
                        {product.print_time_hours}h
                      </span>
                    )}
                  </div>

                  {product.materials.length > 0 && (
                    <ul className="text-xs text-neutral-400">
                      {product.materials.map((line, i) => (
                        <li key={i}>
                          {materialName(line.material_id)} — {line.quantity_g}g
                        </li>
                      ))}
                    </ul>
                  )}

                  {cost ? (
                    <div className="flex items-center justify-between border-t border-neutral-800 pt-2 text-sm">
                      <span className="text-neutral-400">Custo: {formatCurrency(cost.production_cost)}</span>
                      <span className="font-medium text-green-400">Venda: {formatCurrency(cost.suggested_price)}</span>
                    </div>
                  ) : (
                    <p className="border-t border-neutral-800 pt-2 text-xs text-neutral-600">
                      Cadastre um perfil de custo para ver o preço sugerido.
                    </p>
                  )}

                  <div className="flex gap-3 border-t border-neutral-800 pt-2">
                    <button onClick={() => startEdit(product)} className="text-xs text-blue-400 hover:underline">
                      Editar
                    </button>
                    <button onClick={() => handleDelete(product)} className="text-xs text-red-400 hover:underline">
                      Excluir
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </AppShell>
  );
}
