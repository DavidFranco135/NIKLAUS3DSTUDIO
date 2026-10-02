"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { CartLine, OrderLine, PublicProduct, PublicStore, StoreSlide } from "@/lib/store";
import { formatWhatsappDisplay, themeVars, whatsappLink } from "@/lib/store";
import { CartDrawer, type CustomerInfo } from "./CartDrawer";
import { HeroSlider } from "./HeroSlider";
import { ProductCard } from "./ProductCard";
import { ProductModal } from "./ProductModal";
import {
  IconArrowRight,
  IconCart,
  IconCheck,
  IconClock,
  IconInstagram,
  IconPin,
  IconSearch,
  IconSparkle,
  IconWhatsapp,
  Reveal,
  useSwipe,
} from "./ui";

const TABS = ["Início", "Catálogo", "Como pedir", "Contato"] as const;

function useStoredState<T>(key: string, initial: T): [T, (next: T | ((prev: T) => T)) => void] {
  const [value, setValue] = useState<T>(initial);
  const loaded = useRef(false);

  useEffect(() => {
    const id = setTimeout(() => {
      try {
        const raw = window.localStorage.getItem(key);
        if (raw) setValue(JSON.parse(raw) as T);
      } catch {
        // ignore corrupt/blocked storage
      }
      loaded.current = true;
    }, 0);
    return () => clearTimeout(id);
  }, [key]);

  useEffect(() => {
    if (!loaded.current) return;
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // storage unavailable
    }
  }, [key, value]);

  return [value, setValue];
}

