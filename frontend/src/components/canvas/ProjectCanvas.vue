<template>
  <div class="project-canvas-container">
    <flow-canvas
      :connections="connections"
      :nodes="allNodePositions"
    >
      <!-- 项目信息节点（固定在左上角） -->
      <div class="project-info-node" :style="projectInfoStyle">
        <div class="project-info-header">
          <div class="flex-1">
            <h2 class="text-xl font-bold">{{ project.name }}</h2>
            <p v-if="project.description" class="text-sm text-base-content/60 mt-1">{{ project.description }}</p>
          </div>
          <status-badge :status="project.status" type="project" />
        </div>

        <div class="project-info-meta">
          <div class="meta-item">
            <span class="meta-label">创建时间:</span>
            <span class="meta-value">{{ formatDate(project.created_at) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">更新时间:</span>
            <span class="meta-value">{{ formatDate(project.updated_at) }}</span>
          </div>
        </div>

        <!-- 剪映草稿信息 -->
        <div v-if="project.jianying_draft_path" class="draft-info">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="text-xs">剪映草稿已生成</span>
        </div>

        <!-- 剪映草稿生成按钮 -->
        <jianying-draft-button
          :project-id="project.id"
          :project="project"
          @generated="handleDraftGenerated"
        />
      </div>

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
    },
    storyboards: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      // 节点位置配置
      nodePositions: {
        rewrite: { x: 100, y: 100, width: 480, height: 600 }
      },
      // 项目信息节点位置
      projectInfoPosition: { x: 20, y: 20, width: 320, height: 200 }
    };
  },
  computed: {
    rewriteStage() {
      return this.stages.find(s => s.stage_type === 'rewrite') || null;
    },
    projectInfoStyle() {
      return {
        position: 'absolute',
        left: `${this.projectInfoPosition.x}px`,
        top: `${this.projectInfoPosition.y}px`,
        width: `${this.projectInfoPosition.width}px`,
        zIndex: 100
      };
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
        rewrite: this.nodePositions.rewrite
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
      handler(newVal) {
        console.log('[ProjectCanvas] Storyboards changed:', newVal);
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
      if (storyboard.images && storyboard.images.length > 0) {
        return 'completed';
      }
      return 'pending';
    },

    // 获取图片URL
    getImageUrl(storyboard) {
      if (storyboard.images && storyboard.images.length > 0) {
        return storyboard.images[0].image_url;
      }
      return '';
    },

    // 获取运镜状态
    getCameraStatus(storyboard) {
      if (storyboard.camera_movement) {
        return 'completed';
      }
      return 'pending';
    },

    // 获取运镜类型
    getCameraMovementType(storyboard) {
      if (storyboard.camera_movement) {
        return storyboard.camera_movement.movement_type;
      }
      return '';
    },

    // 获取运镜参数
    getCameraMovementParams(storyboard) {
      if (storyboard.camera_movement) {
        return storyboard.camera_movement.movement_params;
      }
      return null;
    },

    // 获取视频状态
    getVideoStatus(storyboard) {
      if (storyboard.videos && storyboard.videos.length > 0) {
        return 'completed';
      }
      return 'pending';
    },

    // 获取视频URL
    getVideoUrl(storyboard) {
      if (storyboard.videos && storyboard.videos.length > 0) {
        return storyboard.videos[0].video_url;
      }
      return '';
    },

    // 获取视频信息
    getVideoInfo(storyboard) {
      if (storyboard.videos && storyboard.videos.length > 0) {
        const video = storyboard.videos[0];
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

    handleSaveStage({ stageType, outputData }) {
      this.$emit('save-stage', { stageType, outputData });
    },

    handleGenerateImage({ storyboardId, prompt }) {
      this.$emit('generate-image', { storyboardId, prompt });
    },

    handleGenerateCamera({ storyboardId, movementType }) {
      this.$emit('generate-camera', { storyboardId, movementType });
    },

    handleGenerateVideo({ storyboardId }) {
      this.$emit('generate-video', { storyboardId });
    },

    handleSaveStoryboard({ storyboardId, data }) {
      this.$emit('save-storyboard', { storyboardId, data });
    },

    handleDeleteStoryboard(storyboardId) {
      this.$emit('delete-storyboard', storyboardId);
    },

    handleDraftGenerated(data) {
      this.$emit('draft-generated', data);
    }
  }
};
</script>

<style scoped>
.project-canvas-container {
  width: 100%;
  height: 100%;
}

/* 项目信息节点样式 */
.project-info-node {
  background: hsl(var(--b1));
  border: 2px solid hsl(var(--bc) / 0.2);
  border-radius: 0.75rem;
  padding: 1rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.project-info-header {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.project-info-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: hsl(var(--bc) / 0.6);
}

.meta-item {
  display: flex;
  gap: 0.5rem;
}

.meta-label {
  font-weight: 600;
}

.meta-value {
  color: hsl(var(--bc) / 0.8);
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
