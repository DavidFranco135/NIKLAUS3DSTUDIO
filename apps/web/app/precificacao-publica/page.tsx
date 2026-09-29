"use client";

import { useEffect, useState } from "react";
import { formatCurrency } from "@/lib/format";
import { calculatePricing } from "@/lib/pricing";

function CostBreakdownList({ breakdown }: { breakdown: ReturnType<typeof calculatePricing> }) {
  return (
    <dl className="grid grid-cols-2 gap-y-2 text-sm">
      <dt className="text-neutral-500">Material + itens adicionais</dt>
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
  );
}

type ExtraItem = { name: string; cost: string };

type StoredState = {
  pieceName: string;
  printerName: string;
  printerPowerWatts: string;
  printTimeHours: string;
  weightG: string;
  quantity: string;
  costPerKg: string;
  extraItems: ExtraItem[];
  depreciationMode: "hora" | "peca";
  depreciationValue: string;
  laborHours: string;
  energyCostPerKwh: string;
  laborCostPerHour: string;
  packagingCostFlat: string;
  wastePct: string;
  feesPct: string;
  marginPct: string;
  taxPct: string;
};

const STORAGE_KEY = "precificacao-publica-v1";

const DEFAULTS: StoredState = {
  pieceName: "",
  printerName: "",
  printerPowerWatts: "",
  printTimeHours: "",
  weightG: "",
  quantity: "1",
  costPerKg: "",
  extraItems: [],
  depreciationMode: "hora",
  depreciationValue: "",
  laborHours: "0",
  energyCostPerKwh: "1.10",
  laborCostPerHour: "20",
  packagingCostFlat: "2",
  wastePct: "5",
  feesPct: "0",
  marginPct: "40",
  taxPct: "0",
};

