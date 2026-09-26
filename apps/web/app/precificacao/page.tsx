"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { formatCurrency, formatDateTime } from "@/lib/format";
import { calculatePricing } from "@/lib/pricing";
import type { CostProfile, Machine, Material, Quote } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

type TabKey = "impressora" | "peca" | "resultado" | "salvas";

const TABS: { key: TabKey; label: string }[] = [
  { key: "impressora", label: "Impressora" },
  { key: "peca", label: "Peça" },
  { key: "resultado", label: "Resultado" },
  { key: "salvas", label: "Peças salvas" },
];

export default function PrecificacaoPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const orgPath = `/api/v1/organizations/${currentOrganizationId}`;

  const [activeTab, setActiveTab] = useState<TabKey>("peca");
  const [machines, setMachines] = useState<Machine[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [costProfiles, setCostProfiles] = useState<CostProfile[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // --- Impressora tab: create a printer preset (reuses /machines) ---
  const [showPrinterForm, setShowPrinterForm] = useState(false);
  const [newPrinterName, setNewPrinterName] = useState("Bambu Lab A1");
  const [newPrinterBrand, setNewPrinterBrand] = useState("Bambu Lab");
  const [newPrinterModel, setNewPrinterModel] = useState("A1");
  const [newPrinterCostPerHour, setNewPrinterCostPerHour] = useState("");
  const [newPrinterPowerWatts, setNewPrinterPowerWatts] = useState("");
  const [isSavingPrinter, setIsSavingPrinter] = useState(false);

  // --- Peça tab: the pricing form ---
  const [printerId, setPrinterId] = useState("");
  const [pieceName, setPieceName] = useState("");
  const [printTimeHours, setPrintTimeHours] = useState("");
  const [weightG, setWeightG] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [costPerKg, setCostPerKg] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [depreciationMode, setDepreciationMode] = useState<"hora" | "peca">("hora");
  const [depreciationValue, setDepreciationValue] = useState("");
  const [marginPercent, setMarginPercent] = useState("40");
  const [laborHours, setLaborHours] = useState("0");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [selectedQuoteIds, setSelectedQuoteIds] = useState<string[]>([]);

  const load = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const [machinesData, materialsData, profilesData, quotesData] = await Promise.all([
        apiFetch<Machine[]>(`${orgPath}/machines`, { accessToken }),
        apiFetch<Material[]>(`${orgPath}/materials`, { accessToken }),
        apiFetch<CostProfile[]>(`${orgPath}/cost-profiles`, { accessToken }),
        apiFetch<Quote[]>(`${orgPath}/quotes`, { accessToken }),
      ]);
      setMachines(machinesData);
      setMaterials(materialsData);
      setCostProfiles(profilesData);
      setQuotes(quotesData.filter((q) => q.piece_name));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar dados.");
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

  const defaultCostProfile = useMemo(
    () => costProfiles.find((p) => p.is_default) ?? costProfiles[0] ?? null,
    [costProfiles]
  );

  const selectedPrinter = useMemo(
    () => machines.find((m) => m.id === printerId) ?? null,
    [machines, printerId]
  );

  function handlePickPrinter(id: string) {
    setPrinterId(id);
    const printer = machines.find((m) => m.id === id);
    if (printer?.cost_per_hour != null) {
      setDepreciationMode("hora");
      setDepreciationValue(String(printer.cost_per_hour));
    }
  }

  function handlePickMaterial(id: string) {
    setMaterialId(id);
    const material = materials.find((m) => m.id === id);
    if (material?.cost_per_kg != null) {
      setCostPerKg(String(material.cost_per_kg));
    }
  }

  async function handleCreatePrinter(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    setIsSavingPrinter(true);
    setError(null);
    try {
      await apiFetch(`${orgPath}/machines`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({
          name: newPrinterName,
          brand: newPrinterBrand || null,
          model: newPrinterModel || null,
          technology: "FDM",
          cost_per_hour: newPrinterCostPerHour ? Number(newPrinterCostPerHour) : null,
          power_watts: newPrinterPowerWatts ? Number(newPrinterPowerWatts) : null,
        }),
      });
      setShowPrinterForm(false);
      setNewPrinterCostPerHour("");
      setNewPrinterPowerWatts("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar impressora.");
    } finally {
      setIsSavingPrinter(false);
    }
  }

  // --- Live pricing preview (mirrors the backend engine exactly) ---
  const printTimeHoursNum = Number(printTimeHours || 0);
  const weightGNum = Number(weightG || 0);
  const costPerKgNum = Number(costPerKg || 0);
  const quantityNum = Math.max(1, Number(quantity || 1));
  const depreciationValueNum = Number(depreciationValue || 0);
  const marginPercentNum = Number(marginPercent || 0);
  const laborHoursNum = Number(laborHours || 0);

  const machineCostPerHourEffective =
    depreciationMode === "hora"
      ? depreciationValueNum
      : printTimeHoursNum > 0
        ? depreciationValueNum / printTimeHoursNum
        : depreciationValueNum;

  const energyKwh =
    selectedPrinter?.power_watts != null
      ? (selectedPrinter.power_watts / 1000) * printTimeHoursNum
      : 0;

  const materialCost = (weightGNum / 1000) * costPerKgNum;

  const breakdown = defaultCostProfile
    ? calculatePricing(
        {
          materialCost,
          printTimeHours: printTimeHoursNum,
          machineCostPerHour: machineCostPerHourEffective,
          energyKwh,
          laborHours: laborHoursNum,
        },
        {
          energyCostPerKwh: defaultCostProfile.energy_cost_per_kwh,
          laborCostPerHour: defaultCostProfile.labor_cost_per_hour,
          packagingCostFlat: defaultCostProfile.packaging_cost_flat,
          wastePercentage: defaultCostProfile.waste_percentage,
          feesPercentage: defaultCostProfile.fees_percentage,
          profitMarginPercentage: marginPercentNum,
          taxPercentage: defaultCostProfile.tax_percentage ?? 0,
        }
      )
    : null;

  const canSave = Boolean(defaultCostProfile && pieceName.trim() && printTimeHoursNum >= 0);

  async function handleSavePiece() {
    if (!accessToken || !defaultCostProfile || !canSave) return;
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      await apiFetch(`${orgPath}/quotes`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({
          cost_profile_id: defaultCostProfile.id,
          material_cost: materialCost,
          print_time_hours: printTimeHoursNum,
          machine_cost_per_hour: machineCostPerHourEffective,
          energy_kwh: energyKwh,
          labor_hours: laborHoursNum,
          piece_name: pieceName,
          printer_name: selectedPrinter
            ? `${selectedPrinter.name}${selectedPrinter.model ? " " + selectedPrinter.model : ""}`
            : null,
          weight_g: weightGNum || null,
          quantity: quantityNum,
          profit_margin_percentage: marginPercentNum,
        }),
      });
      setMessage("Peça salva na lista.");
      setPieceName("");
      await load();
      setActiveTab("salvas");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar a peça.");
    } finally {
      setIsSaving(false);
    }
  }

  function toggleQuoteSelection(id: string) {
    setSelectedQuoteIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  const selectedQuotes = quotes.filter((q) => selectedQuoteIds.includes(q.id));

  if (status !== "authenticated") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-neutral-400">Carregando…</p>
      </main>
    );
  }

  return (
    <AppShell title="Precificação">
      <div className="print:hidden">
        <div className="mx-auto max-w-4xl space-y-4">
          {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}
          {message && <p className="rounded bg-green-950 p-2 text-sm text-green-300">{message}</p>}

          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <div className="flex gap-1 border-b border-neutral-800">
              {TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`shrink-0 whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                    activeTab === tab.key
                      ? "border-blue-500 text-blue-300"
                      : "border-transparent text-neutral-500 hover:text-neutral-300"
                  }`}
                >
                  {tab.label}
                  {tab.key === "salvas" && quotes.length > 0 ? ` (${quotes.length})` : ""}
                </button>
              ))}
            </div>
          </div>

          {isLoading ? (
            <p className="text-neutral-500">Carregando…</p>
          ) : (
            <>
              {activeTab === "impressora" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-neutral-500">
                      {machines.length} impressora(s) salva(s)
                    </p>
                    <button
                      onClick={() => setShowPrinterForm((v) => !v)}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500"
                    >
                      {showPrinterForm ? "Cancelar" : "+ Nova impressora"}
                    </button>
                  </div>

                  {showPrinterForm && (
                    <form
                      onSubmit={handleCreatePrinter}
                      className="grid gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:grid-cols-2"
                    >
                      <input required placeholder="Nome" value={newPrinterName} onChange={(e) => setNewPrinterName(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
                      <input placeholder="Marca" value={newPrinterBrand} onChange={(e) => setNewPrinterBrand(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
                      <input placeholder="Modelo" value={newPrinterModel} onChange={(e) => setNewPrinterModel(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
                      <input type="number" step="0.01" placeholder="Depreciação por hora (R$)" value={newPrinterCostPerHour} onChange={(e) => setNewPrinterCostPerHour(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2" />
                      <input type="number" step="1" placeholder="Potência (W) — opcional" value={newPrinterPowerWatts} onChange={(e) => setNewPrinterPowerWatts(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2 sm:col-span-2" />
                      <button type="submit" disabled={isSavingPrinter} className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50 sm:col-span-2">
                        {isSavingPrinter ? "Salvando…" : "Salvar impressora"}
                      </button>
                    </form>
                  )}

                  <div className="grid gap-3 sm:grid-cols-2">
                    {machines.length === 0 ? (
                      <p className="text-sm text-neutral-500">
                        Nenhuma impressora salva ainda — cadastre a sua (ex: Bambu Lab A1) acima.
                      </p>
                    ) : (
                      machines.map((m) => (
                        <div key={m.id} className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
                          <p className="font-medium">{m.name}</p>
                          <p className="text-xs text-neutral-500">{m.brand ?? "—"} {m.model ?? ""}</p>
                          <p className="mt-1 text-sm text-neutral-300">
                            {formatCurrency(m.cost_per_hour)}/h de depreciação
                            {m.power_watts ? ` · ${m.power_watts}W` : ""}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {activeTab === "peca" && (
                <div className="space-y-4">
                  {!defaultCostProfile && (
                    <p className="rounded-lg border border-yellow-800 bg-yellow-950/40 px-4 py-3 text-sm text-yellow-300">
                      Cadastre um perfil de custo na aba Calculadora primeiro (energia, taxas de
                      marketplace, etc.) — sem ele não dá pra calcular o preço aqui.
                    </p>
                  )}

                  <div className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 space-y-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="sm:col-span-2">
                        <label className="mb-1 block text-xs text-neutral-500">Impressora</label>
                        <select
                          value={printerId}
                          onChange={(e) => handlePickPrinter(e.target.value)}
                          className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
                        >
                          <option value="">Nenhuma salva (preencher depreciação manualmente)</option>
                          {machines.map((m) => (
                            <option key={m.id} value={m.id}>{m.name} {m.model ?? ""}</option>
                          ))}
                        </select>
                      </div>

                      <div className="sm:col-span-2">
                        <label className="mb-1 block text-xs text-neutral-500">Nome do projeto (peça)</label>
                        <input
                          placeholder='Ex: "Suporte de celular articulado"'
                          value={pieceName}
                          onChange={(e) => setPieceName(e.target.value)}
                          className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
                        />
                      </div>

                      <div>
                        <label className="mb-1 block text-xs text-neutral-500">Tempo de impressão (h)</label>
                        <input type="number" step="0.01" placeholder="Ex: 3.5" value={printTimeHours} onChange={(e) => setPrintTimeHours(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-neutral-500">Quantidade de peças</label>
                        <input type="number" min={1} value={quantity} onChange={(e) => setQuantity(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                      </div>

                      <div>
                        <label className="mb-1 block text-xs text-neutral-500">Peso da peça (g)</label>
                        <input type="number" step="0.1" placeholder="Ex: 25" value={weightG} onChange={(e) => setWeightG(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-neutral-500">Material</label>
                        <select value={materialId} onChange={(e) => handlePickMaterial(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
                          <option value="">Informar custo/kg manualmente</option>
                          {materials.map((m) => (
                            <option key={m.id} value={m.id}>{m.name}</option>
                          ))}
                        </select>
                      </div>

                      <div className="sm:col-span-2">
                        <label className="mb-1 block text-xs text-neutral-500">Custo do material por kg (R$)</label>
                        <input type="number" step="0.01" value={costPerKg} onChange={(e) => setCostPerKg(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                      </div>

                      <div className="sm:col-span-2">
                        <label className="mb-1 block text-xs text-neutral-500">Depreciação da máquina</label>
                        <div className="flex gap-2">
                          <button type="button" onClick={() => setDepreciationMode("hora")} className={`flex-1 rounded border px-3 py-2 text-sm ${depreciationMode === "hora" ? "border-blue-500 bg-blue-950 text-blue-300" : "border-neutral-700 text-neutral-400"}`}>
                            Por hora
                          </button>
                          <button type="button" onClick={() => setDepreciationMode("peca")} className={`flex-1 rounded border px-3 py-2 text-sm ${depreciationMode === "peca" ? "border-blue-500 bg-blue-950 text-blue-300" : "border-neutral-700 text-neutral-400"}`}>
                            Por peça
                          </button>
                          <input
                            type="number"
                            step="0.01"
                            placeholder={depreciationMode === "hora" ? "R$/hora" : "R$/peça"}
                            value={depreciationValue}
                            onChange={(e) => setDepreciationValue(e.target.value)}
                            className="w-28 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
                          />
                        </div>
                      </div>

                      <div className="sm:col-span-2">
                        <label className="mb-1 block text-xs text-neutral-500">Margem de lucro (%)</label>
                        <input type="number" step="0.1" value={marginPercent} onChange={(e) => setMarginPercent(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                      </div>
                    </div>

                    <button type="button" onClick={() => setShowAdvanced((v) => !v)} className="text-xs text-blue-400 hover:underline">
                      {showAdvanced ? "Ocultar avançado" : "Avançado (energia, mão de obra)"}
                    </button>
                    {showAdvanced && (
                      <div className="grid gap-3 border-t border-neutral-800 pt-3 sm:grid-cols-2">
                        <div>
                          <label className="mb-1 block text-xs text-neutral-500">Energia (kWh) — automático se a impressora tiver potência salva</label>
                          <input type="number" value={energyKwh.toFixed(3)} disabled className="w-full rounded border border-neutral-800 bg-neutral-900/50 px-3 py-2 text-sm text-neutral-500" />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs text-neutral-500">Mão de obra (h)</label>
                          <input type="number" step="0.1" value={laborHours} onChange={(e) => setLaborHours(e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
                        </div>
                      </div>
                    )}
                  </div>

                  {breakdown && (
                    <div className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs text-neutral-500">Custo de produção (por peça)</p>
                          <p className="text-xl font-semibold">{formatCurrency(breakdown.productionCost)}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-neutral-500">Preço de venda sugerido</p>
                          <p className="text-xl font-semibold text-green-400">{formatCurrency(breakdown.suggestedPrice)}</p>
                        </div>
                      </div>
                      <p className="mt-2 text-xs text-neutral-500">
                        Total para {quantityNum} peça(s): {formatCurrency(breakdown.suggestedPrice * quantityNum)}
                      </p>
                      <button
                        onClick={handleSavePiece}
                        disabled={!canSave || isSaving}
                        className="mt-3 w-full rounded bg-purple-600 px-4 py-2 font-medium hover:bg-purple-500 disabled:opacity-50"
                      >
                        {isSaving ? "Salvando…" : "Salvar peça calculada"}
                      </button>
                      {!pieceName.trim() && (
                        <p className="mt-1 text-xs text-yellow-300">Dê um nome à peça para poder salvar.</p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {activeTab === "resultado" && (
                <div className="space-y-3">
                  {!breakdown ? (
                    <p className="text-sm text-neutral-500">Preencha a aba Peça primeiro.</p>
                  ) : (
                    <div className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
                      <h2 className="mb-3 text-sm font-medium text-neutral-300">
                        {pieceName || "Peça sem nome"}
                      </h2>
                      <dl className="grid grid-cols-2 gap-y-2 text-sm">
                        <dt className="text-neutral-500">Custo do material</dt>
                        <dd className="text-right">{formatCurrency(breakdown.materialCost)}</dd>
                        <dt className="text-neutral-500">Desperdício</dt>
                        <dd className="text-right">{formatCurrency(breakdown.wasteCost)}</dd>
                        <dt className="text-neutral-500">Energia</dt>
                        <dd className="text-right">{formatCurrency(breakdown.energyCost)}</dd>
                        <dt className="text-neutral-500">Depreciação da máquina</dt>
                        <dd className="text-right">{formatCurrency(breakdown.machineCost)}</dd>
                        <dt className="text-neutral-500">Mão de obra</dt>
                        <dd className="text-right">{formatCurrency(breakdown.laborCost)}</dd>
                        <dt className="text-neutral-500">Embalagem</dt>
                        <dd className="text-right">{formatCurrency(breakdown.packagingCost)}</dd>
                        <dt className="text-neutral-500">Taxas (marketplace/pagamento)</dt>
                        <dd className="text-right">{formatCurrency(breakdown.fees)}</dd>
                        <dt className="border-t border-neutral-800 pt-2 font-medium text-neutral-300">Custo de produção</dt>
                        <dd className="border-t border-neutral-800 pt-2 text-right font-medium">{formatCurrency(breakdown.productionCost)}</dd>
                        <dt className="text-neutral-500">Imposto</dt>
                        <dd className="text-right">{formatCurrency(breakdown.taxAmount)}</dd>
                        <dt className="font-medium text-green-400">Preço de venda sugerido</dt>
                        <dd className="text-right font-medium text-green-400">{formatCurrency(breakdown.suggestedPrice)}</dd>
                      </dl>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "salvas" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-neutral-500">{quotes.length} peça(s) salva(s)</p>
                    <button
                      onClick={() => window.print()}
                      disabled={selectedQuoteIds.length === 0}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium disabled:opacity-40"
                    >
                      Gerar resumo / Imprimir ({selectedQuoteIds.length})
                    </button>
                  </div>

                  <div className="overflow-x-auto rounded-xl border border-neutral-800">
                    <table className="w-full min-w-[700px] text-left text-sm">
                      <thead className="border-b border-neutral-800 bg-neutral-950/50 text-neutral-400">
                        <tr>
                          <th className="px-3 py-3"></th>
                          <th className="px-3 py-3 font-medium">Peça</th>
                          <th className="px-3 py-3 font-medium">Impressora</th>
                          <th className="px-3 py-3 font-medium">Peso</th>
                          <th className="px-3 py-3 font-medium">Qtd.</th>
                          <th className="px-3 py-3 font-medium">Custo</th>
                          <th className="px-3 py-3 font-medium">Preço</th>
                          <th className="px-3 py-3 font-medium">Salva em</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-800">
                        {quotes.length === 0 ? (
                          <tr>
                            <td colSpan={8} className="px-3 py-6 text-center text-neutral-500">
                              Nenhuma peça salva ainda — calcule uma na aba Peça.
                            </td>
                          </tr>
                        ) : (
                          quotes.map((q) => (
                            <tr key={q.id} className="hover:bg-neutral-900/50">
                              <td className="px-3 py-3">
                                <input
                                  type="checkbox"
                                  checked={selectedQuoteIds.includes(q.id)}
                                  onChange={() => toggleQuoteSelection(q.id)}
                                  className="rounded border-neutral-700"
                                />
                              </td>
                              <td className="px-3 py-3">{q.piece_name}</td>
                              <td className="px-3 py-3">{q.printer_name ?? "—"}</td>
                              <td className="px-3 py-3">{q.weight_g != null ? `${q.weight_g}g` : "—"}</td>
                              <td className="px-3 py-3">{q.quantity}</td>
                              <td className="px-3 py-3">{formatCurrency(q.production_cost)}</td>
                              <td className="px-3 py-3 font-medium text-green-400">{formatCurrency(q.suggested_price)}</td>
                              <td className="px-3 py-3 text-neutral-500">{formatDateTime(q.created_at)}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Printable summary — invisible on screen, shown only via window.print() */}
      <div className="hidden print:block print:bg-white print:p-8 print:text-black">
        <h1 className="mb-4 text-xl font-bold">Resumo de Precificação</h1>
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-black">
              <th className="py-2 text-left">Peça</th>
              <th className="py-2 text-left">Impressora</th>
              <th className="py-2 text-right">Peso</th>
              <th className="py-2 text-right">Qtd.</th>
              <th className="py-2 text-right">Custo/un.</th>
              <th className="py-2 text-right">Preço/un.</th>
              <th className="py-2 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {selectedQuotes.map((q) => (
              <tr key={q.id} className="border-b border-neutral-400">
                <td className="py-2">{q.piece_name}</td>
                <td className="py-2">{q.printer_name ?? "—"}</td>
                <td className="py-2 text-right">{q.weight_g != null ? `${q.weight_g}g` : "—"}</td>
                <td className="py-2 text-right">{q.quantity}</td>
                <td className="py-2 text-right">{formatCurrency(q.production_cost)}</td>
                <td className="py-2 text-right">{formatCurrency(q.suggested_price)}</td>
                <td className="py-2 text-right font-medium">
                  {formatCurrency(q.suggested_price * q.quantity)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-6 text-xs text-neutral-600">
          Gerado em {new Date().toLocaleString("pt-BR")}
        </p>
      </div>
    </AppShell>
  );
}
