<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  status: { type: String, required: true },
  verdict: { type: String, default: null },
})

const CLASSES = {
  'High risk': 'verdict-high',
  'Be careful': 'verdict-careful',
  'No red flags found': 'verdict-clear',
  'Not enough data': 'verdict-nodata',
}

const label = computed(() => {
  if (props.status === 'running') return 'Checking...'
  if (props.status === 'failed') return 'Check could not finish'
  return props.verdict || 'Not enough data'
})

const cls = computed(() => (props.status === 'done' ? CLASSES[props.verdict] : 'verdict-running') || 'verdict-nodata')
</script>

<template>
  <section class="verdict" :class="cls" aria-live="polite">
    <p class="verdict-label">{{ label }}</p>
    <p v-if="status === 'running'" class="small">Searching. Results appear below as each check finishes.</p>
    <p v-else-if="status === 'failed'" class="small">Something went wrong on our side. Try the check again.</p>
    <p class="small"><RouterLink to="/about">How this is decided</RouterLink></p>
  </section>
</template>
