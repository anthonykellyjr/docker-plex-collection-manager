<script setup>
import { ref, computed } from 'vue'
import { useApi } from '../composables/useApi.js'
import { VueDraggable } from 'vue-draggable-plus'
import PosterCard from './PosterCard.vue'
import AddItemsPanel from './AddItemsPanel.vue'

const props = defineProps({
  libraryKey: { type: String, required: true },
})

const emit = defineEmits(['back', 'created', 'toast'])

const { apiFetch } = useApi()

// ── Form ──
const title = ref('')
const summary = ref('')
const items = ref([])
const isSaving = ref(false)

const adminKey = computed(() => localStorage.getItem('collection_manager_admin_key') || '')
const itemKeys = computed(() => new Set(items.value.map(i => i.ratingKey)))
const canSave = computed(() => title.value.trim() && items.value.length > 0)

// ── Actions ──
const addItem = (item) => {
  if (itemKeys.value.has(item.ratingKey)) return
  items.value = [...items.value, item]
}

const removeItem = (item) => {
  items.value = items.value.filter(i => i.ratingKey !== item.ratingKey)
}

const save = async () => {
  if (!canSave.value || isSaving.value) return
  isSaving.value = true
  try {
    const data = await apiFetch('/capi/collections', {
      method: 'POST',
      body: JSON.stringify({
        libraryKey: props.libraryKey,
        title: title.value.trim(),
        summary: summary.value.trim(),
        itemKeys: items.value.map(i => i.ratingKey),
      }),
    })
    emit('toast', 'Collection created', 'success')
    emit('created', data.collection?.ratingKey || '')
  } catch (err) {
    emit('toast', err.message || 'Failed to create', 'error')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div>
    <!-- Top bar -->
    <div class="flex items-center gap-3 mb-6">
      <button @click="$emit('back')"
              class="p-2 text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-slate-800/50">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
      </button>

      <input v-model="title"
             type="text"
             placeholder="New collection name..."
             class="flex-1 text-xl font-bold bg-transparent text-white placeholder-slate-600 focus:outline-none border-b border-transparent focus:border-purple-500/40 transition-colors pb-1"
             autofocus />

      <button @click="save"
              :disabled="!canSave || isSaving"
              class="px-5 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-xl transition-all flex items-center gap-2">
        <svg v-if="isSaving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        {{ isSaving ? 'Creating...' : 'Create' }}
      </button>
    </div>

    <!-- Summary -->
    <div class="mb-4">
      <textarea v-model="summary"
                rows="2"
                placeholder="Add a description..."
                class="w-full px-3 py-2 bg-dark-900/50 border border-white/10 rounded-xl text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-purple-500/30 transition-colors resize-none"></textarea>
    </div>

    <!-- Two-column: items + search -->
    <div class="flex gap-6 flex-col lg:flex-row">

      <!-- Items (main area) -->
      <div class="flex-1 min-w-0">
        <h3 class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">
          {{ items.length }} Item{{ items.length !== 1 ? 's' : '' }} Added
        </h3>

        <div v-if="items.length === 0" class="text-center py-12 text-slate-600">
          <p class="text-sm">Search to start adding items</p>
        </div>

        <VueDraggable
          v-else
          v-model="items"
          :animation="200"
          ghost-class="sortable-ghost"
          class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3">
          <PosterCard
            v-for="item in items"
            :key="item.ratingKey"
            :item="item"
            :removable="true"
            @remove="removeItem"
          />
        </VueDraggable>
      </div>

      <!-- Always-visible add panel (Search / Recent tabs) -->
      <AddItemsPanel :library-key="libraryKey"
                     :added-keys="itemKeys"
                     :admin-key="adminKey"
                     @add="addItem" />
    </div>
  </div>
</template>
