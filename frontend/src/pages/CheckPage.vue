<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getDemoImage, getJson, postForm } from '../api.js'
import { rupees } from '../format.js'
import { rememberCheck } from '../lastCheck.js'

const MAX_IMAGE = 5 * 1024 * 1024
const MAX_PRICE = 10_000_000
const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const router = useRouter()
const instagram = ref('')
const website = ref('')
const productName = ref('')
const price = ref('')
const claimedMrp = ref('')
const imageUrl = ref('')
const imageFile = ref(null)
const preview = ref('')
const fileInput = ref(null)
const demos = ref([])
const error = ref('')
const busy = ref(false)
const demoNote = ref('')

onMounted(async () => {
  try {
    demos.value = await getJson('/demos')
  } catch {
    demos.value = []
  }
})

onBeforeUnmount(() => setPreview(''))

function setPreview(url) {
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = url
}

function setFile(file) {
  imageFile.value = file
  setPreview(file ? URL.createObjectURL(file) : '')
}

function onFile(event) {
  const file = event.target.files?.[0] || null
  error.value = ''
  demoNote.value = ''
  if (file && !IMAGE_TYPES.includes(file.type)) {
    error.value = 'The photo must be a JPG, PNG or WebP file.'
    event.target.value = ''
    setFile(null)
    return
  }
  if (file && file.size > MAX_IMAGE) {
    error.value = 'The photo is larger than 5 MB. Use a smaller photo or a screenshot.'
    event.target.value = ''
    setFile(null)
    return
  }
  setFile(file)
}

function clearPhoto() {
  setFile(null)
  if (fileInput.value) fileInput.value.value = ''
  demoNote.value = ''
}

async function useDemo(demo) {
  error.value = ''
  instagram.value = demo.instagram || ''
  website.value = demo.website || ''
  productName.value = demo.product_name || ''
  price.value = demo.quoted_price ? String(demo.quoted_price) : ''
  claimedMrp.value = demo.claimed_mrp ? String(demo.claimed_mrp) : ''
  imageUrl.value = ''
  if (fileInput.value) fileInput.value.value = ''
  setFile(null)
  demoNote.value = ''
  if (demo.image_path) {
    try {
      setFile(await getDemoImage(demo))
      demoNote.value = `Demo photo attached: ${demo.image}`
    } catch (e) {
      error.value = e.message
    }
  }
}

function validate() {
  if (!instagram.value.trim() && !website.value.trim()) return 'Enter an Instagram handle or a website link.'
  if (productName.value.trim().length > 120) return 'Keep the product name under 120 characters.'
  for (const [value, what] of [[price.value, 'price'], [claimedMrp.value, 'original price']]) {
    if (value === '') continue
    const n = Number(value)
    if (!Number.isInteger(n) || n < 1 || n > MAX_PRICE) return `Enter the ${what} as a whole number from 1 to ${rupees(MAX_PRICE)}.`
  }
  const link = imageUrl.value.trim()
  if (link && !/^https?:\/\/\S+$/i.test(link)) return 'The image link must start with http:// or https://.'
  if (link && imageFile.value) return 'Use a photo or an image link, not both.'
  if (imageFile.value && imageFile.value.size > MAX_IMAGE) return 'The photo is larger than 5 MB.'
  return ''
}

async function submit() {
  error.value = validate()
  if (error.value) return
  const form = new FormData()
  const fields = {
    instagram: instagram.value.trim(),
    website: website.value.trim(),
    product_name: productName.value.trim(),
    quoted_price: String(price.value).trim(),
    claimed_mrp: String(claimedMrp.value).trim(),
    image_url: imageUrl.value.trim(),
  }
  for (const [k, v] of Object.entries(fields)) if (v) form.append(k, v)
  if (imageFile.value) form.append('image', imageFile.value, imageFile.value.name)
  busy.value = true
  try {
    const { id } = await postForm('/checks', form)
    rememberCheck(id, form)
    router.push({ name: 'report', params: { id } })
  } catch (e) {
    error.value = e.message
    busy.value = false
  }
}
</script>

<template>
  <div class="check-layout">
    <section class="check-intro">
      <h1>Check a store before you pay</h1>
      <p class="muted">
        Enter what the seller gave you. Parakh searches public data and shows what it found, with a link to
        every source.
      </p>
      <ol class="steps">
        <li><strong>Price.</strong> What the same product sells for elsewhere.</li>
        <li><strong>Photo.</strong> Whether the product photo appears on other sites.</li>
        <li><strong>Complaints.</strong> Public posts that mention the store.</li>
        <li><strong>Account and buyers.</strong> The Instagram account's history and reports from other buyers.</li>
      </ol>
      <p class="small muted">
        Parakh shows signals and where they came from. It does not decide whether a store is honest.
        Check the sources yourself.
      </p>
    </section>

    <section class="check-main page">
      <div v-if="demos.length" class="card">
        <h2>Try a demo</h2>
        <p class="small muted">Fills the form with a recorded example. Then press Check.</p>
        <div class="row">
          <button v-for="d in demos" :key="d.name" type="button" class="secondary" @click="useDemo(d)">
            {{ d.instagram ? `@${d.instagram}` : d.website }}<template v-if="d.product_name">, {{ d.product_name }}</template>
          </button>
        </div>
      </div>

      <form class="card" novalidate @submit.prevent="submit">
        <div class="field">
          <label for="instagram">Instagram handle or link</label>
          <input id="instagram" v-model="instagram" type="text" autocomplete="off" autocapitalize="off"
                 spellcheck="false" placeholder="e.g. @storename" />
        </div>
        <div class="field">
          <label for="website">Website link</label>
          <input id="website" v-model="website" type="text" autocomplete="off" autocapitalize="off"
                 spellcheck="false" placeholder="e.g. shopname.in" />
          <span class="hint">Give at least one: the Instagram handle or the website.</span>
        </div>
        <div class="field">
          <label for="product">Product name</label>
          <input id="product" v-model="productName" type="text" maxlength="120" placeholder="e.g. boAt Rockerz 110" />
          <span class="hint">Needed to compare prices.</span>
        </div>
        <div class="field">
          <label for="price">Price quoted to you (Rs)</label>
          <input id="price" v-model="price" type="number" inputmode="numeric" min="1" :max="MAX_PRICE" step="1"
                 placeholder="e.g. 699" />
        </div>
        <div class="field">
          <label for="mrp">Original price shown by the store (optional)</label>
          <input id="mrp" v-model="claimedMrp" type="number" inputmode="numeric" min="1" :max="MAX_PRICE" step="1"
                 placeholder="e.g. 1999" />
          <span class="hint">The crossed-out "MRP" or "was" price, in Rs.</span>
        </div>
        <div class="field">
          <label for="photo">Product photo</label>
          <input id="photo" ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" @change="onFile" />
          <span class="hint">JPG, PNG or WebP, up to 5 MB. A screenshot from the seller works.</span>
          <template v-if="preview">
            <img :src="preview" alt="Selected product photo" class="preview" />
            <p v-if="demoNote" class="small muted">{{ demoNote }}</p>
            <button type="button" class="secondary" @click="clearPhoto">Remove photo</button>
          </template>
          <p class="or">or</p>
          <label for="image-url">Image link</label>
          <input id="image-url" v-model="imageUrl" type="url" autocomplete="off" placeholder="e.g. https://..." />
        </div>
        <div class="field">
          <button type="submit" :disabled="busy">{{ busy ? 'Starting...' : 'Check' }}</button>
        </div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
      </form>
    </section>
  </div>
</template>
