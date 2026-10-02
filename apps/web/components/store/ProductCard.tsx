"use client";

import type { PublicProduct } from "@/lib/store";
import { formatCurrency } from "@/lib/format";
import { IconMinus, IconPlus } from "./ui";

export function ProductCard({
  product,
  qty,
  onOpen,
  onAdd,
  onChangeQty,
}: {
  product: PublicProduct;
  qty: number;
  onOpen: () => void;
  onAdd: () => void;
  onChangeQty: (qty: number) => void;
}) {
  const cover = product.photo_urls[0];

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-3xl border border-[var(--line)] bg-[var(--surface)] shadow-[0_1px_0_rgba(0,0,0,0.02)] transition duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] hover:-translate-y-1.5 hover:shadow-[0_24px_50px_-24px_rgba(0,0,0,0.35)]">
      <button
        onClick={onOpen}
        aria-label={`Ver ${product.name}`}
        className="relative block aspect-[4/5] w-full overflow-hidden bg-[var(--accent-soft)] text-left"
      >
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cover}
            alt={product.name}
            loading="lazy"
            className={`h-full w-full object-cover transition duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:scale-[1.07] ${
              product.available ? "" : "grayscale"
            }`}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center font-[family-name:var(--font-display)] text-6xl text-[var(--accent)] opacity-40">
            {product.name.slice(0, 1).toUpperCase()}
          </div>
        )}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/25 via-transparent to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
        <div className="absolute left-3 top-3 flex flex-col items-start gap-1.5">
          {product.featured && product.available && (
            <span className="rounded-full bg-[var(--accent)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--accent-ink)] shadow">
              Destaque
            </span>
          )}
          {!product.available && (
            <span className="rounded-full bg-black/75 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white backdrop-blur">
              Esgotado
            </span>
          )}
          {product.available && product.stock_quantity != null && product.stock_quantity <= 3 && (
            <span className="rounded-full bg-white/90 px-2.5 py-1 text-[10px] font-semibold text-neutral-800 backdrop-blur">
              Últimas {product.stock_quantity}
            </span>
          )}
        </div>
        {product.photo_urls.length > 1 && (
          <span className="absolute bottom-3 right-3 rounded-full bg-black/55 px-2 py-0.5 text-[10px] text-white backdrop-blur">
            {product.photo_urls.length} fotos
          </span>
        )}
      </button>

      <div className="flex flex-1 flex-col gap-3 p-4 sm:p-5">
        <div className="min-w-0 space-y-1">
          <h3 className="line-clamp-2 text-[15px] font-semibold leading-snug text-[var(--ink)]">
            {product.name}
          </h3>
          {product.size && <p className="truncate text-xs text-[var(--muted)]">{product.size}</p>}
        </div>

        <div className="mt-auto flex flex-col gap-2.5 min-[520px]:flex-row min-[520px]:items-center min-[520px]:justify-between">
          <p className="font-[family-name:var(--font-display)] text-xl font-semibold text-[var(--ink)]">
            {formatCurrency(product.price)}
          </p>

          {!product.available ? (
            <span className="text-xs text-[var(--muted)]">Indisponível</span>
          ) : qty > 0 ? (
            <div className="flex items-center justify-between gap-1 rounded-full border border-[var(--line)] bg-[var(--bg)] p-1">
              <button
                onClick={() => onChangeQty(qty - 1)}
                aria-label="Diminuir"
                className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--ink)] transition hover:bg-[var(--accent-soft)]"
              >
                <IconMinus className="h-4 w-4" />
              </button>
              <span className="w-6 text-center text-sm font-semibold text-[var(--ink)]">{qty}</span>
              <button
                onClick={() => onChangeQty(qty + 1)}
                aria-label="Aumentar"
                className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--accent-ink)] transition hover:brightness-110"
              >
                <IconPlus className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={onAdd}
              className="inline-flex h-10 items-center justify-center gap-1.5 rounded-full bg-[var(--accent)] px-4 text-sm font-semibold text-[var(--accent-ink)] shadow-sm transition hover:-translate-y-0.5 hover:shadow-md active:translate-y-0"
            >
              <IconPlus className="h-4 w-4" />
              Adicionar
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
