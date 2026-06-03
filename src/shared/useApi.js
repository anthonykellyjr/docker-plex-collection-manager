import { ref } from 'vue'

// API base. Defaults to /capi (app served at the domain root). Set VITE_API_BASE
// to serve the app under a subpath, e.g. /demos/collection-manager/capi.
const API_BASE = (import.meta.env.VITE_API_BASE || '/capi').replace(/\/$/, '')

// Rewrite a "/capi/..." path onto the configured base. Both our own calls and the
// backend-built poster URLs start with /capi, so this covers both.
export function apiUrl(path) {
  return path && path.startsWith('/capi') ? API_BASE + path.slice(5) : path
}

export function useApi({ storageKey, headerName }) {
  const authKey = ref(localStorage.getItem(storageKey) || '')

  const setAuthKey = (key) => {
    authKey.value = key
    localStorage.setItem(storageKey, key)
  }

  const clearAuthKey = () => {
    authKey.value = ''
    localStorage.removeItem(storageKey)
  }

  const apiFetch = async (path, options = {}) => {
    // For FormData (file uploads) let the browser set the multipart boundary,
    // so only force a JSON content-type for everything else.
    const isForm = typeof FormData !== 'undefined' && options.body instanceof FormData
    const res = await fetch(apiUrl(path), {
      ...options,
      headers: {
        ...(isForm ? {} : { 'Content-Type': 'application/json' }),
        [headerName]: authKey.value,
        ...(options.headers || {}),
      },
    })
    if (res.status === 401) {
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.error || `API error: ${res.status}`)
    }
    return res.json()
  }

  return { authKey, setAuthKey, clearAuthKey, apiFetch }
}
