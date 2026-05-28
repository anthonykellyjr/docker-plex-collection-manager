<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import { useApi } from '../composables/useApi.js'

const props = defineProps({
  libraryKey: { type: String, default: '' },
})

const emit = defineEmits(['select', 'new', 'orderChanged', 'toast'])

const { apiFetch } = useApi()

const collections = ref([])
const isLoading = ref(false)
const orderChanged = ref(false)
const isSavingOrder = ref(false)

// Auto-save (mirrors the pattern in CollectionDetail.vue)
const AUTO_SAVE_DEBOUNCE_MS = 500
let autoSaveTimer = null
const autoSavePending = ref(false)

// Big in-page "Saved" flash, identical pattern to CollectionDetail. Visible
// confirmation that doesn't depend on the toast.
const autoSavedFlash = ref('')
let flashTimer = null
const showAutoSavedFlash = (msg) => {
  autoSavedFlash.value = msg
  if (flashTimer) clearTimeout(flashTimer)
  flashTimer = setTimeout(() => { autoSavedFlash.value = '' }, 3000)
}

const adminKey = computed(() => localStorage.getItem('collection_manager_admin_key') || '')

const fetchCollections = async () => {
  if (!props.libraryKey) return
  isLoading.value = true
  try {
    const data = await apiFetch(`/capi/libraries/${props.libraryKey}/collections`)
    collections.value = data.collections || []
    orderChanged.value = false
  } catch (err) {
    console.error('Error fetching collections:', err)
  } finally {
    isLoading.value = false
  }
}

watch(() => props.libraryKey, () => {
  // Library switched — cancel any pending auto-save for the old library.
  if (autoSaveTimer) { clearTimeout(autoSaveTimer); autoSaveTimer = null }
  autoSavePending.value = false
  fetchCollections()
}, { immediate: true })

onUnmounted(() => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  if (flashTimer) clearTimeout(flashTimer)
})

const scheduleAutoSave = () => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSavePending.value = false
  if (isLoading.value || isSavingOrder.value) return
  autoSavePending.value = true
  console.debug('[collections-grid] auto-save armed for', AUTO_SAVE_DEBOUNCE_MS, 'ms')
  autoSaveTimer = setTimeout(() => {
    autoSavePending.value = false
    console.debug('[collections-grid] auto-save timer fired', {
      orderChanged: orderChanged.value, isSavingOrder: isSavingOrder.value,
    })
    if (orderChanged.value && !isSavingOrder.value) {
      saveOrder({ mode: 'auto' })
    }
  }, AUTO_SAVE_DEBOUNCE_MS)
}

const onDragEnd = () => {
  orderChanged.value = true
  scheduleAutoSave()
}

const saveOrder = async ({ mode = 'explicit' } = {}) => {
  // If the user clicked Save Order while a debounce was pending, cancel it.
  if (autoSaveTimer) { clearTimeout(autoSaveTimer); autoSaveTimer = null }
  autoSavePending.value = false

  isSavingOrder.value = true
  const startTime = Date.now()
  console.debug('[collections-grid] saveOrder start', { mode, count: collections.value.length })
  try {
    const collectionKeys = collections.value.map(c => c.ratingKey)
    await apiFetch(`/capi/libraries/${props.libraryKey}/collections/order`, {
      method: 'PUT',
      body: JSON.stringify({ collectionKeys }),
    })
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
    orderChanged.value = false
    const count = collectionKeys.length
    const msg = `Reordered ${count} collection${count !== 1 ? 's' : ''} · ${elapsed}s`
    console.debug('[collections-grid] saveOrder success', { mode, elapsed })
    if (mode === 'auto') {
      emit('toast', `Auto-saved: ${msg}`, 'success')
      showAutoSavedFlash(msg)
    } else {
      emit('toast', `Saved: ${msg}`, 'success')
      showAutoSavedFlash(msg)
    }
  } catch (err) {
    console.error('[collections-grid] saveOrder FAILED', err)
    emit('toast', `${mode === 'auto' ? 'Auto-save' : 'Save'} failed: ${err.message || 'unknown error'}`, 'error')
  } finally {
    isSavingOrder.value = false
  }
}

const refresh = () => fetchCollections()
defineExpose({ refresh })
</script>

