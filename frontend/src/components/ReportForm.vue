<script setup>
import { computed, ref } from 'vue'
import { postJson } from '../api.js'
import { OUTCOME_LABELS } from '../format.js'

const props = defineProps({
  kind: { type: String, required: true },
  storeKey: { type: String, required: true },
  display: { type: String, default: '' },
})
const emit = defineEmits(['submitted'])

const MAX_NOTE = 280
const outcome = ref('')
const note = ref('')
const busy = ref(false)
const error = ref('')
const done = ref(false)
const left = computed(() => MAX_NOTE - note.value.length)
const uid = Math.random().toString(36).slice(2, 8)

async function submit() {
  error.value = ''
  done.value = false
  if (!outcome.value) {
    error.value = 'Choose what happened.'
    return
  }
  if (note.value.length > MAX_NOTE) {
    error.value = `Keep the note to ${MAX_NOTE} characters.`
    return
  }
  busy.value = true
  try {
    const path = `/stores/${encodeURIComponent(props.kind)}/${encodeURIComponent(props.storeKey)}/reports`
    await postJson(path, { outcome: outcome.value, note: note.value.trim() || null })
    done.value = true
    outcome.value = ''
    note.value = ''
    emit('submitted')
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form class="report-form" @submit.prevent="submit">
    <fieldset class="field">
      <legend>Bought from {{ display || 'this store' }}? What happened?</legend>
      <label v-for="(text, value) in OUTCOME_LABELS" :key="value" class="radio">
        <input v-model="outcome" type="radio" :name="`outcome-${uid}`" :value="value" />
        {{ text }}
      </label>
    </fieldset>
    <div class="field">
      <label :for="`note-${uid}`">Note <span class="hint">Optional. Plain text, up to {{ MAX_NOTE }} characters.</span></label>
      <textarea :id="`note-${uid}`" v-model="note" :maxlength="MAX_NOTE" rows="3"></textarea>
      <span class="hint">{{ left }} characters left</span>
    </div>
    <div class="field">
      <button type="submit" :disabled="busy">{{ busy ? 'Sending...' : 'Add report' }}</button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="done" class="ok" role="status">Thanks. Your report is saved.</p>
  </form>
</template>
