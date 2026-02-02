<template>
  <div class="project-canvas-container">
    <!-- 项目信息节点（固定在左上角，不随画布移动） -->
    <div class="project-info-node">
      <div class="project-info-main">
        <h2 class="text-lg font-bold project-name" :title="project.name">{{ truncatedProjectName }}</h2>
        <status-badge :status="project.status" type="project" />
        <div class="meta-item">
          <span class="meta-value">{{ formatDate(project.updated_at) }}</span>
        </div>

        <!-- 提示词模板 -->
        <div v-if="project.prompt_set_name" class="meta-item">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span class="meta-label">模板:</span>
          <span class="meta-value">{{ project.prompt_set_name }}</span>
        </div>

        <!-- 剪映草稿信息 -->
        <div v-if="project.jianying_draft_path" class="draft-info">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="text-xs">剪映草稿已生成</span>
        </div>

        <!-- 运行流程按钮 -->
        <button
          class="btn btn-ghost btn-sm gap-2"
          :class="{ loading: isRunningPipeline }"
          :disabled="isRunningPipeline"
          @click="handleRunPipeline"
        >
          <svg
            v-if="!isRunningPipeline"
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
              d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {{ isRunningPipeline ? '运行中...' : '' }}
        </button>

        <!-- 剪映草稿生成按钮 -->
        <jianying-draft-button
          :project-id="project.id"
          :project="project"
          @generated="handleDraftGenerated"
        />
      </div>
    </div>

    <div class="canvas-wrapper">
      <flow-canvas
        :connections="connections"
        :nodes="allNodePositions"
      >

      <!-- 文案改写节点 -->
      <rewrite-node-expanded
        v-if="project"
        :status="rewriteStage ? rewriteStage.status : 'pending'"
        :position="nodePositions.rewrite"
        :data="rewriteStage ? rewriteStage.domain_data : null"
        :original-topic="project.original_topic"
        :project-id="project.id"
        @execute="handleExecuteStage"
        @save="handleSaveStage"
        @storyboard-generated="$emit('storyboard-generated')"
      />

      <!-- 每个分镜及其子节点 -->
      <template v-for="(storyboard, index) in storyboards">
        <!-- 分镜节点 -->
        <storyboard-node
          :key="`storyboard-${index}`"
          :storyboard="storyboard"
          :index="index"
          :position="calculateStoryboardPosition(index)"
          @save="handleSaveStoryboard"
        />

        <!-- 文生图节点 -->
        <image-gen-node
          :key="`image-${index}`"
          :status="getImageStatus(storyboard)"
          :position="calculateImagePosition(index)"
          :image-url="getImageUrl(storyboard)"
          :prompt="storyboard.image_prompt"
          :storyboard-id="storyboard.id"
          @generate="handleGenerateImage"
          @save="handleSaveStoryboard"
        />

        <!-- 运镜节点 -->
        <camera-node
          :key="`camera-${index}`"
          :status="getCameraStatus(storyboard)"
          :position="calculateCameraPosition(index)"
          :movement-type="getCameraMovementType(storyboard)"
          :movement-params="getCameraMovementParams(storyboard)"
          :storyboard-id="storyboard.id"
          :can-generate="getImageStatus(storyboard) === 'completed'"
          @generate="handleGenerateCamera"
        />

        <!-- 视频生成节点 -->
        <video-gen-node
          :key="`video-${index}`"
          :status="getVideoStatus(storyboard)"
          :position="calculateVideoPosition(index)"
          :video-url="getVideoUrl(storyboard)"
          :video-info="getVideoInfo(storyboard)"
          :storyboard-id="storyboard.id"
          :can-generate="getCameraStatus(storyboard) === 'completed'"
          @generate="handleGenerateVideo"
        />
      </template>

      <!-- 空状态提示 -->
      <div v-if="!rewriteStage && storyboards.length === 0" class="empty-canvas">
        <div class="empty-icon">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div class="empty-text">暂无工作流数据</div>
        <div class="empty-hint">请先执行文案改写阶段</div>
      </div>
    </flow-canvas>
    </div>
  </div>
