export const USD_TO_INR = 83.5;

export function formatINR(usdAmount: number | null | undefined, decimals = 4): string {
  if (usdAmount === null || usdAmount === undefined) return 'NULL (Unknown)';
  const inrAmount = Number(usdAmount) * USD_TO_INR;
  return `₹${inrAmount.toFixed(decimals)}`;
}

export function formatINRShort(usdAmount: number | null | undefined, decimals = 2): string {
  if (usdAmount === null || usdAmount === undefined) return '₹0.00';
  const inrAmount = Number(usdAmount) * USD_TO_INR;
  return `₹${inrAmount.toFixed(decimals)}`;
}

export function formatUSD(usdAmount: number | null | undefined, decimals = 4): string {
  if (usdAmount === null || usdAmount === undefined) return '$0.00';
  return `$${Number(usdAmount).toFixed(decimals)}`;
}
