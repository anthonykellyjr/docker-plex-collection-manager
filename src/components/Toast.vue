<script setup>
import { watch, onUnmounted } from 'vue'

const props = defineProps({
  message:  { type: String,  default: '' },
  type:     { type: String,  default: 'success' }, // success | error
  show:     { type: Boolean, default: false },
  duration: { type: Number,  default: 8000 },        // 8s, much harder to miss
})

const emit = defineEmits(['close'])

// Re-trigger the dismiss timer on EITHER show or message change. The previous
// implementation watched only `show`, so a second auto-save in a row inherited
// the first one's already-running timer and could vanish in <1s.
let dismissTimer = null
watch(
  () => [props.show, props.message],
  ([show]) => {
    if (dismissTimer) { clearTimeout(dismissTimer); dismissTimer = null }
    if (show) {
      dismissTimer = setTimeout(() => emit('close'), props.duration)
    }
  },
  { immediate: true }
)

onUnmounted(() => { if (dismissTimer) clearTimeout(dismissTimer) })
</script>

<template>
  <Transition name="toast">
    <div v-if="show"
         class="fixed bottom-6 right-6 z-[100] px-6 py-4 rounded-2xl backdrop-blur-xl border-2 shadow-[0_20px_60px_-10px_rgba(0,0,0,0.6)] flex items-center gap-3 max-w-md min-w-[280px]"
         :class="type === 'error'
           ? 'bg-red-950/95 border-red-500/60 text-red-100'
           : 'bg-emerald-950/95 border-emerald-500/60 text-emerald-100'"
         role="status"
         :aria-live="type === 'error' ? 'assertive' : 'polite'">
      <div class="w-10 h-10 flex-shrink-0 rounded-full flex items-center justify-center"
           :class="type === 'error' ? 'bg-red-500/20' : 'bg-emerald-500/20'">
        <svg v-if="type === 'success'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
        </svg>
        <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <div class="text-xs font-bold uppercase tracking-wider opacity-70 mb-0.5">
          {{ type === 'error' ? 'Error' : 'Saved' }}
        </div>
        <div class="text-base font-medium leading-snug break-words">{{ message }}</div>
      </div>
      <button @click="$emit('close')"
              class="opacity-50 hover:opacity-100 transition-opacity flex-shrink-0 -mr-1"
              aria-label="Dismiss">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.toast-enter-active { transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1); }
.toast-leave-active { transition: all 0.25s ease-in; }
.toast-enter-from   { opacity: 0; transform: translateY(20px) scale(0.95); }
.toast-leave-to     { opacity: 0; transform: translateY(8px) scale(0.97); }
</style>
