"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatCurrency, formatDateTime } from "@/lib/format";
import type { CostProfile, Customer, Machine, Quote } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

export default function CalculadoraPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [profiles, setProfiles] = useState<CostProfile[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingQuote, setIsSavingQuote] = useState(false);
  const [showProfileForm, setShowProfileForm] = useState(false);

  const [profileName, setProfileName] = useState("");
  const [energyCost, setEnergyCost] = useState("0.9");
  const [laborCost, setLaborCost] = useState("20");
  const [packagingCost, setPackagingCost] = useState("2");
  const [wastePct, setWastePct] = useState("5");
  const [feesPct, setFeesPct] = useState("0");
  const [profitPct, setProfitPct] = useState("40");
  const [taxPct, setTaxPct] = useState("0");
  const [isDefault, setIsDefault] = useState(false);

  const [costProfileId, setCostProfileId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [materialCost, setMaterialCost] = useState("");
  const [printHours, setPrintHours] = useState("");
  const [machineId, setMachineId] = useState("");
  const [manualMachineCost, setManualMachineCost] = useState("");
  const [energyKwh, setEnergyKwh] = useState("0");
  const [laborHours, setLaborHours] = useState("0");

  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const [profilesData, quotesData, machinesData, customersData] = await Promise.all([
        apiFetch<CostProfile[]>(`${orgPath}/cost-profiles`, { accessToken }),
        apiFetch<Quote[]>(`${orgPath}/quotes`, { accessToken }),
        apiFetch<Machine[]>(`${orgPath}/machines`, { accessToken }),
        apiFetch<Customer[]>(`${orgPath}/customers`, { accessToken }),
      ]);
      setProfiles(profilesData);
      setQuotes(quotesData);
      setMachines(machinesData);
      setCustomers(customersData);
      setCostProfileId((prev) => prev || profilesData.find((p) => p.is_default)?.id || profilesData[0]?.id || "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar calculadora.");
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

  async function handleCreateProfile(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    setIsSavingProfile(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/cost-profiles`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({
          name: profileName,
          energy_cost_per_kwh: Number(energyCost),
          labor_cost_per_hour: Number(laborCost),
          packaging_cost_flat: Number(packagingCost),
          waste_percentage: Number(wastePct),
          fees_percentage: Number(feesPct),
          profit_margin_percentage: Number(profitPct),
          tax_percentage: taxPct ? Number(taxPct) : null,
          is_default: isDefault,
        }),
      });
      setProfileName("");
      setShowProfileForm(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao criar perfil de custo.");
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handleCreateQuote(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken || !costProfileId) return;
    if (!machineId && !manualMachineCost) {
      setError("Selecione uma máquina ou informe o custo/hora manualmente.");
      return;
    }
    setIsSavingQuote(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/quotes`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({
          cost_profile_id: costProfileId,
          customer_id: customerId || null,
          material_cost: Number(materialCost || 0),
          print_time_hours: Number(printHours || 0),
          machine_id: machineId || null,
          machine_cost_per_hour: machineId ? null : Number(manualMachineCost),
          energy_kwh: Number(energyKwh || 0),
          labor_hours: Number(laborHours || 0),
        }),
      });
      setMaterialCost("");
      setPrintHours("");
      setManualMachineCost("");
      setEnergyKwh("0");
      setLaborHours("0");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao gerar orçamento.");
    } finally {
      setIsSavingQuote(false);
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
    <AppShell title="Calculadora de preços">
      <div className="mx-auto max-w-5xl space-y-8">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-neutral-300">Perfis de custo</h2>
            <button
              onClick={() => setShowProfileForm((v) => !v)}
              className="rounded-lg bg-neutral-800 px-3 py-1.5 text-xs font-medium hover:bg-neutral-700"
            >
              {showProfileForm ? "Cancelar" : "+ Novo perfil"}
            </button>
          </div>

          {showProfileForm && (
            <form
              onSubmit={handleCreateProfile}
              className="grid gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-3"
            >
              <input required placeholder="Nome do perfil" value={profileName} onChange={(e) => setProfileName(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 sm:col-span-3" />
              <input type="number" step="0.01" placeholder="Energia (R$/kWh)" value={energyCost} onChange={(e) => setEnergyCost(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <input type="number" step="0.01" placeholder="Mão de obra (R$/h)" value={laborCost} onChange={(e) => setLaborCost(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <input type="number" step="0.01" placeholder="Embalagem fixa (R$)" value={packagingCost} onChange={(e) => setPackagingCost(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <input type="number" step="0.01" placeholder="Desperdício (%)" value={wastePct} onChange={(e) => setWastePct(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <input type="number" step="0.01" placeholder="Taxas (%)" value={feesPct} onChange={(e) => setFeesPct(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <input type="number" step="0.01" placeholder="Margem de lucro (%)" value={profitPct} onChange={(e) => setProfitPct(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <input type="number" step="0.01" placeholder="Imposto (%)" value={taxPct} onChange={(e) => setTaxPct(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
              <label className="flex items-center gap-2 text-sm text-neutral-400">
                <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} className="rounded border-neutral-700" />
                Perfil padrão
              </label>
              <button type="submit" disabled={isSavingProfile} className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50 sm:col-span-3">
                {isSavingProfile ? "Salvando…" : "Salvar perfil"}
              </button>
            </form>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {isLoading ? (
              <p className="text-sm text-neutral-500">Carregando…</p>
            ) : profiles.length === 0 ? (
              <p className="text-sm text-neutral-500">Nenhum perfil de custo cadastrado ainda.</p>
            ) : (
              profiles.map((p) => (
                <div key={p.id} className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{p.name}</span>
                    {p.is_default && <span className="rounded bg-blue-950 px-1.5 py-0.5 text-xs text-blue-300">padrão</span>}
                  </div>
                  <p className="mt-1 text-neutral-500">Margem {p.profit_margin_percentage}% · Desperdício {p.waste_percentage}%</p>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-medium text-neutral-300">Novo orçamento</h2>
          <form
            onSubmit={handleCreateQuote}
            className="grid gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-2"
          >
            <select required value={costProfileId} onChange={(e) => setCostProfileId(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2">
              <option value="">Perfil de custo…</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2">
              <option value="">Sem cliente vinculado</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <input required type="number" step="0.01" placeholder="Custo do material (R$)" value={materialCost} onChange={(e) => setMaterialCost(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input required type="number" step="0.01" placeholder="Tempo de impressão (h)" value={printHours} onChange={(e) => setPrintHours(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <select value={machineId} onChange={(e) => { setMachineId(e.target.value); if (e.target.value) setManualMachineCost(""); }} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2">
              <option value="">Informar custo/hora manualmente…</option>
              {machines.map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
            <input
              type="number"
              step="0.01"
              placeholder="Custo/hora manual (R$)"
              value={manualMachineCost}
              onChange={(e) => setManualMachineCost(e.target.value)}
              disabled={!!machineId}
              className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 disabled:opacity-40"
            />
            <input type="number" step="0.01" placeholder="Energia (kWh)" value={energyKwh} onChange={(e) => setEnergyKwh(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <input type="number" step="0.01" placeholder="Mão de obra (h)" value={laborHours} onChange={(e) => setLaborHours(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
            <button type="submit" disabled={isSavingQuote || profiles.length === 0} className="rounded bg-purple-600 px-4 py-2 font-medium hover:bg-purple-500 disabled:opacity-50 sm:col-span-2">
              {isSavingQuote ? "Calculando…" : "Calcular orçamento"}
            </button>
            {profiles.length === 0 && (
              <p className="text-xs text-yellow-300 sm:col-span-2">Crie um perfil de custo antes de gerar orçamentos.</p>
            )}
          </form>
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-medium text-neutral-300">Orçamentos recentes</h2>
          <div className="overflow-x-auto rounded-xl border border-neutral-800">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead className="border-b border-neutral-800 bg-neutral-950/50 text-neutral-400">
                <tr>
                  <th className="px-4 py-3 font-medium">Cliente</th>
                  <th className="px-4 py-3 font-medium">Custo de produção</th>
                  <th className="px-4 py-3 font-medium">Preço sugerido</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Criado em</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800">
                {quotes.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-neutral-500">Nenhum orçamento ainda.</td>
                  </tr>
                ) : (
                  quotes.map((q) => (
                    <tr key={q.id} className="hover:bg-neutral-900/50">
                      <td className="px-4 py-3">{customers.find((c) => c.id === q.customer_id)?.name ?? "—"}</td>
                      <td className="px-4 py-3">{formatCurrency(q.production_cost)}</td>
                      <td className="px-4 py-3 font-medium text-green-400">{formatCurrency(q.final_price ?? q.suggested_price)}</td>
                      <td className="px-4 py-3">{q.status}</td>
                      <td className="px-4 py-3">{formatDateTime(q.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
