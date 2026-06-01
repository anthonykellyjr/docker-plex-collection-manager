<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useApi } from '../composables/useApi.js'

// Tabbed "add a film" sidebar shared by CollectionDetail + NewCollection.
//   Search tab — type-to-find (existing behaviour).
//   Recent tab — newest-added films, lazy-loaded, so you can browse-and-add.
const props = defineProps({
  libraryKey: { type: String, required: true },
  addedKeys: { type: Set, default: () => new Set() }, // ratingKeys already in the collection
  adminKey: { type: String, default: '' },            // for the poster ?k= query param
})

const emit = defineEmits(['add'])

const { apiFetch } = useApi()

const activeTab = ref('search')   // 'search' | 'recent'

// ── Search ──
const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)

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

// ── Recent (newest-added first, paginated/lazy-loaded) ──
const RECENT_PAGE_SIZE = 50
const recentItems = ref([])
const recentPage = ref(1)
const recentTotal = ref(0)
const recentLoading = ref(false)
const recentHasMore = ref(true)
const recentLoaded = ref(false)      // first page fetched yet?
const recentSentinel = ref(null)
let observer = null

const fetchRecent = async (reset = false) => {
  if (!props.libraryKey || recentLoading.value) return
  if (!reset && !recentHasMore.value) return

  recentLoading.value = true
  if (reset) {
    recentItems.value = []
    recentPage.value = 1
    recentHasMore.value = true
  }

  try {
    const params = new URLSearchParams({
      sort: 'addedAt',
      page: recentPage.value,
      size: RECENT_PAGE_SIZE,
    })
    const data = await apiFetch(`/capi/libraries/${props.libraryKey}/items?${params}`)
    const newItems = data.items || []
    recentItems.value = reset ? newItems : [...recentItems.value, ...newItems]
    recentTotal.value = data.totalSize || 0
    recentHasMore.value = recentItems.value.length < recentTotal.value && newItems.length === RECENT_PAGE_SIZE
    recentPage.value++
    recentLoaded.value = true
  } catch (err) {
    console.error('[AddItemsPanel] recent fetch failed:', err)
  } finally {
    recentLoading.value = false
  }
}

const setupObserver = () => {
  if (observer) observer.disconnect()
  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && recentHasMore.value && !recentLoading.value) {
      fetchRecent()
    }
  }, { rootMargin: '150px' })
  nextTick(() => {
    if (recentSentinel.value) observer.observe(recentSentinel.value)
  })
}

// Lazy-load the recent list the first time the tab is opened, and (re)attach the
// scroll observer whenever the sentinel re-renders.
watch(activeTab, (tab) => {
  if (tab === 'recent') {
    if (!recentLoaded.value) fetchRecent(true)
    setupObserver()
  }
})

// A library switch (parent reuse) invalidates the cached recent list.
watch(() => props.libraryKey, () => {
  recentLoaded.value = false
  recentItems.value = []
  if (activeTab.value === 'recent') {
    fetchRecent(true)
    setupObserver()
  }
})

// Warm the Recent list in the background so switching to it is instant — but yield
// to the collection's own content load first (run when the main thread goes idle).
const scheduleIdle = (fn) => {
  if (typeof requestIdleCallback === 'function') requestIdleCallback(fn, { timeout: 1500 })
  else setTimeout(fn, 800)
}
onMounted(() => {
  scheduleIdle(() => {
    if (props.libraryKey && !recentLoaded.value) fetchRecent(true)
  })
})

onUnmounted(() => {
  if (observer) observer.disconnect()
  clearTimeout(searchTimer)
})

const add = (item) => {
  if (props.addedKeys.has(item.ratingKey)) return
  emit('add', item)
}
</script>

