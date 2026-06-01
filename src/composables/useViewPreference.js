import { ref, watch } from 'vue'

// Remembers whether the collection editor shows items as a ranked LIST or a
// poster GRID. Persisted to localStorage so the choice sticks across sessions.
const STORAGE_KEY = 'collection_view_mode'

const stored = (() => {
  try { return localStorage.getItem(STORAGE_KEY) } catch { return null }
})()

// Module-level singleton so every component shares (and stays in sync on) the choice.
const viewMode = ref(stored === 'grid' || stored === 'list' ? stored : 'list')

watch(viewMode, (v) => {
  try { localStorage.setItem(STORAGE_KEY, v) } catch { /* ignore */ }
})

export function useViewPreference() {
  const setView = (v) => { if (v === 'grid' || v === 'list') viewMode.value = v }
  return { viewMode, setView }
}
