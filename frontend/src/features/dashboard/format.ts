export function formatMoney(value: number | null): string {
  if (value === null) return '—'
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function formatQuantity(value: number | null): string {
  if (value === null) return '—'
  return value.toLocaleString(undefined, { maximumFractionDigits: 8 })
}

export function formatDateTime(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

export function symbolLabel(symbol: { ticker: string } | null): string {
  return symbol?.ticker ?? '—'
}

export function pnlClass(value: number | null): string {
  if (value === null) return ''
  return value >= 0 ? 'positive' : 'negative'
}
