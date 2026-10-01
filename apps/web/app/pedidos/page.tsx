"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatCurrency, formatDate } from "@/lib/format";
import { ORDER_STATUSES } from "@/lib/types";
import type { CostProfile, Customer, Order, OrderItem, Product, ProductCost } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

const STATUS_LABELS: Record<string, string> = {
  quote: "Orçamento",
  order: "Pedido",
  paid: "Pago",
  production: "Produção",
  printing: "Imprimindo",
  finishing: "Acabamento",
  packaging: "Embalagem",
  delivered: "Entregue",
  completed: "Concluído",
  cancelled: "Cancelado",
};

const STATUS_TONE: Record<string, string> = {
  quote: "bg-neutral-800 text-neutral-300",
  order: "bg-blue-950 text-blue-300",
  paid: "bg-cyan-950 text-cyan-300",
  production: "bg-purple-950 text-purple-300",
  printing: "bg-purple-950 text-purple-300",
  finishing: "bg-indigo-950 text-indigo-300",
  packaging: "bg-indigo-950 text-indigo-300",
  delivered: "bg-green-950 text-green-300",
  completed: "bg-green-950 text-green-300",
  cancelled: "bg-red-950 text-red-300",
};

function nextStatus(current: string): string | null {
  const idx = ORDER_STATUSES.indexOf(current as (typeof ORDER_STATUSES)[number]);
  if (idx < 0 || idx >= ORDER_STATUSES.length - 2) return null;
  return ORDER_STATUSES[idx + 1];
}

