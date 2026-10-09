export const SIGNALS = ['price', 'photo', 'complaints', 'account', 'community']

export const SIGNAL_TITLES = {
  price: 'Price',
  photo: 'Photo',
  complaints: 'Complaints',
  account: 'Account',
  community: 'Community',
}

export const SEVERITY_LABELS = {
  good: 'Good',
  info: 'Note',
  warn: 'Caution',
  bad: 'Red flag',
}

export const OUTCOME_LABELS = {
  delivered: 'Delivered as described',
  not_delivered: 'Paid but not delivered',
  differs: 'Product differs from the photo',
  other: 'Other',
}

export function rupees(n) {
  if (n === null || n === undefined) return ''
  return `Rs ${Number(n).toLocaleString('en-IN')}`
}

export function count(n) {
  if (n === null || n === undefined) return 'unknown'
  return Number(n).toLocaleString('en-IN')
}

export function domainOf(url) {
  if (!url || url.startsWith('/')) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

// The API sends naive UTC timestamps.
export function formatDate(value, withTime = true) {
  if (!value) return ''
  const iso = /[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('en-IN', withTime ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium' })
}

export function plural(n, word, many = `${word}s`) {
  return `${n} ${n === 1 ? word : many}`
}
