<script setup>
import { ref } from 'vue'

// One row in the ranked LIST view, rank · thumbnail · title/year · remove.
// Mirrors PosterCard's data shape; the parent VueDraggable handles reordering
// (drag by the handle so the remove button stays clickable).
const props = defineProps({
  item: { type: Object, required: true },
  position: { type: Number, default: 0 },
  removable: { type: Boolean, default: false },
})

defineEmits(['remove'])

const loaded = ref(false)
const errored = ref(false)

const adminKey = localStorage.getItem('collection_manager_admin_key') || ''
const posterSrc = props.item.thumb
  ? `${props.item.thumb}?k=${encodeURIComponent(adminKey)}&w=120&h=180`
  : null
</script>

<template>
  <div class="group flex items-center gap-3 px-2.5 py-2 bg-slate-950/40 border border-white/10 rounded-xl hover:border-purple-500/40 transition-colors">
    <!-- Drag handle -->
    <button class="drag-handle flex-shrink-0 text-slate-600 hover:text-slate-300 cursor-grab active:cursor-grabbing transition-colors"
            title="Drag to reorder" aria-label="Drag to reorder">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
        <circle cx="9" cy="6" r="1.6"/><circle cx="15" cy="6" r="1.6"/>
        <circle cx="9" cy="12" r="1.6"/><circle cx="15" cy="12" r="1.6"/>
        <circle cx="9" cy="18" r="1.6"/><circle cx="15" cy="18" r="1.6"/>
      </svg>
    </button>

    <!-- Rank -->
    <div class="flex-shrink-0 w-7 text-right">
      <span class="text-sm font-bold text-purple-300 tabular-nums">{{ position }}</span>
    </div>

    <!-- Thumbnail (skeleton until loaded, then fades in) -->
    <div class="relative w-9 h-[54px] flex-shrink-0 rounded-md overflow-hidden bg-slate-800">
      <div v-if="!loaded && !errored && posterSrc" class="absolute inset-0 bg-slate-800 animate-pulse"></div>
      <img v-if="posterSrc && !errored"
           :src="posterSrc"
           :alt="item.title"
           class="w-full h-full object-cover transition-opacity duration-300"
           :class="{ 'opacity-0': !loaded }"
           loading="lazy"
           decoding="async"
           @load="loaded = true"
           @error="errored = true" />
      <div v-if="!posterSrc || errored" class="w-full h-full flex items-center justify-center text-slate-600 text-sm">?</div>
    </div>

    <!-- Title + year -->
    <div class="flex-1 min-w-0">
      <div class="text-sm font-semibold text-white truncate">{{ item.title }}</div>
      <div v-if="item.year" class="text-xs text-slate-500">{{ item.year }}</div>
    </div>

    <!-- Remove -->
    <button v-if="removable"
            @click.stop="$emit('remove', item)"
            class="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-full text-slate-600 hover:text-white hover:bg-red-600/80 opacity-0 group-hover:opacity-100 transition-all"
            title="Remove from collection" aria-label="Remove from collection">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
      </svg>
    </button>
  </div>
</template>
