async function request(path, options = {}) {
  let res
  try {
    res = await fetch(`/api${path}`, options)
  } catch {
    throw new Error('Could not reach the Parakh server. Check your connection and try again.')
  }
  let body = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) {
    const err = new Error(body?.error?.message || `Request failed (${res.status})`)
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
