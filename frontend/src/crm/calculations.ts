export function quoteTotals(
  unitPrice: number,
  quantity: number,
  months: number,
  discount: number,
  setupFee: number,
) {
  const monthly =
    Math.round((unitPrice * quantity * (1 - discount / 100) + Number.EPSILON) * 100) / 100
  const total = Math.round((monthly * months + setupFee + Number.EPSILON) * 100) / 100
  return {
    monthly,
    total,
    firstMonth: Math.round((monthly + setupFee + Number.EPSILON) * 100) / 100,
  }
}

export function boundedNumber(
  value: string,
  minimum: number,
  maximum: number,
  integer = false,
): number | null {
  if (!value.trim()) return null
  const number = Number(value)
  return Number.isFinite(number) &&
    number >= minimum &&
    number <= maximum &&
    (!integer || Number.isInteger(number))
    ? number
    : null
}
