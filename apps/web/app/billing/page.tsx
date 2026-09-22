"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Plan, Subscription, UsageItem } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

const STATUS_LABELS: Record<string, string> = {
  trialing: "Em teste",
  active: "Ativa",
  past_due: "Pagamento pendente",
  canceled: "Cancelada",
  incomplete: "Incompleta",
  unpaid: "Não pago",
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("pt-BR");
}

function formatUsageValue(item: UsageItem): string {
  if (item.limit_type === "boolean") {
    return item.enabled ? "Disponível" : "Não disponível";
  }
  const limit = item.limit === null ? "sem limite" : item.limit;
  return `${item.current_usage ?? 0} / ${limit}`;
}

export default function BillingPage() {
  const { status, accessToken, currentOrganizationId, organizations } = useAuth();
  const router = useRouter();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [usage, setUsage] = useState<UsageItem[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);

  const isOwner = organizations.find(
    (m) => m.organization.id === currentOrganizationId
  )?.role === "OWNER";

  const loadAll = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [subscriptionData, usageData, plansData] = await Promise.all([
        apiFetch<Subscription>(
          `/api/v1/organizations/${currentOrganizationId}/billing/subscription`,
          { accessToken }
        ),
        apiFetch<UsageItem[]>(`/api/v1/organizations/${currentOrganizationId}/billing/usage`, {
          accessToken,
        }),
        apiFetch<Plan[]>("/api/v1/billing/plans", { accessToken }),
      ]);
      setSubscription(subscriptionData);
      setUsage(usageData);
      setPlans(plansData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar dados de faturamento.");
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
    const timeoutId = setTimeout(loadAll, 0);
    return () => clearTimeout(timeoutId);
  }, [status, router, loadAll]);

  async function handleCancel(atPeriodEnd: boolean) {
    if (!accessToken || !currentOrganizationId) return;
    setIsActing(true);
    setError(null);
    try {
      await apiFetch(`/api/v1/organizations/${currentOrganizationId}/billing/subscription/cancel`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({ at_period_end: atPeriodEnd }),
      });
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao cancelar a assinatura.");
    } finally {
      setIsActing(false);
    }
  }

  async function handleChangePlan(planCode: string) {
    if (!accessToken || !currentOrganizationId || !planCode) return;
    setIsActing(true);
    setError(null);
    try {
      await apiFetch(
        `/api/v1/organizations/${currentOrganizationId}/billing/subscription/change-plan`,
        { method: "POST", accessToken, body: JSON.stringify({ plan_code: planCode }) }
      );
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao trocar de plano.");
    } finally {
      setIsActing(false);
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
    <AppShell title="Faturamento">
      <div className="mx-auto max-w-3xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        {isLoading ? (
          <p className="text-neutral-400">Carregando…</p>
        ) : (
          <>
            <section className="space-y-2 rounded border border-neutral-800 p-4">
              <h2 className="font-medium">Plano atual</h2>
              {subscription ? (
                <div className="space-y-1 text-sm text-neutral-300">
                  <p>
                    <span className="text-neutral-500">Plano: </span>
                    {subscription.plan.name}
                  </p>
                  <p>
                    <span className="text-neutral-500">Status: </span>
                    {STATUS_LABELS[subscription.status] ?? subscription.status}
                    {subscription.cancel_at_period_end && " (cancelamento agendado)"}
                  </p>
                  <p>
                    <span className="text-neutral-500">Período atual: </span>
                    {formatDate(subscription.current_period_start)} a{" "}
                    {formatDate(subscription.current_period_end)}
                  </p>
                  {subscription.trial_end && (
                    <p>
                      <span className="text-neutral-500">Teste até: </span>
                      {formatDate(subscription.trial_end)}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-neutral-500">Nenhuma assinatura encontrada.</p>
              )}
            </section>

            <section className="space-y-2 rounded border border-neutral-800 p-4">
              <h2 className="font-medium">Uso e limites</h2>
              <ul className="divide-y divide-neutral-800 text-sm">
                {usage.map((item) => (
                  <li key={item.key} className="flex items-center justify-between py-2">
                    <span className="text-neutral-400">{item.key}</span>
                    <span>{formatUsageValue(item)}</span>
                  </li>
                ))}
              </ul>
            </section>

            {isOwner && subscription && (
              <section className="space-y-3 rounded border border-neutral-800 p-4">
                <h2 className="font-medium">Gerenciar assinatura</h2>
                <div className="flex flex-wrap gap-2">
                  <select
                    disabled={isActing}
                    defaultValue=""
                    onChange={(e) => e.target.value && handleChangePlan(e.target.value)}
                    className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
                  >
                    <option value="" disabled>
                      Trocar de plano…
                    </option>
                    {plans.map((plan) => (
                      <option key={plan.code} value={plan.code}>
                        {plan.name}
                      </option>
                    ))}
                  </select>
                  <button
                    disabled={isActing || subscription.status === "canceled"}
                    onClick={() => handleCancel(true)}
                    className="rounded border border-neutral-700 px-3 py-2 text-sm disabled:opacity-50"
                  >
                    Cancelar ao fim do período
                  </button>
                  <button
                    disabled={isActing || subscription.status === "canceled"}
                    onClick={() => handleCancel(false)}
                    className="rounded bg-red-900 px-3 py-2 text-sm text-red-200 disabled:opacity-50"
                  >
                    Cancelar agora
                  </button>
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
