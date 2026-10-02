export type StoreSlide = { url: string; title: string; subtitle: string };
export type StoreHighlight = { title: string; text: string };

export type StoreSettings = {
  display_name: string;
  tagline: string;
  about: string;
  whatsapp: string;
  instagram: string;
  hours: string;
  address: string;
  accent: string;
  theme: "light" | "dark";
  slides: StoreSlide[];
  highlights: StoreHighlight[];
  hidden_product_ids: string[];
  featured_product_ids: string[];
};

export type StoreAdminResponse = { slug: string; name: string; settings: StoreSettings };

export type PublicProduct = {
  id: string;
  name: string;
  description: string | null;
  size: string | null;
  photo_urls: string[];
  price: number;
  stock_quantity: number | null;
  available: boolean;
  featured: boolean;
};

export type PublicStore = {
  slug: string;
  name: string;
  settings: Omit<StoreSettings, "hidden_product_ids" | "featured_product_ids">;
  products: PublicProduct[];
};

export type CartLine = { id: string; qty: number; note: string };

export const DEFAULT_WHATSAPP = "5521970386065";

export const ACCENTS: Record<string, { label: string; color: string; soft: string }> = {
  indigo: { label: "Índigo", color: "#4f46e5", soft: "#eef2ff" },
  emerald: { label: "Esmeralda", color: "#047857", soft: "#ecfdf5" },
  rose: { label: "Rosé", color: "#be123c", soft: "#fff1f2" },
  amber: { label: "Âmbar", color: "#b45309", soft: "#fffbeb" },
  slate: { label: "Grafite", color: "#1e293b", soft: "#f1f5f9" },
};

export const THEMES = {
  light: { bg: "#faf8f5", surface: "#ffffff", ink: "#1c1917", muted: "#78716c", line: "#e7e5e4" },
  dark: { bg: "#0b0b10", surface: "#15151c", ink: "#f5f5f4", muted: "#a1a1aa", line: "#2a2a33" },
} as const;

function rgba(hex: string, alpha: number): string {
  const n = parseInt(hex.replace("#", ""), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

export function themeVars(accent: string, theme: "light" | "dark"): React.CSSProperties {
  const a = ACCENTS[accent] ?? ACCENTS.indigo;
  const t = THEMES[theme] ?? THEMES.light;
  return {
    "--bg": t.bg,
    "--surface": t.surface,
    "--ink": t.ink,
    "--muted": t.muted,
    "--line": t.line,
    "--accent": theme === "dark" && accent === "slate" ? "#e2e8f0" : a.color,
    "--accent-ink": theme === "dark" && accent === "slate" ? "#0f172a" : "#ffffff",
    "--bg-glass": rgba(t.bg, 0.82),
    "--surface-glass": rgba(t.surface, 0.82),
    "--accent-ring": rgba(theme === "dark" && accent === "slate" ? "#e2e8f0" : a.color, 0.22),
    "--accent-soft": theme === "dark" ? "rgba(255,255,255,0.06)" : a.soft,
  } as React.CSSProperties;
}

export function normalizeWhatsapp(input: string): string {
  const digits = input.replace(/\D/g, "");
  if (digits.length === 10 || digits.length === 11) return `55${digits}`;
  return digits;
}

export function whatsappLink(number: string, text: string): string {
  const digits = normalizeWhatsapp(number || DEFAULT_WHATSAPP);
  return `https://wa.me/${digits}?text=${encodeURIComponent(text)}`;
}

export function formatWhatsappDisplay(number: string): string {
  const d = normalizeWhatsapp(number).replace(/^55/, "");
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return number;
}

export type OrderLine = { product: PublicProduct; qty: number; note: string };

export function buildOrderMessage(
  storeName: string,
  lines: OrderLine[],
  customer: { name: string; extra: string }
): string {
  const brl = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const total = lines.reduce((sum, l) => sum + l.product.price * l.qty, 0);
  const items = lines
    .map((l, i) => {
      const size = l.product.size ? ` (${l.product.size})` : "";
      const note = l.note ? `\n   Obs: ${l.note}` : "";
      return `*${i + 1}.* ${l.product.name}${size}\n   ${l.qty} × ${brl(l.product.price)} = ${brl(
        l.product.price * l.qty
      )}${note}`;
    })
    .join("\n\n");
  const parts = [
    `Olá, ${storeName}! Gostaria de fazer um pedido:`,
    items,
    `*Total estimado: ${brl(total)}*`,
  ];
  if (customer.name.trim()) parts.push(`*Nome:* ${customer.name.trim()}`);
  if (customer.extra.trim()) parts.push(`*Informações adicionais:* ${customer.extra.trim()}`);
  return parts.join("\n\n");
}