</template>

<script>
import FlowCanvas from './FlowCanvas.vue';
import RewriteNodeExpanded from './RewriteNodeExpanded.vue';
import StoryboardNode from './StoryboardNode.vue';
import ImageGenNode from './ImageGenNode.vue';
import CameraNode from './CameraNode.vue';
import VideoGenNode from './VideoGenNode.vue';
import StatusBadge from '@/components/common/StatusBadge.vue';
import JianyingDraftButton from '@/components/projects/JianyingDraftButton.vue';
import { formatDate } from '@/utils/helpers';

export default {
  name: 'ProjectCanvas',
  components: {
    FlowCanvas,
    RewriteNodeExpanded,
    StoryboardNode,
    ImageGenNode,
    CameraNode,
    VideoGenNode,
    StatusBadge,
    JianyingDraftButton
  },
  props: {
    project: {
      type: Object,
      required: true
    },
    stages: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      // 跟踪正在执行的节点
      executingNodes: {
        images: {}, // { storyboardId: true }
        cameras: {}, // { storyboardId: true }
        videos: {} // { storyboardId: true }
      },
      // 跟踪正在执行的阶段（用于整个阶段的 loading 状态）
      executingStages: {
        rewrite: false,
        storyboard: false,
        image_generation: false,
        camera_movement: false,
        video_generation: false
      },
      // 运行流程状态
      isRunningPipeline: false,
      pipelineTaskId: null,
      pipelineChannel: null
    };
  },
  computed: {
    // 截断项目名称
    truncatedProjectName() {
      const maxLength = 10;
      if (this.project.name && this.project.name.length > maxLength) {
        return this.project.name.slice(0, maxLength) + '...';
      }
      return this.project.name;
    },
    // 节点位置配置（固定位置，由 FlowCanvas 自动居中）
    nodePositions() {
      return {
        rewrite: { x: 50, y: 100 }
      };
    },
    rewriteStage() {
      return this.stages.find(s => s.stage_type === 'rewrite') || null;
    },
    storyboards() {
      const storyboardStage = this.stages.find(s => s.stage_type === 'storyboard') || null;
      return storyboardStage?.domain_data?.storyboards || [];
    },
    connections() {
      const conns = [];

      // 文案改写 → 第一个分镜
      if (this.rewriteStage && this.storyboards.length > 0) {
        conns.push({
          id: 'rewrite-to-storyboard-0',
          from: 'rewrite',
          to: 'storyboard-0'
        });
      }

      // 每个分镜的连接线
      this.storyboards.forEach((storyboard, index) => {
        // 分镜 → 文生图
        conns.push({
          id: `storyboard-${index}-to-image-${index}`,
          from: `storyboard-${index}`,
          to: `image-${index}`
        });

        // 文生图 → 运镜
        conns.push({
          id: `image-${index}-to-camera-${index}`,
          from: `image-${index}`,
          to: `camera-${index}`
        });

        // 运镜 → 视频生成
        conns.push({
          id: `camera-${index}-to-video-${index}`,
          from: `camera-${index}`,
          to: `video-${index}`
        });

        // 分镜之间的连接（垂直）
        if (index < this.storyboards.length - 1) {
          conns.push({
            id: `storyboard-${index}-to-storyboard-${index + 1}`,
            from: `storyboard-${index}`,
            to: `storyboard-${index + 1}`
          });
        }
      });

      return conns;
    },
    // 计算所有节点的位置信息（用于画布自动适配和连接线计算）
    allNodePositions() {
      const positions = {
        rewrite: {
          ...this.nodePositions.rewrite,
          width: 580,
          height: 400
        }
      };

      // 添加所有分镜及其子节点的位置
      this.storyboards.forEach((storyboard, index) => {
        // 分镜节点
        const storyboardPos = this.calculateStoryboardPosition(index);
        positions[`storyboard-${index}`] = {
          x: storyboardPos.x,
          y: storyboardPos.y,
          width: 280,
          height: 250
        };

        // 文生图节点
        const imagePos = this.calculateImagePosition(index);
        positions[`image-${index}`] = {
          x: imagePos.x,
          y: imagePos.y,
          width: 250,
          height: 250
        };

        // 运镜节点
        const cameraPos = this.calculateCameraPosition(index);
        positions[`camera-${index}`] = {
          x: cameraPos.x,
          y: cameraPos.y,
          width: 250,
          height: 250
        };

        // 视频生成节点
        const videoPos = this.calculateVideoPosition(index);
        positions[`video-${index}`] = {
          x: videoPos.x,
          y: videoPos.y,
          width: 250,
          height: 250
        };
      });

      return positions;
    }
  },
  mounted() {
    // 调试信息
    console.log('[ProjectCanvas] Mounted');
    console.log('[ProjectCanvas] Project:', this.project);
    console.log('[ProjectCanvas] Stages:', this.stages);
    console.log('[ProjectCanvas] Storyboards:', this.storyboards);
    console.log('[ProjectCanvas] AllNodePositions:', this.allNodePositions);
  },
  watch: {
    storyboards: {
      deep: true,
      handler(newVal, oldVal) {
        console.log('[ProjectCanvas] Storyboards changed:', newVal);

        // 检查并清除已完成的执行状态
        newVal.forEach(storyboard => {
          // 如果图片已生成,清除执行状态
          if (storyboard.image_generation?.images && storyboard.image_generation.images.length > 0) {
            this.$set(this.executingNodes.images, storyboard.id, false);
          }
          // 如果运镜已生成,清除执行状态
          if (storyboard.camera_movement?.data) {
            this.$set(this.executingNodes.cameras, storyboard.id, false);
          }
          // 如果视频已生成,清除执行状态
          if (storyboard.video_generation?.videos && storyboard.video_generation.videos.length > 0) {
            this.$set(this.executingNodes.videos, storyboard.id, false);
          }
        });
      }
    },
    // 监听项目状态变化，重置运行流程按钮状态
    'project.status': {
      handler(newStatus, oldStatus) {
        console.log('[ProjectCanvas] Project status changed:', oldStatus, '->', newStatus);

        // 如果项目状态变为 completed 或 failed，重置运行流程按钮
        if (this.isRunningPipeline && (newStatus === 'completed' || newStatus === 'failed')) {
          this.isRunningPipeline = false;
          this.pipelineTaskId = null;
          this.pipelineChannel = null;
        }
      }
    }
  },
  methods: {
    formatDate,

    // 计算分镜节点位置（垂直排列）
    calculateStoryboardPosition(index) {
      const startX = 700;
      const startY = 100;
      const rowHeight = 400; // 每行高度（包含间距）

      return {
        x: startX,
        y: startY + index * rowHeight
      };
    },

    // 计算文生图节点位置
    calculateImagePosition(index) {
      const storyboardPos = this.calculateStoryboardPosition(index);
      return {
        x: storyboardPos.x + 320, // 分镜节点右侧
        y: storyboardPos.y
      };
    },

    // 计算运镜节点位置
    calculateCameraPosition(index) {
      const imagePos = this.calculateImagePosition(index);
      return {
        x: imagePos.x + 290, // 文生图节点右侧
        y: imagePos.y
      };
    },

    // 计算视频生成节点位置
    calculateVideoPosition(index) {
      const cameraPos = this.calculateCameraPosition(index);
      return {
        x: cameraPos.x + 290, // 运镜节点右侧
        y: cameraPos.y
      };
    },

    // 获取图片状态
    getImageStatus(storyboard) {
      // 检查整个阶段是否正在执行
      if (this.executingStages.image_generation) {
        // 如果整个阶段正在执行，检查该分镜是否正在处理
        if (this.executingNodes.images[storyboard.id]) {
          return 'processing';
        }
      }
      // 检查单个节点是否正在执行
      if (this.executingNodes.images[storyboard.id]) {
        return 'processing';
      }
      // 检查是否已完成
      if (storyboard.image_generation?.images && storyboard.image_generation.images.length > 0) {
        return 'completed';
      }
      return 'pending';
    },

    // 获取图片URL
    getImageUrl(storyboard) {
      if (storyboard.image_generation.images && storyboard.image_generation.images.length > 0) {
        return storyboard.image_generation.images[0].image_url;
      }
      return '';
    },

    // 获取运镜状态
    getCameraStatus(storyboard) {
      // 检查整个阶段是否正在执行
      if (this.executingStages.camera_movement) {
        // 如果整个阶段正在执行，检查该分镜是否正在处理
        if (this.executingNodes.cameras[storyboard.id]) {
          return 'processing';
        }
      }
      // 检查单个节点是否正在执行
      if (this.executingNodes.cameras[storyboard.id]) {
        return 'processing';
      }
      // 检查是否已完成（需要检查 camera_movement.data 是否存在）
      if (storyboard.camera_movement?.data) {
        return 'completed';
      }
      return 'pending';
    },

    // 获取运镜类型
    getCameraMovementType(storyboard) {
      if (storyboard.camera_movement?.data) {
        return storyboard.camera_movement.data.movement_type;
      }
      return '';
    },

    // 获取运镜参数
    getCameraMovementParams(storyboard) {
      if (storyboard.camera_movement?.data) {
        return storyboard.camera_movement.data.movement_params;
      }
      return null;
    },

    // 获取视频状态
    getVideoStatus(storyboard) {
      // 检查整个阶段是否正在执行
      if (this.executingStages.video_generation) {
        // 如果整个阶段正在执行，检查该分镜是否正在处理
        if (this.executingNodes.videos[storyboard.id]) {
          return 'processing';
        }
      }
      // 检查单个节点是否正在执行
      if (this.executingNodes.videos[storyboard.id]) {
        return 'processing';
      }
      // 检查是否已完成
      if (storyboard.video_generation?.videos && storyboard.video_generation.videos.length > 0) {
        return 'completed';
      }
      return 'pending';
    },

    // 获取视频URL
    getVideoUrl(storyboard) {
      if (storyboard.video_generation.videos && storyboard.video_generation.videos.length > 0) {
        return storyboard.video_generation.videos[0].video_url;
      }
      return '';
    },

    // 获取视频信息
    getVideoInfo(storyboard) {
      if (storyboard.video_generation?.videos && storyboard.video_generation.videos.length > 0) {
        const video = storyboard.video_generation.videos[0];
        return {
          duration: video.duration || 0,
          width: video.width || 0,
          height: video.height || 0,
          fps: video.fps || 0
        };
      }
      return null;
    },

    handleExecuteStage({ stageType, inputData }) {
      this.$emit('execute-stage', { stageType, inputData });
    },

    handleSaveStage({ stageType, outputData, silent, skipRefresh }) {
      this.$emit('save-stage', { stageType, outputData, silent, skipRefresh });
    },

    async handleGenerateImage({ storyboardId, prompt }) {
      console.log('[ProjectCanvas] 生成图片:', { storyboardId, prompt });

      try {
        // 查找对应的分镜数据
        const storyboard = this.storyboards.find(s => s.id === storyboardId);
        if (!storyboard) {
          this.$message?.error(`未找到分镜 ${storyboardId}`);
          return;
        }

        // 设置执行状态
        this.$set(this.executingNodes.images, storyboardId, true);

        // 准备输入数据
        const inputData = {
          storyboard_ids: [storyboardId],
          scenes: [{
            scene_number: storyboard.sequence_number,
            narration: storyboard.narration_text,
            visual_prompt: prompt || storyboard.image_prompt,
            shot_type: storyboard.shot_type || '标准镜头',
          }]
        };

        // 触发执行事件
        this.$emit('execute-stage', {
          stageType: 'image_generation',
          inputData,
          storyboardId
        });
      } catch (error) {
        console.error('[ProjectCanvas] 生成图片失败:', error);
        this.$message?.error(error.message || '生成图片失败');
        // 清除执行状态
        this.$set(this.executingNodes.images, storyboardId, false);
      }
    },

    async handleGenerateCamera({ storyboardId, movementType }) {
      console.log('[ProjectCanvas] 生成运镜:', { storyboardId, movementType });

      try {
        // 查找对应的分镜数据
        const storyboard = this.storyboards.find(s => s.id === storyboardId);
        if (!storyboard) {
          this.$message?.error(`未找到分镜 ${storyboardId}`);
          return;
        }

        // 设置执行状态
        this.$set(this.executingNodes.cameras, storyboardId, true);

        // 准备输入数据
        const inputData = {
          storyboard_ids: [storyboardId],
          scenes: [{
            scene_number: storyboard.sequence_number,
            image_url: storyboard.image_generation.images[0].image_url,
            movement_type: movementType || 'auto',
          }]
        };

        // 触发执行事件
        this.$emit('execute-stage', {
          stageType: 'camera_movement',
          inputData,
          storyboardId
        });
      } catch (error) {
        console.error('[ProjectCanvas] 生成运镜失败:', error);
        this.$message?.error(error.message || '生成运镜失败');
        // 清除执行状态
        this.$set(this.executingNodes.cameras, storyboardId, false);
      }
    },

    async handleGenerateVideo({ storyboardId }) {
      console.log('[ProjectCanvas] 生成视频:', { storyboardId });

      try {
        // 查找对应的分镜数据
        const storyboard = this.storyboards.find(s => s.id === storyboardId);
        if (!storyboard) {
          this.$message?.error(`未找到分镜 ${storyboardId}`);
          return;
        }

        // 检查是否有运镜
        if (!storyboard.camera_movement?.data) {
          this.$message?.warning('请先生成运镜');
          return;
        }

        // 检查是否有图片
        if (!storyboard.image_generation?.images || storyboard.image_generation.images.length === 0) {
          this.$message?.warning('请先生成图片');
          return;
        }

        // 设置执行状态
        this.$set(this.executingNodes.videos, storyboardId, true);

        // 准备输入数据
        const inputData = {
          storyboard_ids: [storyboardId],
          scenes: [{
            scene_number: storyboard.sequence_number,
            image_url: storyboard.image_generation.images[0].image_url,
            camera_movement: {
              movement_type: storyboard.camera_movement.data.movement_type,
              movement_params: storyboard.camera_movement.data.movement_params,
            }
          }]
        };

        // 触发执行事件
        this.$emit('execute-stage', {
          stageType: 'video_generation',
          inputData,
          storyboardId
        });
      } catch (error) {
        console.error('[ProjectCanvas] 生成视频失败:', error);
        this.$message?.error(error.message || '生成视频失败');
        // 清除执行状态
        this.$set(this.executingNodes.videos, storyboardId, false);
      }
    },

    handleSaveStoryboard({ storyboardId, data, silent }) {
      this.$emit('save-storyboard', { storyboardId, data, silent });
    },

    handleDeleteStoryboard(storyboardId) {
      this.$emit('delete-storyboard', storyboardId);
    },

    handleDraftGenerated(data) {
      this.$emit('draft-generated', data);
    },

    async handleRunPipeline() {
      console.log('[ProjectCanvas] 运行完整流程');

      try {
        this.isRunningPipeline = true;

        // 调用API启动工作流
        const response = await this.$store.dispatch('projects/runPipeline', {
          projectId: this.project.id
        });

        this.pipelineTaskId = response.task_id;
        this.pipelineChannel = response.channel;

        console.log('[ProjectCanvas] 工作流已启动:', {
          taskId: this.pipelineTaskId,
          channel: this.pipelineChannel
        });

        // 通知父组件开始监听进度
        this.$emit('pipeline-started', {
          taskId: this.pipelineTaskId,
          channel: this.pipelineChannel
        });

        // 显示成功消息
        this.$message?.success('工作流已启动，正在执行...');

      } catch (error) {
        console.error('[ProjectCanvas] 启动工作流失败:', error);
        this.$message?.error(error.response?.data?.error || error.message || '启动工作流失败');
        this.isRunningPipeline = false;
      }
    },

    /**
     * 设置阶段的 loading 状态
     * @param {string} stageName - 阶段名称
     * @param {boolean} isLoading - 是否正在加载
     */
    setStageLoading(stageName, isLoading) {
      console.log('[ProjectCanvas] 设置阶段 loading:', stageName, isLoading);
      if (this.executingStages.hasOwnProperty(stageName)) {
        this.executingStages[stageName] = isLoading;
      }
    },

    /**
     * 设置单个分镜节点的 loading 状态
     * @param {string} itemType - 节点类型 (image/camera/video)
     * @param {number} sequenceNumber - 分镜序号
     * @param {boolean} isLoading - 是否正在加载
     */
    setItemLoading(itemType, sequenceNumber, isLoading) {
      console.log('[ProjectCanvas] 设置节点 loading:', itemType, sequenceNumber, isLoading);

      // 根据序号找到对应的分镜
      const storyboard = this.storyboards.find(s => s.sequence_number === sequenceNumber);
      if (!storyboard) {
        console.warn('[ProjectCanvas] 未找到分镜:', sequenceNumber);
        return;
      }

      const storyboardId = storyboard.id;

      if (itemType === 'image') {
        this.$set(this.executingNodes.images, storyboardId, isLoading);
      } else if (itemType === 'camera') {
        this.$set(this.executingNodes.cameras, storyboardId, isLoading);
      } else if (itemType === 'video') {
        this.$set(this.executingNodes.videos, storyboardId, isLoading);
      }
    },

    /**
     * 重置所有 loading 状态
     */
    resetAllLoading() {
      console.log('[ProjectCanvas] 重置所有 loading 状态');
      this.isRunningPipeline = false;
      this.executingStages = {
        rewrite: false,
        storyboard: false,
        image_generation: false,
        camera_movement: false,
        video_generation: false
      };
      this.executingNodes = {
        images: {},
        cameras: {},
        videos: {}
      };
    }
  }
};
</script>

<style scoped>
.project-canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.canvas-wrapper {
  flex: 1;
  min-height: 0;
  position: relative;
}

/* 项目信息节点样式 - 固定在顶部 */
.project-info-node {
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 200;
  background: hsl(var(--b1));
  border: 2px solid hsl(var(--bc) / 0.2);
  border-radius: 0.75rem;
  padding: 0.75rem 1rem;
  /* box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); */
  pointer-events: auto;
}

.project-info-main {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: hsl(var(--bc) / 0.6);
}

.meta-label {
  font-weight: 600;
}

.meta-value {
  color: hsl(var(--bc) / 0.8);
}

.project-name {
  max-width: 200px;
  cursor: default;
}

.draft-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: hsl(var(--su) / 0.1);
  border-radius: 0.5rem;
  color: hsl(var(--su));
  font-size: 0.75rem;
}

.empty-canvas {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: hsl(var(--bc) / 0.4);
  z-index: 10;
}

.empty-icon {
  opacity: 0.5;
}

.empty-text {
  font-size: 1.125rem;
  font-weight: 600;
}

.empty-hint {
  font-size: 0.875rem;
}
</style>
