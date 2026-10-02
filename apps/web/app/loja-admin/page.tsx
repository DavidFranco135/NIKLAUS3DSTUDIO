"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError, uploadImage } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { Product } from "@/lib/types";
import type { StoreAdminResponse, StoreSettings } from "@/lib/store";
import { ACCENTS, DEFAULT_WHATSAPP, formatWhatsappDisplay, normalizeWhatsapp } from "@/lib/store";
import { AppShell } from "@/components/AppShell";

const EMPTY: StoreSettings = {
  display_name: "",
  tagline: "",
  about: "",
  whatsapp: DEFAULT_WHATSAPP,
  instagram: "",
  hours: "",
  address: "",
  accent: "indigo",
  theme: "light",
  slides: [],
  highlights: [],
  hidden_product_ids: [],
  featured_product_ids: [],
};

const input =
  "w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm placeholder:text-neutral-600";

function Card({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:p-5">
      <div>
        <h2 className="font-medium">{title}</h2>
        {hint && <p className="text-xs text-neutral-500">{hint}</p>}
      </div>
      {children}
    </section>
  );
}

export default function LojaAdminPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [slug, setSlug] = useState("");
  const [settings, setSettings] = useState<StoreSettings>(EMPTY);
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const [store, productsData] = await Promise.all([
        apiFetch<StoreAdminResponse>(`${orgPath}/store`, { accessToken }),
        apiFetch<Product[]>(`${orgPath}/products`, { accessToken }),
      ]);
      setSlug(store.slug);
      setSettings({ ...EMPTY, ...store.settings });
      setProducts(productsData);
      setDirty(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar a loja.");
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

  const publicUrl = useMemo(
    () => (slug && typeof window !== "undefined" ? `${window.location.origin}/loja?s=${slug}` : ""),
    [slug]
  );

  function update(patch: Partial<StoreSettings>) {
    setSettings((s) => ({ ...s, ...patch }));
    setDirty(true);
    setMessage(null);
  }

  async function handleSlideUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length === 0 || !accessToken) return;
    const room = 10 - settings.slides.length;
    setIsUploading(true);
    setError(null);
    try {
      const added: StoreSettings["slides"] = [];
      for (const file of files.slice(0, room)) {
        const { url } = await uploadImage(`${orgPath}/uploads/image`, accessToken, file);
        added.push({ url, title: "", subtitle: "" });
      }
      update({ slides: [...settings.slides, ...added] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao enviar imagem.");
    } finally {
      setIsUploading(false);
    }
  }

  function moveSlide(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= settings.slides.length) return;
    const next = [...settings.slides];
    [next[index], next[target]] = [next[target], next[index]];
    update({ slides: next });
  }

  function toggleId(list: "hidden_product_ids" | "featured_product_ids", id: string) {
    const current = settings[list];
    update({ [list]: current.includes(id) ? current.filter((x) => x !== id) : [...current, id] });
  }

  async function handleSave() {
    if (!accessToken) return;
    setIsSaving(true);
    setError(null);
    try {
      const body = {
        ...settings,
        whatsapp: normalizeWhatsapp(settings.whatsapp) || DEFAULT_WHATSAPP,
        highlights: settings.highlights.filter((h) => h.title.trim() || h.text.trim()),
      };
      const saved = await apiFetch<StoreAdminResponse>(`${orgPath}/store`, {
        method: "PUT",
        accessToken,
        body: JSON.stringify(body),
      });
      setSettings({ ...EMPTY, ...saved.settings });
      setDirty(false);
      setMessage("Alterações salvas. A loja pública atualiza em até 30 segundos.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar.");
    } finally {
      setIsSaving(false);
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(publicUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      window.prompt("Copie o link:", publicUrl);
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
    <AppShell title="Minha Loja">
      <div className="mx-auto max-w-4xl space-y-5 pb-28">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}
        {message && <p className="rounded bg-green-950 p-2 text-sm text-green-300">{message}</p>}

        {isLoading ? (
          <p className="text-neutral-500">Carregando…</p>
        ) : (
          <>
            <Card title="Link da loja pública" hint="Compartilhe com seus clientes. Não precisa de login.">
              <div className="flex flex-col gap-2 sm:flex-row">
                <input readOnly value={publicUrl} className={`${input} sm:flex-1`} />
                <div className="flex gap-2">
                  <button
                    onClick={copyLink}
                    className="rounded bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
                  >
                    {copied ? "Copiado!" : "Copiar link"}
                  </button>
                  <a
                    href={publicUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded border border-neutral-700 px-4 py-2 text-sm hover:border-neutral-500"
                  >
                    Abrir loja
                  </a>
                </div>
              </div>
              {dirty && (
                <p className="text-xs text-yellow-400">Você tem alterações não salvas — salve para publicá-las.</p>
              )}
            </Card>

            <Card title="Capa com slides" hint="Fotos que passam automaticamente no topo da loja (até 10). Sem slides, usamos as fotos dos seus produtos.">
              <label className="inline-block cursor-pointer rounded border border-dashed border-neutral-600 px-4 py-3 text-sm text-neutral-300 hover:border-blue-500">
                {isUploading ? "Enviando…" : "+ Adicionar fotos da capa"}
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  disabled={isUploading || settings.slides.length >= 10}
                  onChange={handleSlideUpload}
                  className="hidden"
                />
              </label>
              {settings.slides.length === 0 ? (
                <p className="text-sm text-neutral-500">Nenhum slide ainda.</p>
              ) : (
                <ul className="space-y-3">
                  {settings.slides.map((slide, i) => (
                    <li key={`${slide.url}-${i}`} className="flex flex-col gap-3 rounded-lg border border-neutral-800 p-3 sm:flex-row">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={slide.url} alt="" className="h-24 w-full rounded object-cover sm:w-40" />
                      <div className="flex-1 space-y-2">
                        <input
                          className={input}
                          placeholder="Título (opcional)"
                          value={slide.title}
                          maxLength={120}
                          onChange={(e) =>
                            update({
                              slides: settings.slides.map((s, j) => (j === i ? { ...s, title: e.target.value } : s)),
                            })
                          }
                        />
                        <input
                          className={input}
                          placeholder="Subtítulo (opcional)"
                          value={slide.subtitle}
                          maxLength={240}
                          onChange={(e) =>
                            update({
                              slides: settings.slides.map((s, j) =>
                                j === i ? { ...s, subtitle: e.target.value } : s
                              ),
                            })
                          }
                        />
                      </div>
                      <div className="flex gap-2 sm:flex-col">
                        <button onClick={() => moveSlide(i, -1)} disabled={i === 0} className="rounded border border-neutral-700 px-3 py-1 text-xs disabled:opacity-30">
                          ↑
                        </button>
                        <button onClick={() => moveSlide(i, 1)} disabled={i === settings.slides.length - 1} className="rounded border border-neutral-700 px-3 py-1 text-xs disabled:opacity-30">
                          ↓
                        </button>
                        <button
                          onClick={() => update({ slides: settings.slides.filter((_, j) => j !== i) })}
                          className="rounded border border-red-900 px-3 py-1 text-xs text-red-400 hover:bg-red-950"
                        >
                          Apagar
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card title="Informações da loja">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-xs text-neutral-500">Nome da loja</label>
                  <input className={input} value={settings.display_name} placeholder="Ex.: Ateliê 3D" maxLength={120} onChange={(e) => update({ display_name: e.target.value })} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-neutral-500">Frase de efeito</label>
                  <input className={input} value={settings.tagline} placeholder="Ex.: Peças únicas impressas em 3D" maxLength={200} onChange={(e) => update({ tagline: e.target.value })} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-neutral-500">WhatsApp (com DDD)</label>
                  <input className={input} value={settings.whatsapp} placeholder="21 97038-6065" onChange={(e) => update({ whatsapp: e.target.value })} />
                  <p className="text-[11px] text-neutral-600">Será exibido como {formatWhatsappDisplay(settings.whatsapp)}</p>
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-neutral-500">Instagram (opcional)</label>
                  <input className={input} value={settings.instagram} placeholder="@sualoja" maxLength={120} onChange={(e) => update({ instagram: e.target.value })} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-neutral-500">Horário de atendimento</label>
                  <textarea className={input} rows={2} value={settings.hours} placeholder="Seg a Sex, 9h às 18h" maxLength={300} onChange={(e) => update({ hours: e.target.value })} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-neutral-500">Endereço / região de entrega</label>
                  <textarea className={input} rows={2} value={settings.address} placeholder="Rio de Janeiro - RJ" maxLength={300} onChange={(e) => update({ address: e.target.value })} />
                </div>
                <div className="space-y-1 sm:col-span-2">
                  <label className="text-xs text-neutral-500">Sobre a loja</label>
                  <textarea className={input} rows={4} value={settings.about} placeholder="Conte sua história, seus diferenciais…" maxLength={2000} onChange={(e) => update({ about: e.target.value })} />
                </div>
              </div>
            </Card>

            <Card title="Diferenciais" hint="Até 3 cards logo abaixo da capa (ex.: Entrega rápida, Personalizado).">
              <div className="space-y-2">
                {settings.highlights.map((h, i) => (
                  <div key={i} className="flex flex-col gap-2 sm:flex-row">
                    <input className={`${input} sm:w-56`} placeholder="Título" value={h.title} maxLength={80}
                      onChange={(e) => update({ highlights: settings.highlights.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)) })} />
                    <input className={`${input} sm:flex-1`} placeholder="Descrição" value={h.text} maxLength={240}
                      onChange={(e) => update({ highlights: settings.highlights.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)) })} />
                    <button onClick={() => update({ highlights: settings.highlights.filter((_, j) => j !== i) })} className="rounded border border-red-900 px-3 py-2 text-xs text-red-400 hover:bg-red-950">
                      Remover
                    </button>
                  </div>
                ))}
                {settings.highlights.length < 3 && (
                  <button onClick={() => update({ highlights: [...settings.highlights, { title: "", text: "" }] })} className="text-sm text-blue-400 hover:underline">
                    + Adicionar diferencial
                  </button>
                )}
              </div>
            </Card>

            <Card title="Aparência">
              <div className="space-y-2">
                <p className="text-xs text-neutral-500">Cor de destaque</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(ACCENTS).map(([key, a]) => (
                    <button
                      key={key}
                      onClick={() => update({ accent: key })}
                      className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${
                        settings.accent === key ? "border-blue-500 bg-blue-950" : "border-neutral-700 hover:border-neutral-500"
                      }`}
                    >
                      <span className="h-4 w-4 rounded-full" style={{ background: a.color }} />
                      {a.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-xs text-neutral-500">Tema</p>
                <div className="flex gap-2">
                  {(["light", "dark"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => update({ theme: t })}
                      className={`rounded-lg border px-4 py-2 text-sm ${
                        settings.theme === t ? "border-blue-500 bg-blue-950 text-blue-200" : "border-neutral-700 text-neutral-400 hover:border-neutral-500"
                      }`}
                    >
                      {t === "light" ? "Claro" : "Escuro"}
                    </button>
                  ))}
                </div>
              </div>
            </Card>

            <Card title="Produtos na loja" hint="Escolha o que aparece e o que fica em destaque. O preço mostrado ao cliente é o preço de venda; custos nunca são exibidos.">
              {products.length === 0 ? (
                <p className="text-sm text-neutral-500">Nenhum produto cadastrado.</p>
              ) : (
                <ul className="divide-y divide-neutral-800">
                  {products.map((p) => {
                    const hidden = settings.hidden_product_ids.includes(p.id);
                    const featured = settings.featured_product_ids.includes(p.id);
                    return (
                      <li key={p.id} className="flex flex-wrap items-center gap-x-3 gap-y-2 py-3">
                        <div className="h-12 w-12 shrink-0 overflow-hidden rounded bg-neutral-900">
                          {p.photo_urls[0] && (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={p.photo_urls[0]} alt="" className="h-full w-full object-cover" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1 basis-40">
                          <p className={`truncate text-sm font-medium ${hidden ? "text-neutral-500 line-through" : ""}`}>{p.name}</p>
                          <p className="text-xs text-neutral-500">
                            {p.manual_price != null ? formatCurrency(p.manual_price) : "Preço calculado pela receita"}
                            {p.stock_quantity === 0 ? " · Esgotado" : ""}
                          </p>
                        </div>
                        <div className="flex w-full gap-2 sm:w-auto">
                        <button
                          onClick={() => toggleId("featured_product_ids", p.id)}
                          disabled={hidden}
                          title="Destaque"
                          className={`rounded-full border px-3 py-1 text-xs disabled:opacity-30 ${
                            featured ? "border-yellow-600 bg-yellow-950 text-yellow-300" : "border-neutral-700 text-neutral-400"
                          }`}
                        >
                          ★ Destaque
                        </button>
                        <button
                          onClick={() => toggleId("hidden_product_ids", p.id)}
                          className={`rounded-full border px-3 py-1 text-xs ${
                            hidden ? "border-neutral-700 text-neutral-400" : "border-green-800 bg-green-950 text-green-300"
                          }`}
                        >
                          {hidden ? "Oculto" : "Visível"}
                        </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>
          </>
        )}
      </div>

      {!isLoading && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-neutral-800 bg-neutral-950/95 px-4 py-3 backdrop-blur lg:left-60">
          <div className="mx-auto flex max-w-4xl items-center justify-between gap-3">
            <p className="text-xs text-neutral-500">{dirty ? "Alterações não salvas" : "Tudo salvo"}</p>
            <button
              onClick={handleSave}
              disabled={isSaving || !dirty}
              className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-40"
            >
              {isSaving ? "Salvando…" : "Salvar alterações"}
            </button>
          </div>
        </div>
      )}
    </AppShell>
  );
}