export default function PrecificacaoPublicaPage() {
  const [state, setState] = useState<StoredState>(DEFAULTS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setState({ ...DEFAULTS, ...JSON.parse(raw) });
    } catch {
      // ignore — start from defaults
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // ignore — localStorage may be unavailable (private mode, etc.)
    }
  }, [state, hydrated]);

  function set<K extends keyof StoredState>(key: K, value: StoredState[K]) {
    setState((prev) => ({ ...prev, [key]: value }));
  }

  function addExtraItem() {
    setState((prev) => ({ ...prev, extraItems: [...prev.extraItems, { name: "", cost: "" }] }));
  }

  function updateExtraItem(index: number, patch: Partial<ExtraItem>) {
    setState((prev) => ({
      ...prev,
      extraItems: prev.extraItems.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    }));
  }

  function removeExtraItem(index: number) {
    setState((prev) => ({ ...prev, extraItems: prev.extraItems.filter((_, i) => i !== index) }));
  }

  const printTimeHoursNum = Number(state.printTimeHours || 0);
  const weightGNum = Number(state.weightG || 0);
  const costPerKgNum = Number(state.costPerKg || 0);
  const quantityNum = Math.max(1, Number(state.quantity || 1));
  const depreciationValueNum = Number(state.depreciationValue || 0);
  const laborHoursNum = Number(state.laborHours || 0);
  const powerWattsNum = Number(state.printerPowerWatts || 0);

  const machineCostPerHourEffective =
    state.depreciationMode === "hora"
      ? depreciationValueNum
      : printTimeHoursNum > 0
        ? depreciationValueNum / printTimeHoursNum
        : depreciationValueNum;

  const energyKwh = powerWattsNum > 0 ? (powerWattsNum / 1000) * printTimeHoursNum : 0;

  const extraItemsCost = state.extraItems.reduce((sum, item) => sum + (Number(item.cost) || 0), 0);
  const materialCost = (weightGNum / 1000) * costPerKgNum + extraItemsCost;

  const breakdown = calculatePricing(
    {
      materialCost,
      printTimeHours: printTimeHoursNum,
      machineCostPerHour: machineCostPerHourEffective,
      energyKwh,
      laborHours: laborHoursNum,
    },
    {
      energyCostPerKwh: Number(state.energyCostPerKwh || 0),
      laborCostPerHour: Number(state.laborCostPerHour || 0),
      packagingCostFlat: Number(state.packagingCostFlat || 0),
      wastePercentage: Number(state.wastePct || 0),
      feesPercentage: Number(state.feesPct || 0),
      profitMarginPercentage: Number(state.marginPct || 0),
      taxPercentage: Number(state.taxPct || 0),
    }
  );

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <div className="print:hidden">
        <header className="border-b border-neutral-800 px-4 py-4 sm:px-6">
          <div className="mx-auto max-w-4xl">
            <h1 className="text-lg font-semibold">Calculadora de Precificação — 3D AI Studio</h1>
            <p className="text-sm text-neutral-500">
              Preencha os custos abaixo para calcular o preço de venda sugerido de uma peça impressa em 3D.
            </p>
          </div>
        </header>

        <main className="mx-auto max-w-4xl space-y-6 p-4 sm:p-6">
          <section className="space-y-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
            <h2 className="text-sm font-medium text-neutral-300">Custos gerais (energia, mão de obra, taxas)</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Energia (R$/kWh)</label>
                <input type="number" step="0.01" value={state.energyCostPerKwh} onChange={(e) => set("energyCostPerKwh", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Mão de obra (R$/hora)</label>
                <input type="number" step="0.01" value={state.laborCostPerHour} onChange={(e) => set("laborCostPerHour", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Embalagem fixa (R$)</label>
                <input type="number" step="0.01" value={state.packagingCostFlat} onChange={(e) => set("packagingCostFlat", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Desperdício de material (%)</label>
                <input type="number" step="0.1" value={state.wastePct} onChange={(e) => set("wastePct", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Taxas de marketplace/pagamento (%)</label>
                <input type="number" step="0.1" value={state.feesPct} onChange={(e) => set("feesPct", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Margem de lucro (%)</label>
                <input type="number" step="0.1" value={state.marginPct} onChange={(e) => set("marginPct", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Imposto (%)</label>
                <input type="number" step="0.1" value={state.taxPct} onChange={(e) => set("taxPct", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
            </div>
          </section>

          <section className="space-y-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
            <h2 className="text-sm font-medium text-neutral-300">Impressora e peça</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs text-neutral-500">Nome do projeto (peça)</label>
                <input placeholder='Ex: "Suporte de celular articulado"' value={state.pieceName} onChange={(e) => set("pieceName", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Impressora (nome/modelo)</label>
                <input placeholder="Ex: Bambu Lab A1" value={state.printerName} onChange={(e) => set("printerName", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Potência da impressora (W) — opcional, calcula a energia automaticamente</label>
                <input type="number" step="1" placeholder="Ex: 350" value={state.printerPowerWatts} onChange={(e) => set("printerPowerWatts", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Tempo de impressão (h)</label>
                <input type="number" step="0.01" placeholder="Ex: 3.5" value={state.printTimeHours} onChange={(e) => set("printTimeHours", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Quantidade de peças</label>
                <input type="number" min={1} value={state.quantity} onChange={(e) => set("quantity", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Peso da peça (g)</label>
                <input type="number" step="0.1" placeholder="Ex: 25" value={state.weightG} onChange={(e) => set("weightG", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Custo do filamento por kg (R$)</label>
                <input type="number" step="0.01" placeholder="Ex: 89.90" value={state.costPerKg} onChange={(e) => set("costPerKg", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>

              <div className="sm:col-span-2 space-y-2">
                <label className="block text-xs text-neutral-500">Itens adicionais (embalagem, argola, etiqueta, etc.)</label>
                {state.extraItems.map((item, index) => (
                  <div key={index} className="flex flex-col gap-2 sm:flex-row">
                    <input
                      placeholder="Nome (ex: Embalagem)"
                      value={item.name}
                      onChange={(e) => updateExtraItem(index, { name: e.target.value })}
                      className="w-full min-w-0 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm sm:flex-1"
                    />
                    <div className="flex gap-2">
                      <input
                        type="number"
                        step="0.01"
                        placeholder="Custo (R$)"
                        value={item.cost}
                        onChange={(e) => updateExtraItem(index, { cost: e.target.value })}
                        className="w-full min-w-0 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm sm:w-28"
                      />
                      <button
                        type="button"
                        onClick={() => removeExtraItem(index)}
                        className="shrink-0 rounded border border-neutral-700 px-3 py-2 text-sm text-neutral-400 hover:border-red-700 hover:text-red-400"
                      >
                        Remover
                      </button>
                    </div>
                  </div>
                ))}
                <button type="button" onClick={addExtraItem} className="text-sm text-blue-400 hover:underline">
                  + Adicionar item
                </button>
              </div>

              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs text-neutral-500">Depreciação da máquina</label>
                <div className="flex gap-2">
                  <button type="button" onClick={() => set("depreciationMode", "hora")} className={`flex-1 rounded border px-3 py-2 text-sm ${state.depreciationMode === "hora" ? "border-blue-500 bg-blue-950 text-blue-300" : "border-neutral-700 text-neutral-400"}`}>
                    Por hora
                  </button>
                  <button type="button" onClick={() => set("depreciationMode", "peca")} className={`flex-1 rounded border px-3 py-2 text-sm ${state.depreciationMode === "peca" ? "border-blue-500 bg-blue-950 text-blue-300" : "border-neutral-700 text-neutral-400"}`}>
                    Por peça
                  </button>
                  <input
                    type="number"
                    step="0.01"
                    placeholder={state.depreciationMode === "hora" ? "R$/hora" : "R$/peça"}
                    value={state.depreciationValue}
                    onChange={(e) => set("depreciationValue", e.target.value)}
                    className="w-28 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs text-neutral-500">Mão de obra (horas)</label>
                <input type="number" step="0.1" value={state.laborHours} onChange={(e) => set("laborHours", e.target.value)} className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-neutral-500">Energia (kWh) — automático se a potência foi informada</label>
                <input type="number" value={energyKwh.toFixed(3)} disabled className="w-full rounded border border-neutral-800 bg-neutral-900/50 px-3 py-2 text-sm text-neutral-500" />
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs text-neutral-500">Custo de produção (por peça)</p>
                <p className="text-xl font-semibold">{formatCurrency(breakdown.productionCost)}</p>
              </div>
              <div className="sm:text-right">
                <p className="text-xs text-neutral-500">Preço de venda sugerido</p>
                <p className="text-xl font-semibold text-green-400">{formatCurrency(breakdown.suggestedPrice)}</p>
              </div>
            </div>
            <p className="mt-2 text-xs text-neutral-500">
              Total para {quantityNum} peça(s): {formatCurrency(breakdown.suggestedPrice * quantityNum)}
            </p>

            <div className="mt-4 border-t border-neutral-800 pt-4">
              <h3 className="mb-2 text-xs font-medium text-neutral-400">Resumo dos custos</h3>
              <CostBreakdownList breakdown={breakdown} />
            </div>

            <button
              onClick={() => window.print()}
              className="mt-4 w-full rounded bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500"
            >
              Imprimir / gerar PDF
            </button>
          </section>

          <p className="text-center text-xs text-neutral-600">
            Calculadora pública e independente — os valores digitados aqui ficam salvos só neste
            navegador e não são enviados a nenhuma conta.
          </p>
        </main>
      </div>

      <div className="hidden print:block print:bg-white print:p-8 print:text-black">
        <h1 className="mb-1 text-xl font-bold">{state.pieceName || "Peça sem nome"}</h1>
        <p className="mb-4 text-sm text-neutral-700">
          {state.printerName || "—"} · {state.weightG ? `${state.weightG}g` : "—"} · {quantityNum} peça(s)
        </p>
        <table className="w-full border-collapse text-sm">
          <tbody>
            <tr className="border-b border-neutral-400">
              <td className="py-2">Material + itens adicionais</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.materialCost)}</td>
            </tr>
            <tr className="border-b border-neutral-400">
              <td className="py-2">Desperdício</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.wasteCost)}</td>
            </tr>
            <tr className="border-b border-neutral-400">
              <td className="py-2">Energia</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.energyCost)}</td>
            </tr>
            <tr className="border-b border-neutral-400">
              <td className="py-2">Depreciação da máquina</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.machineCost)}</td>
            </tr>
            <tr className="border-b border-neutral-400">
              <td className="py-2">Mão de obra</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.laborCost)}</td>
            </tr>
            <tr className="border-b border-neutral-400">
              <td className="py-2">Embalagem</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.packagingCost)}</td>
            </tr>
            <tr className="border-b border-neutral-400">
              <td className="py-2">Taxas</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.fees)}</td>
            </tr>
            <tr className="border-b-2 border-black font-medium">
              <td className="py-2">Custo de produção</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.productionCost)}</td>
            </tr>
            <tr className="border-b border-neutral-400">
              <td className="py-2">Imposto</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.taxAmount)}</td>
            </tr>
            <tr className="font-bold">
              <td className="py-2">Preço de venda sugerido (un.)</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.suggestedPrice)}</td>
            </tr>
            <tr className="font-bold">
              <td className="py-2">Total ({quantityNum} peça(s))</td>
              <td className="py-2 text-right">{formatCurrency(breakdown.suggestedPrice * quantityNum)}</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-6 text-xs text-neutral-600">Gerado em {new Date().toLocaleString("pt-BR")}</p>
      </div>
    </div>
  );
}
