<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import { useApi } from '../composables/useApi.js'
import PosterCard from './PosterCard.vue'

const props = defineProps({
  collectionKey: { type: String, required: true },
  libraryKey: { type: String, required: true },
})

const emit = defineEmits(['back', 'saved', 'deleted', 'toast'])

const { apiFetch } = useApi()

// ── Collection data ──
const collection = ref(null)
const items = ref([])
const originalKeys = ref(new Set())
const originalItems = ref([])             // ordered snapshot of last-saved items, for Cancel/discard
const originalTitle = ref('')
const originalSummary = ref('')
const title = ref('')
const summary = ref('')
const isLoading = ref(true)
const isReloading = ref(false)            // spinner state for the Reload button
const isSaving = ref(false)
const hasChanges = ref(false)
const autoSavePending = ref(false)        // a debounce timer is currently armed
const justSaved = ref(false)              // brief 'Saved' pill after a successful auto-save

// ── Save progress modal (shown for BOTH manual and auto saves) ──
const saveOverlay = ref(false)
const saveElapsed = ref(0)
const saveResult = ref(null)
let elapsedTimer = null
let autoCloseTimer = null    // auto-dismiss the modal after an auto-save

// ── Leave guard (custom unsaved-changes confirm for in-app back nav) ──
const leaveGuard = ref(false)

// ── Auto-save plumbing ──
// Long enough to coalesce a flurry of reorders/edits into ONE save to Plex
// (reorder PUTs are heavy), short enough to still feel automatic once the user stops.
const AUTO_SAVE_DEBOUNCE_MS = 1500
let autoSaveTimer = null
// Set when a mutation lands while a save is in flight, so we can re-arm afterward
// instead of silently dropping it.
let changedDuringSave = false
// Set while we programmatically revert fields (Cancel) so the title/summary
// watchers don't re-mark the form dirty during the revert.
let reverting = false

// Template ref for the collection-name input — used by the pencil-icon click handler.
const titleInput = ref(null)

// Brief "Saved" confirmation shown in the header status pill. The pill lives in the
// top bar (fixed slot), so flipping it does NOT shift the poster grid below.
let savedTimer = null
const flagSaved = () => {
  justSaved.value = true
  if (savedTimer) clearTimeout(savedTimer)
  savedTimer = setTimeout(() => { justSaved.value = false }, 2500)
}

// ── Search ──
const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)

// ── State ──
const itemKeys = computed(() => new Set(items.value.map(i => i.ratingKey)))
const isKometa = computed(() => collection.value?.kometaManaged || false)
const isSmart = computed(() => collection.value?.smart || false)
const canSave = computed(() => title.value.trim() && items.value.length > 0 && hasChanges.value && !isSmart.value)
// Anything not yet persisted — drives the leave guard + the native unload prompt.
const hasUnsaved = computed(() => hasChanges.value || autoSavePending.value || isSaving.value)

const adminKey = computed(() => localStorage.getItem('collection_manager_admin_key') || '')

// ── Pending changes summary ──
const pendingChanges = computed(() => {
  const currentKeys = new Set(items.value.map(i => i.ratingKey))
  const adding = items.value.filter(i => !originalKeys.value.has(i.ratingKey)).length
  const removing = [...originalKeys.value].filter(k => !currentKeys.has(k)).length
  const totalItems = items.value.length
  return { adding, removing, totalItems }
})

// ── Load collection ──
// Pure fetch: populates state and resets the dirty baseline. Returns true on
// success. Does NOT touch isLoading or emit toasts — callers own that UX.
const fetchCollection = async () => {
  try {
    const data = await apiFetch(`/capi/collections/${props.collectionKey}/items`)
    collection.value = data.collection
    items.value = data.items || []
    originalItems.value = [...(data.items || [])]
    originalKeys.value = new Set((data.items || []).map(i => i.ratingKey))
    title.value = data.collection.title || ''
    summary.value = data.collection.summary || ''
    originalTitle.value = title.value
    originalSummary.value = summary.value
    hasChanges.value = false
    return true
  } catch (err) {
    return false
  }
}

