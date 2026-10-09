<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header class="site-header">
    <div class="wrap header-row">
      <RouterLink to="/" class="brand">Parakh</RouterLink>
      <nav class="nav">
        <RouterLink to="/">Check a store</RouterLink>
        <RouterLink to="/about">How it works</RouterLink>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <RouterView />
  </main>
  <footer class="site-footer wrap">
    Parakh shows signals and where they came from. It does not decide whether a store is honest.
    Check the sources yourself.
  </footer>
</template>
