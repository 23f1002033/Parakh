<script setup>
import EvidenceItem from './EvidenceItem.vue'

defineProps({
  title: { type: String, required: true },
  status: { type: String, default: 'pending' },
  items: { type: Array, default: () => [] },
  showSources: { type: Boolean, default: true },
  showDetail: { type: Boolean, default: true },
})

const STATUS_LABELS = { pending: 'Checking', done: 'Done', unavailable: 'Unavailable', skipped: 'Not run' }
</script>

<template>
  <section class="card" :aria-busy="status === 'pending'">
    <div class="section-head">
      <h2>{{ title }}</h2>
      <span class="status">{{ STATUS_LABELS[status] || status }}</span>
    </div>
    <p v-if="status === 'pending'" class="placeholder">Waiting for results...</p>
    <template v-else>
      <ul class="evidence">
        <EvidenceItem v-for="(item, i) in items" :key="i" :item="item" :show-sources="showSources"
                      :show-detail="showDetail" />
      </ul>
      <slot v-if="status === 'done'" />
      <slot name="extra" />
    </template>
  </section>
</template>
