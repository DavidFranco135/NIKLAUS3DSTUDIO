"use client";

import { useEffect } from "react";
import type { OrderLine } from "@/lib/store";
import { buildOrderMessage, whatsappLink } from "@/lib/store";
import { formatCurrency } from "@/lib/format";
import { IconClose, IconMinus, IconPlus, IconTrash, IconWhatsapp } from "./ui";

export type CustomerInfo = { name: string; extra: string };

export function CartDrawer({
  open,
  lines,
  storeName,
  whatsapp,
  customer,
  onCustomer,
  onClose,
  onQty,
  onNote,
  onRemove,
  onClear,
  onBrowse,
  onSent,
}: {
  open: boolean;
  lines: OrderLine[];
  storeName: string;
  whatsapp: string;
  customer: CustomerInfo;
  onCustomer: (next: CustomerInfo) => void;
  onClose: () => void;
  onQty: (id: string, qty: number) => void;
  onNote: (id: string, note: string) => void;
  onRemove: (id: string) => void;
  onClear: () => void;
  onBrowse: () => void;
  onSent: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [open, onClose]);

  if (!open) return null;

  const total = lines.reduce((sum, l) => sum + l.product.price * l.qty, 0);
  const units = lines.reduce((sum, l) => sum + l.qty, 0);
  const href = whatsappLink(whatsapp, buildOrderMessage(storeName, lines, customer));

  return (
    <div className="fixed inset-0 z-[80] animate-fade-in bg-black/55 backdrop-blur-sm" onClick={onClose}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Seu pedido"
        onClick={(e) => e.stopPropagation()}
        className="absolute inset-y-0 right-0 flex w-full max-w-md animate-drawer-in flex-col bg-[var(--surface)] text-[var(--ink)] shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-[var(--line)] px-6 py-5">
          <div>
            <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold">Seu pedido</h2>
            <p className="text-xs text-[var(--muted)]">
              {units} {units === 1 ? "item" : "itens"}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Fechar"
            className="flex h-10 w-10 items-center justify-center rounded-full transition hover:bg-[var(--accent-soft)]"
          >
            <IconClose className="h-5 w-5" />
          </button>
        </header>

        {lines.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 px-8 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--accent-soft)] text-2xl">
              🛍️
            </div>
            <p className="font-medium">Seu pedido está vazio</p>
            <p className="text-sm text-[var(--muted)]">
              Escolha produtos no catálogo para montar seu pedido e enviar pelo WhatsApp.
            </p>
            <button
              onClick={() => {
                onClose();
                onBrowse();
              }}
              className="rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-[var(--accent-ink)] transition hover:-translate-y-0.5"
            >
              Ver catálogo
            </button>
          </div>
        ) : (
          <>
            <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
              {lines.map(({ product, qty, note }, i) => (
                <div
                  key={product.id}
                  style={{ animationDelay: `${i * 40}ms` }}
                  className="animate-fade-up rounded-2xl border border-[var(--line)] bg-[var(--bg)] p-3"
                >
                  <div className="flex gap-3">
                    <div className="h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-[var(--accent-soft)]">
                      {product.photo_urls[0] ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={product.photo_urls[0]} alt="" className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-2xl text-[var(--accent)] opacity-40">
                          {product.name.slice(0, 1)}
                        </div>
                      )}
                    </div>
                    <div className="flex min-w-0 flex-1 flex-col justify-between">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="line-clamp-2 text-sm font-semibold leading-snug">{product.name}</p>
                          {product.size && (
                            <p className="truncate text-xs text-[var(--muted)]">{product.size}</p>
                          )}
                        </div>
                        <button
                          onClick={() => onRemove(product.id)}
                          aria-label="Remover"
                          className="shrink-0 rounded-lg p-1.5 text-[var(--muted)] transition hover:bg-red-500/10 hover:text-red-500"
                        >
                          <IconTrash className="h-4 w-4" />
                        </button>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1 rounded-full border border-[var(--line)] bg-[var(--surface)] p-0.5">
                          <button
                            onClick={() => onQty(product.id, qty - 1)}
                            aria-label="Diminuir"
                            className="flex h-7 w-7 items-center justify-center rounded-full transition hover:bg-[var(--accent-soft)]"
                          >
                            <IconMinus className="h-3.5 w-3.5" />
                          </button>
                          <span className="w-6 text-center text-sm font-semibold">{qty}</span>
                          <button
                            onClick={() => onQty(product.id, qty + 1)}
                            aria-label="Aumentar"
                            className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--accent-ink)]"
                          >
                            <IconPlus className="h-3.5 w-3.5" />
                          </button>
                        </div>
                        <p className="text-sm font-semibold">{formatCurrency(product.price * qty)}</p>
                      </div>
                    </div>
                  </div>
                  <input
                    value={note}
                    onChange={(e) => onNote(product.id, e.target.value)}
                    maxLength={300}
                    placeholder="Observação deste item (cor, personalização…)"
                    className="mt-3 w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-xs text-[var(--ink)] outline-none transition placeholder:text-[var(--muted)] focus:border-[var(--accent)]"
                  />
                </div>
              ))}

              <div className="space-y-3 pt-2">
                <input
                  value={customer.name}
                  onChange={(e) => onCustomer({ ...customer, name: e.target.value })}
                  placeholder="Seu nome"
                  className="w-full rounded-2xl border border-[var(--line)] bg-[var(--bg)] px-4 py-3 text-sm outline-none transition placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-ring)]"
                />
                <textarea
                  value={customer.extra}
                  onChange={(e) => onCustomer({ ...customer, extra: e.target.value })}
                  rows={3}
                  maxLength={600}
                  placeholder="Informações adicionais: endereço de entrega, prazo desejado, forma de pagamento…"
                  className="w-full resize-none rounded-2xl border border-[var(--line)] bg-[var(--bg)] px-4 py-3 text-sm outline-none transition placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-ring)]"
                />
              </div>
            </div>

            <footer className="space-y-3 border-t border-[var(--line)] bg-[var(--surface)] px-6 py-5">
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-[var(--muted)]">Total estimado</span>
                <span className="font-[family-name:var(--font-display)] text-3xl font-semibold">
                  {formatCurrency(total)}
                </span>
              </div>
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                onClick={onSent}
                className="flex h-13 items-center justify-center gap-2 rounded-full bg-[#25d366] px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-[#25d366]/30 transition hover:-translate-y-0.5 hover:brightness-105 active:translate-y-0"
              >
                <IconWhatsapp className="h-5 w-5" />
                Enviar pedido pelo WhatsApp
              </a>
              <button
                onClick={onClear}
                className="w-full text-center text-xs text-[var(--muted)] transition hover:text-red-500"
              >
                Limpar pedido
              </button>
              <p className="text-center text-[11px] text-[var(--muted)]">
                O valor final e o prazo são confirmados com você no WhatsApp.
              </p>
            </footer>
          </>
        )}
      </aside>
    </div>
  );
}
