<script setup>
import { RouterLink } from 'vue-router'
import { SEVERITY_LABELS, domainOf } from '../format.js'

defineProps({
  item: { type: Object, required: true },
  showSources: { type: Boolean, default: true },
  showDetail: { type: Boolean, default: true },
})
</script>

<template>
  <li>
    <div class="finding-row">
      <span class="chip" :class="`chip-${item.severity}`">{{ SEVERITY_LABELS[item.severity] || item.severity }}</span>
      <span class="finding">{{ item.finding }}</span>
    </div>
    <p v-if="showDetail && item.detail" class="small muted">{{ item.detail }}</p>
    <ul v-if="showSources && item.sources.length" class="sources">
      <li v-for="(s, i) in item.sources" :key="i">
        <RouterLink v-if="s.url.startsWith('/')" :to="s.url">{{ s.title }}</RouterLink>
        <template v-else-if="s.url">
          <a :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.title }}</a>
          <span class="source-domain">{{ domainOf(s.url) }}</span>
        </template>
      </li>
    </ul>
  </li>
</template>
