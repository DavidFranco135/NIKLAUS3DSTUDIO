"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError, uploadImage } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { CostProfile, Product, ProductCostItem } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

export default function CatalogoPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [costs, setCosts] = useState<Record<string, ProductCostItem>>({});
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");

  const [viewingId, setViewingId] = useState<string | null>(null);
  const [photoIndex, setPhotoIndex] = useState(0);
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const touchStartX = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const [productsData, profilesData] = await Promise.all([
        apiFetch<Product[]>(`${orgPath}/products`, { accessToken }),
        apiFetch<CostProfile[]>(`${orgPath}/cost-profiles`, { accessToken }),
      ]);
      setProducts(productsData);

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
      setError(err instanceof ApiError ? err.message : "Falha ao carregar catálogo.");
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

  const filtered = products.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  const viewingProduct = products.find((p) => p.id === viewingId) ?? null;

  function openViewer(product: Product) {
    setViewingId(product.id);
    setPhotoIndex(0);
    setModalError(null);
  }

  function closeViewer() {
    setViewingId(null);
    setModalError(null);
  }

  function showPrevPhoto() {
    if (!viewingProduct) return;
    setPhotoIndex((i) => (i - 1 + viewingProduct.photo_urls.length) % viewingProduct.photo_urls.length);
  }

  function showNextPhoto() {
    if (!viewingProduct) return;
    setPhotoIndex((i) => (i + 1) % viewingProduct.photo_urls.length);
  }

  function handleTouchStart(event: React.TouchEvent) {
    touchStartX.current = event.touches[0].clientX;
  }

  function handleTouchEnd(event: React.TouchEvent) {
    if (touchStartX.current == null) return;
    const delta = event.changedTouches[0].clientX - touchStartX.current;
    touchStartX.current = null;
    if (Math.abs(delta) < 40) return;
    if (delta > 0) showPrevPhoto();
    else showNextPhoto();
  }

  async function patchPhotoUrls(product: Product, photoUrls: string[]) {
    if (!accessToken) return;
    const updated = await apiFetch<Product>(`${orgPath}/products/${product.id}`, {
      method: "PATCH",
      accessToken,
      body: JSON.stringify({ photo_urls: photoUrls }),
    });
    setProducts((items) => items.map((p) => (p.id === updated.id ? updated : p)));
  }

  async function handleAddPhoto(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length === 0 || !accessToken || !viewingProduct) return;
    setIsUploadingPhoto(true);
    setModalError(null);
    try {
      let urls = viewingProduct.photo_urls;
      for (const file of files) {
        const { url } = await uploadImage(`${orgPath}/uploads/image`, accessToken, file);
        urls = [...urls, url];
      }
      await patchPhotoUrls(viewingProduct, urls);
      setPhotoIndex(urls.length - 1);
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Falha ao enviar foto.");
    } finally {
      setIsUploadingPhoto(false);
    }
  }

  async function handleDeletePhoto() {
    if (!viewingProduct) return;
    const current = viewingProduct.photo_urls[photoIndex];
    if (!current) return;
    if (!window.confirm("Apagar esta foto?")) return;
    setModalError(null);
    try {
      const urls = viewingProduct.photo_urls.filter((_, i) => i !== photoIndex);
      await patchPhotoUrls(viewingProduct, urls);
      setPhotoIndex((i) => Math.max(0, Math.min(i, urls.length - 1)));
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Falha ao apagar foto.");
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
    <AppShell title="Catálogo">
      <div className="mx-auto max-w-6xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        <input
          placeholder="Buscar produto…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 sm:max-w-xs"
        />

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {isLoading ? (
            <p className="col-span-full text-neutral-500">Carregando…</p>
          ) : filtered.length === 0 ? (
            <p className="col-span-full text-neutral-500">Nenhum produto encontrado.</p>
          ) : (
            filtered.map((product) => {
              const price = product.manual_price ?? costs[product.id]?.suggested_price;
              return (
                <button
                  key={product.id}
                  onClick={() => openViewer(product)}
                  className="space-y-2 rounded-xl border border-neutral-800 bg-neutral-950/50 p-3 text-left hover:border-neutral-600"
                >
                  <div className="relative flex aspect-square items-center justify-center overflow-hidden rounded-lg bg-neutral-900">
                    {product.photo_urls.length > 0 ? (
                      <img
                        src={product.photo_urls[0]}
                        alt={product.name}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <span className="text-xs text-neutral-600">Sem foto</span>
                    )}
                    {product.photo_urls.length > 1 && (
                      <span className="absolute right-1 top-1 rounded-full bg-black/70 px-1.5 py-0.5 text-[10px] text-neutral-200">
                        +{product.photo_urls.length - 1}
                      </span>
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{product.name}</p>
                    {product.size && (
                      <p className="truncate text-xs text-neutral-500">{product.size}</p>
                    )}
                    <p className="text-sm font-medium text-green-400">
                      {price != null ? formatCurrency(price) : "—"}
                    </p>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {viewingProduct && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
          onClick={closeViewer}
        >
          <div
            className="relative flex w-full max-w-3xl flex-col gap-4 sm:flex-row"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={closeViewer}
              className="absolute -top-10 right-0 text-sm text-neutral-300 hover:text-white sm:-top-8"
              aria-label="Fechar"
            >
              Fechar ✕
            </button>

            <div
              className="relative flex aspect-square w-full items-center justify-center overflow-hidden rounded-lg bg-neutral-900 sm:w-2/3"
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
            >
              {viewingProduct.photo_urls.length > 0 ? (
                <img
                  src={viewingProduct.photo_urls[photoIndex]}
                  alt={viewingProduct.name}
                  className="h-full w-full object-contain"
                />
              ) : (
                <span className="text-sm text-neutral-600">Sem foto</span>
              )}

              {viewingProduct.photo_urls.length > 1 && (
                <>
                  <button
                    onClick={showPrevPhoto}
                    className="absolute left-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-black/60 text-lg text-white hover:bg-black/80"
                    aria-label="Foto anterior"
                  >
                    ‹
                  </button>
                  <button
                    onClick={showNextPhoto}
                    className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-black/60 text-lg text-white hover:bg-black/80"
                    aria-label="Próxima foto"
                  >
                    ›
                  </button>
                  <span className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-black/60 px-2 py-0.5 text-xs text-neutral-200">
                    {photoIndex + 1} / {viewingProduct.photo_urls.length}
                  </span>
                </>
              )}
            </div>

            <div className="flex w-full flex-col gap-3 rounded-lg bg-neutral-950 p-4 sm:w-1/3">
              <div>
                <h2 className="text-lg font-medium">{viewingProduct.name}</h2>
                {viewingProduct.description && (
                  <p className="mt-1 text-sm text-neutral-400">{viewingProduct.description}</p>
                )}
              </div>

              <div className="space-y-1 text-sm text-neutral-400">
                {viewingProduct.size && <p>Tamanho: {viewingProduct.size}</p>}
                {viewingProduct.print_time_hours != null && (
                  <p>Tempo de impressão: {viewingProduct.print_time_hours}h</p>
                )}
                {(() => {
                  const price = viewingProduct.manual_price ?? costs[viewingProduct.id]?.suggested_price;
                  return price != null ? (
                    <p className="text-base font-medium text-green-400">{formatCurrency(price)}</p>
                  ) : null;
                })()}
              </div>

              {modalError && <p className="rounded bg-red-950 p-2 text-xs text-red-300">{modalError}</p>}

              <div className="mt-auto flex flex-wrap gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  className="hidden"
                  onChange={handleAddPhoto}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploadingPhoto}
                  className="rounded bg-blue-600 px-3 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
                >
                  {isUploadingPhoto ? "Enviando…" : "Editar (adicionar foto)"}
                </button>
                <button
                  onClick={handleDeletePhoto}
                  disabled={viewingProduct.photo_urls.length === 0}
                  className="rounded border border-red-800 px-3 py-2 text-sm text-red-400 hover:bg-red-950 disabled:opacity-30"
                >
                  Apagar foto
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