const loadCollection = async () => {
  isLoading.value = true
  const ok = await fetchCollection()
  isLoading.value = false
  if (!ok) emit('toast', 'Failed to load collection', 'error')
}

// Native browser guard for hard unloads (tab close / refresh / typing a new URL).
// The browser shows its OWN dialog here — its text can't be customized and it can't
// be replaced with our modal. Our custom modal only covers in-app back navigation.
const onBeforeUnload = (e) => {
  if (hasUnsaved.value) { e.preventDefault(); e.returnValue = '' }
}

onMounted(() => {
  loadCollection()
  window.addEventListener('beforeunload', onBeforeUnload)
})

onUnmounted(() => {
  if (elapsedTimer) clearInterval(elapsedTimer)
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  if (savedTimer) clearTimeout(savedTimer)
  if (autoCloseTimer) clearTimeout(autoCloseTimer)
  window.removeEventListener('beforeunload', onBeforeUnload)
})

// Mark the form dirty WITHOUT scheduling an auto-save. Reordering uses this — the
// user must persist a reorder with an explicit Save press.
const markDirty = () => {
  hasChanges.value = true
  justSaved.value = false
  if (isSaving.value) changedDuringSave = true
}

// Mark dirty AND arm/reset the auto-save debounce timer. Used by title, summary,
// add and remove — everything except reorder auto-saves.
const markChanged = () => {
  markDirty()
  scheduleAutoSave()
}

const scheduleAutoSave = () => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSavePending.value = false
  if (isLoading.value || isSaving.value || isSmart.value) return
  autoSavePending.value = true
  console.debug('[collection-manager] auto-save armed for', AUTO_SAVE_DEBOUNCE_MS, 'ms')
  autoSaveTimer = setTimeout(() => {
    autoSavePending.value = false
    console.debug('[collection-manager] auto-save timer fired', {
      canSave: canSave.value, hasChanges: hasChanges.value, isSaving: isSaving.value,
    })
    if (canSave.value && hasChanges.value && !isSaving.value) {
      save({ mode: 'auto' })
    }
  }, AUTO_SAVE_DEBOUNCE_MS)
}

// Build a short human label for the event we just saved (used in toast + modal).
// pendingChanges() is computed BEFORE the save() call zeroes hasChanges,
// so capture it eagerly when save() starts.
const describeEvent = (snapshot) => {
  const titleChanged = title.value.trim() !== originalTitle.value
  const summaryChanged = summary.value.trim() !== originalSummary.value
  const { adding, removing } = snapshot
  const parts = []
  if (adding > 0)    parts.push(`+${adding} item${adding !== 1 ? 's' : ''}`)
  if (removing > 0)  parts.push(`-${removing} item${removing !== 1 ? 's' : ''}`)
  if (titleChanged)   parts.push('renamed')
  if (summaryChanged) parts.push('description')
  if (!parts.length) parts.push('reordered')
  return parts.join(' · ')
}

// ── Search library ──
let searchTimer = null
watch(searchQuery, (q) => {
  clearTimeout(searchTimer)
  if (!q.trim()) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    isSearching.value = true
    try {
      const data = await apiFetch(`/capi/libraries/${props.libraryKey}/items?search=${encodeURIComponent(q)}&size=20`)
      searchResults.value = data.items || []
    } catch {
      searchResults.value = []
    } finally {
      isSearching.value = false
    }
  }, 300)
})

// ── Actions ──
const addItem = (item) => {
  if (itemKeys.value.has(item.ratingKey)) return
  items.value = [...items.value, item]
  markChanged()
}

const removeItem = (item) => {
  items.value = items.value.filter(i => i.ratingKey !== item.ratingKey)
  markChanged()
}

const onDragEnd = (e) => {
  // Ignore no-op drags (picked up and dropped back in the same slot).
  if (e && e.oldIndex === e.newIndex) return
  // Reorder is dirty but does NOT auto-save — the user must click Save.
  markDirty()
}