export default function PedidosPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [defaultCostProfile, setDefaultCostProfile] = useState<CostProfile | null>(null);
  const [itemsByOrder, setItemsByOrder] = useState<Record<string, OrderItem[]>>({});
  const [expandedOrderId, setExpandedOrderId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [customerId, setCustomerId] = useState("");
  const [notes, setNotes] = useState("");

  const [itemProductId, setItemProductId] = useState("");
  const [itemQuantity, setItemQuantity] = useState("1");
  const [itemUnitCost, setItemUnitCost] = useState("");
  const [itemUnitPrice, setItemUnitPrice] = useState("");
  const [isPricingItem, setIsPricingItem] = useState(false);
  const [isAddingItem, setIsAddingItem] = useState(false);

  const [editingOrderId, setEditingOrderId] = useState<string | null>(null);
  const [editCustomerId, setEditCustomerId] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [isSavingOrderEdit, setIsSavingOrderEdit] = useState(false);

  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editItemProductId, setEditItemProductId] = useState("");
  const [editItemQuantity, setEditItemQuantity] = useState("1");
  const [editItemUnitCost, setEditItemUnitCost] = useState("");
  const [editItemUnitPrice, setEditItemUnitPrice] = useState("");
  const [isPricingItemEdit, setIsPricingItemEdit] = useState(false);
  const [isSavingItemEdit, setIsSavingItemEdit] = useState(false);

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const customerName = useCallback(
    (id: string) => customers.find((c) => c.id === id)?.name ?? "—",
    [customers]
  );

  const productName = useCallback(
    (id: string | null) => (id ? products.find((p) => p.id === id)?.name ?? "—" : "—"),
    [products]
  );

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const [ordersData, customersData, productsData, profilesData] = await Promise.all([
        apiFetch<Order[]>(`${orgPath}/orders`, { accessToken }),
        apiFetch<Customer[]>(`${orgPath}/customers`, { accessToken }),
        apiFetch<Product[]>(`${orgPath}/products`, { accessToken }),
        apiFetch<CostProfile[]>(`${orgPath}/cost-profiles`, { accessToken }),
      ]);
      setOrders(ordersData);
      setCustomers(customersData);
      setProducts(productsData);
      setDefaultCostProfile(profilesData.find((p) => p.is_default) ?? profilesData[0] ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar pedidos.");
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
    if (!accessToken || !customerId) return;
    setIsSaving(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/orders`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({ customer_id: customerId, notes: notes || null }),
      });
      setCustomerId("");
      setNotes("");
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao criar pedido.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleAdvance(order: Order) {
    if (!accessToken) return;
    const next = nextStatus(order.status);
    if (!next) return;
    setError(null);
    try {
      await apiFetch(`${orgPath}/orders/${order.id}/transition`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({ status: next }),
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao avançar status.");
    }
  }

  function startEditOrder(order: Order) {
    setEditingOrderId(order.id);
    setEditCustomerId(order.customer_id);
    setEditNotes(order.notes ?? "");
  }

  function cancelEditOrder() {
    setEditingOrderId(null);
  }

  async function handleSaveOrderEdit(order: Order) {
    if (!accessToken) return;
    setIsSavingOrderEdit(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/orders/${order.id}`, {
        method: "PATCH",
        accessToken,
        body: JSON.stringify({ customer_id: editCustomerId, notes: editNotes }),
      });
      setEditingOrderId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar pedido.");
    } finally {
      setIsSavingOrderEdit(false);
    }
  }

  async function handleDeleteOrder(order: Order) {
    if (!accessToken) return;
    if (!window.confirm(`Excluir o pedido de "${customerName(order.customer_id)}"?`)) return;
    setError(null);
    try {
      await apiFetch(`${orgPath}/orders/${order.id}`, { method: "DELETE", accessToken });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao excluir pedido.");
    }
  }

  function startEditItem(item: OrderItem) {
    setEditingItemId(item.id);
    setEditItemProductId(item.product_id ?? "");
    setEditItemQuantity(String(item.quantity));
    setEditItemUnitCost(item.unit_cost != null ? String(item.unit_cost) : "");
    setEditItemUnitPrice(item.unit_price != null ? String(item.unit_price) : "");
  }

  function cancelEditItem() {
    setEditingItemId(null);
  }

  async function handleEditPickProduct(productId: string) {
    setEditItemProductId(productId);
    setEditItemUnitCost("");
    setEditItemUnitPrice("");
    if (!productId) return;
    const manualPrice = products.find((p) => p.id === productId)?.manual_price;
    if (manualPrice != null) {
      setEditItemUnitPrice(manualPrice.toFixed(2));
      return;
    }
    if (!accessToken || !defaultCostProfile) return;
    setIsPricingItemEdit(true);
    try {
      const cost = await apiFetch<ProductCost>(
        `${orgPath}/products/${productId}/cost?cost_profile_id=${defaultCostProfile.id}`,
        { accessToken }
      );
      setEditItemUnitCost(cost.production_cost.toFixed(2));
      setEditItemUnitPrice(cost.suggested_price.toFixed(2));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao calcular custo do produto.");
    } finally {
      setIsPricingItemEdit(false);
    }
  }

  async function handleSaveItemEdit(orderId: string, item: OrderItem) {
    if (!accessToken) return;
    setIsSavingItemEdit(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/orders/${orderId}/items/${item.id}`, {
        method: "PATCH",
        accessToken,
        body: JSON.stringify({
          product_id: editItemProductId || null,
          quantity: Number(editItemQuantity || 1),
          unit_cost: editItemUnitCost ? Number(editItemUnitCost) : null,
          unit_price: editItemUnitPrice ? Number(editItemUnitPrice) : null,
        }),
      });
      setEditingItemId(null);
      const data = await apiFetch<OrderItem[]>(`${orgPath}/orders/${orderId}/items`, { accessToken });
      setItemsByOrder((prev) => ({ ...prev, [orderId]: data }));
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar item.");
    } finally {
      setIsSavingItemEdit(false);
    }
  }

  async function handleDeleteItem(orderId: string, item: OrderItem) {
    if (!accessToken) return;
    if (!window.confirm("Remover este item do pedido?")) return;
    setError(null);
    try {
      await apiFetch(`${orgPath}/orders/${orderId}/items/${item.id}`, {
        method: "DELETE",
        accessToken,
      });
      const data = await apiFetch<OrderItem[]>(`${orgPath}/orders/${orderId}/items`, { accessToken });
      setItemsByOrder((prev) => ({ ...prev, [orderId]: data }));
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao remover item.");
    }
  }

  async function toggleItems(orderId: string) {
    if (expandedOrderId === orderId) {
      setExpandedOrderId(null);
      return;
    }
    setExpandedOrderId(orderId);
    setItemProductId("");
    setItemQuantity("1");
    setItemUnitCost("");
    setItemUnitPrice("");
    if (!itemsByOrder[orderId] && accessToken) {
      try {
        const data = await apiFetch<OrderItem[]>(`${orgPath}/orders/${orderId}/items`, { accessToken });
        setItemsByOrder((prev) => ({ ...prev, [orderId]: data }));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Falha ao carregar itens do pedido.");
      }
    }
  }

  async function handlePickProduct(productId: string) {
    setItemProductId(productId);
    setItemUnitCost("");
    setItemUnitPrice("");
    if (!productId) return;
    const manualPrice = products.find((p) => p.id === productId)?.manual_price;
    if (manualPrice != null) {
      setItemUnitPrice(manualPrice.toFixed(2));
      return;
    }
    if (!accessToken || !defaultCostProfile) return;
    setIsPricingItem(true);
    try {
      const cost = await apiFetch<ProductCost>(
        `${orgPath}/products/${productId}/cost?cost_profile_id=${defaultCostProfile.id}`,
        { accessToken }
      );
      setItemUnitCost(cost.production_cost.toFixed(2));
      setItemUnitPrice(cost.suggested_price.toFixed(2));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao calcular custo do produto.");
    } finally {
      setIsPricingItem(false);
    }
  }

  async function handleAddItem(orderId: string, event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken || !itemProductId) return;
    setIsAddingItem(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/orders/${orderId}/items`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({
          product_id: itemProductId,
          quantity: Number(itemQuantity || 1),
          unit_cost: itemUnitCost ? Number(itemUnitCost) : null,
          unit_price: itemUnitPrice ? Number(itemUnitPrice) : null,
        }),
      });
      setItemProductId("");
      setItemQuantity("1");
      setItemUnitCost("");
      setItemUnitPrice("");
      const data = await apiFetch<OrderItem[]>(`${orgPath}/orders/${orderId}/items`, { accessToken });
      setItemsByOrder((prev) => ({ ...prev, [orderId]: data }));
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao adicionar item.");
    } finally {
      setIsAddingItem(false);
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
    <AppShell title="Pedidos">
      <div className="mx-auto max-w-5xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        <div className="flex items-center justify-between">
          <p className="text-sm text-neutral-500">{orders.length} pedido(s)</p>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
          >
            {showForm ? "Cancelar" : "+ Novo pedido"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleCreate}
            className="grid grid-cols-1 gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-2"
          >
            <select required value={customerId} onChange={(e) => setCustomerId(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2">
              <option value="">Selecione o cliente…</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <input placeholder="Observações (opcional)" value={notes} onChange={(e) => setNotes(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            {customers.length === 0 && (
              <p className="text-xs text-yellow-300 sm:col-span-2">
                Nenhum cliente cadastrado ainda — crie um cliente primeiro na aba Clientes.
              </p>
            )}
            <button type="submit" disabled={isSaving || !customerId} className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50 sm:col-span-2">
              {isSaving ? "Salvando…" : "Salvar pedido"}
            </button>
          </form>
        )}

        <div className="rounded-xl border border-neutral-800 divide-y divide-neutral-800">
          {isLoading ? (
            <p className="px-4 py-6 text-center text-sm text-neutral-500">Carregando…</p>
          ) : orders.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-neutral-500">Nenhum pedido ainda.</p>
          ) : (
            orders.map((order) => {
              const next = nextStatus(order.status);
              return (
                <div key={order.id} className="space-y-3 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{customerName(order.customer_id)}</p>
                      <p className="text-xs text-neutral-500">{formatDate(order.created_at)}</p>
                    </div>
                    <span className={`shrink-0 rounded px-2 py-0.5 text-xs ${STATUS_TONE[order.status] ?? "bg-neutral-800 text-neutral-300"}`}>
                      {STATUS_LABELS[order.status] ?? order.status}
                    </span>
                  </div>
                  <p className="text-sm text-neutral-300">
                    Total: <span className="font-medium text-neutral-100">{formatCurrency(order.total_amount)}</span>
                  </p>
                  <div className="flex flex-wrap gap-x-3 gap-y-2 text-sm">
                    <button onClick={() => toggleItems(order.id)} className="text-blue-400 hover:underline">
                      Itens
                    </button>
                    {next && (
                      <button onClick={() => handleAdvance(order)} className="text-green-400 hover:underline">
                        Avançar → {STATUS_LABELS[next]}
                      </button>
                    )}
                    <button onClick={() => startEditOrder(order)} className="text-blue-400 hover:underline">
                      Editar
                    </button>
                    <button onClick={() => handleDeleteOrder(order)} className="text-red-400 hover:underline">
                      Excluir
                    </button>
                  </div>
                  {editingOrderId === order.id && (
                    <div className="rounded border border-neutral-800 bg-neutral-950/80 p-3">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                        <div className="w-full sm:flex-1">
                          <label className="mb-1 block text-xs text-neutral-500">Cliente</label>
                          <select value={editCustomerId} onChange={(e) => setEditCustomerId(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
                            {customers.map((c) => (
                              <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                          </select>
                        </div>
                        <div className="w-full sm:flex-1">
                          <label className="mb-1 block text-xs text-neutral-500">Observações</label>
                          <input value={editNotes} onChange={(e) => setEditNotes(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                        </div>
                        <div className="flex gap-2">
                          <button onClick={() => handleSaveOrderEdit(order)} disabled={isSavingOrderEdit} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium disabled:opacity-50">
                            {isSavingOrderEdit ? "Salvando…" : "Salvar"}
                          </button>
                          <button onClick={cancelEditOrder} className="rounded border border-neutral-700 px-4 py-2 text-sm text-neutral-400 hover:border-neutral-500">
                            Cancelar
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                  {expandedOrderId === order.id && (
                    <div className="space-y-4 rounded border border-neutral-800 bg-neutral-950/80 p-3">
                      {!itemsByOrder[order.id] ? (
                        <p className="text-sm text-neutral-500">Carregando itens…</p>
                      ) : itemsByOrder[order.id].length === 0 ? (
                        <p className="text-sm text-neutral-500">Nenhum item neste pedido ainda.</p>
                      ) : (
                        <ul className="space-y-2 text-sm text-neutral-300">
                          {itemsByOrder[order.id].map((item) => (
                            <li key={item.id} className="space-y-2">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="min-w-0 flex-1 truncate">
                                  {productName(item.product_id)} · Qtd. {item.quantity} — {item.status}
                                </span>
                                <span className="shrink-0">{formatCurrency((item.unit_price ?? 0) * item.quantity)}</span>
                                <span className="shrink-0 space-x-2">
                                  <button onClick={() => startEditItem(item)} className="text-xs text-blue-400 hover:underline">
                                    Editar
                                  </button>
                                  <button onClick={() => handleDeleteItem(order.id, item)} className="text-xs text-red-400 hover:underline">
                                    Excluir
                                  </button>
                                </span>
                              </div>
                              {editingItemId === item.id && (
                                <div className="grid grid-cols-1 gap-2 rounded border border-neutral-800 bg-neutral-950/60 p-3 sm:grid-cols-2">
                                  <div className="sm:col-span-2">
                                    <label className="mb-1 block text-xs text-neutral-500">Produto</label>
                                    <select
                                      value={editItemProductId}
                                      onChange={(e) => handleEditPickProduct(e.target.value)}
                                      className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
                                    >
                                      <option value="">Selecione o produto…</option>
                                      {products.map((p) => (
                                        <option key={p.id} value={p.id}>{p.name}</option>
                                      ))}
                                    </select>
                                  </div>
                                  <div>
                                    <label className="mb-1 block text-xs text-neutral-500">Qtd.</label>
                                    <input type="number" min={1} value={editItemQuantity} onChange={(e) => setEditItemQuantity(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                                  </div>
                                  <div>
                                    <label className="mb-1 block text-xs text-neutral-500">Custo unit.</label>
                                    <input type="number" step="0.01" value={editItemUnitCost} onChange={(e) => setEditItemUnitCost(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                                  </div>
                                  <div>
                                    <label className="mb-1 block text-xs text-neutral-500">Preço unit.</label>
                                    <input type="number" step="0.01" value={editItemUnitPrice} onChange={(e) => setEditItemUnitPrice(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                                  </div>
                                  <div className="flex flex-wrap gap-2 sm:col-span-2">
                                    <button onClick={() => handleSaveItemEdit(order.id, item)} disabled={isSavingItemEdit || isPricingItemEdit} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium disabled:opacity-50">
                                      {isPricingItemEdit ? "Calculando…" : isSavingItemEdit ? "Salvando…" : "Salvar"}
                                    </button>
                                    <button onClick={cancelEditItem} className="rounded border border-neutral-700 px-4 py-2 text-sm text-neutral-400 hover:border-neutral-500">
                                      Cancelar
                                    </button>
                                  </div>
                                </div>
                              )}
                            </li>
                          ))}
                        </ul>
                      )}

                      {products.length === 0 ? (
                        <p className="text-xs text-yellow-300">
                          Cadastre um produto na aba Produtos para poder adicioná-lo aqui.
                        </p>
                      ) : (
                        <form
                          onSubmit={(e) => handleAddItem(order.id, e)}
                          className="grid grid-cols-1 gap-2 border-t border-neutral-800 pt-3 sm:grid-cols-2"
                        >
                          <select
                            required
                            value={itemProductId}
                            onChange={(e) => handlePickProduct(e.target.value)}
                            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm sm:col-span-2"
                          >
                            <option value="">Selecione o produto…</option>
                            {products.map((p) => (
                              <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                          </select>
                          <input
                            type="number"
                            min={1}
                            placeholder="Qtd."
                            value={itemQuantity}
                            onChange={(e) => setItemQuantity(e.target.value)}
                            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
                          />
                          <input
                            type="number"
                            step="0.01"
                            placeholder="Custo unit."
                            value={itemUnitCost}
                            onChange={(e) => setItemUnitCost(e.target.value)}
                            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
                          />
                          <input
                            type="number"
                            step="0.01"
                            placeholder="Preço unit."
                            value={itemUnitPrice}
                            onChange={(e) => setItemUnitPrice(e.target.value)}
                            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
                          />
                          <button
                            type="submit"
                            disabled={isAddingItem || isPricingItem || !itemProductId}
                            className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
                          >
                            {isPricingItem ? "Calculando…" : isAddingItem ? "Adicionando…" : "Adicionar item"}
                          </button>
                          {!defaultCostProfile && (
                            <p className="text-xs text-yellow-300 sm:col-span-2">
                              Sem perfil de custo cadastrado — preencha custo/preço manualmente.
                            </p>
                          )}
                        </form>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </AppShell>
  );
}
