<template>
  <div class="not-found">
    <el-result
      icon="warning"
      title="404"
      subTitle="抱歉,您访问的页面不存在"
    >
      <template slot="extra">
        <el-button type="primary" @click="goHome">返回首页</el-button>
      </template>
    </el-result>
  </div>
</template>

<script>
export default {
  name: 'NotFound',
  methods: {
    goHome() {
      this.$router.push('/series');
    },
  },
};
</script>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background-color: #fff;
}
</style>
