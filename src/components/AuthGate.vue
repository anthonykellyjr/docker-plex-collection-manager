<script setup>
import { ref } from 'vue'
import PasswordInput from '../shared/PasswordInput.vue'
import { useApi } from '../composables/useApi.js'

const { adminKey, setAdminKey, apiFetch } = useApi()

const emit = defineEmits(['authenticated'])

const keyInput = ref('')
const isChecking = ref(false)
const error = ref('')
const demoHint = ref(false)

const tryAuth = async () => {
  if (!keyInput.value.trim()) return
  isChecking.value = true
  error.value = ''

  // Temporarily set the key to test it
  setAdminKey(keyInput.value.trim())

  try {
    await apiFetch('/capi/libraries')
    emit('authenticated')
  } catch (e) {
    error.value = e.message === 'Unauthorized' ? 'Invalid admin key' : 'Could not connect to API'
    setAdminKey('')
  } finally {
    isChecking.value = false
  }
}

// Auto-check stored key on mount
const autoCheck = async () => {
  if (!adminKey.value) return
  isChecking.value = true
  try {
    await apiFetch('/capi/libraries')
    emit('authenticated')
  } catch {
    setAdminKey('')
  } finally {
    isChecking.value = false
  }
}

const init = async () => {
  // If the backend is in demo mode, hint the key so anyone can get in.
  try {
    const h = await apiFetch('/capi/health')
    if (h && h.demo) {
      demoHint.value = true
      if (!adminKey.value) keyInput.value = 'demo'
    }
  } catch { /* ignore */ }
  await autoCheck()
}

init()
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="bg-slate-950/60 backdrop-blur-xl border border-white/15 rounded-2xl p-8 max-w-sm w-full shadow-2xl">
      <h1 class="text-xl font-bold text-white mb-1">Collection Manager</h1>
      <p class="text-sm text-slate-400 mb-6">Enter admin key to continue</p>

      <div v-if="demoHint" class="mb-5 px-3 py-2.5 bg-purple-500/10 border border-purple-500/30 rounded-xl text-xs text-purple-200">
        Demo mode. The key is <span class="font-mono font-bold text-white">demo</span>. Nothing here touches a real Plex server.
      </div>

      <div v-if="isChecking" class="flex justify-center py-8">
        <div class="flex gap-2">
          <span class="w-3 h-3 rounded-full bg-purple-500 animate-bounce" style="animation-delay: 0s"></span>
          <span class="w-3 h-3 rounded-full bg-fuchsia-500 animate-bounce" style="animation-delay: 0.15s"></span>
          <span class="w-3 h-3 rounded-full bg-pink-500 animate-bounce" style="animation-delay: 0.3s"></span>
        </div>
      </div>

      <form v-else @submit.prevent="tryAuth" class="space-y-4">
        <PasswordInput
          v-model="keyInput"
          placeholder="Admin key"
          autocomplete="current-password"
          class="w-full px-4 py-3 bg-dark-900 border border-white/15 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/60 transition-colors"
        />
        <p v-if="error" class="text-sm text-red-400">{{ error }}</p>
        <button type="submit"
                :disabled="!keyInput.trim()"
                class="w-full py-3 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium rounded-xl transition-all">
          Authenticate
        </button>
      </form>
    </div>
  </div>
</template>
