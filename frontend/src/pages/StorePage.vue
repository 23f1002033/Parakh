<script setup>
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { getJson } from '../api.js'
import ReportForm from '../components/ReportForm.vue'
import { OUTCOME_LABELS, formatDate } from '../format.js'

const props = defineProps({
  kind: { type: String, required: true },
  storeKey: { type: String, required: true },
})

const page = ref(null)
const error = ref('')
const notFound = ref(false)

async function load() {
  try {
    page.value = await getJson(`/stores/${encodeURIComponent(props.kind)}/${encodeURIComponent(props.storeKey)}`)
    error.value = ''
    notFound.value = false
  } catch (e) {
    notFound.value = e.status === 404
    error.value = e.message
  }
}

watch(() => [props.kind, props.storeKey], load, { immediate: true })

const KIND_LABELS = { instagram: 'Instagram store', website: 'Website store' }
</script>

<template>
  <section class="page">
    <template v-if="page">
      <div>
        <h1>{{ page.store.display }}</h1>
        <p class="muted small">
          {{ KIND_LABELS[page.store.kind] || page.store.kind }}. First checked {{ formatDate(page.created_at) }}<template
            v-if="page.last_checked_at">, last checked {{ formatDate(page.last_checked_at) }}</template>.
        </p>
      </div>

      <section class="card">
        <h2>Past checks</h2>
        <p v-if="!page.checks.length" class="muted">No checks yet.</p>
        <div v-else class="table-scroll">
          <table>
            <thead>
              <tr><th>Date</th><th>Result</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="c in page.checks" :key="c.id">
                <td>{{ formatDate(c.created_at) }}</td>
                <td>{{ c.status === 'running' ? 'Still checking' : c.verdict || 'Could not finish' }}</td>
                <td><RouterLink :to="`/c/${c.id}`">Open report</RouterLink></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card">
        <h2>Buyer reports</h2>
        <ul class="facts small">
          <li v-for="(text, outcome) in OUTCOME_LABELS" :key="outcome">{{ text }}: {{ page.report_counts[outcome] }}</li>
        </ul>
        <p v-if="!page.reports.length" class="muted">No reports yet.</p>
        <ul v-else class="plain-list">
          <li v-for="r in page.reports" :key="r.id">
            <strong>{{ OUTCOME_LABELS[r.outcome] || r.outcome }}</strong>
            <span class="source-domain">{{ formatDate(r.created_at) }}</span>
            <p v-if="r.note" class="small">{{ r.note }}</p>
          </li>
        </ul>
      </section>

      <section class="card">
        <ReportForm :kind="page.store.kind" :store-key="page.store.key" :display="page.store.display" @submitted="load" />
      </section>
    </template>

    <template v-else-if="notFound">
      <h1>No checks for this store yet</h1>
      <p>Parakh has no record of this store. <RouterLink to="/">Run a check</RouterLink> to create one.</p>
    </template>
    <p v-else-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else class="placeholder">Loading...</p>
  </section>
</template>