// Two modes, both surface the SAME modal so every save is unmistakable:
//   'explicit' — Save button. Success modal stays until the user clicks Done.
//   'auto'     — debounced auto-save. Success modal auto-dismisses after a beat.
const save = async ({ mode = 'explicit' } = {}) => {
  if (!canSave.value) {
    console.debug('[save] skipped — canSave is false', {
      title: title.value.trim(), items: items.value.length,
      hasChanges: hasChanges.value, isSmart: isSmart.value,
    })
    return
  }

  // If the user clicked Save while a debounce was pending, cancel the timer —
  // the explicit save covers it.
  if (autoSaveTimer) { clearTimeout(autoSaveTimer); autoSaveTimer = null }
  autoSavePending.value = false

  // Snapshot what's about to change so we can describe the event AFTER save zeroes hasChanges.
  const snapshot = { ...pendingChanges.value }
  const eventName = describeEvent(snapshot)
  const collectionTitle = title.value.trim() || 'collection'

  console.debug('[save] start', { mode, eventName, collectionTitle, snapshot })

  isSaving.value = true
  changedDuringSave = false
  if (autoCloseTimer) { clearTimeout(autoCloseTimer); autoCloseTimer = null }
  saveOverlay.value = true
  saveElapsed.value = 0
  saveResult.value = null

  const startTime = Date.now()
  elapsedTimer = setInterval(() => {
    saveElapsed.value = ((Date.now() - startTime) / 1000).toFixed(1)
  }, 100)

  // Snapshot exactly what we're sending so post-save state matches the PUT body,
  // not whatever the user mutated while the request was in flight.
  const savedItems = [...items.value]
  const savedKeys = items.value.map(i => i.ratingKey)
  const savedTitle = title.value.trim()
  const savedSummary = summary.value.trim()

  try {
    const res = await apiFetch(`/capi/collections/${props.collectionKey}`, {
      method: 'PUT',
      body: JSON.stringify({
        title: savedTitle,
        summary: savedSummary,
        itemKeys: savedKeys,
      }),
    })
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null }
    saveElapsed.value = elapsed
    const stats = res.stats || {}

    console.debug('[save] success', { mode, elapsed, stats })

    saveResult.value = {
      success: true,
      auto: mode === 'auto',
      eventName,
      collectionTitle,
      stats,
    }
    flagSaved()
    // Auto-save: dismiss the confirmation on its own so it doesn't block the user.
    if (mode === 'auto') {
      autoCloseTimer = setTimeout(closeSaveOverlay, 2000)
    }

    originalItems.value = savedItems
    originalKeys.value = new Set(savedKeys)
    originalTitle.value = savedTitle
    originalSummary.value = savedSummary
    // Keep dirty if the user edited mid-save, and re-arm so that edit isn't lost.
    hasChanges.value = changedDuringSave
    emit('saved')
    if (changedDuringSave && !isSmart.value) scheduleAutoSave()
  } catch (err) {
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null }
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
    saveElapsed.value = elapsed
    console.error('[save] FAILED', { mode, elapsed, err })
    // Surface failures in the modal for both modes — a failed auto-save must not
    // be missed. Errors never auto-dismiss; the user has to acknowledge them.
    saveResult.value = {
      success: false,
      auto: mode === 'auto',
      error: err.message || 'Failed to save',
      collectionTitle,
    }
  } finally {
    isSaving.value = false
  }
}

const closeSaveOverlay = () => {
  if (autoCloseTimer) { clearTimeout(autoCloseTimer); autoCloseTimer = null }
  saveOverlay.value = false
  saveResult.value = null
}

// ── Leave guard ──
// One mechanism for every "leaving the editor" path: the internal Back button AND
// parent-driven nav (home link, library switch, logout) which call confirmLeave()
// through a template ref. Resolves true when it's safe to navigate, false to stay.
let leaveResolver = null
const confirmLeave = () => {
  if (!hasUnsaved.value) return Promise.resolve(true)
  leaveGuard.value = true
  return new Promise((resolve) => { leaveResolver = resolve })
}
const resolveLeave = (ok) => {
  leaveGuard.value = false
  const resolve = leaveResolver
  leaveResolver = null
  resolve?.(ok)
}
const discardChanges = () => resolveLeave(true)
const dismissGuard = () => resolveLeave(false)
const saveAndContinue = async () => {
  leaveGuard.value = false        // hide the guard; the save modal takes over
  await save({ mode: 'explicit' })
  // Continue only if the save actually persisted — a failure keeps its error modal up.
  resolveLeave(!hasChanges.value && !isSaving.value)
}
const attemptBack = async () => {
  if (await confirmLeave()) emit('back')
}

