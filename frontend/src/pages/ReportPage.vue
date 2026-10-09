<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { getJson } from '../api.js'
import PriceTable from '../components/PriceTable.vue'
import ReportForm from '../components/ReportForm.vue'
import SignalSection from '../components/SignalSection.vue'
import VerdictBanner from '../components/VerdictBanner.vue'
import { OUTCOME_LABELS, SIGNALS, SIGNAL_TITLES, count, domainOf, formatDate, plural, rupees } from '../format.js'

const POLL_MS = 1500

const props = defineProps({ id: { type: String, required: true } })

const check = ref(null)
const error = ref('')
const storeCounts = ref({})
const copied = ref('')
let timer = null
let stopped = false

async function load() {
  try {
    check.value = await getJson(`/checks/${encodeURIComponent(props.id)}`)
    error.value = ''
  } catch (e) {
    error.value = e.message
    if (e.status === 404) return
  }
  if (!stopped && (!check.value || check.value.status === 'running')) {
    timer = setTimeout(load, POLL_MS)
  }
}

async function loadCounts() {
  if (!check.value) return
  const out = {}
  for (const s of check.value.stores) {
    try {
      const page = await getJson(`/stores/${encodeURIComponent(s.kind)}/${encodeURIComponent(s.key)}`)
      out[s.path] = page.report_counts
    } catch {
      out[s.path] = null
    }
  }
  storeCounts.value = out
}

watch(() => props.id, () => {
  clearTimeout(timer)
  check.value = null
  storeCounts.value = {}
  load()
}, { immediate: true })

watch(() => check.value?.status, (status) => {
  if (status && status !== 'running') loadCounts()
})

onBeforeUnmount(() => {
  stopped = true
  clearTimeout(timer)
})

const status = (name) => check.value?.signal_status?.[name] || 'pending'
const items = (name) => check.value?.evidence?.[name] || []

const price = computed(() => items('price').find((i) => i.data && 'kept' in i.data)?.data || null)
const complaints = computed(() => items('complaints').find((i) => i.data?.results)?.data || null)
const account = computed(() => items('account').find((i) => i.data && 'followers' in i.data) || null)
const totalSearches = computed(() => (check.value ? check.value.live_searches + check.value.cached_searches : 0))

const yesNo = (v) => (v ? 'Yes' : 'No')

async function copyLink() {
  const url = window.location.href
  try {
    await navigator.clipboard.writeText(url)
    copied.value = 'Link copied.'
  } catch {
    copied.value = `Copy this link: ${url}`
  }
}
</script>

