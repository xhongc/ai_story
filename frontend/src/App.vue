<template>
  <div id="app" :data-theme="theme" class="app-shell">
    <router-view />
  </div>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  name: 'App',
  computed: {
    ...mapGetters('ui', ['theme']),
  },
};
</script>

<style scoped>
#app {
  width: 100%;
  height: 100%;
}

.app-shell {
  color: var(--fallback-bc, oklch(var(--bc)/1));
  transition: color 220ms ease, background-color 220ms ease;
}
</style>
