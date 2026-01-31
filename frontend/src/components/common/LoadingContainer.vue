<template>
  <div class="loading-container">
    <div v-if="loading" class="flex items-center justify-center">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>
    <slot v-else></slot>
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
  height: 100%;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}
</style>