<template>
  <div>
    <!-- Top bar -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-3">
        <h2 class="text-sm font-bold text-slate-300 uppercase tracking-widest">Collections</h2>
        <span v-if="collections.length" class="text-xs text-slate-600">({{ collections.length }})</span>
      </div>
      <div class="flex items-center gap-2">
        <!-- Status pill: saving > pending auto-save > unsaved order -->
        <span v-if="isSavingOrder"
              class="text-[10px] text-purple-300 uppercase tracking-wider flex items-center gap-1">
          <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          Saving
        </span>
        <span v-else-if="autoSavePending"
              class="text-[10px] text-amber-400/80 uppercase tracking-wider">Pending</span>
        <span v-else-if="orderChanged" class="text-[10px] text-amber-400 uppercase tracking-wider">Unsaved</span>

        <!-- Save order (explicit, only shown when needed) -->
        <button v-if="orderChanged"
                @click="saveOrder({ mode: 'explicit' })"
                :disabled="isSavingOrder"
                class="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-700 text-white text-sm font-medium rounded-xl transition-all">
          Save now
        </button>
        <!-- New collection -->
        <button @click="$emit('new')"
                class="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium rounded-xl transition-all flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          New Collection
        </button>
      </div>
    </div>

    <!-- Big inline "Saved" flash banner — unmissable confirmation after auto-save. -->
    <Transition name="flash">
      <div v-if="autoSavedFlash"
           class="flex items-center gap-2 p-3 mb-4 bg-emerald-600/15 border border-emerald-500/40 rounded-xl text-sm text-emerald-200 font-medium">
        <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
        </svg>
        <span>{{ autoSavedFlash }}</span>
      </div>
    </Transition>

    <!-- Loading skeletons -->
    <div v-if="isLoading" class="grid grid-cols-3 md:grid-cols-4 gap-4">
      <div v-for="i in 8" :key="i" class="bg-slate-800 animate-pulse rounded-xl aspect-[2/3]"></div>
    </div>

    <!-- Empty state -->
    <div v-else-if="collections.length === 0"
         class="text-center py-20 text-slate-600">
      <svg class="w-16 h-16 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
      </svg>
      <p class="text-lg">No collections yet</p>
      <p class="text-sm mt-1">Create your first collection to get started</p>
    </div>

    <!-- Sortable collection grid — 3 cols on mobile, 4 on desktop. Each card uses
         the true 2:3 poster ratio, so heights scale naturally with width. -->
    <VueDraggable
      v-else
      v-model="collections"
      :animation="250"
      ghost-class="sortable-ghost"
      handle=".drag-handle"
      class="grid grid-cols-3 md:grid-cols-4 gap-4"
      @end="onDragEnd">

      <div v-for="col in collections"
           :key="col.ratingKey"
           @click="$emit('select', col.ratingKey)"
           class="group relative bg-slate-950/60 backdrop-blur-xl border border-white/15 rounded-xl overflow-hidden cursor-pointer transition-all duration-300 hover:border-purple-500/50 hover:shadow-[0_10px_30px_-8px_rgba(0,0,0,0.7),0_0_20px_rgba(168,85,247,0.2)]">

        <!-- Drag handle — small enough to fit a thumbnail card -->
        <div class="drag-handle absolute top-1.5 left-1.5 z-10 w-7 h-7 bg-black/50 backdrop-blur-sm rounded-md flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing"
             @click.stop>
          <svg class="w-3.5 h-3.5 text-slate-300" fill="currentColor" viewBox="0 0 24 24">
            <circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/>
            <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
            <circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/>
          </svg>
        </div>

        <!-- Badges -->
        <div class="absolute top-1.5 right-1.5 z-10 flex gap-1">
          <span v-if="col.kometaManaged"
                class="text-[8px] font-bold px-1.5 py-0.5 bg-amber-600/40 backdrop-blur-sm text-amber-200 border border-amber-500/30 rounded-md uppercase tracking-wide">
            Kometa
          </span>
          <span v-if="col.smart"
                class="text-[8px] font-bold px-1.5 py-0.5 bg-blue-600/40 backdrop-blur-sm text-blue-200 border border-blue-500/30 rounded-md uppercase tracking-wide">
            Smart
          </span>
        </div>

        <!-- Collection poster / gradient — true poster aspect ratio (no more chopped heads).
             onerror="this.remove()" makes 404s (collections w/o a Plex poster) fall back
             to the v-else gradient cleanly instead of showing the broken-image icon. -->
        <div class="aspect-[2/3] relative overflow-hidden bg-gradient-to-br from-purple-900/40 to-slate-900">
          <img v-if="col.thumb"
               :src="`${col.thumb}?k=${encodeURIComponent(adminKey)}`"
               :alt="col.title"
               class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
               loading="lazy"
               @error="(e) => e.target.style.display = 'none'">
          <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent"></div>
        </div>

        <!-- Info — tighter padding + smaller type for the smaller card -->
        <div class="p-2 pt-1.5 -mt-6 relative">
          <h3 class="text-xs sm:text-sm font-bold text-white truncate">{{ col.title }}</h3>
          <p class="text-[10px] text-slate-400 mt-0.5">{{ col.childCount }} item{{ col.childCount !== 1 ? 's' : '' }}</p>
        </div>
      </div>
    </VueDraggable>

    <!-- Drag hint -->
    <p v-if="collections.length > 1 && !orderChanged" class="text-center text-[10px] text-slate-700 mt-4">
      Drag to reorder · changes auto-save after 500ms
    </p>
  </div>
</template>

<style scoped>
/* Saved-flash banner: slides+fades in from above, fades out. */
.flash-enter-active { transition: transform 0.25s ease-out, opacity 0.25s ease-out; }
.flash-leave-active { transition: transform 0.3s ease-in,  opacity 0.3s ease-in;  }
.flash-enter-from   { opacity: 0; transform: translateY(-8px); }
.flash-leave-to     { opacity: 0; transform: translateY(-4px); }
</style>
