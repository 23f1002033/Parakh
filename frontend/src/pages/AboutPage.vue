<script setup>
import { onMounted, ref } from 'vue'
import { getJson } from '../api.js'
import { OUTCOME_LABELS } from '../format.js'

const rules = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    rules.value = await getJson('/meta/rules')
  } catch (e) {
    error.value = e.message
  }
})

const pct = (x) => `${Math.round(x * 100)}%`
const list = (xs) => xs.join(', ')
const outcomeList = (xs) => xs.map((o) => OUTCOME_LABELS[o] || o).join(', ')
</script>

<template>
  <section class="page">
    <div>
      <h1>How Parakh decides</h1>
      <p>
        Parakh shows signals and where they came from. It does not decide whether a store is honest.
        Check the sources yourself.
      </p>
    </div>

    <section class="card">
      <h2>Where the data comes from</h2>
      <p>
        All searches run through SerpApi: Google Lens (same product and copies of the photo), Google Shopping
        (prices when Lens finds too few), Google Search and Google Forums (public discussion), and the Instagram
        profile (account numbers and recent posts). Only recent Instagram posts are visible, so older history
        cannot be checked. Prices are seller listings, not verified prices.
      </p>
    </section>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="!rules" class="placeholder">Loading the rules...</p>

    <template v-if="rules">
      <section class="card">
        <h2>Price</h2>
        <p>
          Parakh finds listings for the same product and compares their median price with the price you were
          quoted. It makes no price claim without enough matching listings.
        </p>
        <ul class="facts small">
          <li>Sources: {{ list(rules.price.sources) }}.</li>
          <li>
            A listing counts as the same product when at least {{ pct(rules.price.containment) }} of the words in
            the product name appear in its title<template v-if="rules.price.model_numbers_must_match">, and every
            model number matches exactly</template>. Used and refurbished listings are left out.
          </li>
          <li>At least {{ rules.price.min_sample }} matching listings are needed.</li>
          <li>Red flag: quote is {{ rules.price.bad_ratio }}x the median or more.</li>
          <li>Caution: quote is {{ rules.price.warn_ratio }}x the median or more.</li>
          <li>
            Caution: quote is {{ rules.price.low_ratio }}x the median or less and the brand or a major retailer
            lists it ({{ list(rules.price.major_retailers) }}). Without such a listing this is a note, not a good
            sign.
          </li>
          <li>
            Caution: the original price the store shows is {{ rules.price.mrp_ratio }}x the median or more, so the
            discount may be overstated. This is never a good sign.
          </li>
          <li>Listings from the store's own website are left out of the comparison.</li>
        </ul>
      </section>

      <section class="card">
        <h2>Photo</h2>
        <p>
          Parakh looks for exact copies of the product photo on other websites. Screenshots and edited photos
          often have no exact copies, so finding none is never counted as a good sign.
        </p>
        <ul class="facts small">
          <li>Caution: the same photo is on a marketplace ({{ list(rules.photo.marketplaces) }}).</li>
          <li>Note: the photo is on {{ rules.photo.many_sites }} or more other sites.</li>
        </ul>
      </section>

      <section class="card">
        <h2>Complaints</h2>
        <p>
          Parakh searches Google and Google Forums for the store name and reads only results that mention the
          store. The store's own website and Instagram profile are left out. Finding no discussion is a note, not
          a good sign.
        </p>
        <ul class="facts small">
          <li>A result mentions the store when it has the {{ rules.complaints.relevance }}.</li>
          <li>Store-context words: {{ list(rules.complaints.store_context_words) }}.</li>
          <li>Problem words: {{ list(rules.complaints.negative_terms) }}.</li>
          <li>Good-experience words: {{ list(rules.complaints.positive_terms) }}.</li>
          <li>
            Red flag at {{ rules.complaints.bad_at_negatives }} results with problem words; caution at
            {{ rules.complaints.warn_at_negatives }}. Good at {{ rules.complaints.good_at_positives }} results
            with good-experience words and no problem words.
          </li>
        </ul>
      </section>

      <section class="card">
        <h2>Account</h2>
        <p>Parakh reads the Instagram profile and its recent posts.</p>
        <ul class="facts small">
          <li>Caution: no Instagram account exists with this handle.</li>
          <li>Caution: the account is private.</li>
          <li>
            Caution: the oldest visible post is under {{ rules.account.new_account_days }} days old and fewer
            than {{ rules.account.new_account_posts }} posts are visible.
          </li>
          <li>Caution: the bio links to a different website than the one you gave.</li>
          <li>
            Note: {{ rules.account.large_following.toLocaleString('en-IN') }} or more followers but fewer than
            {{ rules.account.few_posts }} visible posts.
          </li>
          <li>Good: the account is verified by Instagram.</li>
        </ul>
      </section>

      <section class="card">
        <h2>Community</h2>
        <p>Buyers can report what happened after they ordered. Reports are not checked by Parakh.</p>
        <ul class="facts small">
          <li>Count against the store: {{ outcomeList(rules.community.negative_outcomes) }}.</li>
          <li>Count for the store: {{ outcomeList(rules.community.positive_outcomes) }}.</li>
          <li>Reports add at most {{ rules.community.cap }} points, so a few reports cannot decide the result alone.</li>
        </ul>
      </section>

      <section class="card">
        <h2>The result</h2>
        <div class="table-scroll">
          <table>
            <thead><tr><th>Each finding</th><th class="num">Points</th></tr></thead>
            <tbody>
              <tr><td>Red flag</td><td class="num">+{{ rules.verdict.points.bad }}</td></tr>
              <tr><td>Caution</td><td class="num">+{{ rules.verdict.points.warn }}</td></tr>
              <tr>
                <td>Good (at most {{ rules.verdict.points.good_cap }} count)</td>
                <td class="num">{{ rules.verdict.points.good }}</td>
              </tr>
              <tr><td>Note</td><td class="num">0</td></tr>
              <tr><td>Buyer reports: {{ rules.verdict.reports.formula }}</td><td class="num">0 to {{ rules.verdict.reports.cap }}</td></tr>
            </tbody>
          </table>
        </div>
        <h3>Cut-offs</h3>
        <ul class="facts small">
          <li v-for="level in rules.verdict.levels" :key="level.verdict">
            <strong>{{ level.verdict }}</strong>:
            <template v-if="level.when">{{ level.when }}.</template>
            <template v-else-if="level.min_points !== null">{{ level.min_points }} points or more.</template>
            <template v-else>fewer points than above.</template>
          </li>
        </ul>
        <p class="small muted">"{{ rules.verdict.levels[0].verdict }}" is checked first.</p>
      </section>
    </template>
  </section>
</template>