function TabBar({
  tab,
  onChange,
  catalogCount,
  className = "",
}: {
  tab: number;
  onChange: (index: number) => void;
  catalogCount: number;
  className?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const [pill, setPill] = useState({ left: 0, width: 0 });

  useLayoutEffect(() => {
    const measure = () => {
      const el = refs.current[tab];
      if (el) setPill({ left: el.offsetLeft, width: el.offsetWidth });
    };
    measure();
    window.addEventListener("resize", measure);
    // Fonts load after first paint and change the tab widths.
    document.fonts?.ready.then(measure);
    return () => window.removeEventListener("resize", measure);
  }, [tab]);

  return (
    <div
      role="tablist"
      className={`relative inline-flex rounded-full border border-[var(--line)] bg-[var(--surface-glass)] p-1 shadow-sm backdrop-blur ${className}`}
    >
      <span
        aria-hidden
        className="absolute bottom-1 top-1 rounded-full bg-[var(--accent)] shadow-md transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]"
        style={{ left: pill.left, width: pill.width }}
      />
      {TABS.map((label, i) => (
        <button
          key={label}
          ref={(el) => {
            refs.current[i] = el;
          }}
          role="tab"
          aria-selected={tab === i}
          onClick={() => onChange(i)}
          className={`relative z-10 flex-1 whitespace-nowrap rounded-full px-2 py-2 text-[12.5px] font-semibold transition-colors duration-300 min-[400px]:px-3.5 min-[400px]:text-[13px] sm:px-5 sm:text-sm ${
            tab === i ? "text-[var(--accent-ink)]" : "text-[var(--muted)] hover:text-[var(--ink)]"
          }`}
        >
          {label}
          {i === 1 && catalogCount > 0 && (
            <span
              className={`ml-1.5 rounded-full px-1.5 py-0.5 text-[10px] ${
                tab === i ? "bg-white/25" : "bg-[var(--accent-soft)] text-[var(--accent)]"
              }`}
            >
              {catalogCount}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

function SectionTitle({
  eyebrow,
  title,
  action,
}: {
  eyebrow?: string;
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div className="space-y-2">
        {eyebrow && (
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">
            {eyebrow}
          </p>
        )}
        <h2 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">
          {title}
        </h2>
      </div>
      {action}
    </div>
  );
}

function SkeletonStore() {
  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6">
      <div className="relative h-[52vh] overflow-hidden rounded-[28px] bg-[var(--line)]">
        <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/30 to-transparent" />
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="relative aspect-[4/5] overflow-hidden rounded-3xl bg-[var(--line)]">
            <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/30 to-transparent" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function Storefront({ slug }: { slug: string }) {
  const [store, setStore] = useState<PublicStore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState(0);
  const [dir, setDir] = useState(1);
  const [lines, setLines] = useStoredState<CartLine[]>(`loja-cart-${slug}`, []);
  const [customer, setCustomer] = useStoredState<CustomerInfo>(`loja-customer-${slug}`, {
    name: "",
    extra: "",
  });
  const [cartOpen, setCartOpen] = useState(false);
  const [openProductId, setOpenProductId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"relevance" | "price-asc" | "price-desc" | "name">("relevance");
  const [onlyAvailable, setOnlyAvailable] = useState(false);
  const [question, setQuestion] = useState({ name: "", text: "" });
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch<PublicStore>(`/api/v1/public/stores/${encodeURIComponent(slug)}`)
      .then((data) => {
        if (!cancelled) setStore(data);
      })
      .catch((err) => {
        if (!cancelled)
          setError(
            err instanceof ApiError && err.status === 404
              ? "Loja não encontrada."
              : "Não foi possível carregar a loja agora. Tente novamente em instantes."
          );
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    if (store) document.title = `${store.settings.display_name} · Catálogo`;
  }, [store]);

  const productsById = useMemo(() => {
    const map = new Map<string, PublicProduct>();
    store?.products.forEach((p) => map.set(p.id, p));
    return map;
  }, [store]);

  const orderLines: OrderLine[] = useMemo(
    () =>
      lines
        .map((l) => ({ product: productsById.get(l.id), qty: l.qty, note: l.note }))
        .filter((l): l is OrderLine => !!l.product && l.product.available),
    [lines, productsById]
  );
  const units = orderLines.reduce((sum, l) => sum + l.qty, 0);
  const total = orderLines.reduce((sum, l) => sum + l.product.price * l.qty, 0);

  const showToast = useCallback((message: string) => {
    setToast(message);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2400);
  }, []);

  const clampQty = (id: string, qty: number) => {
    const max = productsById.get(id)?.stock_quantity ?? 99;
    return Math.min(max, qty);
  };

  const setLine = useCallback(
    (id: string, qty: number, note?: string) => {
      setLines((prev) => {
        const existing = prev.find((l) => l.id === id);
        const nextQty = clampQty(id, qty);
        if (nextQty <= 0) return prev.filter((l) => l.id !== id);
        if (existing)
          return prev.map((l) =>
            l.id === id ? { ...l, qty: nextQty, note: note ?? l.note } : l
          );
        return [...prev, { id, qty: nextQty, note: note ?? "" }];
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setLines, productsById]
  );

  const goTab = useCallback(
    (next: number) => {
      const clamped = Math.max(0, Math.min(TABS.length - 1, next));
      if (clamped === tab) return;
      setDir(clamped > tab ? 1 : -1);
      setTab(clamped);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [tab]
  );

  const swipe = useSwipe(
    () => goTab(tab + 1),
    () => goTab(tab - 1)
  );

  const filtered = useMemo(() => {
    if (!store) return [];
    const term = search.trim().toLowerCase();
    let list = store.products.filter(
      (p) =>
        (!term || p.name.toLowerCase().includes(term) || (p.description ?? "").toLowerCase().includes(term)) &&
        (!onlyAvailable || p.available)
    );
    if (sort === "price-asc") list = [...list].sort((a, b) => a.price - b.price);
    else if (sort === "price-desc") list = [...list].sort((a, b) => b.price - a.price);
    else if (sort === "name") list = [...list].sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
    else list = [...list].sort((a, b) => Number(b.featured) - Number(a.featured));
    return list;
  }, [store, search, sort, onlyAvailable]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 p-6 text-center text-neutral-700">
        <div className="space-y-2">
          <p className="text-2xl font-semibold">{error}</p>
          <p className="text-sm text-neutral-500">Confira o endereço do link da loja.</p>
        </div>
      </div>
    );
  }

  const settings = store?.settings;
  const vars = themeVars(settings?.accent ?? "indigo", settings?.theme ?? "light");

  if (!store || !settings) {
    return (
      <div style={themeVars("indigo", "light")} className="min-h-screen bg-[var(--bg)]">
        <SkeletonStore />
      </div>
    );
  }

  const storeName = settings.display_name || store.name;
  const waGeneral = whatsappLink(
    settings.whatsapp,
    `Olá, ${storeName}! Gostaria de saber mais sobre os produtos.`
  );
  const openProduct = openProductId ? productsById.get(openProductId) ?? null : null;
  const featuredProducts = (() => {
    const featured = store.products.filter((p) => p.featured);
    return (featured.length > 0 ? featured : store.products).slice(0, 8);
  })();
  const slides: StoreSlide[] =
    settings.slides.length > 0
      ? settings.slides
      : store.products
          .filter((p) => p.photo_urls.length > 0)
          .slice(0, 5)
          .map((p) => ({ url: p.photo_urls[0], title: p.name, subtitle: formatCurrency(p.price) }));

  const qtyOf = (id: string) => lines.find((l) => l.id === id)?.qty ?? 0;

  const cardFor = (product: PublicProduct) => (
    <ProductCard
      key={product.id}
      product={product}
      qty={qtyOf(product.id)}
      onOpen={() => setOpenProductId(product.id)}
      onAdd={() => {
        setLine(product.id, 1);
        showToast(`${product.name} adicionado ao pedido`);
      }}
      onChangeQty={(q) => setLine(product.id, q)}
    />
  );

  const steps = [
    { title: "Escolha seus produtos", text: "Navegue pelo catálogo e toque no produto para ver fotos, tamanho e detalhes." },
    { title: "Monte seu pedido", text: "Adicione ao pedido, ajuste a quantidade e escreva informações como cor ou personalização." },
    { title: "Envie pelo WhatsApp", text: "Um toque e o pedido completo vai pronto para o nosso WhatsApp, sem cadastro." },
    { title: "Combine e receba", text: "Confirmamos valor final, prazo, pagamento e entrega com você." },
  ];

  return (
    <div
      style={vars}
      className="min-h-screen bg-[var(--bg)] font-[family-name:var(--font-sans)] text-[var(--ink)] antialiased selection:bg-[var(--accent)] selection:text-[var(--accent-ink)]"
    >
      <header className="sticky top-0 z-50 border-b border-[var(--line)] bg-[var(--bg-glass)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <button onClick={() => goTab(0)} className="flex min-w-0 items-center gap-3 text-left">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--accent)] font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--accent-ink)] shadow-md">
              {storeName.slice(0, 1).toUpperCase()}
            </span>
            <span className="min-w-0">
              <span className="block truncate font-[family-name:var(--font-display)] text-lg font-semibold leading-tight">
                {storeName}
              </span>
              {settings.tagline && (
                <span className="hidden truncate text-xs text-[var(--muted)] sm:block">{settings.tagline}</span>
              )}
            </span>
          </button>

          <TabBar tab={tab} onChange={goTab} catalogCount={store.products.length} className="hidden md:inline-flex" />

          <div className="flex items-center gap-2">
            <a
              href={waGeneral}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Falar no WhatsApp"
              className="hidden h-10 items-center gap-2 rounded-full border border-[var(--line)] bg-[var(--surface)] px-4 text-sm font-semibold transition hover:border-[#25d366] hover:text-[#25d366] sm:inline-flex"
            >
              <IconWhatsapp className="h-4 w-4 text-[#25d366]" />
              WhatsApp
            </a>
            <button
              onClick={() => setCartOpen(true)}
              aria-label="Abrir pedido"
              className="relative flex h-10 items-center gap-2 rounded-full bg-[var(--accent)] px-4 text-sm font-semibold text-[var(--accent-ink)] shadow-md transition hover:-translate-y-0.5 hover:shadow-lg"
            >
              <IconCart className="h-5 w-5" />
              <span className="hidden sm:inline">Pedido</span>
              {units > 0 && (
                <span
                  key={units}
                  className="ml-0.5 animate-pop rounded-full bg-white px-2 py-0.5 text-xs font-bold text-neutral-900"
                >
                  {units}
                </span>
              )}
            </button>
          </div>
        </div>
        <div className="px-4 pb-3 md:hidden">
          <TabBar tab={tab} onChange={goTab} catalogCount={store.products.length} className="flex w-full" />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-32 pt-6 sm:px-6 sm:pt-8" {...swipe}>
        <div key={tab} className={dir >= 0 ? "animate-slide-in-right" : "animate-slide-in-left"}>
          {tab === 0 && (
            <div className="space-y-20 sm:space-y-28">
              <HeroSlider
                slides={slides}
                storeName={storeName}
                tagline={settings.tagline}
                whatsappHref={waGeneral}
                onCatalog={() => goTab(1)}
              />

              {settings.highlights.some((h) => h.title) && (
                <div className="grid gap-4 sm:grid-cols-3">
                  {settings.highlights
                    .filter((h) => h.title)
                    .map((h, i) => (
                      <Reveal key={i} delay={i * 90}>
                        <div className="h-full rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6 transition duration-500 hover:-translate-y-1 hover:shadow-xl">
                          <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
                            <IconSparkle className="h-5 w-5" />
                          </div>
                          <h3 className="mb-1.5 font-semibold">{h.title}</h3>
                          <p className="text-sm leading-relaxed text-[var(--muted)]">{h.text}</p>
                        </div>
                      </Reveal>
                    ))}
                </div>
              )}

              {featuredProducts.length > 0 && (
                <section className="space-y-8">
                  <Reveal>
                    <SectionTitle
                      eyebrow="Seleção"
                      title="Destaques da loja"
                      action={
                        <button
                          onClick={() => goTab(1)}
                          className="group hidden items-center gap-2 text-sm font-semibold text-[var(--accent)] sm:inline-flex"
                        >
                          Ver catálogo completo
                          <IconArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                        </button>
                      }
                    />
                  </Reveal>
                  <div className="grid grid-cols-2 gap-3 sm:gap-5 lg:grid-cols-4">
                    {featuredProducts.map((p, i) => (
                      <Reveal key={p.id} delay={(i % 4) * 80}>
                        {cardFor(p)}
                      </Reveal>
                    ))}
                  </div>
                  <button
                    onClick={() => goTab(1)}
                    className="mx-auto flex items-center gap-2 text-sm font-semibold text-[var(--accent)] sm:hidden"
                  >
                    Ver catálogo completo <IconArrowRight className="h-4 w-4" />
                  </button>
                </section>
              )}

              {settings.about && (
                <Reveal>
                  <section className="grid gap-8 rounded-[32px] border border-[var(--line)] bg-[var(--surface)] p-8 sm:p-12 lg:grid-cols-[1fr_1.4fr]">
                    <div className="space-y-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">
                        Sobre nós
                      </p>
                      <h2 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">
                        Feito com cuidado, do projeto à entrega.
                      </h2>
                    </div>
                    <p className="whitespace-pre-line text-base leading-relaxed text-[var(--muted)]">
                      {settings.about}
                    </p>
                  </section>
                </Reveal>
              )}

              <Reveal>
                <section className="relative overflow-hidden rounded-[32px] bg-[var(--accent)] p-8 text-[var(--accent-ink)] sm:p-14">
                  <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-white/10 blur-2xl" />
                  <div className="relative flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
                    <div className="max-w-xl space-y-2">
                      <h2 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">
                        Não achou o que procurava?
                      </h2>
                      <p className="opacity-85">Fale com a gente: criamos peças sob medida e personalizadas.</p>
                    </div>
                    <a
                      href={waGeneral}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex shrink-0 items-center gap-2 rounded-full bg-white px-7 py-3.5 text-sm font-semibold text-neutral-900 shadow-xl transition hover:-translate-y-0.5"
                    >
                      <IconWhatsapp className="h-5 w-5 text-[#25d366]" />
                      Chamar no WhatsApp
                    </a>
                  </div>
                </section>
              </Reveal>
            </div>
          )}

          {tab === 1 && (
            <section className="space-y-8">
              <SectionTitle eyebrow="Catálogo" title="Todos os produtos" />
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="relative flex-1">
                  <IconSearch className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--muted)]" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Buscar produto…"
                    className="h-12 w-full rounded-full border border-[var(--line)] bg-[var(--surface)] pl-12 pr-4 text-sm outline-none transition placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-ring)]"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={sort}
                    onChange={(e) => setSort(e.target.value as typeof sort)}
                    className="h-12 rounded-full border border-[var(--line)] bg-[var(--surface)] px-4 text-sm outline-none focus:border-[var(--accent)]"
                  >
                    <option value="relevance">Relevância</option>
                    <option value="price-asc">Menor preço</option>
                    <option value="price-desc">Maior preço</option>
                    <option value="name">Nome (A–Z)</option>
                  </select>
                  <button
                    onClick={() => setOnlyAvailable((v) => !v)}
                    aria-pressed={onlyAvailable}
                    className={`inline-flex h-12 items-center gap-1.5 whitespace-nowrap rounded-full border px-4 text-sm font-medium transition ${
                      onlyAvailable
                        ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-ink)]"
                        : "border-[var(--line)] bg-[var(--surface)] text-[var(--muted)]"
                    }`}
                  >
                    {onlyAvailable && <IconCheck className="h-4 w-4" />}
                    Disponíveis
                  </button>
                </div>
              </div>

              {filtered.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-[var(--line)] p-12 text-center text-[var(--muted)]">
                  Nenhum produto encontrado.
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 sm:gap-5 md:grid-cols-3 lg:grid-cols-4">
                  {filtered.map((p, i) => (
                    <div
                      key={p.id}
                      className="animate-fade-up"
                      style={{ animationDelay: `${Math.min(i, 12) * 45}ms` }}
                    >
                      {cardFor(p)}
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {tab === 2 && (
            <section className="space-y-12">
              <SectionTitle eyebrow="Passo a passo" title="Como fazer seu pedido" />
              <div className="grid gap-5 sm:grid-cols-2">
                {steps.map((step, i) => (
                  <Reveal key={step.title} delay={i * 100}>
                    <div className="relative h-full overflow-hidden rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-7 transition duration-500 hover:-translate-y-1 hover:shadow-xl">
                      <span className="absolute -right-2 -top-4 font-[family-name:var(--font-display)] text-[110px] font-semibold leading-none text-[var(--accent)] opacity-[0.08]">
                        {i + 1}
                      </span>
                      <div className="relative space-y-2">
                        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--accent)] text-sm font-bold text-[var(--accent-ink)]">
                          {i + 1}
                        </span>
                        <h3 className="pt-2 text-lg font-semibold">{step.title}</h3>
                        <p className="text-sm leading-relaxed text-[var(--muted)]">{step.text}</p>
                      </div>
                    </div>
                  </Reveal>
                ))}
              </div>
              <div className="flex justify-center">
                <button
                  onClick={() => goTab(1)}
                  className="inline-flex items-center gap-2 rounded-full bg-[var(--accent)] px-8 py-4 text-sm font-semibold text-[var(--accent-ink)] shadow-lg transition hover:-translate-y-0.5"
                >
                  Começar meu pedido <IconArrowRight className="h-4 w-4" />
                </button>
              </div>
            </section>
          )}

          {tab === 3 && (
            <section className="space-y-10">
              <SectionTitle eyebrow="Contato" title="Fale com a gente" />
              <div className="grid gap-5 lg:grid-cols-2">
                <div className="grid gap-4">
                  <a
                    href={waGeneral}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex items-center gap-4 rounded-3xl bg-[#25d366] p-6 text-white shadow-lg shadow-[#25d366]/25 transition hover:-translate-y-1"
                  >
                    <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20">
                      <IconWhatsapp className="h-7 w-7" />
                    </span>
                    <span>
                      <span className="block text-xs uppercase tracking-wider opacity-80">WhatsApp</span>
                      <span className="block text-xl font-semibold">{formatWhatsappDisplay(settings.whatsapp)}</span>
                    </span>
                    <IconArrowRight className="ml-auto h-5 w-5 transition-transform group-hover:translate-x-1" />
                  </a>
                  {settings.instagram && (
                    <a
                      href={`https://instagram.com/${settings.instagram.replace(/^@/, "")}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-4 rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6 transition hover:-translate-y-1 hover:shadow-lg"
                    >
                      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
                        <IconInstagram className="h-6 w-6" />
                      </span>
                      <span>
                        <span className="block text-xs uppercase tracking-wider text-[var(--muted)]">Instagram</span>
                        <span className="block font-semibold">@{settings.instagram.replace(/^@/, "")}</span>
                      </span>
                    </a>
                  )}
                  {settings.hours && (
                    <div className="flex items-start gap-4 rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6">
                      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
                        <IconClock className="h-6 w-6" />
                      </span>
                      <span>
                        <span className="block text-xs uppercase tracking-wider text-[var(--muted)]">Atendimento</span>
                        <span className="block whitespace-pre-line font-medium">{settings.hours}</span>
                      </span>
                    </div>
                  )}
                  {settings.address && (
                    <div className="flex items-start gap-4 rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6">
                      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
                        <IconPin className="h-6 w-6" />
                      </span>
                      <span>
                        <span className="block text-xs uppercase tracking-wider text-[var(--muted)]">Endereço</span>
                        <span className="block whitespace-pre-line font-medium">{settings.address}</span>
                      </span>
                    </div>
                  )}
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const text = `Olá, ${storeName}! ${question.text.trim()}${
                      question.name.trim() ? `\n\n— ${question.name.trim()}` : ""
                    }`;
                    window.open(whatsappLink(settings.whatsapp, text), "_blank", "noopener,noreferrer");
                  }}
                  className="space-y-4 rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6 sm:p-8"
                >
                  <h3 className="font-[family-name:var(--font-display)] text-2xl font-semibold">Tire suas dúvidas</h3>
                  <p className="text-sm text-[var(--muted)]">Escreva sua pergunta e enviamos direto para o nosso WhatsApp.</p>
                  <input
                    value={question.name}
                    onChange={(e) => setQuestion((q) => ({ ...q, name: e.target.value }))}
                    placeholder="Seu nome"
                    className="h-12 w-full rounded-2xl border border-[var(--line)] bg-[var(--bg)] px-4 text-sm outline-none transition focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-ring)]"
                  />
                  <textarea
                    required
                    value={question.text}
                    onChange={(e) => setQuestion((q) => ({ ...q, text: e.target.value }))}
                    rows={5}
                    placeholder="Como podemos ajudar?"
                    className="w-full resize-none rounded-2xl border border-[var(--line)] bg-[var(--bg)] px-4 py-3 text-sm outline-none transition focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-ring)]"
                  />
                  <button
                    type="submit"
                    className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-[#25d366] text-sm font-semibold text-white shadow-lg shadow-[#25d366]/25 transition hover:-translate-y-0.5"
                  >
                    <IconWhatsapp className="h-5 w-5" />
                    Enviar no WhatsApp
                  </button>
                </form>
              </div>
            </section>
          )}
        </div>
      </main>

      <footer className="border-t border-[var(--line)] py-8 text-center text-xs text-[var(--muted)]">
        © {new Date().getFullYear()} {storeName}. Todos os direitos reservados.
      </footer>

      <div className="fixed bottom-5 right-5 z-40 flex flex-col items-end gap-3">
        {units > 0 && (
          <button
            onClick={() => setCartOpen(true)}
            className="flex animate-fade-up items-center gap-3 rounded-full bg-[var(--accent)] py-3 pl-5 pr-6 text-sm font-semibold text-[var(--accent-ink)] shadow-2xl transition hover:-translate-y-0.5"
          >
            <IconCart className="h-5 w-5" />
            {units} {units === 1 ? "item" : "itens"} · {formatCurrency(total)}
          </button>
        )}
        <a
          href={waGeneral}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Falar no WhatsApp"
          className="flex h-14 w-14 items-center justify-center rounded-full bg-[#25d366] text-white shadow-xl shadow-[#25d366]/40 transition hover:scale-110"
        >
          <IconWhatsapp className="h-7 w-7" />
        </a>
      </div>

      {toast && (
        <div className="fixed inset-x-0 bottom-24 z-[90] flex justify-center px-4">
          <div className="flex animate-toast-in items-center gap-2 rounded-full bg-neutral-900 px-5 py-3 text-sm font-medium text-white shadow-2xl">
            <IconCheck className="h-4 w-4 text-emerald-400" />
            {toast}
          </div>
        </div>
      )}

      {openProduct && (
        <ProductModal
          key={openProduct.id}
          product={openProduct}
          line={lines.find((l) => l.id === openProduct.id)}
          storeName={storeName}
          whatsapp={settings.whatsapp}
          onClose={() => setOpenProductId(null)}
          onSave={(qty, note) => {
            setLine(openProduct.id, qty, note);
            setOpenProductId(null);
            showToast(`${openProduct.name} no seu pedido`);
          }}
        />
      )}

      <CartDrawer
        open={cartOpen}
        lines={orderLines}
        storeName={storeName}
        whatsapp={settings.whatsapp}
        customer={customer}
        onCustomer={setCustomer}
        onClose={() => setCartOpen(false)}
        onQty={(id, qty) => setLine(id, qty)}
        onNote={(id, note) =>
          setLines((prev) => prev.map((l) => (l.id === id ? { ...l, note } : l)))
        }
        onRemove={(id) => setLines((prev) => prev.filter((l) => l.id !== id))}
        onClear={() => setLines([])}
        onBrowse={() => goTab(1)}
        onSent={() => showToast("Abrindo o WhatsApp…")}
      />
    </div>
  );
}
