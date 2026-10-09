<script setup>
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <header class="site-header">
    <div class="wrap header-row" :class="{ wide: route.meta.wide }">
      <RouterLink to="/" class="brand">Parakh</RouterLink>
      <nav class="nav">
        <RouterLink to="/">Check a store</RouterLink>
        <RouterLink to="/about">How it works</RouterLink>
      </nav>
    </div>
  </header>
  <main class="wrap" :class="{ wide: route.meta.wide }">
    <RouterView />
  </main>
  <footer class="site-footer wrap" :class="{ wide: route.meta.wide }">
    Parakh shows signals and where they came from. It does not decide whether a store is honest.
    Check the sources yourself.
  </footer>
</template>