// Let the parent (App.vue) gate its own navigation on our unsaved state.
defineExpose({ confirmLeave })

const deleteCollection = async () => {
  try {
    await apiFetch(`/capi/collections/${props.collectionKey}`, { method: 'DELETE' })
    emit('toast', 'Collection deleted', 'success')
    emit('deleted')
  } catch (err) {
    emit('toast', err.message || 'Failed to delete', 'error')
  }
}

// ── Reload (in-app refresh) ──
const reload = async () => {
  // Reloading overwrites local edits — guard unsaved work first.
  if (hasUnsaved.value && !(await confirmLeave())) return
  const start = Date.now()
  isLoading.value = true
  isReloading.value = true
  const ok = await fetchCollection()
  // Hold the spinner for a beat so a refresh always reads as deliberate.
  const elapsed = Date.now() - start
  if (elapsed < 600) await new Promise((r) => setTimeout(r, 600 - elapsed))
  isLoading.value = false
  isReloading.value = false
  emit('toast', ok ? 'Collection refreshed' : 'Refresh failed', ok ? 'success' : 'error')
}

// ── Cancel / discard unsaved changes ──
const cancelChanges = () => {
  if (autoSaveTimer) { clearTimeout(autoSaveTimer); autoSaveTimer = null }
  autoSavePending.value = false
  reverting = true
  items.value = [...originalItems.value]
  title.value = originalTitle.value
  summary.value = originalSummary.value
  reverting = false
  hasChanges.value = false
  justSaved.value = false
}

// Skip the watch on initial load. We use flush: 'sync' so the watcher runs SYNCHRONOUSLY
// when title.value changes inside loadCollection — at that moment isLoading is still true,
// so markChanged is correctly skipped. The default 'pre' flush queues watchers as microtasks
// that run AFTER the finally clause flips isLoading=false, defeating the guard.
watch(title,   () => { if (!isLoading.value && !reverting) markChanged() }, { flush: 'sync' })
watch(summary, () => { if (!isLoading.value && !reverting) markChanged() }, { flush: 'sync' })
</script>

