export type PricingInputs = {
  materialCost: number;
  printTimeHours: number;
  machineCostPerHour: number;
  energyKwh: number;
  laborHours: number;
};

export type PricingProfile = {
  energyCostPerKwh: number;
  laborCostPerHour: number;
  packagingCostFlat: number;
  wastePercentage: number;
  feesPercentage: number;
  profitMarginPercentage: number;
  taxPercentage: number;
};

export type PricingBreakdown = {
  materialCost: number;
  wasteCost: number;
  energyCost: number;
  machineCost: number;
  laborCost: number;
  packagingCost: number;
  fees: number;
  productionCost: number;
  taxAmount: number;
  suggestedPrice: number;
};

/** Mirrors apps/api/src/domain/calculator/engine.py exactly, for instant

 * client-side preview — the authoritative calculation still happens
 * server-side when the piece is saved (POST /quotes).
 */
export function calculatePricing(inputs: PricingInputs, profile: PricingProfile): PricingBreakdown {
  const materialWithWaste = inputs.materialCost * (1 + profile.wastePercentage / 100);
  const wasteCost = materialWithWaste - inputs.materialCost;

  const energyCost = inputs.energyKwh * profile.energyCostPerKwh;
  const machineCost = inputs.printTimeHours * inputs.machineCostPerHour;
  const laborCost = inputs.laborHours * profile.laborCostPerHour;
  const packagingCost = profile.packagingCostFlat;

  const subtotal = materialWithWaste + energyCost + machineCost + laborCost + packagingCost;
  const fees = subtotal * (profile.feesPercentage / 100);
  const productionCost = subtotal + fees;

  const priceBeforeTax = productionCost * (1 + profile.profitMarginPercentage / 100);
  const taxAmount = priceBeforeTax * (profile.taxPercentage / 100);
  const suggestedPrice = priceBeforeTax + taxAmount;

  return {
    materialCost: inputs.materialCost,
    wasteCost,
    energyCost,
    machineCost,
    laborCost,
    packagingCost,
    fees,
    productionCost,
    taxAmount,
    suggestedPrice,
  };
}
