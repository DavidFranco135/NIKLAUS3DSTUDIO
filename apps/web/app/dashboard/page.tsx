"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { DashboardData } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

const ORDER_STATUS_LABELS: Record<string, string> = {
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

const STATUS_COLORS = [
  "#60a5fa",
  "#34d399",
  "#fbbf24",
  "#f87171",
  "#a78bfa",
  "#fb923c",
  "#38bdf8",
  "#4ade80",
  "#f472b6",
  "#94a3b8",
];

function KpiCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "positive" | "negative" | "warning";
}) {
  const toneClass =
    tone === "positive"
      ? "text-green-400"
      : tone === "negative"
        ? "text-red-400"
        : tone === "warning"
          ? "text-yellow-300"
          : "text-neutral-100";
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const result = await apiFetch<DashboardData>(
        `/api/v1/organizations/${currentOrganizationId}/dashboard`,
        { accessToken }
      );
      setData(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar o painel.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, currentOrganizationId]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status !== "authenticated") return;
    const timeoutId = setTimeout(loadDashboard, 0);
    return () => clearTimeout(timeoutId);
  }, [status, router, loadDashboard]);

  if (status !== "authenticated") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-neutral-400">Carregando…</p>
      </main>
    );
  }

  const ordersChartData = data
    ? Object.entries(data.orders_by_status).map(([key, value]) => ({
        status: ORDER_STATUS_LABELS[key] ?? key,
        total: value,
      }))
    : [];

  const totalOrders = ordersChartData.reduce((sum, item) => sum + item.total, 0);

  return (
    <AppShell title="Painel">
      <div className="mx-auto max-w-6xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        {isLoading && !data ? (
          <p className="text-neutral-400">Carregando painel…</p>
        ) : data ? (
          <>
            {data.low_stock_items_count > 0 && (
              <Link
                href="/estoque"
                className="block rounded-lg border border-yellow-800 bg-yellow-950/60 px-4 py-3 text-sm text-yellow-300 hover:bg-yellow-950"
              >
                ⚠ {data.low_stock_items_count} item(ns) de estoque abaixo do mínimo — ver estoque
              </Link>
            )}

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <KpiCard label="Receita" value={formatCurrency(data.financial.total_revenue)} tone="positive" />
              <KpiCard label="Custo" value={formatCurrency(data.financial.total_cost)} />
              <KpiCard label="Despesa" value={formatCurrency(data.financial.total_expense)} />
              <KpiCard
                label="Lucro"
                value={formatCurrency(data.financial.profit)}
                tone={data.financial.profit >= 0 ? "positive" : "negative"}
              />
              <KpiCard label="A receber" value={formatCurrency(data.financial.pending_receivables)} tone="warning" />
              <KpiCard label="A pagar" value={formatCurrency(data.financial.pending_payables)} tone="warning" />
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <KpiCard label="Pedidos" value={String(totalOrders)} />
              <KpiCard label="Clientes" value={String(data.customers_count)} />
              <KpiCard label="Projetos" value={String(data.projects_count)} />
              <KpiCard
                label="Estoque baixo"
                value={String(data.low_stock_items_count)}
                tone={data.low_stock_items_count > 0 ? "warning" : "default"}
              />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
                <h2 className="mb-3 text-sm font-medium text-neutral-300">Pedidos por status</h2>
                {ordersChartData.length === 0 ? (
                  <p className="text-sm text-neutral-500">Nenhum pedido ainda.</p>
                ) : (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={ordersChartData} margin={{ left: -20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                      <XAxis dataKey="status" stroke="#a3a3a3" fontSize={12} interval={0} angle={-20} textAnchor="end" height={60} />
                      <YAxis stroke="#a3a3a3" fontSize={12} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{ background: "#171717", border: "1px solid #404040", borderRadius: 8 }}
                        labelStyle={{ color: "#e5e5e5" }}
                      />
                      <Bar dataKey="total" radius={[4, 4, 0, 0]}>
                        {ordersChartData.map((_, index) => (
                          <Cell key={index} fill={STATUS_COLORS[index % STATUS_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>

              <div className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
                <h2 className="mb-3 text-sm font-medium text-neutral-300">Receita x custo x despesa</h2>
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: "Receita", value: Math.max(data.financial.total_revenue, 0) },
                        { name: "Custo", value: Math.max(data.financial.total_cost, 0) },
                        { name: "Despesa", value: Math.max(data.financial.total_expense, 0) },
                      ]}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={55}
                      outerRadius={90}
                      paddingAngle={2}
                    >
                      <Cell fill="#34d399" />
                      <Cell fill="#60a5fa" />
                      <Cell fill="#f87171" />
                    </Pie>
                    <Tooltip
                      formatter={(value) => formatCurrency(typeof value === "number" ? value : Number(value))}
                      contentStyle={{ background: "#171717", border: "1px solid #404040", borderRadius: 8 }}
                      labelStyle={{ color: "#e5e5e5" }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