<template>
  <div>
    <!-- Save progress overlay -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="saveOverlay"
             class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div class="bg-slate-900 border border-white/15 rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">

            <!-- In progress -->
            <div v-if="!saveResult" class="text-center">
              <svg class="w-10 h-10 animate-spin text-purple-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              <h3 class="text-white font-bold mb-2">Syncing to Plex</h3>
              <div class="text-xs text-slate-400 space-y-1 mb-3">
                <p v-if="pendingChanges.adding > 0">Adding {{ pendingChanges.adding }} item{{ pendingChanges.adding !== 1 ? 's' : '' }}</p>
                <p v-if="pendingChanges.removing > 0">Removing {{ pendingChanges.removing }} item{{ pendingChanges.removing !== 1 ? 's' : '' }}</p>
                <p>Reordering {{ pendingChanges.totalItems }} items</p>
              </div>
              <div class="text-lg font-mono text-purple-400">{{ saveElapsed }}s</div>
              <p class="text-[10px] text-slate-600 mt-2">All operations run locally on 10.0.0.222</p>
            </div>

            <!-- Success -->
            <div v-else-if="saveResult.success" class="text-center">
              <div class="w-12 h-12 bg-emerald-600/20 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg class="w-7 h-7 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                </svg>
              </div>
              <p v-if="saveResult.auto" class="text-[10px] text-emerald-400/70 uppercase tracking-widest mb-1">Auto-saved</p>
              <h3 class="text-white font-bold mb-1">Saved "{{ saveResult.collectionTitle }}"</h3>
              <p class="text-xs text-slate-400 mb-3">{{ saveResult.eventName }}</p>
              <div class="bg-slate-800/60 rounded-xl p-3 text-xs text-slate-300 space-y-1.5 text-left mb-4">
                <div class="flex justify-between">
                  <span class="text-slate-500">Total items</span>
                  <span>{{ saveResult.stats.totalItems || 0 }}</span>
                </div>
                <div v-if="saveResult.stats.added" class="flex justify-between">
                  <span class="text-slate-500">Added</span>
                  <span class="text-emerald-400">+{{ saveResult.stats.added }}</span>
                </div>
                <div v-if="saveResult.stats.removed" class="flex justify-between">
                  <span class="text-slate-500">Removed</span>
                  <span class="text-red-400">-{{ saveResult.stats.removed }}</span>
                </div>
                <div v-if="saveResult.stats.reordered" class="flex justify-between">
                  <span class="text-slate-500">Reorder ops</span>
                  <span>{{ saveResult.stats.reordered }}</span>
                </div>
                <div class="flex justify-between border-t border-white/10 pt-1.5">
                  <span class="text-slate-500">Plex API calls</span>
                  <span class="font-mono">{{ saveResult.stats.plexCalls || 0 }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-slate-500">Wall time</span>
                  <span class="font-mono">{{ saveResult.stats.elapsed || saveElapsed }}s</span>
                </div>
                <div v-if="saveResult.stats.plexCalls && Number(saveResult.stats.elapsed || saveElapsed) > 0"
                     class="flex justify-between">
                  <span class="text-slate-500">Throughput</span>
                  <span class="font-mono">
                    {{ (Number(saveResult.stats.plexCalls) / Number(saveResult.stats.elapsed || saveElapsed)).toFixed(1) }} calls/s
                  </span>
                </div>
              </div>
              <p class="text-[10px] text-slate-600 mb-3">All operations run locally on 10.0.0.222</p>
              <button @click="closeSaveOverlay"
                      class="w-full py-2.5 bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium rounded-xl transition-colors">
                Done
              </button>
            </div>

            <!-- Error -->
            <div v-else class="text-center">
              <div class="w-12 h-12 bg-red-600/20 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg class="w-7 h-7 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </div>
              <h3 class="text-white font-bold mb-1">Save failed: "{{ saveResult.collectionTitle }}"</h3>
              <p class="text-sm text-red-300 mb-1">{{ saveResult.error }}</p>
              <p class="text-[10px] text-slate-600 mb-4">after {{ saveElapsed }}s</p>
              <button @click="closeSaveOverlay"
                      class="w-full py-2.5 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-xl transition-colors">
                Close
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Unsaved-changes leave guard (custom — for in-app back navigation) -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="leaveGuard"
             class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
             @click.self="dismissGuard">
          <div class="bg-slate-900 border border-white/15 rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl text-center">
            <div class="w-12 h-12 bg-amber-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg class="w-7 h-7 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
              </svg>
            </div>
            <h3 class="text-white font-bold mb-1">Unsaved changes</h3>
            <p class="text-xs text-slate-400 mb-5">You have unsaved changes to this collection. What would you like to do?</p>
            <div class="space-y-2">
              <button @click="saveAndContinue"
                      class="w-full py-2.5 bg-purple-600 hover:bg-purple-500 text-white text-sm font-bold rounded-xl transition-colors">
                Save changes
              </button>
              <button @click="discardChanges"
                      class="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-xl transition-colors">
                Discard changes
              </button>
              <button @click="dismissGuard"
                      class="w-full py-2 text-slate-500 hover:text-slate-300 text-xs transition-colors">
                Cancel
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Sticky action bar — identity row + save row. Sticks just under the page header. -->
    <div class="sticky top-12 z-20 -mx-4 px-4 py-3 mb-4 bg-dark-900/90 backdrop-blur-xl border-b border-white/10">

      <!-- Row 1: back · title (pencil to the right) · status · reload · delete -->
      <div class="flex items-center gap-2 sm:gap-3">
        <!-- Back -->
        <button @click="attemptBack"
                title="Back to collections"
                class="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800/70 transition-colors flex-shrink-0">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>

        <!-- Editable title — pencil affordance sits to the RIGHT of the text -->
        <div class="flex-1 min-w-0 flex items-center gap-1.5 group">
          <input ref="titleInput"
                 v-model="title"
                 :disabled="isSmart"
                 type="text"
                 placeholder="Collection name..."
                 class="flex-1 min-w-0 text-xl font-bold bg-transparent text-white placeholder-slate-600 focus:outline-none border-b border-transparent focus:border-purple-500/40 transition-colors pb-1 disabled:opacity-50" />
          <button v-if="!isSmart"
                  @click="titleInput?.focus()"
                  title="Edit collection name"
                  class="p-1.5 rounded-lg text-slate-500 group-focus-within:text-purple-400 hover:text-purple-300 hover:bg-purple-500/15 transition-colors flex-shrink-0">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
          </button>
        </div>

        <!-- Status pill (desktop only — the Save button conveys state on mobile) -->
        <span class="hidden sm:inline-flex justify-end min-w-[60px] text-[10px] uppercase tracking-wider flex-shrink-0">
          <span v-if="isSaving" class="text-purple-300 flex items-center gap-1">
            <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            Saving
          </span>
          <span v-else-if="autoSavePending" class="text-amber-400/80" title="Auto-save will fire shortly">Pending</span>
          <span v-else-if="hasChanges" class="text-amber-400">Unsaved</span>
          <span v-else-if="justSaved" class="text-emerald-400">Saved</span>
        </span>

        <!-- Reload (in-app refresh) -->
        <button @click="reload"
                :disabled="isReloading"
                title="Reload from Plex"
                class="p-1.5 rounded-lg text-slate-500 hover:text-purple-300 hover:bg-purple-500/15 transition-colors flex-shrink-0 disabled:opacity-60">
          <svg class="w-5 h-5" :class="{ 'animate-spin': isReloading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>

        <!-- Delete -->
        <button @click="deleteCollection"
                title="Delete collection"
                class="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/15 transition-colors flex-shrink-0">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
          </svg>
        </button>
      </div>

      <!-- Row 2: save actions (hidden for smart collections). Save grows to fill the row. -->
      <div v-if="!isSmart" class="flex items-center gap-2 mt-2.5">
        <button v-if="hasChanges"
                @click="cancelChanges"
                :disabled="isSaving"
                title="Discard unsaved changes"
                class="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-xl transition-colors flex-shrink-0 disabled:opacity-50">
          Cancel
        </button>
        <button @click="save({ mode: 'explicit' })"
                :disabled="!canSave || isSaving"
                :class="canSave && !isSaving
                  ? 'save-attn bg-purple-600 hover:bg-purple-500 text-white'
                  : 'bg-slate-800/70 text-slate-500 cursor-not-allowed'"
                class="flex-1 px-6 py-2.5 text-sm font-bold rounded-xl transition-all flex items-center justify-center gap-2"
                title="Save changes to Plex">
          <svg v-if="isSaving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          <span>{{ isSaving ? 'Saving…' : (canSave ? 'Save changes' : 'All changes saved') }}</span>
        </button>
      </div>
    </div>

    <!-- Kometa warning -->
    <div v-if="isKometa"
         class="flex items-center gap-2 p-3 mb-4 bg-amber-950/30 border border-amber-500/30 rounded-xl text-xs text-amber-300">
      <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
      </svg>
      Managed by <strong class="mx-1">Kometa</strong> — changes may be overwritten at 3:00 AM
    </div>

    <!-- Summary -->
    <div class="mb-4">
      <textarea v-model="summary"
                :disabled="isSmart"
                rows="2"
                placeholder="Add a description..."
                class="w-full px-3 py-2 bg-dark-900/50 border border-white/10 rounded-xl text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-purple-500/30 transition-colors resize-none disabled:opacity-50"></textarea>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="py-20 flex justify-center">
      <div class="flex gap-2">
        <span class="w-3 h-3 rounded-full bg-purple-500 animate-bounce" style="animation-delay: 0s"></span>
        <span class="w-3 h-3 rounded-full bg-fuchsia-500 animate-bounce" style="animation-delay: 0.15s"></span>
        <span class="w-3 h-3 rounded-full bg-pink-500 animate-bounce" style="animation-delay: 0.3s"></span>
      </div>
    </div>

    <template v-else>
      <!-- Two-column layout: items + search sidebar -->
      <div class="flex gap-6" :class="isSmart ? '' : 'flex-col lg:flex-row'">

        <!-- Items (main area) -->
        <div class="flex-1 min-w-0">
          <h3 class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">
            {{ items.length }} Item{{ items.length !== 1 ? 's' : '' }}
          </h3>

          <div v-if="items.length === 0" class="text-center py-12 text-slate-600">
            <p class="text-sm">No items in this collection</p>
            <p class="text-xs mt-1">Search to start adding items</p>
          </div>

          <VueDraggable
            v-else
            v-model="items"
            :animation="200"
            :disabled="isSmart"
            ghost-class="sortable-ghost"
            @end="onDragEnd"
            class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4 gap-5">
            <PosterCard
              v-for="(item, idx) in items"
              :key="item.ratingKey"
              :item="item"
              :position="idx + 1"
              :removable="!isSmart"
              @remove="removeItem"
            />
          </VueDraggable>
        </div>

        <!-- Always-visible search panel (Letterboxd-style) -->
        <div v-if="!isSmart" class="w-full lg:w-72 flex-shrink-0">
          <div class="lg:sticky lg:top-20">
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Add a Film</h3>
            <div class="p-3 bg-slate-900/50 border border-white/10 rounded-2xl">
              <div class="relative mb-2">
                <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
                <input v-model="searchQuery"
                       type="text"
                       placeholder="Search library..."
                       class="w-full pl-10 pr-4 py-2 bg-dark-900 border border-white/15 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/60 transition-colors" />
              </div>

              <div v-if="isSearching" class="flex justify-center py-3">
                <svg class="w-5 h-5 animate-spin text-slate-500" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
              </div>

              <div v-else-if="searchResults.length > 0" class="max-h-[400px] overflow-y-auto thin-scrollbar space-y-0.5">
                <button v-for="result in searchResults"
                        :key="result.ratingKey"
                        @click="addItem(result)"
                        :disabled="itemKeys.has(result.ratingKey)"
                        class="w-full flex items-center gap-2.5 p-2 rounded-lg text-left transition-colors"
                        :class="itemKeys.has(result.ratingKey)
                          ? 'opacity-40 cursor-not-allowed'
                          : 'hover:bg-slate-800/60 cursor-pointer'">
                  <div class="w-8 h-12 flex-shrink-0 rounded-md overflow-hidden bg-slate-800">
                    <img v-if="result.thumb"
                         :src="`${result.thumb}?k=${encodeURIComponent(adminKey)}`"
                         :alt="result.title"
                         class="w-full h-full object-cover"
                         loading="lazy" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-xs text-white truncate">{{ result.title }}</div>
                    <div class="text-[10px] text-slate-500">{{ result.year }}</div>
                  </div>
                  <svg v-if="itemKeys.has(result.ratingKey)" class="w-4 h-4 text-purple-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                  </svg>
                  <svg v-else class="w-4 h-4 text-slate-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                  </svg>
                </button>
              </div>

              <div v-else-if="searchQuery && !isSearching" class="text-center py-3 text-xs text-slate-600">
                No results for "{{ searchQuery }}"
              </div>

              <div v-else class="text-center py-3 text-xs text-slate-600">
                Type to search
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.fade-enter-active { transition: opacity 0.2s ease-out; }
.fade-leave-active { transition: opacity 0.15s ease-in; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Save button attention pulse while there are unsaved changes. */
.save-attn { animation: save-pulse 1.8s ease-out infinite; }
@keyframes save-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(168, 85, 247, 0.45); }
  70%  { box-shadow: 0 0 0 8px rgba(168, 85, 247, 0); }
  100% { box-shadow: 0 0 0 0 rgba(168, 85, 247, 0); }
}
@media (prefers-reduced-motion: reduce) {
  .save-attn { animation: none; box-shadow: 0 0 0 2px rgba(168, 85, 247, 0.5); }
}
</style>
