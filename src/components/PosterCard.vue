<script setup>
import { ref, computed } from 'vue'
import { usePosterVersion } from '../composables/usePosterVersion.js'

const props = defineProps({
  item: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  removable: { type: Boolean, default: false },
  coverable: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  position: { type: Number, default: 0 },
  size: { type: String, default: 'full' }, // 'full' (grid 300x450) | 'thumb' (120x180)
})

defineEmits(['click', 'remove', 'cover'])

const loaded = ref(false)
const errored = ref(false)

const { suffix } = usePosterVersion()
const adminKey = localStorage.getItem('collection_manager_admin_key') || ''
const [pw, ph] = props.size === 'thumb' ? [120, 180] : [300, 450]
const posterSrc = computed(() => props.item.thumb
  ? `${props.item.thumb}?k=${encodeURIComponent(adminKey)}&w=${pw}&h=${ph}${suffix(props.item.ratingKey)}`
  : null)
</script>

<template>
  <div class="group relative bg-slate-950/60 border border-white/10 rounded-xl overflow-hidden cursor-pointer transition-colors duration-200"
       :class="selected ? 'ring-2 ring-purple-500/60 opacity-60' : 'hover:border-purple-500/40'"
       @click="$emit('click', item)">

    <!-- Poster image -->
    <div class="relative w-full aspect-[2/3] overflow-hidden">
      <!-- Skeleton placeholder -->
      <div v-if="!loaded && !errored && posterSrc"
           class="absolute inset-0 bg-slate-800 animate-pulse"></div>

      <!-- Actual image -->
      <img v-if="posterSrc && !errored"
           :src="posterSrc"
           :alt="item.title"
           class="w-full h-full object-cover transition-opacity duration-300"
           :class="{ 'opacity-0': !loaded }"
           loading="lazy"
           decoding="async"
           @load="loaded = true"
           @error="errored = true">

      <!-- No poster fallback -->
      <div v-if="!posterSrc || errored"
           class="w-full h-full bg-slate-800 flex items-center justify-center">
        <span class="text-slate-600 text-xl">?</span>
      </div>

      <!-- Gradient overlay -->
      <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-60"></div>

      <!-- Position badge -->
      <div v-if="position"
           class="absolute top-1.5 left-1.5 min-w-[22px] h-[22px] px-1 bg-purple-600/90 rounded-full flex items-center justify-center z-10">
        <span class="text-[10px] font-bold text-white leading-none">#{{ position }}</span>
      </div>

      <!-- Selected checkmark -->
      <div v-if="selected"
           class="absolute top-2 right-2 w-6 h-6 bg-purple-600 rounded-full flex items-center justify-center">
        <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
        </svg>
      </div>

      <!-- Make cover button -->
      <button v-if="coverable"
              @click.stop="$emit('cover', item)"
              title="Use as collection cover"
              class="absolute top-1.5 right-9 w-6 h-6 bg-slate-900/80 hover:bg-purple-600 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
        <svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
      </button>

      <!-- Remove button -->
      <button v-if="removable"
              @click.stop="$emit('remove', item)"
              class="absolute top-1.5 right-1.5 w-6 h-6 bg-red-600/80 hover:bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
        <svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <!-- Title overlay -->
    <div class="absolute bottom-0 inset-x-0 p-2 bg-gradient-to-t from-slate-950/90 to-transparent">
      <div class="text-[11px] font-bold text-white truncate drop-shadow-md">{{ item.title }}</div>
      <div v-if="item.year" class="text-[10px] text-slate-300 mt-0.5">{{ item.year }}</div>
    </div>
  </div>
</template>
