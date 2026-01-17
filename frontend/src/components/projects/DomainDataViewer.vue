<template>
  <div class="domain-data-viewer">
    <!-- 文案改写数据 -->
    <div v-if="stageType === 'rewrite' && domainData" class="space-y-4">
      <div class="stats shadow w-full">
        <div class="stat">
          <div class="stat-title">原始文本长度</div>
          <div class="stat-value text-primary">{{ domainData.original_text?.length || 0 }}</div>
          <div class="stat-desc">字符</div>
        </div>
        <div class="stat">
          <div class="stat-title">改写后文本长度</div>
          <div class="stat-value text-secondary">{{ domainData.rewritten_text?.length || 0 }}</div>
          <div class="stat-desc">字符</div>
        </div>
        <div class="stat">
          <div class="stat-title">使用的模型</div>
          <div class="stat-value text-sm">{{ domainData.model_provider?.name || '未知' }}</div>
          <div class="stat-desc">{{ domainData.model_provider?.model_name || '' }}</div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="card bg-base-200">
          <div class="card-body">
            <h3 class="card-title text-sm">原始文本</h3>
            <div class="text-sm whitespace-pre-wrap">{{ domainData.original_text }}</div>
          </div>
        </div>
        <div class="card bg-base-200">
          <div class="card-body">
            <h3 class="card-title text-sm">改写后文本</h3>
            <div class="text-sm whitespace-pre-wrap">{{ domainData.rewritten_text }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分镜数据 -->
    <div v-else-if="stageType === 'storyboard' && domainData" class="space-y-4">
      <div class="alert alert-info">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <div class="font-bold">共 {{ domainData.count }} 个分镜</div>
          <div class="text-xs">使用的模型: {{ getModelName(domainData.storyboards?.[0]) }}</div>
        </div>
      </div>

      <div class="space-y-3">
        <div
          v-for="sb in domainData.storyboards"
          :key="sb.id"
          class="card bg-base-200 shadow-sm"
        >
          <div class="card-body p-4">
            <div class="flex justify-between items-start">
              <h3 class="card-title text-sm">分镜 {{ sb.sequence_number }}</h3>
              <div class="badge badge-primary">{{ sb.duration_seconds }}秒</div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div>
                <div class="font-semibold text-xs text-base-content/60 mb-1">场景描述</div>
                <div>{{ sb.scene_description }}</div>
              </div>
              <div>
                <div class="font-semibold text-xs text-base-content/60 mb-1">旁白文案</div>
                <div>{{ sb.narration_text }}</div>
              </div>
            </div>
            <div class="mt-2">
              <div class="font-semibold text-xs text-base-content/60 mb-1">文生图提示词</div>
              <div class="text-xs bg-base-300 p-2 rounded">{{ sb.image_prompt }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 文生图数据 -->
    <div v-else-if="stageType === 'image_generation' && domainData" class="space-y-4">
      <div class="alert alert-info">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <div class="font-bold">共 {{ domainData.count }} 个分镜的图片</div>
          <div class="text-xs">总图片数: {{ getTotalImageCount() }}</div>
        </div>
      </div>

      <div class="space-y-4">
        <div
          v-for="sb in domainData.storyboards"
          :key="sb.storyboard_id"
          class="card bg-base-200 shadow-sm"
        >
          <div class="card-body p-4">
            <h3 class="card-title text-sm">分镜 {{ sb.sequence_number }}</h3>

            <div v-if="sb.images && sb.images.length > 0" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              <div
                v-for="img in sb.images"
                :key="img.id"
                class="relative group"
              >
                <img
                  :src="img.image_url"
                  :alt="`分镜 ${sb.sequence_number} 图片`"
                  class="w-full h-32 object-cover rounded cursor-pointer hover:opacity-80 transition"
                  @click="openImageModal(img.image_url)"
                />
                <div class="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs p-1 rounded-b opacity-0 group-hover:opacity-100 transition">
                  <div>{{ img.width }}x{{ img.height }}</div>
                  <div>{{ getModelName(img) }}</div>
                </div>
                <div class="absolute top-1 right-1">
                  <div class="badge badge-sm" :class="getStatusBadgeClass(img.status)">
                    {{ img.status_display }}
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-sm text-base-content/60">
              暂无图片
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 运镜数据 -->
    <div v-else-if="stageType === 'camera_movement' && domainData" class="space-y-4">
      <div class="alert alert-info">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <div class="font-bold">共 {{ domainData.count }} 个分镜的运镜</div>
          <div class="text-xs">已设置运镜: {{ getSetCameraCount() }} 个</div>
        </div>
      </div>

      <div class="space-y-3">
        <div
          v-for="sb in domainData.storyboards"
          :key="sb.storyboard_id"
          class="card bg-base-200 shadow-sm"
        >
          <div class="card-body p-4">
            <h3 class="card-title text-sm">分镜 {{ sb.sequence_number }}</h3>

            <div v-if="sb.camera_movement" class="space-y-2">
              <div class="flex gap-2 items-center">
                <div class="badge badge-primary">{{ sb.camera_movement.movement_type_display || '未设置' }}</div>
                <div class="text-xs text-base-content/60">
                  模型: {{ getModelName(sb.camera_movement) }}
                </div>
              </div>

              <div v-if="sb.camera_movement.movement_params" class="bg-base-300 p-2 rounded">
                <div class="text-xs font-semibold mb-1">运镜参数:</div>
                <pre class="text-xs">{{ JSON.stringify(sb.camera_movement.movement_params, null, 2) }}</pre>
              </div>
            </div>
            <div v-else class="text-sm text-base-content/60">
              暂无运镜数据
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 无数据提示 -->
    <div v-else-if="!domainData" class="alert alert-warning">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <span>暂无领域数据,请先执行 AI 生成</span>
    </div>

    <!-- 图片预览模态框 -->
    <div v-if="showImageModal" class="modal modal-open" @click="closeImageModal">
      <div class="modal-box max-w-4xl" @click.stop>
        <img :src="currentImage" alt="预览" class="w-full" />
        <div class="modal-action">
          <button class="btn" @click="closeImageModal">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DomainDataViewer',
  props: {
    stageType: {
      type: String,
      required: true,
    },
    domainData: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      showImageModal: false,
      currentImage: '',
    };
  },
  methods: {
    getModelName(item) {
      return item?.model_provider?.name || '未知模型';
    },

    getTotalImageCount() {
      if (!this.domainData || !this.domainData.storyboards) return 0;
      return this.domainData.storyboards.reduce((total, sb) => {
        return total + (sb.images?.length || 0);
      }, 0);
    },

    getSetCameraCount() {
      if (!this.domainData || !this.domainData.storyboards) return 0;
      return this.domainData.storyboards.filter(sb => sb.camera_movement).length;
    },

    getStatusBadgeClass(status) {
      const classMap = {
        pending: 'badge-warning',
        processing: 'badge-info',
        completed: 'badge-success',
        failed: 'badge-error',
      };
      return classMap[status] || 'badge-ghost';
    },

    openImageModal(imageUrl) {
      this.currentImage = imageUrl;
      this.showImageModal = true;
    },

    closeImageModal() {
      this.showImageModal = false;
      this.currentImage = '';
    },
  },
};
</script>

<style scoped>
.domain-data-viewer {
  width: 100%;
}
</style>
