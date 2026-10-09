<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="page">
    <h1>Page not found</h1>
    <p>This link does not match any page. <RouterLink to="/">Start a new check</RouterLink>.</p>
  </section>
</template>
