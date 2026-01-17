<template>
  <div class="stage-content">
    <!-- 阶段状态信息 -->
    <div v-if="stage" class="alert mb-4" :class="getAlertClass(stage.status)">
      <svg v-if="stage.status === 'running'" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6 animate-spin">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
      <svg v-else-if="stage.status === 'completed'" xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <svg v-else-if="stage.status === 'failed'" xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div>
        <div class="font-bold">{{ stage.status_display }}</div>
        <div v-if="stage.error_message" class="text-xs">{{ stage.error_message }}</div>
        <div v-else-if="stage.updated_at" class="text-xs">{{ formatDate(stage.updated_at) }}</div>
      </div>
    </div>
    <div v-else class="alert alert-info mb-4">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>此阶段尚未创建</span>
    </div>

    <!-- 操作按钮 -->
    <div class="flex justify-end gap-2 mb-6">
      <button
        class="btn btn-outline"
        :disabled="isRunning"
        @click="handleReset"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        重置
      </button>
      <button
        class="btn btn-primary"
        :disabled="isRunning"
        @click="handleSave"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
        </svg>
        保存数据
      </button>
      <button
        class="btn btn-success"
        :disabled="isRunning || !canExecute"
        @click="handleExecute"
      >
        <svg v-if="isRunning" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ isRunning ? '执行中...' : 'AI生成' }}
      </button>
    </div>

    <!-- 输入/输出编辑区域 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4" v-if="['rewrite','storyboard', 'camera_movement', 'image_generation', 'video_generation'].indexOf(stageType) !==-1">
      <!-- 输入数据 -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">输入数据</span>
          <span class="label-text-alt text-xs">支持JSON格式或纯文本</span>
        </label>
        <textarea
          v-model="localInputData"
          class="textarea textarea-bordered h-80 font-mono text-sm"
          :placeholder="getInputPlaceholder()"
          :disabled="isRunning"
        ></textarea>
        <label class="label">
          <span class="label-text-alt text-xs text-base-content/60">{{ getInputDescription() }}</span>
        </label>
      </div>

      <!-- 输出数据 -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">输出数据</span>
          <span class="label-text-alt text-xs">
            {{ isStreaming ? 'AI正在实时生成...' : 'AI生成结果或手动输入' }}
          </span>
        </label>
        <div class="relative">
          <textarea
            v-model="localOutputData"
            class="textarea textarea-bordered h-80 font-mono text-sm w-full"
            :class="{ 'textarea-info': isStreaming }"
            :placeholder="getOutputPlaceholder()"
            :disabled="isRunning"
            ref="outputTextarea"
          ></textarea>
          <!-- 流式生成动画指示器 -->
          <div v-if="isStreaming" class="absolute top-2 right-2 flex items-center gap-2 bg-info text-info-content px-3 py-1 rounded-lg shadow-lg">
            <span class="loading loading-dots loading-sm"></span>
            <span class="text-xs font-medium">实时生成中</span>
          </div>
        </div>
        <!-- 进度条 -->
        <div v-if="isStreaming && streamProgress > 0" class="mt-2">
          <progress class="progress progress-info w-full" :value="streamProgress" max="100"></progress>
          <div class="text-xs text-center text-base-content/60 mt-1">{{ streamProgress }}%</div>
        </div>
        <!-- 错误提示 -->
        <div v-if="streamError" class="alert alert-error mt-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ streamError }}</span>
        </div>
        <label class="label">
          <span class="label-text-alt text-xs text-base-content/60">{{ getOutputDescription() }}</span>
        </label>
      </div>
    </div>

    <!-- 领域数据展示区域 -->
    <div v-if="stage && stage.domain_data" class="mt-6">
      <div class="divider">领域数据</div>
      <DomainDataViewer
        :stage-type="stageType"
        :domain-data="stage.domain_data"
      />
    </div>

    <!-- 分镜可视化展示区域 -->
    <div v-if="['storyboard', 'image_generation','camera_movement', 'video_generation'].indexOf(stageType) !==-1 && localOutputData" class="mt-6">
      <div class="divider">分镜可视化</div>
      <StoryboardViewer
        :stage-type="stageType"
        :data="humanTextOutput"
        :project-id="projectId"
        @scene-generated="handleSceneGenerated"
        @stage-completed="handleStageCompleted"
        @scenes-updated="handleScenesUpdated"
      />
    </div>
  </div>
</template>

