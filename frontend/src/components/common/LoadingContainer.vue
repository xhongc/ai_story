<template>
  <div v-if="loading" class="loading-container">
    <span class="loading loading-spinner loading-lg text-primary"></span>
  </div>
  <div v-else class="loading-slot">
    <slot></slot>
  </div>
</template>

<script>
export default {
  name: 'LoadingContainer',
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style scoped>
.loading-container {
  width: 100%;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-slot {
  display: contents;
}
</style>
