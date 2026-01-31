<template>
  <div class="model-list p-6">
    <page-card title="模型管理">
      <template slot="header-right">
        <button class="btn btn-primary btn-sm gap-2" @click="handleCreate">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
              clip-rule="evenodd"
            />
          </svg>
          添加模型
        </button>
      </template>

      <!-- 筛选区域 -->
      <div class="flex flex-wrap gap-3 mb-6">
        <div class="form-control">
          <div class="input-group">
            <input
              v-model="filters.search"
              type="text"
              placeholder="搜索模型名称"
              class="input input-bordered input-sm w-48"
              @keyup.enter="handleFilter"
            />
            <button class="btn btn-square btn-sm" @click="handleFilter">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </button>
          </div>
        </div>
        <select
          v-model="filters.provider_type"
          class="select select-bordered select-sm w-40"
          @change="handleFilter"
        >
          <option value="">全部类型</option>
          <option value="llm">LLM模型</option>
          <option value="text2image">文生图模型</option>
          <option value="image2video">图生视频模型</option>
        </select>
        <select
          v-model="filters.is_active"
          class="select select-bordered select-sm w-32"
          @change="handleFilter"
        >
          <option value="">全部状态</option>
          <option value="true">已激活</option>
          <option value="false">未激活</option>
        </select>
      </div>

      <!-- 模型列表 -->
      <loading-container :loading="loading">
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                <th class="w-1/6">模型名称</th>
                <th class="w-24">类型</th>
                <th class="w-1/6">模型</th>
                <th class="w-20">优先级</th>
                <th class="w-24">状态</th>
                <th class="w-32">使用次数</th>
                <th class="w-48">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="providers.length === 0">
                <td colspan="8" class="text-center py-8 text-base-content/60">
                  暂无数据
                </td>
              </tr>
              <tr v-for="provider in providers" :key="provider.id">
                <td>
                  <div class="font-medium">{{ provider.name }}</div>
                </td>
                <td>
                  <span
                    class="badge badge-sm"
                    :class="getProviderTypeBadgeClass(provider.provider_type)"
                  >
                    {{ getProviderTypeLabel(provider.provider_type) }}
                  </span>
                </td>
                <td>
                  <div class="truncate max-w-xs" :title="provider.model_name">
                    {{ provider.model_name }}
                  </div>
                </td>
                <td>
                  <span class="badge badge-outline badge-sm">{{ provider.priority }}</span>
                </td>
                <td>
                  <span
                    class="badge badge-sm"
                    :class="provider.is_active ? 'badge-success' : 'badge-ghost'"
                  >
                    {{ provider.is_active ? '已激活' : '未激活' }}
                  </span>
                </td>
                <td>
                  <div class="text-sm">
                    <div>总计: {{ provider.total_usage_count || 0 }}</div>
                    <div class="text-base-content/60">
                      近7天: {{ provider.recent_usage_count || 0 }}
                    </div>
                  </div>
                </td>
                <td>
                  <div class="flex">
                    <button
                      class="btn btn-xs btn-ghost"
                      @click="handleTest(provider)"
                      :disabled="!provider.is_active || testing"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M13 10V3L4 14h7v7l9-11h-7z"
                        />
                      </svg>
                      测试
                    </button>
                    <button
                      class="btn btn-xs btn-ghost"
                      @click="handleToggleStatus(provider)"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                        />
                      </svg>
                      {{ provider.is_active ? '停用' : '启用' }}
                    </button>
                    <button class="btn btn-xs btn-ghost" @click="handleEdit(provider)">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                        />
                      </svg>
                      编辑
                    </button>
                    <button
                      class="btn btn-xs btn-ghost text-error"
                      @click="handleDelete(provider)"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                      删除
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </loading-container>
    </page-card>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'
import PageCard from '@/components/common/PageCard.vue'
import LoadingContainer from '@/components/common/LoadingContainer.vue'

export default {
  name: 'ModelList',
  components: {
    PageCard,
    LoadingContainer
  },
  data() {
    return {
      filters: {
        search: '',
        provider_type: '',
        is_active: ''
      },
      testing: false
    }
  },
  computed: {
    ...mapState('models', {
      providers: (state) => state.providers,
      loading: (state) => state.loading.providers
    })
  },
  created() {
    this.loadProviders()
  },
  methods: {
    ...mapActions('models', [
      'fetchProviders',
      'deleteProvider',
      'toggleProviderStatus',
      'testProviderConnection'
    ]),

    async loadProviders() {
      try {
        await this.fetchProviders(this.getFilterParams())
      } catch (error) {
        console.error('加载模型提供商列表失败:', error)
        this.$message?.error('加载模型列表失败')
      }
    },

    getFilterParams() {
      const params = {}
      if (this.filters.search) {
        params.search = this.filters.search
      }
      if (this.filters.provider_type) {
        params.provider_type = this.filters.provider_type
      }
      if (this.filters.is_active !== '') {
        params.is_active = this.filters.is_active === 'true'
      }
      return params
    },

    handleFilter() {
      this.loadProviders()
    },

    handleCreate() {
      this.$router.push({ name: 'model-create' })
    },

    handleEdit(provider) {
      this.$router.push({ name: 'model-edit', params: { id: provider.id } })
    },

    async handleToggleStatus(provider) {
      try {
        await this.toggleProviderStatus(provider.id)
        this.$message?.success(`模型已${provider.is_active ? '停用' : '启用'}`)
      } catch (error) {
        console.error('切换模型状态失败:', error)
        this.$message?.error('切换状态失败')
      }
    },

    async handleTest(provider) {
      this.testing = true
      try {
        const result = await this.testProviderConnection({
          id: provider.id,
          testPrompt: 'Hello, this is a test.'
        })

        if (result.success) {
          alert(`测试成功! 延迟: ${result.latency_ms}ms`)
        } else {
          alert(`测试失败: ${result.error}`)
        }
      } catch (error) {
        console.error('测试连接失败:', error)
        alert('测试连接失败')
      } finally {
        this.testing = false
      }
    },

    async handleDelete(provider) {
      if (!confirm(`确定要删除模型 "${provider.name}" 吗?`)) {
        return
      }

      try {
        await this.deleteProvider(provider.id)
        alert('删除成功')
      } catch (error) {
        console.error('删除模型失败:', error)
        alert(error.response?.data?.error || '删除失败,该模型可能正在被项目使用')
      }
    },

    getProviderTypeLabel(type) {
      const labels = {
        llm: 'LLM',
        text2image: '文生图',
        image2video: '图生视频'
      }
      return labels[type] || type
    },

    getProviderTypeBadgeClass(type) {
      const classes = {
        llm: 'badge-primary',
        text2image: 'badge-secondary',
        image2video: 'badge-accent'
      }
      return classes[type] || 'badge-ghost'
    }
  }
}
</script>