<template>
  <section class="page">
    <p v-if="error && !check" class="error" role="alert">{{ error }}</p>

    <template v-if="check">
      <div>
        <h1>Store check</h1>
        <p class="muted small">
          Checked {{ formatDate(check.created_at) }}<template v-if="check.product_name">
          for {{ check.product_name }}</template><template v-if="check.quoted_price">, quoted
          {{ rupees(check.quoted_price) }}</template>.
        </p>
        <p class="small">
          <template v-for="(s, i) in check.stores" :key="s.path">
            <template v-if="i">, </template>
            <RouterLink :to="s.path">Store page for {{ s.display }}</RouterLink>
          </template>
        </p>
      </div>

      <VerdictBanner :status="check.status" :verdict="check.verdict" />
      <p v-if="error" class="error" role="alert">{{ error }}</p>

      <template v-for="name in SIGNALS" :key="name">
        <SignalSection v-if="name === 'price'" :title="SIGNAL_TITLES.price" :status="status('price')"
                       :items="items('price')" :show-sources="false"
                       :show-detail="!price?.median">
          <template v-if="price">
            <ul class="facts small">
              <li v-if="price.median && price.ratio !== undefined">
                Quoted {{ rupees(price.quoted) }} against a median of {{ rupees(price.median) }}:
                {{ price.ratio }}x.
              </li>
              <li v-else-if="price.median">Median of matching listings: {{ rupees(price.median) }}.</li>
              <li>
                {{ price.kept }} of {{ plural(price.listings_inr, 'listing') }} with prices in rupees matched the
                product ({{ price.listings_total }} listings found in total).
              </li>
              <li>Prices came from {{ price.source_label }}. They are seller listings, not verified prices.</li>
            </ul>
            <template v-if="price.cheapest.length">
              <h3>Cheapest matching listings</h3>
              <PriceTable :listings="price.cheapest" />
            </template>
          </template>
        </SignalSection>

        <SignalSection v-else-if="name === 'complaints'" :title="SIGNAL_TITLES.complaints"
                       :status="status('complaints')" :items="items('complaints')" :show-sources="false">
          <template v-if="complaints">
            <p class="small muted">
              {{ complaints.searched }} search results checked; {{ complaints.relevant }} mention this store.
            </p>
            <ul v-if="complaints.results.length" class="plain-list">
              <li v-for="r in complaints.results" :key="r.url">
                <a :href="r.url" target="_blank" rel="noopener noreferrer">{{ r.title || r.url }}</a>
                <span class="source-domain">{{ r.source || domainOf(r.url) }}<template v-if="r.date">, {{ r.date }}</template></span>
                <p v-if="r.snippet" class="small muted">{{ r.snippet }}</p>
                <p v-if="r.negative.length || r.positive.length" class="small">
                  <span v-for="t in r.negative" :key="`n-${t}`" class="tag">mentions "{{ t }}"</span>
                  <span v-for="t in r.positive" :key="`p-${t}`" class="tag">mentions "{{ t }}"</span>
                </p>
              </li>
            </ul>
          </template>
        </SignalSection>

        <SignalSection v-else-if="name === 'account'" :title="SIGNAL_TITLES.account" :status="status('account')"
                       :items="items('account')">
          <template v-if="account">
            <dl class="stats">
              <div class="stat"><dt>Followers</dt><dd>{{ count(account.data.followers) }}</dd></div>
              <div class="stat"><dt>Following</dt><dd>{{ count(account.data.following) }}</dd></div>
              <div class="stat"><dt>Verified</dt><dd>{{ yesNo(account.data.is_verified) }}</dd></div>
              <div class="stat"><dt>Private</dt><dd>{{ yesNo(account.data.is_private) }}</dd></div>
              <div class="stat"><dt>Visible posts</dt><dd>{{ account.data.visible_posts }}</dd></div>
              <div class="stat">
                <dt>Post dates</dt>
                <dd v-if="account.data.oldest_visible_post">
                  {{ formatDate(account.data.oldest_visible_post, false) }} to
                  {{ formatDate(account.data.newest_visible_post, false) }}
                </dd>
                <dd v-else>Not visible</dd>
              </div>
            </dl>
          </template>
        </SignalSection>

        <SignalSection v-else-if="name === 'community'" :title="SIGNAL_TITLES.community"
                       :status="status('community')" :items="items('community')">
          <template #extra>
            <div v-for="s in check.stores" :key="s.path" class="field">
              <h3>{{ s.display }}</h3>
              <p v-if="storeCounts[s.path]" class="small">
                Reports so far, including any added after this check:
                <template v-for="(text, outcome, i) in OUTCOME_LABELS" :key="outcome">
                  <template v-if="i">; </template>{{ text }}: {{ storeCounts[s.path][outcome] }}
                </template>
              </p>
              <ReportForm :kind="s.kind" :store-key="s.key" :display="s.display" @submitted="loadCounts" />
            </div>
          </template>
        </SignalSection>

        <SignalSection v-else :title="SIGNAL_TITLES[name]" :status="status(name)" :items="items(name)" />
      </template>

      <footer class="card small">
        <p v-if="check.status !== 'running'">
          This check used {{ plural(totalSearches, 'search', 'searches') }}: {{ check.live_searches }} live,
          {{ check.cached_searches }} from cache.
        </p>
        <div class="row">
          <button type="button" class="secondary" @click="copyLink">Copy link</button>
          <span v-if="copied" role="status">{{ copied }}</span>
        </div>
      </footer>
    </template>

    <p v-else-if="!error" class="placeholder">Loading...</p>
  </section>
</template>
