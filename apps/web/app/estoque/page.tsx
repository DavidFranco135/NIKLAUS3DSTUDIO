"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { INVENTORY_MOVEMENT_TYPES } from "@/lib/types";
import type { InventoryItem } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

const CATEGORY_LABELS: Record<string, string> = {
  filament: "Filamento",
  resin: "Resina",
  component: "Componente",
  packaging: "Embalagem",
  spare_part: "Peça de reposição",
};

const MOVEMENT_LABELS: Record<string, string> = {
  entrada: "Entrada",
  saida: "Saída",
  ajuste: "Ajuste",
  consumo: "Consumo",
  perda: "Perda",
};

export default function EstoquePage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [movementItemId, setMovementItemId] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [category, setCategory] = useState("filament");
  const [unit, setUnit] = useState("g");
  const [minimumStock, setMinimumStock] = useState("0");
  const [unitCost, setUnitCost] = useState("");
  const [supplier, setSupplier] = useState("");
  const [initialQuantity, setInitialQuantity] = useState("0");

  const [movementType, setMovementType] = useState("entrada");
  const [movementQuantity, setMovementQuantity] = useState("");
  const [movementNotes, setMovementNotes] = useState("");

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const data = await apiFetch<InventoryItem[]>(
        `${orgPath}/inventory-items?low_stock_only=${lowStockOnly}`,
        { accessToken }
      );
      setItems(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar estoque.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, currentOrganizationId, orgPath, lowStockOnly]);

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
    setCategory("filament");
    setUnit("g");
    setMinimumStock("0");
    setUnitCost("");
    setSupplier("");
    setInitialQuantity("0");
    setEditingId(null);
    setShowForm(false);
  }

  function startEdit(item: InventoryItem) {
    setEditingId(item.id);
    setName(item.name);
    setCategory(item.category);
    setUnit(item.unit);
    setMinimumStock(String(item.minimum_stock));
    setUnitCost(item.unit_cost != null ? String(item.unit_cost) : "");
    setSupplier(item.supplier ?? "");
    setShowForm(true);
    setMovementItemId(null);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    setIsSaving(true);
    setError(null);
    try {
      if (editingId) {
        await apiFetch(`${orgPath}/inventory-items/${editingId}`, {
          method: "PATCH",
          accessToken,
          body: JSON.stringify({
            name,
            minimum_stock: Number(minimumStock || 0),
            unit_cost: unitCost ? Number(unitCost) : null,
            supplier: supplier || null,
          }),
        });
      } else {
        await apiFetch(`${orgPath}/inventory-items`, {
          method: "POST",
          accessToken,
          body: JSON.stringify({
            name,
            category,
            unit,
            minimum_stock: Number(minimumStock || 0),
            unit_cost: unitCost ? Number(unitCost) : null,
            supplier: supplier || null,
            initial_quantity: Number(initialQuantity || 0),
          }),
        });
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar item.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(item: InventoryItem) {
    if (!accessToken) return;
    if (!window.confirm(`Excluir o item de estoque "${item.name}"?`)) return;
    setError(null);
    try {
      await apiFetch(`${orgPath}/inventory-items/${item.id}`, { method: "DELETE", accessToken });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao excluir item.");
    }
  }

  async function handleMovement(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken || !movementItemId) return;
    setIsSaving(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/inventory-items/${movementItemId}/movements`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({
          type: movementType,
          quantity: Number(movementQuantity),
          notes: movementNotes || null,
        }),
      });
      setMovementQuantity("");
      setMovementNotes("");
      setMovementItemId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao registrar movimento.");
    } finally {
      setIsSaving(false);
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
    <AppShell title="Estoque">
      <div className="mx-auto max-w-5xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex items-center gap-2 text-sm text-neutral-400">
            <input
              type="checkbox"
              checked={lowStockOnly}
              onChange={(e) => setLowStockOnly(e.target.checked)}
              className="rounded border-neutral-700"
            />
            Mostrar só estoque baixo
          </label>
          <button
            onClick={() => (showForm ? resetForm() : setShowForm(true))}
            className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
          >
            {showForm ? "Cancelar" : "+ Novo item"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="grid grid-cols-1 gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-2"
          >
            <input required placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <select value={category} onChange={(e) => setCategory(e.target.value)} disabled={!!editingId} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 disabled:opacity-50">
              {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <select value={unit} onChange={(e) => setUnit(e.target.value)} disabled={!!editingId} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 disabled:opacity-50">
              <option value="g">g</option>
              <option value="kg">kg</option>
              <option value="un">un</option>
            </select>
            <input type="number" step="0.01" placeholder="Estoque mínimo" value={minimumStock} onChange={(e) => setMinimumStock(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input type="number" step="0.01" placeholder="Custo unitário (R$)" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input placeholder="Fornecedor" value={supplier} onChange={(e) => setSupplier(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            {!editingId && (
              <input type="number" step="0.01" placeholder="Quantidade inicial" value={initialQuantity} onChange={(e) => setInitialQuantity(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            )}
            <button type="submit" disabled={isSaving} className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50 sm:col-span-2">
              {isSaving ? "Salvando…" : editingId ? "Salvar alterações" : "Salvar item"}
            </button>
          </form>
        )}

        <div className="overflow-x-auto rounded-xl border border-neutral-800">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead className="border-b border-neutral-800 bg-neutral-950/50 text-neutral-400">
              <tr>
                <th className="px-4 py-3 font-medium">Nome</th>
                <th className="px-4 py-3 font-medium">Categoria</th>
                <th className="px-4 py-3 font-medium">Quantidade</th>
                <th className="px-4 py-3 font-medium">Mínimo</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-neutral-500">Carregando…</td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-neutral-500">Nenhum item de estoque.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <Fragment key={item.id}>
                    <tr className={item.is_low_stock ? "bg-yellow-950/20" : "hover:bg-neutral-900/50"}>
                      <td className="px-4 py-3">
                        {item.name}
                        {item.is_low_stock && (
                          <span className="ml-2 rounded bg-yellow-950 px-1.5 py-0.5 text-xs text-yellow-300">baixo</span>
                        )}
                      </td>
                      <td className="px-4 py-3">{CATEGORY_LABELS[item.category] ?? item.category}</td>
                      <td className="px-4 py-3">{item.quantity_on_hand} {item.unit}</td>
                      <td className="px-4 py-3">{item.minimum_stock} {item.unit}</td>
                      <td className="px-4 py-3 text-right space-x-3">
                        <button
                          onClick={() => setMovementItemId(movementItemId === item.id ? null : item.id)}
                          className="text-sm text-blue-400 hover:underline"
                        >
                          Movimentar
                        </button>
                        <button onClick={() => startEdit(item)} className="text-sm text-blue-400 hover:underline">
                          Editar
                        </button>
                        <button onClick={() => handleDelete(item)} className="text-sm text-red-400 hover:underline">
                          Excluir
                        </button>
                      </td>
                    </tr>
                    {movementItemId === item.id && (
                      <tr>
                        <td colSpan={5} className="bg-neutral-950/80 px-4 py-4">
                          <form onSubmit={handleMovement} className="flex flex-wrap items-end gap-2">
                            <select value={movementType} onChange={(e) => setMovementType(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
                              {INVENTORY_MOVEMENT_TYPES.map((t) => (
                                <option key={t} value={t}>{MOVEMENT_LABELS[t]}</option>
                              ))}
                            </select>
                            <input required type="number" step="0.01" placeholder="Quantidade" value={movementQuantity} onChange={(e) => setMovementQuantity(e.target.value)} className="w-32 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                            <input placeholder="Observação (opcional)" value={movementNotes} onChange={(e) => setMovementNotes(e.target.value)} className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                            <button type="submit" disabled={isSaving} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium disabled:opacity-50">
                              Confirmar
                            </button>
                          </form>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
