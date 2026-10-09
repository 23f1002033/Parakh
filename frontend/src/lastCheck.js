// The last submitted form, kept in memory only, so a failed check can be sent again.
let last = null

export function rememberCheck(id, form) {
  last = { id, form }
}

export function formFor(id) {
  return last && last.id === id ? last.form : null
}
