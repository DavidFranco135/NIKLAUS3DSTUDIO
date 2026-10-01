"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
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
                <div
                  key={product.id}
                  className="space-y-2 rounded-xl border border-neutral-800 bg-neutral-950/50 p-3"
                >
                  <div className="flex aspect-square items-center justify-center overflow-hidden rounded-lg bg-neutral-900">
                    {product.photo_url ? (

                      <img
                        src={product.photo_url}
                        alt={product.name}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <span className="text-xs text-neutral-600">Sem foto</span>
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
                </div>
              );
            })
          )}
        </div>
      </div>
    </AppShell>
  );
}