<script>
import { formatDate } from '@/utils/helpers';
import { createProjectStageSSE, SSE_EVENT_TYPES } from '@/services/sseService';
import StoryboardViewer from '@/components/content/StoryboardViewer.vue';
import DomainDataViewer from './DomainDataViewer.vue';

export default {
  name: 'StageContent',
  components: {
    StoryboardViewer,
    DomainDataViewer,
  },
  props: {
    stageType: {
      type: String,
      required: true,
      validator: (value) => ['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation'].includes(value),
    },
    stage: {
      type: Object,
      default: null,
    },
    allStages: {
      type: Array,
      default: () => [],
    },
    projectId: {
      type: String,
      required: true,
    },
    originalTopic: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      localInputData: '',
      localOutputData: '',
      humanTextOutput: '',
      humanTextIntput: '',
      isStreaming: false,
      sseClient: null,
      streamProgress: 0, // SSE 流式进度
      streamError: null, // SSE 错误信息
    };
  },
  computed: {
    isRunning() {
      return this.stage?.status === 'running' || this.isStreaming;
    },
    canSave() {
      const originalInput = this.formatJSON(this.stage?.input_data);
      const originalOutput = this.formatJSON(this.stage?.output_data);
      return this.localInputData !== originalInput || this.localOutputData !== originalOutput;
    },
    canExecute() {
      return this.localInputData.trim().length > 0 && !this.isStreaming;
    },
  },
  watch: {
    stage: {
      immediate: true,
      handler(newStage) {
        // 只有在非流式状态下才加载数据，避免在SSE连接期间重新加载导致数据丢失
        if (!this.isStreaming) {
          this.loadData(newStage);
        } else {
          console.log('[StageContent] 流式生成中，跳过数据加载');
        }
      },
    },
    allStages: {
      deep: true,
      handler() {
        // 当所有阶段数据更新时,重新加载当前阶段数据
        // 但在流式生成期间不加载，避免覆盖正在接收的SSE数据
        if (!this.isStreaming) {
          this.loadData(this.stage);
        } else {
          console.log('[StageContent] 流式生成中，跳过阶段数据加载');
        }
      },
    },
    originalTopic: {
      immediate: true,
      handler() {
        // 当 originalTopic 变化时,如果是 rewrite 阶段且当前输入为空,则更新
        if (this.stageType === 'rewrite' && !this.localInputData && this.originalTopic) {
          this.localInputData = this.originalTopic;
        }
      },
    },
  },
  beforeDestroy() {
    // 组件销毁时断开SSE连接
    this.disconnectSSE();
  },
  methods: {
    formatDate,

    handleStageCompleted(data) {
      console.log('[StageContent] 阶段完成:', data);
      this.$emit('stage-completed', data);
    },
    // 获取指定类型的阶段数据
    getStageByType(stageType) {
      return this.allStages.find((s) => s.stage_type === stageType) || null;
    },

    // 获取前一个阶段的数据
    getPreviousStage() {
      const stageOrder = ['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation'];
      const currentIndex = stageOrder.indexOf(this.stageType);
      if (currentIndex > 0) {
        const previousType = stageOrder[currentIndex - 1];
        return this.getStageByType(previousType);
      }
      return null;
    },

    // 获取前一个阶段的输出数据
    getPreviousStageOutput() {
      const previousStage = this.getPreviousStage();
      if (previousStage && previousStage.output_data) {
        return previousStage.output_data;
      }
      return null;
    },

    loadData(stage) {
      // 加载输入数据
      let inputData = this.formatJSON(stage?.input_data);

      this.localInputData = inputData;

      // 加载输出数据
      this.localOutputData = this.formatJSON(stage?.output_data);
      this.humanTextOutput = stage?.output_data?.human_text;

    },

    isEmptyData(data) {
      // 检查数据是否为空(null, undefined, 空字符串, 空对象, 空数组)
      if (!data) return true;
      if (typeof data === 'string' && data.trim() === '') return true;
      if (typeof data === 'object') {
        if (Array.isArray(data)) return data.length === 0;
        return Object.keys(data).length === 0;
      }
      return false;
    },

    formatJSON(data) {
      if (!data) return '';
      if (typeof data === 'string') return data;
      return JSON.stringify(data, null, 2);
    },

    parseData(text) {
      if (!text || !text.trim()) return null;
      try {
        return JSON.parse(text);
      } catch {
        return text;
      }
    },

    getAlertClass(status) {
      const classMap = {
        pending: 'alert-info',
        running: 'alert-warning',
        completed: 'alert-success',
        failed: 'alert-error',
        skipped: 'alert-info',
      };
      return classMap[status] || 'alert-info';
    },


    getInputPlaceholder() {
      const placeholders = {
        rewrite: '输入原始文案或上一阶段的输出结果',
        storyboard: '输入改写后的文案',
        image_generation: '输入分镜描述(JSON数组格式)',
        camera_movement: '输入生成的图片信息',
        video_generation: '输入运镜参数',
      };
      return placeholders[this.stageType] || '输入数据';
    },

    getOutputPlaceholder() {
      const placeholders = {
        rewrite: 'AI改写后的文案',
        storyboard: '分镜列表(JSON数组格式)',
        image_generation: '生成的图片URL列表',
        camera_movement: '运镜参数配置',
        video_generation: '生成的视频URL列表',
      };
      return placeholders[this.stageType] || '输出数据';
    },

    getInputDescription() {
      const descriptions = {
        rewrite: '可以输入原始文案,也可以手动编辑',
        storyboard: '输入改写后的文案,AI将生成分镜',
        image_generation: '输入分镜描述,AI将生成对应图片',
        camera_movement: '输入图片信息,AI将生成运镜参数',
        video_generation: '输入运镜参数,AI将生成视频',
      };
      return descriptions[this.stageType] || '';
    },

    getOutputDescription() {
      const descriptions = {
        rewrite: '改写后的文案,可手动修改',
        storyboard: '分镜列表,每个分镜包含描述和时长',
        image_generation: '生成的图片URL,可批量下载',
        camera_movement: '运镜参数,包含运动类型和参数',
        video_generation: '生成的视频文件URL',
      };
      return descriptions[this.stageType] || '';
    },

    handleReset() {
      this.loadData(this.stage);
    },

    handleSave() {
      const inputData = this.parseData(this.localInputData);
      const outputData = this.parseData(this.localOutputData);
      this.$emit('save', {
        stageType: this.stageType,
        inputData,
        outputData,
      });
    },

    handleExecute() {
      // 使用 SSE 流式执行
      this.handleSSEExecute();
    },

    /**
     * SSE 流式执行
     */
    handleSSEExecute() {
      // 先保存当前输入数据（跳过刷新，避免断开即将建立的SSE连接）
      const inputData = this.parseData(this.localInputData);
      this.$emit('save', {
        stageType: this.stageType,
        inputData: inputData,
        outputData: this.parseData(this.localOutputData),
        skipRefresh: true, // 关键：跳过数据刷新
      });

      // 清空之前的输出和错误
      this.localOutputData = '';
      this.streamProgress = 0;
      this.streamError = null;
      this.isStreaming = true;

      // 创建 SSE 客户端连接
      this.connectSSE();

      // 触发执行事件（通知父组件开始执行）
      this.$emit('execute', {
        stageType: this.stageType,
        inputData: inputData,
      });
    },

    /**
     * 连接 SSE 流
     */
    connectSSE() {
      // 断开已有连接
      this.disconnectSSE();

      console.log('[StageContent] 连接 SSE:', this.projectId, this.stageType);

      // 创建 SSE 客户端
      this.sseClient = createProjectStageSSE(this.projectId, this.stageType, {
        autoReconnect: false, // 不自动重连，避免重复执行
      });

      // 监听事件
      this.sseClient
        .on(SSE_EVENT_TYPES.OPEN, () => {
          console.log('[StageContent] SSE 连接已建立');
        })
        .on(SSE_EVENT_TYPES.CONNECTED, (data) => {
          console.log('[StageContent] SSE 连接成功:', data);
        })
        .on(SSE_EVENT_TYPES.TOKEN, (data) => {
          // 实时更新输出文本
          console.log('[StageContent] 收到 token:', data);
          if (data.full_text !== undefined) {
            this.localOutputData = data.full_text;
            // 自动滚动到底部
            this.$nextTick(() => {
              const textarea = this.$refs.outputTextarea;
              if (textarea) {
                textarea.scrollTop = textarea.scrollHeight;
              }
            });
          }
        })
        .on(SSE_EVENT_TYPES.STAGE_UPDATE, (data) => {
          console.log('[StageContent] 阶段更新:', data);
          if (data.progress !== undefined) {
            this.streamProgress = data.progress;
          }
        })
        .on(SSE_EVENT_TYPES.PROGRESS, (data) => {
          console.log('[StageContent] 进度更新:', data);
          if (data.progress !== undefined) {
            this.streamProgress = data.progress;
          }
        })
        .on(SSE_EVENT_TYPES.DONE, (data) => {
          console.log('[StageContent] 生成完成:', data);
          // 更新最终输出
          if (data.full_text !== undefined) {
            this.localOutputData = data.full_text;
          } else if (data.result !== undefined) {
            this.localOutputData = typeof data.result === 'string'
              ? data.result
              : JSON.stringify(data.result, null, 2);
          }
          this.streamProgress = 100;
          this.isStreaming = false;

          // 延迟通知父组件刷新数据，确保 isStreaming 状态已更新
          this.$nextTick(() => {
            this.$emit('stage-completed', {
              stageType: this.stageType,
            });
          });

          // 显示成功提示
          this.$message?.success(`${this.getStageName()} 生成完成！`);
        })
        .on(SSE_EVENT_TYPES.ERROR, (data) => {
          console.error('[StageContent] SSE 错误:', data);
          this.streamError = data.error || 'SSE 连接错误';
          this.isStreaming = false;

          // 显示错误提示
          this.$message?.error(this.streamError);
        })
        .on(SSE_EVENT_TYPES.STREAM_END, (data) => {
          console.log('[StageContent] SSE 流结束:', data);
          this.isStreaming = false;
        })
        .on(SSE_EVENT_TYPES.CLOSE, () => {
          console.log('[StageContent] SSE 连接关闭');
          this.isStreaming = false;
        });
    },

    /**
     * 断开 SSE 连接
     */
    disconnectSSE() {
      if (this.sseClient) {
        console.log('[StageContent] 断开 SSE 连接');
        this.sseClient.disconnect();
        this.sseClient = null;
      }
    },

    /**
     * 获取阶段名称
     */
    getStageName() {
      const names = {
        rewrite: '文案改写',
        storyboard: '分镜生成',
        image_generation: '文生图',
        camera_movement: '运镜生成',
        video_generation: '图生视频',
      };
      return names[this.stageType] || this.stageType;
    },

    // 处理单个场景生成完成事件
    handleSceneGenerated(eventData) {
      console.log('[StageContent] 场景生成完成:', eventData);

      // 如果 sceneNumber 为 null，表示整体刷新（WebSocket推送的完成消息）
      if (eventData.sceneNumber === null) {
        console.log('[StageContent] 收到WebSocket完成消息，触发数据刷新');

        // 触发父组件刷新数据
        this.$emit('stage-completed', {
          stageType: this.stageType,
        });

        return;
      }

      // 单个场景生成完成（旧的API调用方式，已废弃）
      // 现在由WebSocket自动处理，这里保留兼容性
      console.log('[StageContent] 单个场景生成完成（兼容模式）');
    },

    // 处理场景数据更新事件（来自 StoryboardViewer 的编辑）
    handleScenesUpdated(updatedScenes) {
      console.log('[StageContent] 场景数据已更新:', updatedScenes);

      // 根据阶段类型构建输出数据结构
      let outputData;

      if (this.stageType === 'storyboard') {
        // 分镜阶段：输出分镜列表
        outputData = {
          scenes: updatedScenes,
          human_text: updatedScenes, // 保持 human_text 同步
        };
      } else if (this.stageType === 'image_generation') {
        // 文生图阶段：保持图片URL结构
        outputData = {
          scenes: updatedScenes,
          human_text: updatedScenes,
        };
      } else if (this.stageType === 'camera_movement') {
        // 运镜阶段：保持运镜参数结构
        outputData = {
          scenes: updatedScenes,
          human_text: updatedScenes,
        };
      } else if (this.stageType === 'video_generation') {
        // 图生视频阶段：保持视频URL结构
        outputData = {
          scenes: updatedScenes,
          human_text: updatedScenes,
        };
      } else {
        // 其他阶段：直接使用场景数据
        outputData = updatedScenes;
      }

      // 更新本地输出数据
      this.localOutputData = JSON.stringify(outputData, null, 2);
      this.humanTextOutput = updatedScenes;

      console.log('[StageContent] 输出数据已同步:', {
        localOutputData: this.localOutputData,
        humanTextOutput: this.humanTextOutput,
      });

      // 提示用户保存
      this.$message?.info('场景数据已更新，请点击"保存数据"按钮保存修改');
    },
  },
};
</script>

<style scoped>
.stage-content {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
}
</style>
