import { reactive } from 'vue'

// Tracks a version bump per rating key so a poster URL can be busted after its
// art changes (a collection keeps the same /capi/poster/<key> URL, so without
// this the browser would keep showing the old cached image).
const versions = reactive({})

export function usePosterVersion() {
  return {
    bump: (key) => { versions[key] = Date.now() },
    suffix: (key) => (versions[key] ? `&v=${versions[key]}` : ''),
  }
}
