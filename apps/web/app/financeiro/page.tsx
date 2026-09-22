"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatCurrency, formatDate } from "@/lib/format";
import { FINANCE_TRANSACTION_TYPES } from "@/lib/types";
import type { FinancialSummary, FinancialTransaction } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

const TYPE_LABELS: Record<string, string> = {
  receita: "Receita",
  custo: "Custo",
  despesa: "Despesa",
};

const TYPE_TONE: Record<string, string> = {
  receita: "text-green-400",
  custo: "text-yellow-300",
  despesa: "text-red-400",
};

export default function FinanceiroPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [transactions, setTransactions] = useState<FinancialTransaction[]>([]);
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");

  const [type, setType] = useState("receita");
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [markPaid, setMarkPaid] = useState(false);

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const query = typeFilter ? `?type=${typeFilter}` : "";
      const [transactionsData, summaryData] = await Promise.all([
        apiFetch<FinancialTransaction[]>(`${orgPath}/finance/transactions${query}`, { accessToken }),
        apiFetch<FinancialSummary>(`${orgPath}/finance/summary`, { accessToken }),
      ]);
      setTransactions(transactionsData);
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar financeiro.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, currentOrganizationId, orgPath, typeFilter]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status !== "authenticated") return;
    const timeoutId = setTimeout(load, 0);
    return () => clearTimeout(timeoutId);
  }, [status, router, load]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    setIsSaving(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/finance/transactions`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({
          type,
          category,
          amount: Number(amount),
          due_date: dueDate || null,
          mark_as_paid: markPaid,
        }),
      });
      setType("receita");
      setCategory("");
      setAmount("");
      setDueDate("");
      setMarkPaid(false);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao criar lançamento.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleMarkPaid(transactionId: string) {
    if (!accessToken) return;
    setError(null);
    try {
      await apiFetch(`${orgPath}/finance/transactions/${transactionId}/mark-paid`, {
        method: "POST",
        accessToken,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao marcar como pago.");
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
    <AppShell title="Financeiro">
      <div className="mx-auto max-w-5xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        {summary && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {[
              { label: "Receita", value: summary.total_revenue, tone: "text-green-400" },
              { label: "Custo", value: summary.total_cost, tone: "text-neutral-100" },
              { label: "Despesa", value: summary.total_expense, tone: "text-red-400" },
              { label: "Lucro", value: summary.profit, tone: summary.profit >= 0 ? "text-green-400" : "text-red-400" },
              { label: "A receber", value: summary.pending_receivables, tone: "text-yellow-300" },
              { label: "A pagar", value: summary.pending_payables, tone: "text-yellow-300" },
            ].map((kpi) => (
              <div key={kpi.label} className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
                <p className="text-xs text-neutral-500">{kpi.label}</p>
                <p className={`mt-1 text-lg font-semibold ${kpi.tone}`}>{formatCurrency(kpi.value)}</p>
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
            <option value="">Todos os tipos</option>
            {FINANCE_TRANSACTION_TYPES.map((t) => (
              <option key={t} value={t}>{TYPE_LABELS[t]}</option>
            ))}
          </select>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
          >
            {showForm ? "Cancelar" : "+ Novo lançamento"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleCreate}
            className="grid gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-2"
          >
            <select value={type} onChange={(e) => setType(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2">
              {FINANCE_TRANSACTION_TYPES.map((t) => (
                <option key={t} value={t}>{TYPE_LABELS[t]}</option>
              ))}
            </select>
            <input required placeholder="Categoria" value={category} onChange={(e) => setCategory(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input required type="number" step="0.01" placeholder="Valor (R$)" value={amount} onChange={(e) => setAmount(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input type="date" placeholder="Vencimento" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <label className="flex items-center gap-2 text-sm text-neutral-400 sm:col-span-2">
              <input type="checkbox" checked={markPaid} onChange={(e) => setMarkPaid(e.target.checked)} className="rounded border-neutral-700" />
              Já foi pago
            </label>
            <button type="submit" disabled={isSaving} className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50 sm:col-span-2">
              {isSaving ? "Salvando…" : "Salvar lançamento"}
            </button>
          </form>
        )}

        <div className="overflow-x-auto rounded-xl border border-neutral-800">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead className="border-b border-neutral-800 bg-neutral-950/50 text-neutral-400">
              <tr>
                <th className="px-4 py-3 font-medium">Tipo</th>
                <th className="px-4 py-3 font-medium">Categoria</th>
                <th className="px-4 py-3 font-medium">Valor</th>
                <th className="px-4 py-3 font-medium">Vencimento</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-neutral-500">Carregando…</td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-neutral-500">Nenhum lançamento.</td>
                </tr>
              ) : (
                transactions.map((t) => (
                  <tr key={t.id} className="hover:bg-neutral-900/50">
                    <td className={`px-4 py-3 font-medium ${TYPE_TONE[t.type] ?? ""}`}>{TYPE_LABELS[t.type] ?? t.type}</td>
                    <td className="px-4 py-3">{t.category}</td>
                    <td className="px-4 py-3">{formatCurrency(t.amount)}</td>
                    <td className="px-4 py-3">{formatDate(t.due_date)}</td>
                    <td className="px-4 py-3">
                      {t.paid_at ? (
                        <span className="rounded bg-green-950 px-2 py-0.5 text-xs text-green-300">Pago</span>
                      ) : (
                        <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">Pendente</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {!t.paid_at && (
                        <button onClick={() => handleMarkPaid(t.id)} className="text-sm text-blue-400 hover:underline">
                          Marcar como pago
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
