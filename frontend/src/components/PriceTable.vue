<script setup>
import { rupees } from '../format.js'

defineProps({
  listings: { type: Array, required: true },
})
</script>

<template>
  <div class="table-scroll">
    <table class="price-table">
      <thead>
        <tr>
          <th>Listing</th>
          <th>Seller</th>
          <th class="num">Price</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(x, i) in listings" :key="i">
          <td>
            <a v-if="x.url" :href="x.url" target="_blank" rel="noopener noreferrer">{{ x.title || 'Listing' }}</a>
            <span v-else>{{ x.title }}</span>
          </td>
          <td class="nowrap">{{ x.domain || x.source }}</td>
          <td class="num">{{ rupees(x.price) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
