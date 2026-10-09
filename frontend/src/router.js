import { createRouter, createWebHistory } from 'vue-router'
import CheckPage from './pages/CheckPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'check', component: CheckPage, meta: { wide: true } },
    { path: '/c/:id', name: 'report', component: () => import('./pages/ReportPage.vue'), props: true, meta: { wide: true } },
    {
      path: '/s/:kind/:key',
      name: 'store',
      component: () => import('./pages/StorePage.vue'),
      // "key" is reserved by Vue, so the param reaches the page as storeKey.
      props: (route) => ({ kind: route.params.kind, storeKey: route.params.key }),
    },
    { path: '/about', name: 'about', component: () => import('./pages/AboutPage.vue') },
    { path: '/:rest(.*)*', name: 'missing', component: () => import('./pages/MissingPage.vue') },
  ],
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, top: 16, behavior: 'smooth' }
    if (to.path === from.path) return false
    return { top: 0 }
  },
})

router.afterEach((to) => {
  const titles = { check: 'Check a store', report: 'Report', store: 'Store', about: 'How it works', missing: 'Not found' }
  document.title = `${titles[to.name] || 'Parakh'} - Parakh`
})

export default router