<template>
  <div class="w-full lg:w-72 flex-shrink-0">
    <div class="lg:sticky lg:top-20">
      <h3 class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Add a Film</h3>

      <div class="p-3 bg-slate-900/50 border border-white/10 rounded-2xl">

        <!-- Tabs -->
        <div class="flex gap-1 p-1 mb-3 bg-dark-900 border border-white/10 rounded-xl">
          <button @click="activeTab = 'search'"
                  class="flex-1 py-1.5 text-xs font-medium rounded-lg transition-colors"
                  :class="activeTab === 'search'
                    ? 'bg-purple-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'">
            Search
          </button>
          <button @click="activeTab = 'recent'"
                  class="flex-1 py-1.5 text-xs font-medium rounded-lg transition-colors"
                  :class="activeTab === 'recent'
                    ? 'bg-purple-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'">
            Recent
          </button>
        </div>

        <!-- ── Search tab ── -->
        <template v-if="activeTab === 'search'">
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
                    @click="add(result)"
                    :disabled="addedKeys.has(result.ratingKey)"
                    class="w-full flex items-center gap-2.5 p-2 rounded-lg text-left transition-colors"
                    :class="addedKeys.has(result.ratingKey)
                      ? 'opacity-40 cursor-not-allowed'
                      : 'hover:bg-slate-800/60 cursor-pointer'">
              <div class="w-8 h-12 flex-shrink-0 rounded-md overflow-hidden bg-slate-800">
                <img v-if="result.thumb"
                     :src="`${result.thumb}?k=${encodeURIComponent(adminKey)}&w=120&h=180`"
                     :alt="result.title"
                     class="w-full h-full object-cover"
                     loading="lazy"
                     decoding="async" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-xs text-white truncate">{{ result.title }}</div>
                <div class="text-[10px] text-slate-500">{{ result.year }}</div>
              </div>
              <svg v-if="addedKeys.has(result.ratingKey)" class="w-4 h-4 text-purple-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
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
        </template>

        <!-- ── Recent tab ── -->
        <template v-else>
          <div class="max-h-[440px] overflow-y-auto thin-scrollbar space-y-0.5">

            <!-- Initial load: skeleton rows keep the panel's shape instead of a blank spinner -->
            <template v-if="recentLoading && recentItems.length === 0">
              <div v-for="i in 7" :key="'sk-' + i" class="flex items-center gap-2.5 p-2">
                <div class="w-8 h-12 flex-shrink-0 rounded-md bg-slate-800 animate-pulse"></div>
                <div class="flex-1 min-w-0 space-y-1.5">
                  <div class="h-2.5 w-3/4 bg-slate-800 rounded animate-pulse"></div>
                  <div class="h-2 w-1/3 bg-slate-800/70 rounded animate-pulse"></div>
                </div>
              </div>
            </template>

            <button v-for="item in recentItems"
                    :key="item.ratingKey"
                    @click="add(item)"
                    :disabled="addedKeys.has(item.ratingKey)"
                    class="w-full flex items-center gap-2.5 p-2 rounded-lg text-left transition-colors"
                    :class="addedKeys.has(item.ratingKey)
                      ? 'opacity-40 cursor-not-allowed'
                      : 'hover:bg-slate-800/60 cursor-pointer'">
              <div class="w-8 h-12 flex-shrink-0 rounded-md overflow-hidden bg-slate-800">
                <img v-if="item.thumb"
                     :src="`${item.thumb}?k=${encodeURIComponent(adminKey)}&w=120&h=180`"
                     :alt="item.title"
                     class="w-full h-full object-cover"
                     loading="lazy"
                     decoding="async" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-xs text-white truncate">{{ item.title }}</div>
                <div class="text-[10px] text-slate-500">{{ item.year }}</div>
              </div>
              <svg v-if="addedKeys.has(item.ratingKey)" class="w-4 h-4 text-purple-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
              <svg v-else class="w-4 h-4 text-slate-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
            </button>

            <!-- Infinite-scroll sentinel -->
            <div ref="recentSentinel" class="h-2"></div>

            <!-- Appending more (initial load uses skeletons above) -->
            <div v-if="recentLoading && recentItems.length > 0" class="flex justify-center py-3">
              <svg class="w-5 h-5 animate-spin text-slate-500" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
            </div>

            <div v-else-if="recentLoaded && recentItems.length === 0" class="text-center py-3 text-xs text-slate-600">
              Nothing here yet
            </div>

            <div v-else-if="!recentHasMore && recentItems.length > 0" class="text-center py-2 text-[10px] text-slate-600">
              {{ recentItems.length }} of {{ recentTotal }} loaded
            </div>
          </div>
        </template>

      </div>
    </div>
  </div>
</template>
