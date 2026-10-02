"use client";

import { useEffect, useState } from "react";
import type { CartLine, PublicProduct } from "@/lib/store";
import { whatsappLink } from "@/lib/store";
import { formatCurrency } from "@/lib/format";
import {
  IconChevronLeft,
  IconChevronRight,
  IconClose,
  IconMinus,
  IconPlus,
  IconWhatsapp,
  useSwipe,
} from "./ui";

export function ProductModal({
  product,
  line,
  storeName,
  whatsapp,
  onClose,
  onSave,
}: {
  product: PublicProduct;
  line: CartLine | undefined;
  storeName: string;
  whatsapp: string;
  onClose: () => void;
  onSave: (qty: number, note: string) => void;
}) {
  const [photo, setPhoto] = useState(0);
  const [qty, setQty] = useState(line?.qty ?? 1);
  const [note, setNote] = useState(line?.note ?? "");
  const photos = product.photo_urls;
  const maxQty = product.stock_quantity ?? 99;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [onClose]);

  const next = () => photos.length > 0 && setPhoto((i) => (i + 1) % photos.length);
  const prev = () => photos.length > 0 && setPhoto((i) => (i - 1 + photos.length) % photos.length);
  const swipe = useSwipe(next, prev);

  const ask = whatsappLink(
    whatsapp,
    `Olá, ${storeName}! Tenho uma dúvida sobre o produto *${product.name}*${
      product.size ? ` (${product.size})` : ""
    }.`
  );

  return (
    <div
      className="fixed inset-0 z-[70] flex items-end justify-center bg-black/60 backdrop-blur-sm animate-fade-in sm:items-center sm:p-6"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={product.name}
        onClick={(e) => e.stopPropagation()}
        className="relative grid max-h-[94vh] w-full max-w-4xl animate-sheet-up grid-cols-1 overflow-y-auto rounded-t-[32px] bg-[var(--surface)] text-[var(--ink)] shadow-2xl sm:max-h-[88vh] sm:grid-cols-2 sm:rounded-[32px]"
      >
        <button
          onClick={onClose}
          aria-label="Fechar"
          className="absolute right-4 top-4 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-black/45 text-white backdrop-blur transition hover:bg-black/65"
        >
          <IconClose className="h-5 w-5" />
        </button>

        <div className="relative bg-[var(--accent-soft)] sm:min-h-[520px]" {...swipe}>
          <div className="relative aspect-[4/5] w-full overflow-hidden sm:aspect-auto sm:h-full">
            {photos.length > 0 ? (
              photos.map((src, i) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={src}
                  src={src}
                  alt={`${product.name} - foto ${i + 1}`}
                  className={`absolute inset-0 h-full w-full object-cover transition-all duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                    i === photo ? "scale-100 opacity-100" : "scale-105 opacity-0"
                  }`}
                />
              ))
            ) : (
              <div className="flex h-full w-full items-center justify-center font-[family-name:var(--font-display)] text-8xl text-[var(--accent)] opacity-30">
                {product.name.slice(0, 1).toUpperCase()}
              </div>
            )}
          </div>

          {photos.length > 1 && (
            <>
              <button
                onClick={prev}
                aria-label="Foto anterior"
                className="absolute left-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur transition hover:bg-black/60"
              >
                <IconChevronLeft className="h-5 w-5" />
              </button>
              <button
                onClick={next}
                aria-label="Próxima foto"
                className="absolute right-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur transition hover:bg-black/60"
              >
                <IconChevronRight className="h-5 w-5" />
              </button>
              <div className="absolute inset-x-0 bottom-4 flex justify-center gap-1.5">
                {photos.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setPhoto(i)}
                    aria-label={`Foto ${i + 1}`}
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      i === photo ? "w-6 bg-white" : "w-1.5 bg-white/55"
                    }`}
                  />
                ))}
              </div>
            </>
          )}
        </div>

        <div className="flex flex-col gap-5 p-6 sm:p-8">
          <div className="space-y-2 pr-8">
            {product.featured && (
              <span className="inline-block rounded-full bg-[var(--accent-soft)] px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--accent)]">
                Destaque
              </span>
            )}
            <h2 className="font-[family-name:var(--font-display)] text-3xl font-semibold leading-tight">
              {product.name}
            </h2>
            <p className="font-[family-name:var(--font-display)] text-3xl font-semibold text-[var(--accent)]">
              {formatCurrency(product.price)}
            </p>
          </div>

          <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            {product.size && (
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-[var(--muted)]">Tamanho</dt>
                <dd className="font-medium">{product.size}</dd>
              </div>
            )}
            <div>
              <dt className="text-[11px] uppercase tracking-wider text-[var(--muted)]">Disponibilidade</dt>
              <dd className={`font-medium ${product.available ? "" : "text-red-500"}`}>
                {!product.available
                  ? "Esgotado"
                  : product.stock_quantity != null
                    ? `${product.stock_quantity} em estoque`
                    : "Sob encomenda / disponível"}
              </dd>
            </div>
          </dl>

          {product.description && (
            <p className="whitespace-pre-line text-sm leading-relaxed text-[var(--muted)]">
              {product.description}
            </p>
          )}

          {product.available && (
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-2xl border border-[var(--line)] bg-[var(--bg)] p-2">
                <span className="pl-3 text-sm font-medium">Quantidade</span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setQty((q) => Math.max(1, q - 1))}
                    aria-label="Diminuir"
                    className="flex h-10 w-10 items-center justify-center rounded-xl transition hover:bg-[var(--accent-soft)]"
                  >
                    <IconMinus className="h-4 w-4" />
                  </button>
                  <span className="w-10 text-center text-base font-semibold">{qty}</span>
                  <button
                    onClick={() => setQty((q) => Math.min(maxQty, q + 1))}
                    aria-label="Aumentar"
                    className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)] text-[var(--accent-ink)] transition hover:brightness-110"
                  >
                    <IconPlus className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                maxLength={300}
                placeholder="Informações adicionais: cor, personalização, nome na peça…"
                className="w-full resize-none rounded-2xl border border-[var(--line)] bg-[var(--bg)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-ring)]"
              />
            </div>
          )}

          <div className="mt-auto flex flex-col gap-2.5">
            {product.available && (
              <button
                onClick={() => onSave(qty, note.trim())}
                className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-[var(--accent)] px-6 text-sm font-semibold text-[var(--accent-ink)] shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0"
              >
                {line ? "Atualizar no pedido" : "Adicionar ao pedido"} ·{" "}
                {formatCurrency(product.price * qty)}
              </button>
            )}
            <a
              href={ask}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-12 items-center justify-center gap-2 rounded-full border border-[var(--line)] px-6 text-sm font-semibold transition hover:border-[#25d366] hover:text-[#25d366]"
            >
              <IconWhatsapp className="h-4 w-4 text-[#25d366]" />
              Tirar dúvidas no WhatsApp
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
