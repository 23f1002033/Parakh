const UNREACHABLE = 'Could not reach the Parakh server. Check your connection and try again.'

async function request(path, options = {}) {
  let res
  try {
    res = await fetch(`/api${path}`, options)
  } catch {
    throw new Error(UNREACHABLE)
  }
  let body = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) {
    // A proxy or gateway error has no Parakh error body: treat it as the server being down.
    const fallback = res.status >= 500 && !body ? UNREACHABLE : `Request failed (${res.status})`
    const err = new Error(body?.error?.message || fallback)
    err.status = res.status
    throw err
  }
  return body
}

export const getJson = (path) => request(path)

export const postJson = (path, data) =>
  request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const postForm = (path, form) => request(path, { method: 'POST', body: form })

export async function getDemoImage(demo) {
  const res = await fetch(demo.image_path)
  if (!res.ok) throw new Error('Could not load the demo photo.')
  const blob = await res.blob()
  return new File([blob], demo.image, { type: blob.type || 'image/png' })
}
