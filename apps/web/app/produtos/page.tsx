"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError, uploadImage } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { CostProfile, Machine, Material, Product, ProductCost, ProductCostItem } from "@/lib/types";
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
  const [mode, setMode] = useState<"simples" | "completo">("completo");

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [printTimeHours, setPrintTimeHours] = useState("");
  const [machineId, setMachineId] = useState("");
  const [bomLines, setBomLines] = useState<BomLine[]>([{ material_id: "", quantity_g: "" }]);
  const [manualPrice, setManualPrice] = useState("");
  const [size, setSize] = useState("");
  const [photoUrls, setPhotoUrls] = useState<string[]>([]);
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);

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
        try {
          const items = await apiFetch<ProductCostItem[]>(
            `${orgPath}/products/costs?cost_profile_id=${defaultProfile.id}`,
            { accessToken }
          );
          setCosts(Object.fromEntries(items.map((item) => [item.product_id, item])));
        } catch {
          setCosts({});
        }
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
    setManualPrice("");
    setSize("");
    setPhotoUrls([]);
    setMode("completo");
    setEditingId(null);
    setShowForm(false);
  }

  async function handlePhotoChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0 || !accessToken) return;
    event.target.value = "";
    setIsUploadingPhoto(true);
    setError(null);
    try {
      for (const file of files) {
        const { url } = await uploadImage(`${orgPath}/uploads/image`, accessToken, file);
        setPhotoUrls((urls) => [...urls, url]);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao enviar foto.");
    } finally {
      setIsUploadingPhoto(false);
    }
  }

  function removePhoto(url: string) {
    setPhotoUrls((urls) => urls.filter((u) => u !== url));
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
    setManualPrice(product.manual_price != null ? String(product.manual_price) : "");
    setSize(product.size ?? "");
    setPhotoUrls(product.photo_urls ?? []);
    setMode(product.manual_price != null ? "simples" : "completo");
    setShowForm(true);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    const validLines = mode === "simples" ? [] : bomLines.filter((l) => l.material_id && l.quantity_g);
    setIsSaving(true);
    setError(null);
    try {
      const body = JSON.stringify({
        name,
        description: description || null,
        print_time_hours: mode === "simples" ? null : printTimeHours ? Number(printTimeHours) : null,
        machine_id: mode === "simples" ? null : machineId || null,
        manual_price: mode === "simples" ? Number(manualPrice) : null,
        size: size || null,
        photo_urls: photoUrls,
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
            Sem materiais cadastrados ainda — isso só afeta o modo &ldquo;Completo&rdquo;; o modo
            &ldquo;Simples&rdquo; não precisa de materiais.
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
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
          >
            {showForm ? "Cancelar" : "+ Novo produto"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4"
          >
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMode("completo")}
                className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium ${
                  mode === "completo"
                    ? "border-blue-500 bg-blue-950 text-blue-200"
                    : "border-neutral-700 text-neutral-400 hover:border-neutral-600"
                }`}
              >
                Completo (produção)
              </button>
              <button
                type="button"
                onClick={() => setMode("simples")}
                className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium ${
                  mode === "simples"
                    ? "border-blue-500 bg-blue-950 text-blue-200"
                    : "border-neutral-700 text-neutral-400 hover:border-neutral-600"
                }`}
              >
                Simples (manual)
              </button>
            </div>
            {mode === "simples" && (
              <p className="text-xs text-neutral-500">
                Só nome e preço — sem máquina, material ou perfil de custo.
              </p>
            )}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <input required placeholder="Nome do produto" value={name} onChange={(e) => setName(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 sm:col-span-2" />
              <input placeholder="Descrição (opcional)" value={description} onChange={(e) => setDescription(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 sm:col-span-2" />
              {mode === "simples" ? (
                <>
                  <input required type="number" step="0.01" min="0" placeholder="Preço de venda (R$)" value={manualPrice} onChange={(e) => setManualPrice(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
                  <input placeholder="Tamanho (opcional, ex: 10x5x3cm)" value={size} onChange={(e) => setSize(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
                </>
              ) : (
                <>
                  <input type="number" step="0.01" placeholder="Tempo de impressão (h)" value={printTimeHours} onChange={(e) => setPrintTimeHours(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
                  <select value={machineId} onChange={(e) => setMachineId(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2">
                    <option value="">Máquina (opcional)</option>
                    {machines.map((m) => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                  <input placeholder="Tamanho (opcional, ex: 10x5x3cm)" value={size} onChange={(e) => setSize(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 sm:col-span-2" />
                </>
              )}
            </div>

            <div className="space-y-1">
              <label className="block text-xs text-neutral-500">Fotos do produto (opcional, pode selecionar várias)</label>
              <input type="file" accept="image/*" multiple onChange={handlePhotoChange} className="block w-full text-sm" />
              {isUploadingPhoto && <p className="text-xs text-neutral-500">Enviando foto…</p>}
              {photoUrls.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {photoUrls.map((url) => (
                    <div key={url} className="relative">
                      <img src={url} alt="" className="h-20 w-20 rounded object-cover" />
                      <button
                        type="button"
                        onClick={() => removePhoto(url)}
                        className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-xs leading-none text-white hover:bg-red-500"
                        aria-label="Remover foto"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {mode === "completo" && (
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
            )}

            <button type="submit" disabled={isSaving || isUploadingPhoto} className="w-full rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50">
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
              const isManual = product.manual_price != null;
              return (
                <div key={product.id} className="space-y-2 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 gap-3">
                      {product.photo_urls.length > 0 && (
                        <div className="relative shrink-0">
                          <img src={product.photo_urls[0]} alt="" className="h-14 w-14 rounded object-cover" />
                          {product.photo_urls.length > 1 && (
                            <span className="absolute -right-1 -top-1 rounded-full bg-neutral-800 px-1.5 py-0.5 text-[10px] text-neutral-300">
                              +{product.photo_urls.length - 1}
                            </span>
                          )}
                        </div>
                      )}
                      <div className="min-w-0">
                        <h3 className="truncate font-medium">{product.name}</h3>
                        {product.description && (
                          <p className="truncate text-xs text-neutral-500">{product.description}</p>
                        )}
                        {product.size && (
                          <p className="text-xs text-neutral-500">{product.size}</p>
                        )}
                      </div>
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

                  {isManual ? (
                    <div className="flex items-center justify-between border-t border-neutral-800 pt-2 text-sm">
                      <span className="text-neutral-500">Preço manual</span>
                      <span className="font-medium text-green-400">{formatCurrency(product.manual_price)}</span>
                    </div>
                  ) : cost ? (
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
