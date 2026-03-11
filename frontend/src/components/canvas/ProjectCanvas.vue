<template>
  <div class="project-canvas-container">
    <!-- 项目信息节点（固定在左上角，不随画布移动） -->
    <div class="project-info-node">
      <div class="project-info-main">
        <div class="project-title-switcher ui-chip-block is-title-chip">
          <button
            class="project-title-trigger"
            type="button"
            :title="project.name"
            @click="toggleEpisodeMenu"
          >
            <span class="project-name text-lg font-bold">{{ currentEpisodeLabel }}</span>
            <svg xmlns="http://www.w3.org/2000/svg" class="title-chevron" :class="{ open: showEpisodeMenu }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <transition name="episode-dropdown">
            <div v-if="showEpisodeMenu" class="episode-dropdown">
              <div class="episode-dropdown-header">快速切换分集</div>
              <div class="episode-search-box">
                <svg xmlns="http://www.w3.org/2000/svg" class="episode-search-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  ref="episodeSearchInput"
                  v-model="episodeSearch"
                  type="text"
                  class="episode-search-input"
                  placeholder="搜索分集标题..."
                  @keydown.down.prevent="moveEpisodeHighlight(1)"
                  @keydown.up.prevent="moveEpisodeHighlight(-1)"
                  @keydown.enter.prevent="selectHighlightedEpisode"
                  @keydown.esc.prevent="closeEpisodeMenu"
                >
              </div>
              <div v-if="filteredEpisodes.length" class="episode-options">
                <button
                  v-for="(episode, index) in filteredEpisodes"
                  :key="episode.id"
                  type="button"
                  class="episode-option"
                  :class="{
                    active: episode.id === project.id,
                    highlighted: highlightedEpisodeIndex === index,
                  }"
                  :disabled="episode.id === project.id || switchingEpisodeId === episode.id"
                  @mouseenter="highlightedEpisodeIndex = index"
                  @click="handleEpisodeSwitch(episode.id)"
                >
                  <div class="episode-option-main">
                    <span class="episode-option-title">{{ getEpisodeLabel(episode) }}</span>
                    <span class="episode-option-series">{{ episode.series_name || project.series_name || '当前作品' }}</span>
                  </div>
                  <span class="episode-option-status">{{ episode.status_display }}</span>
                </button>
              </div>
              <div v-else class="episode-empty">没有匹配的分集</div>
            </div>
          </transition>
        </div>
        <div class="ui-chip-block ui-chip-inline">
          <status-badge :status="project.status" type="project" />
        </div>
        <div class="meta-item ui-chip-block">
          <span class="meta-value">{{ formatDate(project.updated_at) }}</span>
        </div>

        <div v-if="project.prompt_set_name" class="meta-item ui-chip-block">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span class="meta-label">模板:</span>
          <span class="meta-value">{{ project.prompt_set_name }}</span>
        </div>

        <div v-if="project.jianying_draft_path" class="draft-info ui-chip-block">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="text-xs">剪映草稿已生成</span>
        </div>

        <div class="ui-chip-block ui-action-chip">
          <button
            class="btn btn-ghost btn-sm gap-2"
            :class="{ loading: isPipelineActionLoading }"
            :disabled="isPipelineActionLoading"
            @click="handlePipelineAction"
          >
            <svg
              v-if="!isPipelineActionLoading && pipelineActionType === 'run'"
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
            <svg
              v-else-if="!isPipelineActionLoading && pipelineActionType === 'pause'"
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
                d="M10 9v6m4-6v6m5-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <svg
              v-else-if="!isPipelineActionLoading && pipelineActionType === 'resume'"
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
            {{ pipelineActionLabel }}
          </button>
        </div>

        <div class="ui-chip-block ui-action-chip">
          <jianying-draft-button
            :project-id="project.id"
            :project="project"
            @generated="handleDraftGenerated"
          />
        </div>
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
          v-if="showStoryboardNode"
          :key="`storyboard-${index}`"
          :storyboard="storyboard"
          :index="index"
          :position="calculateStoryboardPosition(index)"
          @save="handleSaveStoryboard"
        />

        <!-- 文生图节点 -->
        <image-gen-node
          v-if="showImageNode(storyboard)"
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
          v-if="showCameraNode(storyboard)"
          :key="`camera-${index}`"
          :status="getCameraStatus(storyboard)"
          :position="calculateCameraPosition(index)"
          :movement-type="getCameraMovementType(storyboard)"
          :movement-params="getCameraMovementParams(storyboard)"
          :storyboard-id="storyboard.id"
          :camera-id="getCameraId(storyboard)"
          :can-generate="getImageStatus(storyboard) === 'completed'"
          @generate="handleGenerateCamera"
          @save="handleSaveCamera"
        />

        <!-- 视频生成节点 -->
        <video-gen-node
          v-if="showVideoNode(storyboard)"
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
      <div v-if="!showRewriteNode && !showStoryboardNode" class="empty-canvas">
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
    },
    episodes: {
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
      isPausingPipeline: false,
      isResumingPipeline: false,
      pipelineTaskId: null,
      pipelineChannel: null,
      showEpisodeMenu: false,
      switchingEpisodeId: null,
      episodeSearch: '',
      highlightedEpisodeIndex: 0
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
    currentEpisodeLabel() {
      return this.project?.display_name || this.project?.episode_title || this.truncatedProjectName;
    },
    filteredEpisodes() {
      const keyword = this.episodeSearch.trim().toLowerCase();
      if (!keyword) {
        return this.episodes;
      }
      return this.episodes.filter((episode) => {
        const label = this.getEpisodeLabel(episode) || '';
        const seriesName = episode.series_name || '';
        return label.toLowerCase().includes(keyword) || seriesName.toLowerCase().includes(keyword);
      });
    },
    pipelineActionType() {
      if (this.project?.status === 'processing') {
        return 'pause';
      }
      if (this.project?.status === 'paused') {
        return 'resume';
      }
      return 'run';
    },
    pipelineActionLabel() {
      if (this.isPausingPipeline) {
        return '暂停中...';
      }
      if (this.isResumingPipeline) {
        return '恢复中...';
      }
      if (this.isRunningPipeline) {
        return '启动中...';
      }
      if (this.pipelineActionType === 'pause') {
        return '暂停流程';
      }
      if (this.pipelineActionType === 'resume') {
        return '恢复流程';
      }
      return '运行流程';
    },
    isPipelineActionLoading() {
      return this.isRunningPipeline || this.isPausingPipeline || this.isResumingPipeline;
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
    storyboardStage() {
      return this.stages.find(s => s.stage_type === 'storyboard') || null;
    },
    showRewriteNode() {
      return this.rewriteStage?.template_enabled !== false;
    },
    showStoryboardNode() {
      return this.storyboardStage?.template_enabled !== false;
    },
    storyboards() {
      return this.storyboardStage?.domain_data?.storyboards || [];
    },
    connections() {
      const conns = [];

      // 文案改写 → 第一个分镜
      if (this.showRewriteNode && this.showStoryboardNode && this.storyboards.length > 0) {
        conns.push({
          id: 'rewrite-to-storyboard-0',
          from: 'rewrite',
          to: 'storyboard-0'
        });
      }

      // 每个分镜的连接线
      this.storyboards.forEach((storyboard, index) => {
        // 分镜 → 文生图
        if (this.showStoryboardNode && this.showImageNode(storyboard)) {
          conns.push({
            id: `storyboard-${index}-to-image-${index}`,
            from: `storyboard-${index}`,
            to: `image-${index}`
          });
        }

        // 文生图 → 运镜
        if (this.showImageNode(storyboard) && this.showCameraNode(storyboard)) {
          conns.push({
            id: `image-${index}-to-camera-${index}`,
            from: `image-${index}`,
            to: `camera-${index}`
          });
        }

        // 运镜 → 视频生成
        if (this.showCameraNode(storyboard) && this.showVideoNode(storyboard)) {
          conns.push({
            id: `camera-${index}-to-video-${index}`,
            from: `camera-${index}`,
            to: `video-${index}`
          });
        }

        // 分镜之间的连接（垂直）
        if (this.showStoryboardNode && index < this.storyboards.length - 1) {
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
      const positions = {};

      if (this.showRewriteNode) {
        positions.rewrite = {
          ...this.nodePositions.rewrite,
          width: 580,
          height: 400
        };
      }

      // 添加所有分镜及其子节点的位置
      this.storyboards.forEach((storyboard, index) => {
        // 分镜节点
        if (this.showStoryboardNode) {
          const storyboardPos = this.calculateStoryboardPosition(index);
          positions[`storyboard-${index}`] = {
            x: storyboardPos.x,
            y: storyboardPos.y,
            width: 280,
            height: 250
          };
        }

        // 文生图节点
        if (this.showImageNode(storyboard)) {
          const imagePos = this.calculateImagePosition(index);
          positions[`image-${index}`] = {
            x: imagePos.x,
            y: imagePos.y,
            width: 250,
            height: 250
          };
        }

        // 运镜节点
        if (this.showCameraNode(storyboard)) {
          const cameraPos = this.calculateCameraPosition(index);
          positions[`camera-${index}`] = {
            x: cameraPos.x,
            y: cameraPos.y,
            width: 250,
            height: 250
          };
        }

        // 视频生成节点
        if (this.showVideoNode(storyboard)) {
          const videoPos = this.calculateVideoPosition(index);
          positions[`video-${index}`] = {
            x: videoPos.x,
            y: videoPos.y,
            width: 250,
            height: 250
          };
        }
      });

      return positions;
    }
  },
  mounted() {
    document.addEventListener('click', this.handleDocumentClick);
    // 调试信息
    console.log('[ProjectCanvas] Mounted');
    console.log('[ProjectCanvas] Project:', this.project);
    console.log('[ProjectCanvas] Stages:', this.stages);
    console.log('[ProjectCanvas] Storyboards:', this.storyboards);
    console.log('[ProjectCanvas] AllNodePositions:', this.allNodePositions);
  },
  watch: {
    '$route.params.id'() {
      this.showEpisodeMenu = false;
      this.switchingEpisodeId = null;
      this.episodeSearch = '';
      this.highlightedEpisodeIndex = 0;
    },
    showEpisodeMenu(isOpen) {
      if (isOpen) {
        this.episodeSearch = '';
        this.highlightedEpisodeIndex = this.filteredEpisodes.findIndex((episode) => episode.id !== this.project.id);
        if (this.highlightedEpisodeIndex < 0) {
          this.highlightedEpisodeIndex = 0;
        }
        this.$nextTick(() => {
          this.$refs.episodeSearchInput?.focus();
        });
      }
    },
    episodeSearch() {
      this.highlightedEpisodeIndex = 0;
    },
    storyboards: {
      deep: true,
      handler(newVal) {
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

        // 如果项目状态变更为稳定态，重置流程操作按钮
        if (['completed', 'failed', 'paused', 'processing', 'draft'].includes(newStatus)) {
          this.isRunningPipeline = false;
          this.isPausingPipeline = false;
          this.isResumingPipeline = false;
        }

        if (this.isRunningPipeline && (newStatus === 'completed' || newStatus === 'failed' || newStatus === 'paused')) {
          this.pipelineTaskId = null;
          this.pipelineChannel = null;
        }
      }
    }
  },
  methods: {
    formatDate,
    getEpisodeLabel(episode) {
      return episode.display_name || episode.episode_title || episode.name;
    },
    toggleEpisodeMenu() {
      if (!this.episodes.length) {
        return;
      }
      this.showEpisodeMenu = !this.showEpisodeMenu;
    },
    closeEpisodeMenu() {
      this.showEpisodeMenu = false;
    },
    moveEpisodeHighlight(step) {
      if (!this.filteredEpisodes.length) {
        return;
      }
      const total = this.filteredEpisodes.length;
      this.highlightedEpisodeIndex = (this.highlightedEpisodeIndex + step + total) % total;
    },
    selectHighlightedEpisode() {
      const target = this.filteredEpisodes[this.highlightedEpisodeIndex];
      if (!target) {
        return;
      }
      this.handleEpisodeSwitch(target.id);
    },
    handleDocumentClick(event) {
      if (!this.showEpisodeMenu) {
        return;
      }
      if (!this.$el.contains(event.target)) {
        this.closeEpisodeMenu();
      }
    },
    handleEpisodeSwitch(episodeId) {
      if (!episodeId || episodeId === this.project.id) {
        this.closeEpisodeMenu();
        return;
      }
      this.switchingEpisodeId = episodeId;
      this.closeEpisodeMenu();
      this.$router.push({ name: 'ProjectDetail', params: { id: episodeId } }).finally(() => {
        this.switchingEpisodeId = null;
      });
    },

    showImageNode(storyboard) {
      return storyboard?.image_generation?.template_enabled !== false;
    },

    showCameraNode(storyboard) {
      return storyboard?.camera_movement?.template_enabled !== false;
    },

    showVideoNode(storyboard) {
      return storyboard?.video_generation?.template_enabled !== false;
    },

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
      const images = storyboard.image_generation?.images;
      if (images && images.length > 0) {
        return images[0].image_url;
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

    getCameraId(storyboard) {
      if (storyboard.camera_movement?.data) {
        return storyboard.camera_movement.data.id;
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
      const videos = storyboard.video_generation?.videos;
      if (videos && videos.length > 0) {
        return videos[0].video_url;
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
        const imageUrl = storyboard.image_generation?.images?.[0]?.image_url;
        if (!imageUrl) {
          this.$message?.warning('请先生成图片');
          this.$set(this.executingNodes.cameras, storyboardId, false);
          return;
        }

        const inputData = {
          storyboard_ids: [storyboardId],
          scenes: [{
            scene_number: storyboard.sequence_number,
            image_url: imageUrl,
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
        const imageUrl = storyboard.image_generation?.images?.[0]?.image_url;
        if (!imageUrl) {
          this.$message?.warning('请先生成图片');
          this.$set(this.executingNodes.videos, storyboardId, false);
          return;
        }

        const inputData = {
          storyboard_ids: [storyboardId],
          scenes: [{
            scene_number: storyboard.sequence_number,
            image_url: imageUrl,
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

    handleSaveCamera({ cameraId, data, silent }) {
      this.$emit('save-camera', { cameraId, data, silent });
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

    async handlePausePipeline() {
      console.log('[ProjectCanvas] 暂停完整流程');

      try {
        this.isPausingPipeline = true;

        const response = await this.$store.dispatch('projects/pauseProject', this.project.id);

        this.isRunningPipeline = false;
        this.pipelineTaskId = null;
        this.pipelineChannel = null;

        this.$emit('pipeline-paused', response);
        this.$message?.success(response.message || '工作流已暂停');
      } catch (error) {
        console.error('[ProjectCanvas] 暂停工作流失败:', error);
        this.$message?.error(error.response?.data?.error || error.message || '暂停工作流失败');
      } finally {
        this.isPausingPipeline = false;
      }
    },

    async handleResumePipeline() {
      console.log('[ProjectCanvas] 恢复完整流程');

      try {
        this.isResumingPipeline = true;

        const response = await this.$store.dispatch('projects/resumeProject', this.project.id);

        this.pipelineTaskId = response.task_id;
        this.pipelineChannel = response.channel;

        this.$emit('pipeline-started', {
          taskId: this.pipelineTaskId,
          channel: this.pipelineChannel,
          resumed: true
        });

        this.$message?.success(response.message || '工作流已恢复');
      } catch (error) {
        console.error('[ProjectCanvas] 恢复工作流失败:', error);
        this.$message?.error(error.response?.data?.error || error.message || '恢复工作流失败');
      } finally {
        this.isResumingPipeline = false;
      }
    },

    handlePipelineAction() {
      if (this.pipelineActionType === 'pause') {
        this.handlePausePipeline();
        return;
      }

      if (this.pipelineActionType === 'resume') {
        this.handleResumePipeline();
        return;
      }

      this.handleRunPipeline();
    },

    /**
     * 设置阶段的 loading 状态
     * @param {string} stageName - 阶段名称
     * @param {boolean} isLoading - 是否正在加载
     */
    setStageLoading(stageName, isLoading) {
      console.log('[ProjectCanvas] 设置阶段 loading:', stageName, isLoading);
      if (Object.prototype.hasOwnProperty.call(this.executingStages, stageName)) {
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
  },
  beforeDestroy() {
    document.removeEventListener('click', this.handleDocumentClick);
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
  min-height: 0;
  flex: 1;
}

.canvas-wrapper {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
}

.project-info-node {
  position: absolute;
  top: 1rem;
  left: 1rem;
  right: 1rem;
  z-index: 200;
  background: transparent;
  border: none;
  padding: 0;
  box-shadow: none;
  backdrop-filter: none;
  pointer-events: none;
}

.project-info-main {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.ui-chip-block {
  position: relative;
  pointer-events: auto;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 999px;
  box-shadow: none;
  backdrop-filter: none;
}

.layout-shell.theme-dark .ui-chip-block {
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}

.is-title-chip {
  background: rgba(255, 255, 255, 0.72);
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.layout-shell.theme-dark .is-title-chip {
  background: rgba(15, 23, 42, 0.68);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 10px 24px rgba(2, 6, 23, 0.45);
}

.ui-chip-inline {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.25rem;
}

.ui-action-chip {
  padding: 0.2rem;
}

.project-title-switcher {
  position: relative;
}

.project-title-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.55rem 0.85rem;
  border: none;
  background: transparent;
  cursor: pointer;
}

.project-name {
  max-width: 260px;
  cursor: pointer;
  margin: 0;
  color: #0f172a;
}

.layout-shell.theme-dark .project-name {
  color: #e2e8f0;
}

.title-chevron {
  width: 1rem;
  height: 1rem;
  color: #64748b;
  transition: transform 0.2s ease;
}

.title-chevron.open {
  transform: rotate(180deg);
}

.episode-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  width: 340px;
  max-height: 360px;
  overflow-y: auto;
  padding: 0.75rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(10px);
}

.layout-shell.theme-dark .episode-dropdown {
  background: rgba(15, 23, 42, 0.96);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 18px 36px rgba(2, 6, 23, 0.65);
}

.episode-dropdown-header {
  margin-bottom: 0.5rem;
  padding: 0 0.25rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
}

.episode-search-box {
  position: relative;
  margin-bottom: 0.65rem;
}

.episode-search-icon {
  position: absolute;
  left: 0.85rem;
  top: 50%;
  width: 0.95rem;
  height: 0.95rem;
  color: #94a3b8;
  transform: translateY(-50%);
}

.episode-search-input {
  width: 100%;
  padding: 0.75rem 0.85rem 0.75rem 2.45rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
  color: #0f172a;
  outline: none;
}

.layout-shell.theme-dark .episode-search-input {
  background: rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.24);
  color: #e2e8f0;
}

.episode-search-input:focus {
  border-color: rgba(20, 184, 166, 0.5);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.14);
}

.episode-options {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.episode-option {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.8rem 0.9rem;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.episode-option:hover:not(:disabled),
.episode-option.highlighted:not(:disabled) {
  background: rgba(148, 163, 184, 0.08);
  border-color: rgba(20, 184, 166, 0.28);
  transform: translateY(-1px);
}

.layout-shell.theme-dark .episode-option:hover:not(:disabled),
.layout-shell.theme-dark .episode-option.highlighted:not(:disabled) {
  background: rgba(148, 163, 184, 0.12);
}

.episode-option.active {
  background: rgba(20, 184, 166, 0.12);
  border-color: rgba(20, 184, 166, 0.35);
}

.layout-shell.theme-dark .episode-option.active {
  background: rgba(94, 234, 212, 0.15);
  border-color: rgba(94, 234, 212, 0.35);
}

.episode-option:disabled {
  cursor: default;
}

.episode-option-main {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.episode-option-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .episode-option-title {
  color: #e2e8f0;
}

.episode-option-series,
.episode-option-status,
.episode-empty {
  font-size: 0.78rem;
  color: #64748b;
}

.episode-empty {
  padding: 0.75rem 0.5rem 0.25rem;
  text-align: center;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: #64748b;
  padding: 0.55rem 0.8rem;
}

.layout-shell.theme-dark .meta-item {
  color: #cbd5e1;
}

.meta-label {
  font-weight: 600;
}

.meta-value {
  color: inherit;
}

.draft-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.85rem;
  color: #0f766e;
  font-size: 0.75rem;
}

.layout-shell.theme-dark .draft-info {
  color: #99f6e4;
}

.project-info-node :deep(.btn.btn-ghost),
.project-info-node :deep(.btn.btn-primary),
.project-info-node :deep(.btn.btn-outline) {
  border-radius: 999px;
}

.project-info-node :deep(.btn.btn-ghost) {
  background: #ffffff;
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.12);
}

.project-info-node :deep(.btn.btn-ghost:hover) {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.layout-shell.theme-dark .project-info-node :deep(.btn.btn-ghost) {
  background: rgba(15, 23, 42, 0.9);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.25);
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

.episode-dropdown-enter-active,
.episode-dropdown-leave-active {
  transition: all 0.18s ease;
}

.episode-dropdown-enter,
.episode-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 768px) {
  .project-info-node {
    left: 0.75rem;
    right: 0.75rem;
    top: 0.75rem;
  }

  .project-name {
    max-width: none;
    width: 100%;
  }

  .episode-dropdown {
    width: min(340px, calc(100vw - 2.5rem));
  }
}
</style>
