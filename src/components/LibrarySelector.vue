<script setup>
defineProps({
  libraries: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
})

defineEmits(['update:modelValue'])
</script>

<template>
  <!-- flex-nowrap + overflow-x-auto so chips scroll sideways on narrow viewports
       instead of wrapping into a vertical column that pushes the header off-screen.
       min-w-0 lets the parent flex slot actually constrain us. -->
  <div class="flex gap-1.5 flex-nowrap overflow-x-auto scrollbar-hide min-w-0 -mx-1 px-1">
    <button
      v-for="lib in libraries"
      :key="lib.key"
      @click="$emit('update:modelValue', lib.key)"
      class="flex-shrink-0 px-3 py-1.5 text-xs font-medium rounded-lg transition-all whitespace-nowrap"
      :class="modelValue === lib.key
        ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
        : 'bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700/60 border border-white/10'">
      {{ lib.title }}
      <span class="ml-1 opacity-60">{{ lib.count }}</span>
    </button>
  </div>
</template>
