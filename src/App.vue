<script setup>
import { ref, watch, nextTick } from 'vue'
import { useApi } from './composables/useApi.js'

import AuthGate from './components/AuthGate.vue'
import LibrarySelector from './components/LibrarySelector.vue'
import CollectionsGrid from './components/CollectionsGrid.vue'
import CollectionDetail from './components/CollectionDetail.vue'
import NewCollection from './components/NewCollection.vue'
import Toast from './components/Toast.vue'
import PageHeader from './shared/PageHeader.vue'

const { apiFetch, clearAdminKey } = useApi()

// ── Auth ──
const isAuthenticated = ref(false)

// ── Libraries ──
const libraries = ref([])
const selectedLibrary = ref('')

// ── Navigation: 'grid' or 'detail' or 'new' ──
const view = ref('grid')
const activeCollectionKey = ref('')
const gridRef = ref(null)
const detailRef = ref(null)
// Set while we programmatically reset selectedLibrary (logout / revert) so the
// library-change guard doesn't fire on our own writes.
let suppressLibraryGuard = false

// Ask the detail editor (if mounted) whether it's safe to leave. Resolves true
// when there's nothing unsaved, or the user chose to save / discard.
const confirmLeaveDetail = async () => {
  if (view.value === 'detail' && detailRef.value) {
    return await detailRef.value.confirmLeave()
  }
  return true
}

// ── Toast ──
const toast = ref({ show: false, message: '', type: 'success' })

const showToast = (message, type = 'success') => {
  toast.value = { show: true, message, type }
}

// ── Auth ──
const onAuthenticated = async () => {
  isAuthenticated.value = true
  try {
    const data = await apiFetch('/capi/libraries')
    console.debug('Fetched libraries:', JSON.stringify(data, null, 2));
    libraries.value = data.libraries || []
    if (libraries.value.length > 0) {
      const preferred = libraries.value.find(l => l.title.toLowerCase() === 'movies')
      selectedLibrary.value = (preferred || libraries.value[0]).key
    }
  } catch (err) {
    showToast('Failed to load libraries', 'error')
  }
}

const logout = async () => {
  if (!(await confirmLeaveDetail())) return
  suppressLibraryGuard = true
  clearAdminKey()
  isAuthenticated.value = false
  libraries.value = []
  selectedLibrary.value = ''
  view.value = 'grid'
  await nextTick()
  suppressLibraryGuard = false
}

// ── Navigation ──
const openCollection = (ratingKey) => {
  activeCollectionKey.value = ratingKey
  view.value = 'detail'
}

const startNewCollection = () => {
  activeCollectionKey.value = ''
  view.value = 'new'
}

const backToGrid = () => {
  view.value = 'grid'
  activeCollectionKey.value = ''
  gridRef.value?.refresh()
}

// Title/logo click — same as Back, but gated on unsaved changes in the editor.
const goHome = async () => {
  if (await confirmLeaveDetail()) backToGrid()
}

const onCollectionSaved = () => {
  // Stay on detail view, grid will refresh when user goes back
}

const onCollectionDeleted = () => {
  backToGrid()
}

const onCollectionCreated = (newKey) => {
  // After creating, jump to editing the new collection
  activeCollectionKey.value = newKey
  view.value = 'detail'
  gridRef.value?.refresh()
}

// ── Library change resets view (gated on unsaved changes in the editor) ──
watch(selectedLibrary, async (_newVal, oldVal) => {
  if (suppressLibraryGuard) return
  if (!(await confirmLeaveDetail())) {
    // User cancelled — snap the dropdown back to the previous library.
    suppressLibraryGuard = true
    selectedLibrary.value = oldVal
    await nextTick()
    suppressLibraryGuard = false
    return
  }
  view.value = 'grid'
  activeCollectionKey.value = ''
})
</script>

<template>
  <!-- Auth Gate -->
  <AuthGate v-if="!isAuthenticated" @authenticated="onAuthenticated" />

  <!-- Main App -->
  <div v-else class="min-h-screen bg-gradient-to-br from-dark-900 via-dark-800 to-dark-900">
    <PageHeader variant="bar" title="Collection Manager">
      <template #title>
        <h1 class="text-base sm:text-lg font-bold flex-shrink-0 cursor-pointer" @click="goHome">
          <span class="bg-gradient-to-r from-purple-400 to-fuchsia-400 bg-clip-text text-transparent">Collection Manager</span>
        </h1>
      </template>

      <LibrarySelector v-model="selectedLibrary" :libraries="libraries" />

      <button @click="logout"
              class="flex-shrink-0 p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800/70 transition-colors"
              title="Log out">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
        </svg>
      </button>
    </PageHeader>

    <!-- Content -->
    <main class="max-w-6xl mx-auto p-4">
      <!-- Grid view (default) -->
      <CollectionsGrid
        v-if="view === 'grid'"
        ref="gridRef"
        :library-key="selectedLibrary"
        @select="openCollection"
        @new="startNewCollection"
        @toast="showToast"
      />

      <!-- Detail view (editing existing collection) -->
      <CollectionDetail
        v-if="view === 'detail' && activeCollectionKey"
        ref="detailRef"
        :key="activeCollectionKey"
        :collection-key="activeCollectionKey"
        :library-key="selectedLibrary"
        @back="backToGrid"
        @saved="onCollectionSaved"
        @deleted="onCollectionDeleted"
        @toast="showToast"
      />

      <!-- New collection view -->
      <NewCollection
        v-if="view === 'new'"
        :library-key="selectedLibrary"
        @back="backToGrid"
        @created="onCollectionCreated"
        @toast="showToast"
      />
    </main>

    <!-- Toast -->
    <Toast
      :show="toast.show"
      :message="toast.message"
      :type="toast.type"
      @close="toast.show = false"
    />
  </div>
</template>
