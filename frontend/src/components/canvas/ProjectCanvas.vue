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
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="title-chevron"
              :class="{ open: showEpisodeMenu }"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          <transition name="episode-dropdown">
            <div
              v-if="showEpisodeMenu"
              class="episode-dropdown"
            >
              <div class="episode-dropdown-header">
                快速切换分集
              </div>
              <div class="episode-search-box">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="episode-search-icon"
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
              <div
                v-if="filteredEpisodes.length"
                class="episode-options"
              >
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
              <div
                v-else
                class="episode-empty"
              >
                没有匹配的分集
              </div>
            </div>
          </transition>
        </div>
        <div class="ui-chip-block ui-chip-inline">
          <status-badge
            :status="project.status"
            type="project"
          />
        </div>
        <div class="meta-item ui-chip-block">
          <span class="meta-value">{{ formatDate(project.updated_at) }}</span>
        </div>

        <div
          v-if="project.prompt_set_name"
          class="meta-item ui-chip-block"
        >
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
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <span class="meta-label">模板:</span>
          <span class="meta-value">{{ project.prompt_set_name }}</span>
        </div>

        <div class="ui-chip-block ui-action-chip">
          <button
            ref="assetDrawerToggle"
            class="btn btn-ghost btn-sm gap-2"
            :class="{ loading: loadingAssets || savingAssetBindings }"
            :disabled="loadingAssets || savingAssetBindings"
            @click.stop="toggleAssetDrawer"
          >
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
                d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
              />
            </svg>
            资产 {{ boundAssets.length }}
          </button>
        </div>

        <div
          v-if="project.jianying_draft_path"
          class="draft-info ui-chip-block"
        >
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
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
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

      <transition name="episode-dropdown">
        <div
          v-if="showAssetDrawer"
          ref="assetDrawer"
          class="asset-drawer-card prevent-canvas-wheel"
          @click.stop
        >
          <div class="asset-drawer-header">
            <div>
              <div class="asset-drawer-title">
                资产变量
              </div>
              <div class="asset-drawer-subtitle">
                绑定后在节点输入 <code>`{ {`</code> 即可联想选择变量
              </div>
            </div>
            <button
              class="btn btn-ghost btn-xs"
              @click.stop="showAssetDrawer = false"
            >
              关闭
            </button>
          </div>

          <div
            v-if="loadingAssets"
            class="asset-drawer-empty"
          >
            正在加载可用变量...
          </div>
          <div
            v-else-if="!availableAssets.length"
            class="asset-drawer-empty"
          >
            暂无可绑定变量
          </div>
          <div
            v-else
            class="asset-drawer-list"
          >
            <label
              v-for="asset in availableAssets"
              :key="asset.id"
              class="asset-drawer-item"
            >
              <input
                :checked="selectedAssetIds.includes(asset.id)"
                type="checkbox"
                class="checkbox checkbox-sm"
                @change.stop="handleAssetBindingToggle(asset.id)"
              >
              <div class="asset-drawer-meta">
                <div class="asset-drawer-key-row">
                  <code class="asset-drawer-key">{{ asset.key }}</code>
                  <span
                    v-if="asset.group"
                    class="asset-drawer-group"
                  >{{ asset.group }}</span>
                </div>
                <div class="asset-drawer-type">{{ asset.variable_type_display }} · {{ asset.scope_display }}</div>
              </div>
            </label>
          </div>
        </div>
      </transition>
    </div>

    <div class="canvas-wrapper">
      <flow-canvas
        ref="flowCanvas"
        :connections="connections"
        :nodes="allNodePositions"
      >
        <!-- 文案改写节点 -->
        <rewrite-node-expanded
          v-if="project"
          :status="rewriteStage ? rewriteStage.status : 'pending'"
          :position="nodePositions.rewrite"
          :data="rewriteStage ? rewriteStage.domain_data : null"
          :show-rewrite-node="showRewriteNode"
          :asset-options="boundAssets"
          :original-topic="project.original_topic"
          :project-id="project.id"
          @execute="handleExecuteStage"
          @save="handleSaveStage"
          @storyboard-generated="$emit('storyboard-generated')"
          @node-dblclick="focusCanvasNode('rewrite')"
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
            :asset-options="boundAssets"
            :is-highlighted="Boolean(nodeHighlights.storyboards[storyboard.id])"
            @node-dblclick="focusCanvasNode(`storyboard-${index}`)"
            @save="handleSaveStoryboard"
            @chat-edit="handleOpenStoryboardChat"
          />

          <!-- 文生图节点 -->
          <image-gen-node
            v-if="showImageNode(storyboard)"
            :key="`image-${index}`"
            :status="getImageStatus(storyboard)"
            :position="calculateImagePosition(index)"
            :image-url="getImageUrl(storyboard)"
            :media-width="getStoryboardMediaDimensions(storyboard).width"
            :media-height="getStoryboardMediaDimensions(storyboard).height"
            :prompt="storyboard.image_prompt"
            :storyboard-id="storyboard.id"
            @node-dblclick="focusCanvasNode(`image-${index}`)"
            @generate="handleGenerateImage"
            @media-loaded="handleImageMediaLoaded"
            @save="handleSaveStoryboard"
          />

          <!-- 多宫格节点 -->
          <multi-grid-image-node
            v-if="showMultiGridNode(storyboard)"
            :key="`multi-grid-${index}`"
            :status="getMultiGridStatus(storyboard)"
            :position="calculateMultiGridPosition(index)"
            :source-image-url="getMultiGridSourceUrl(storyboard)"
            :tasks="getMultiGridTasks(storyboard)"
            :media-width="getStoryboardMediaDimensions(storyboard).width"
            :media-height="getStoryboardMediaDimensions(storyboard).height"
            :storyboard-id="storyboard.id"
            @node-dblclick="focusCanvasNode(`multi-grid-${index}`)"
            @generate="handleGenerateMultiGridImage"
            @media-loaded="handleImageMediaLoaded"
          />

          <!-- 图片编辑节点 -->
          <image-edit-node
            v-if="showImageEditNode(storyboard)"
            :key="`image-edit-${index}`"
            :status="getImageEditStatus(storyboard)"
            :position="calculateImageEditPosition(index)"
            :results="getImageEditResults(storyboard)"
            :media-width="getStoryboardMediaDimensions(storyboard).width"
            :media-height="getStoryboardMediaDimensions(storyboard).height"
            :storyboard-id="storyboard.id"
            :can-generate="getMultiGridStatus(storyboard) === 'completed'"
            @node-dblclick="focusCanvasNode(`image-edit-${index}`)"
            @generate="handleGenerateImageEdit"
            @media-loaded="handleImageMediaLoaded"
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
            :can-generate="getCameraInputStatus(storyboard) === 'completed'"
            :is-highlighted="Boolean(nodeHighlights.cameras[getCameraId(storyboard) || storyboard.id])"
            @node-dblclick="focusCanvasNode(`camera-${index}`)"
            @generate="handleGenerateCamera"
            @save="handleSaveCamera"
            @chat-edit="handleOpenCameraChat"
          />

          <!-- 视频生成节点 -->
          <video-gen-node
            v-if="showVideoNode(storyboard)"
            :key="`video-${index}`"
            :status="getVideoStatus(storyboard)"
            :position="calculateVideoPosition(index)"
            :video-url="getVideoUrl(storyboard)"
            :video-info="getVideoInfo(storyboard)"
            :media-width="getStoryboardMediaDimensions(storyboard).width"
            :media-height="getStoryboardMediaDimensions(storyboard).height"
            :storyboard-id="storyboard.id"
            :can-generate="getCameraStatus(storyboard) === 'completed' && getCameraInputStatus(storyboard) === 'completed'"
            @node-dblclick="focusCanvasNode(`video-${index}`)"
            @generate="handleGenerateVideo"
          />
        </template>

        <!-- 空状态提示 -->
        <div
          v-if="!showRewriteNode && !showStoryboardNode"
          class="empty-canvas"
        >
          <div class="empty-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-16 w-16"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <div class="empty-text">
            暂无工作流数据
          </div>
          <div class="empty-hint">
            请先执行文案改写阶段
          </div>
        </div>
      </flow-canvas>
    </div>

    <node-chat-drawer
      ref="nodeChatDrawer"
      :visible="nodeChat.visible"
      :title="nodeChatTitle"
      :subtitle="nodeChatSubtitle"
      :summary="nodeChatSummary"
      :value="nodeChat.input"
      :messages="nodeChat.messages"
      :quick-actions="nodeChatQuickActions"
      :streaming="nodeChat.streaming"
      :applying="nodeChat.applying"
      @close="closeNodeChatDrawer"
      @input="handleNodeChatInput"
      @submit="submitNodeChat"
      @stop="stopNodeChat"
      @apply="applyNodeChatMessage"
      @quick-action="applyNodeQuickAction"
    />
  </div>
</template>

<script>
import FlowCanvas from './FlowCanvas.vue';
import RewriteNodeExpanded from './RewriteNodeExpanded.vue';
import StoryboardNode from './StoryboardNode.vue';
import ImageGenNode from './ImageGenNode.vue';
import MultiGridImageNode from './MultiGridImageNode.vue';
import ImageEditNode from './ImageEditNode.vue';
import CameraNode from './CameraNode.vue';
import VideoGenNode from './VideoGenNode.vue';
import NodeChatDrawer from './NodeChatDrawer.vue';
import StatusBadge from '@/components/common/StatusBadge.vue';
import JianyingDraftButton from '@/components/projects/JianyingDraftButton.vue';
import projectsAPI from '@/api/projects';
import store from '@/store';
import { formatDate } from '@/utils/helpers';

export default {
  name: 'ProjectCanvas',
  components: {
    FlowCanvas,
    RewriteNodeExpanded,
    StoryboardNode,
    ImageGenNode,
    MultiGridImageNode,
    ImageEditNode,
    CameraNode,
    VideoGenNode,
    NodeChatDrawer,
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
    modelConfig: {
      type: Object,
      default: null
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
        multiGridImages: {},
        imageEdits: {},
        cameras: {}, // { storyboardId: true }
        videos: {} // { storyboardId: true }
      },
      nodeHighlights: {
        storyboards: {},
        cameras: {},
      },
      // 跟踪正在执行的阶段（用于整个阶段的 loading 状态）
      executingStages: {
        rewrite: false,
        storyboard: false,
        image_generation: false,
        multi_grid_image: false,
        image_edit: false,
        camera_movement: false,
        video_generation: false
      },
      // 运行流程状态
      isRunningPipeline: false,
      isPausingPipeline: false,
      isResumingPipeline: false,
      pipelineTaskId: null,
      pipelineChannel: null,
      loadingAssets: false,
      savingAssetBindings: false,
      showAssetDrawer: false,
      availableAssets: [],
      selectedAssetIds: [],
      runtimeMediaDimensions: {},
      showEpisodeMenu: false,
      switchingEpisodeId: null,
      episodeSearch: '',
      highlightedEpisodeIndex: 0,
      nodeChat: {
        visible: false,
        type: '',
        nodeId: null,
        storyboardId: null,
        cameraId: null,
        input: '',
        messages: [],
        streaming: false,
        applying: false,
        streamRequestId: 0,
        abortController: null,
      }
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
        rewrite: {
          x: this.treeLayout.rewriteX,
          y: this.treeLayout.rowY.rewrite || this.nodeMetrics.startY
        }
      };
    },
    nodeMetrics() {
      return {
        rewrite: { width: 620, height: 300 },
        storyboard: { width: 280, height: 250 },
        media: { width: 250, headerHeight: 50, minPreviewHeight: 140 },
        multiGrid: { width: 250, headerHeight: 58, minPreviewHeight: 120, minTilesHeight: 110 },
        imageEdit: { width: 250, headerHeight: 58, minPreviewHeight: 120, minResultsHeight: 80 },
        camera: { width: 250, height: 280 },
        startX: 80,
        startY: 60,
        columnGap: 60,
        rowGap: 90,
        rewriteRowGap: 60
      };
    },
    treeLayout() {
      const branchWidth = Math.max(
        this.nodeMetrics.storyboard.width,
        this.nodeMetrics.media.width,
        this.nodeMetrics.multiGrid.width,
        this.nodeMetrics.imageEdit.width,
        this.nodeMetrics.camera.width
      );
      const columnCount = Math.max(this.storyboards.length, 1);
      const totalWidth = columnCount * branchWidth + (columnCount - 1) * this.nodeMetrics.columnGap;
      const rowY = {};
      let currentY = this.nodeMetrics.startY;

      const stageRows = [
        {
          key: 'rewrite',
          visible: true,
          height: this.nodeMetrics.rewrite.height,
        },
        {
          key: 'storyboard',
          visible: this.showStoryboardNode && this.storyboards.length > 0,
          height: this.nodeMetrics.storyboard.height,
        },
        {
          key: 'image',
          visible: this.storyboards.some(storyboard => this.showImageNode(storyboard)),
          height: Math.max(
            this.nodeMetrics.media.headerHeight + this.nodeMetrics.media.minPreviewHeight,
            ...this.storyboards
              .filter(storyboard => this.showImageNode(storyboard))
              .map(storyboard => this.getImageNodeHeight(storyboard))
          ),
        },
        {
          key: 'multiGrid',
          visible: this.storyboards.some(storyboard => this.showMultiGridNode(storyboard)),
          height: Math.max(
            this.nodeMetrics.multiGrid.headerHeight + this.nodeMetrics.multiGrid.minPreviewHeight + this.nodeMetrics.multiGrid.minTilesHeight,
            ...this.storyboards
              .filter(storyboard => this.showMultiGridNode(storyboard))
              .map(storyboard => this.getMultiGridNodeHeight(storyboard))
          ),
        },
        {
          key: 'imageEdit',
          visible: this.storyboards.some(storyboard => this.showImageEditNode(storyboard)),
          height: Math.max(
            this.nodeMetrics.imageEdit.headerHeight + this.nodeMetrics.imageEdit.minPreviewHeight + this.nodeMetrics.imageEdit.minResultsHeight,
            ...this.storyboards
              .filter(storyboard => this.showImageEditNode(storyboard))
              .map(storyboard => this.getImageEditNodeHeight(storyboard))
          ),
        },
        {
          key: 'camera',
          visible: this.storyboards.some(storyboard => this.showCameraNode(storyboard)),
          height: this.nodeMetrics.camera.height,
        },
        {
          key: 'video',
          visible: this.storyboards.some(storyboard => this.showVideoNode(storyboard)),
          height: Math.max(
            this.nodeMetrics.media.headerHeight + this.nodeMetrics.media.minPreviewHeight,
            ...this.storyboards
              .filter(storyboard => this.showVideoNode(storyboard))
              .map(storyboard => this.getVideoNodeHeight(storyboard))
          ),
        },
      ];

      stageRows.forEach((row, index) => {
        if (!row.visible) {
          return;
        }

        rowY[row.key] = currentY;

        const nextVisibleRow = stageRows.slice(index + 1).find(item => item.visible);
        if (!nextVisibleRow) {
          return;
        }

        const gap = row.key === 'rewrite'
          ? this.nodeMetrics.rewriteRowGap
          : this.nodeMetrics.rowGap;

        currentY += row.height + gap;
      });

      return {
        branchWidth,
        columnCount,
        totalWidth,
        rowY,
        rewriteX: this.nodeMetrics.startX + ((totalWidth - this.nodeMetrics.rewrite.width) / 2),
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
    boundAssets() {
      const selectedIds = new Set(this.selectedAssetIds);
      return this.availableAssets.filter(asset => selectedIds.has(asset.id));
    },
    nodeChatTargetStoryboard() {
      if (!this.nodeChat.storyboardId) {
        return null;
      }
      return this.storyboards.find(item => item.id === this.nodeChat.storyboardId) || null;
    },
    nodeChatTitle() {
      if (this.nodeChat.type === 'storyboard') {
        const sequence = this.nodeChatTargetStoryboard?.sequence_number || '';
        return sequence ? `分镜 ${sequence} 对话修改` : '分镜对话修改';
      }
      const sequence = this.nodeChatTargetStoryboard?.sequence_number || '';
      return sequence ? `分镜 ${sequence} 运镜对话修改` : '运镜对话修改';
    },
    nodeChatSubtitle() {
      if (this.nodeChat.type === 'storyboard') {
        return '多轮修改场景、旁白和出图提示词，完成后可一键应用';
      }
      return '围绕当前运镜参数进行微调，完成后可一键应用';
    },
    nodeChatSummary() {
      const storyboard = this.nodeChatTargetStoryboard;
      if (!storyboard) {
        return '';
      }
      if (this.nodeChat.type === 'storyboard') {
        return [
          `场景：${storyboard.scene_description || '暂无'}`,
          `旁白：${storyboard.narration_text || '暂无'}`,
          `图片提示词：${storyboard.image_prompt || '暂无'}`,
          `时长：${storyboard.duration_seconds || 3}s`,
        ].join('\n');
      }
      const camera = storyboard.camera_movement?.data || {};
      const movementParams = camera.movement_params || {};
      return [
        `关联分镜：${storyboard.scene_description || `分镜 ${storyboard.sequence_number}`}`,
        `运镜类型：${camera.movement_type || '暂无'}`,
        `运镜描述：${movementParams.description || movementParams.raw_text || '暂无'}`,
      ].join('\n');
    },
    nodeChatQuickActions() {
      if (this.nodeChat.type === 'storyboard') {
        return ['更电影感', '加强环境细节', '压缩旁白', '更适合出图'];
      }
      return ['更平稳', '更有推进感', '减少晃动', '更适合图生视频'];
    },
    connections() {
      const conns = [];

      // 文案改写 → 每个分镜
      if (this.showRewriteNode && this.showStoryboardNode && this.storyboards.length > 0) {
        this.storyboards.forEach((storyboard, index) => {
          conns.push({
            id: `rewrite-to-storyboard-${index}`,
            from: 'rewrite',
            to: `storyboard-${index}`
          });
        });
      }

      // 每个分镜的连接线
      this.storyboards.forEach((storyboard, index) => {
        if (this.showStoryboardNode && this.showImageNode(storyboard)) {
          conns.push({
            id: `storyboard-${index}-to-image-${index}`,
            from: `storyboard-${index}`,
            to: `image-${index}`
          });
        }

        if (this.showStoryboardNode && this.showMultiGridNode(storyboard)) {
          conns.push({
            id: `storyboard-${index}-to-multi-grid-${index}`,
            from: `storyboard-${index}`,
            to: `multi-grid-${index}`
          });
        }

        if (this.showMultiGridNode(storyboard) && this.showImageEditNode(storyboard)) {
          conns.push({
            id: `multi-grid-${index}-to-image-edit-${index}`,
            from: `multi-grid-${index}`,
            to: `image-edit-${index}`
          });
        }

        if (this.showCameraNode(storyboard) && this.showVideoNode(storyboard)) {
          conns.push({
            id: `camera-${index}-to-video-${index}`,
            from: `camera-${index}`,
            to: `video-${index}`
          });
        }

        if (this.showImageEditNode(storyboard) && this.showCameraNode(storyboard)) {
          conns.push({
            id: `image-edit-${index}-to-camera-${index}`,
            from: `image-edit-${index}`,
            to: `camera-${index}`
          });
        } else if (this.showMultiGridNode(storyboard) && this.showCameraNode(storyboard)) {
          conns.push({
            id: `multi-grid-${index}-to-camera-${index}`,
            from: `multi-grid-${index}`,
            to: `camera-${index}`
          });
        } else if (this.showImageNode(storyboard) && this.showCameraNode(storyboard)) {
          conns.push({
            id: `image-${index}-to-camera-${index}`,
            from: `image-${index}`,
            to: `camera-${index}`
          });
        }
      });

      return conns;
    },
    // 计算所有节点的位置信息（用于画布自动适配和连接线计算）
    allNodePositions() {
      const positions = {};

      positions.rewrite = {
        ...this.nodePositions.rewrite,
        width: this.nodeMetrics.rewrite.width,
        height: this.nodeMetrics.rewrite.height
      };

      // 添加所有分镜及其子节点的位置
      this.storyboards.forEach((storyboard, index) => {
        // 分镜节点
        if (this.showStoryboardNode) {
          const storyboardPos = this.calculateStoryboardPosition(index);
          positions[`storyboard-${index}`] = {
            x: storyboardPos.x,
            y: storyboardPos.y,
            width: this.nodeMetrics.storyboard.width,
            height: this.nodeMetrics.storyboard.height
          };
        }

        // 文生图节点
        if (this.showImageNode(storyboard)) {
          const imagePos = this.calculateImagePosition(index);
          positions[`image-${index}`] = {
            x: imagePos.x,
            y: imagePos.y,
            width: this.nodeMetrics.media.width,
            height: this.getImageNodeHeight(storyboard)
          };
        }

        if (this.showMultiGridNode(storyboard)) {
          const multiGridPos = this.calculateMultiGridPosition(index);
          positions[`multi-grid-${index}`] = {
            x: multiGridPos.x,
            y: multiGridPos.y,
            width: this.nodeMetrics.multiGrid.width,
            height: this.getMultiGridNodeHeight(storyboard)
          };
        }

        if (this.showImageEditNode(storyboard)) {
          const imageEditPos = this.calculateImageEditPosition(index);
          positions[`image-edit-${index}`] = {
            x: imageEditPos.x,
            y: imageEditPos.y,
            width: this.nodeMetrics.imageEdit.width,
            height: this.getImageEditNodeHeight(storyboard)
          };
        }

        // 运镜节点
        if (this.showCameraNode(storyboard)) {
          const cameraPos = this.calculateCameraPosition(index);
          positions[`camera-${index}`] = {
            x: cameraPos.x,
            y: cameraPos.y,
            width: this.nodeMetrics.camera.width,
            height: this.nodeMetrics.camera.height
          };
        }

        // 视频生成节点
        if (this.showVideoNode(storyboard)) {
          const videoPos = this.calculateVideoPosition(index);
          positions[`video-${index}`] = {
            x: videoPos.x,
            y: videoPos.y,
            width: this.nodeMetrics.media.width,
            height: this.getVideoNodeHeight(storyboard)
          };
        }
      });

      return positions;
    }
  },
  watch: {
    '$route.params.id'() {
      this.showEpisodeMenu = false;
      this.showAssetDrawer = false;
      this.switchingEpisodeId = null;
      this.episodeSearch = '';
      this.highlightedEpisodeIndex = 0;
      this.availableAssets = [];
      this.selectedAssetIds = [];
      this.resetNodeChatState();
      this.loadProjectAssets();
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
          if (storyboard.image_generation?.images && storyboard.image_generation.images.length > 0) {
            this.$set(this.executingNodes.images, storyboard.id, false);
          }
          if (storyboard.multi_grid_image?.tasks && storyboard.multi_grid_image.tasks.length > 0) {
            this.$set(this.executingNodes.multiGridImages, storyboard.id, false);
          }
          if (storyboard.image_edit?.results && storyboard.image_edit.results.length > 0) {
            this.$set(this.executingNodes.imageEdits, storyboard.id, false);
          }
          if (storyboard.camera_movement?.data) {
            this.$set(this.executingNodes.cameras, storyboard.id, false);
          }
          if (storyboard.video_generation?.videos && storyboard.video_generation.videos.length > 0) {
            this.$set(this.executingNodes.videos, storyboard.id, false);
          }
        });
      }
    },
    'project.asset_bindings': {
      immediate: true,
      handler(bindings) {
        if (!Array.isArray(bindings)) {
          return;
        }
        this.selectedAssetIds = bindings
          .map(binding => binding?.asset?.id)
          .filter(Boolean);
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
  mounted() {
    document.addEventListener('click', this.handleDocumentClick);
    this.loadProjectAssets();
    // 调试信息
    console.log('[ProjectCanvas] Mounted');
    console.log('[ProjectCanvas] Project:', this.project);
    console.log('[ProjectCanvas] Stages:', this.stages);
    console.log('[ProjectCanvas] Storyboards:', this.storyboards);
    console.log('[ProjectCanvas] AllNodePositions:', this.allNodePositions);
  },
  beforeDestroy() {
    document.removeEventListener('click', this.handleDocumentClick);
    this.resetNodeChatState();
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
      const target = event.target;

      if (this.showEpisodeMenu && !this.$el.contains(target)) {
        this.closeEpisodeMenu();
      }

      if (this.showAssetDrawer) {
        const drawer = this.$refs.assetDrawer;
        const toggle = this.$refs.assetDrawerToggle;
        const clickedInsideDrawer = drawer && drawer.contains(target);
        const clickedToggle = toggle && toggle.contains(target);
        if (!clickedInsideDrawer && !clickedToggle) {
          this.showAssetDrawer = false;
        }
      }
    },
    createChatMessage(role, content = '', extra = {}) {
      return {
        id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role,
        content,
        ...extra,
      };
    },
    resetNodeChatState() {
      if (this.nodeChat.abortController) {
        this.nodeChat.abortController.abort();
      }
      this.nodeChat = {
        visible: false,
        type: '',
        nodeId: null,
        storyboardId: null,
        cameraId: null,
        input: '',
        messages: [],
        streaming: false,
        applying: false,
        streamRequestId: this.nodeChat.streamRequestId || 0,
        abortController: null,
      };
    },
    openNodeChatDrawer(payload) {
      this.nodeChat.visible = true;
      this.nodeChat.type = payload.type;
      this.nodeChat.nodeId = payload.nodeId;
      this.nodeChat.storyboardId = payload.storyboardId;
      this.nodeChat.cameraId = payload.cameraId || null;
      this.nodeChat.input = payload.defaultMessage || '';
      this.nodeChat.messages = [];
      this.nodeChat.streaming = false;
      this.nodeChat.applying = false;
      if (this.nodeChat.abortController) {
        this.nodeChat.abortController.abort();
        this.nodeChat.abortController = null;
      }
    },
    handleOpenStoryboardChat({ storyboardId }) {
      const storyboard = this.storyboards.find(item => item.id === storyboardId);
      if (!storyboard) {
        this.$message?.error('未找到对应分镜');
        return;
      }
      this.openNodeChatDrawer({
        type: 'storyboard',
        nodeId: storyboardId,
        storyboardId,
        defaultMessage: `请帮我优化这个分镜，保留原意但让表达更准确。`,
      });
    },
    handleOpenCameraChat({ cameraId, storyboardId }) {
      const storyboard = this.storyboards.find(item => item.id === storyboardId);
      if (!storyboard || !cameraId) {
        this.$message?.warning('请先生成一次运镜，再使用对话微调');
        return;
      }
      this.openNodeChatDrawer({
        type: 'camera_movement',
        nodeId: cameraId,
        storyboardId,
        cameraId,
        defaultMessage: '请在不改变画面主体的前提下，优化这个运镜。',
      });
    },
    closeNodeChatDrawer() {
      this.resetNodeChatState();
    },
    handleNodeChatInput(value) {
      this.nodeChat.input = value;
    },
    applyNodeQuickAction(value) {
      this.nodeChat.input = value;
      this.$nextTick(() => {
        this.$refs.nodeChatDrawer?.focusInputToEnd?.();
      });
    },
    stopNodeChat() {
      if (this.nodeChat.abortController) {
        this.nodeChat.abortController.abort();
      }
      this.nodeChat.streaming = false;
      this.nodeChat.abortController = null;
    },
    async submitNodeChat() {
      const message = (this.nodeChat.input || '').trim();
      if (!message || this.nodeChat.streaming || !this.project?.id || !this.nodeChat.nodeId) {
        return;
      }

      const userMessage = this.createChatMessage('user', message);
      const assistantMessage = this.createChatMessage('assistant', '', {
        streaming: true,
        applyPatch: null,
        rawText: '',
        applied: false,
      });

      const historyMessages = this.nodeChat.messages.map(item => ({
        role: item.role,
        content: item.content,
      }));

      this.nodeChat.messages = [...this.nodeChat.messages, userMessage, assistantMessage];
      this.nodeChat.input = '';
      this.nodeChat.streaming = true;
      this.nodeChat.streamRequestId += 1;
      const requestId = this.nodeChat.streamRequestId;

      try {
        const initResponse = await projectsAPI.initNodeChat(this.project.id, {
          node_type: this.nodeChat.type,
          node_id: this.nodeChat.nodeId,
          user_message: message,
          messages: historyMessages,
        });

        const accessToken = store.getters['auth/accessToken'];
        const streamUrl = projectsAPI.getNodeChatStreamUrl(this.project.id, initResponse.stream_token, accessToken);
        const controller = new AbortController();
        this.nodeChat.abortController = controller;

        const response = await fetch(streamUrl, {
          method: 'GET',
          credentials: 'include',
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error('节点对话流连接失败');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        let streamDone = false;
        while (!streamDone) {
          const { value, done } = await reader.read();
          if (done) {
            streamDone = true;
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split('\n\n');
          buffer = chunks.pop() || '';

          chunks.forEach((chunk) => {
            const line = chunk.split('\n').find(item => item.startsWith('data: '));
            if (!line) {
              return;
            }
            const payload = JSON.parse(line.slice(6));
            if (requestId !== this.nodeChat.streamRequestId) {
              return;
            }
            const target = this.nodeChat.messages.find(item => item.id === assistantMessage.id);
            if (!target) {
              return;
            }

            if (payload.type === 'token') {
              target.content = payload.full_text || `${target.content || ''}${payload.content || ''}`;
              target.rawText = payload.full_text || target.content;
            } else if (payload.type === 'done') {
              target.content = payload.reply_text || target.content || '已生成修改建议';
              target.rawText = payload.raw_text || target.content;
              target.applyPatch = payload.apply_patch || null;
              target.streaming = false;
              this.nodeChat.streaming = false;
              this.nodeChat.abortController = null;
            } else if (payload.type === 'error') {
              target.content = payload.error || '节点对话生成失败';
              target.streaming = false;
              this.nodeChat.streaming = false;
              this.nodeChat.abortController = null;
              this.$message?.error(target.content);
            }
          });
        }
      } catch (error) {
        const target = this.nodeChat.messages.find(item => item.id === assistantMessage.id);
        const isAbort = error?.name === 'AbortError';
        if (target) {
          target.streaming = false;
          if (isAbort) {
            target.content = target.content || '已停止本次生成';
          } else {
            target.content = error.message || '节点对话生成失败';
            this.$message?.error(target.content);
          }
        }
      } finally {
        const target = this.nodeChat.messages.find(item => item.id === assistantMessage.id);
        if (target) {
          target.streaming = false;
        }
        this.nodeChat.streaming = false;
        this.nodeChat.abortController = null;
      }
    },
    async applyNodeChatMessage(message) {
      if (!message?.applyPatch) {
        return;
      }
      this.nodeChat.applying = true;
      try {
        if (this.nodeChat.type === 'storyboard') {
          this.handleSaveStoryboard({
            storyboardId: this.nodeChat.storyboardId,
            data: message.applyPatch,
            silent: false,
          });
          this.flashNodeHighlight('storyboards', this.nodeChat.storyboardId);
        } else {
          this.handleSaveCamera({
            cameraId: this.nodeChat.cameraId,
            storyboardId: this.nodeChat.storyboardId,
            data: message.applyPatch,
            silent: false,
          });
          this.flashNodeHighlight('cameras', this.nodeChat.cameraId || this.nodeChat.storyboardId);
        }
        this.nodeChat.messages = this.nodeChat.messages.map(item => ({
          ...item,
          applied: item.id === message.id ? true : item.applied,
        }));
      } finally {
        this.nodeChat.applying = false;
      }
    },
    toggleAssetDrawer() {
      this.showAssetDrawer = !this.showAssetDrawer;
      if (this.showAssetDrawer && !this.availableAssets.length) {
        this.loadProjectAssets();
      }
    },
    async loadProjectAssets() {
      if (!this.project?.id) {
        return;
      }

      this.loadingAssets = true;
      try {
        const [availableResponse, bindingResponse] = await Promise.all([
          projectsAPI.getAvailableAssets(this.project.id),
          projectsAPI.getAssetBindings(this.project.id),
        ]);
        this.availableAssets = availableResponse.results || [];
        this.selectedAssetIds = (bindingResponse.results || [])
          .map(binding => binding?.asset?.id)
          .filter(Boolean);
      } catch (error) {
        console.error('[ProjectCanvas] 加载资产变量失败:', error);
        this.$message?.error('加载资产变量失败');
      } finally {
        this.loadingAssets = false;
      }
    },
    async handleAssetBindingToggle(assetId) {
      const selectedIds = new Set(this.selectedAssetIds);
      if (selectedIds.has(assetId)) {
        selectedIds.delete(assetId);
      } else {
        selectedIds.add(assetId);
      }

      const nextIds = Array.from(selectedIds);
      const previousIds = [...this.selectedAssetIds];
      this.selectedAssetIds = nextIds;
      this.savingAssetBindings = true;
      try {
        await projectsAPI.updateAssetBindings(this.project.id, nextIds);
        this.$emit('asset-bindings-updated');
      } catch (error) {
        console.error('[ProjectCanvas] 更新资产变量绑定失败:', error);
        this.selectedAssetIds = previousIds;
        this.$message?.error('更新资产变量失败');
      } finally {
        this.savingAssetBindings = false;
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

    useAdvancedImageFlow(storyboard) {
      return storyboard?.multi_grid_image?.template_enabled !== false || storyboard?.image_edit?.template_enabled !== false;
    },

    showImageNode(storyboard) {
      if (this.useAdvancedImageFlow(storyboard)) {
        return false;
      }
      return storyboard?.image_generation?.template_enabled !== false;
    },

    showMultiGridNode(storyboard) {
      return storyboard?.multi_grid_image?.template_enabled !== false;
    },

    showImageEditNode(storyboard) {
      return storyboard?.image_edit?.template_enabled !== false;
    },

    showCameraNode(storyboard) {
      return storyboard?.camera_movement?.template_enabled !== false;
    },

    showVideoNode(storyboard) {
      return storyboard?.video_generation?.template_enabled !== false;
    },

    parseMediaRatio(ratio) {
      if (!ratio || typeof ratio !== 'string') {
        return null;
      }

      const normalizedRatio = ratio.trim();
      const matched = normalizedRatio.match(/^(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)$/);
      if (!matched) {
        return null;
      }

      const width = Number(matched[1]);
      const height = Number(matched[2]);

      if (!width || !height) {
        return null;
      }

      return {
        width: Math.round(width * 100),
        height: Math.round(height * 100)
      };
    },

    getDefaultImageRatio() {
      const provider = this.modelConfig?.image_providers_detail?.[0];
      return provider?.extra_config?.default_ratio || provider?.extra_config?.ratio || null;
    },

    getDefaultVideoRatio() {
      const provider = this.modelConfig?.video_providers_detail?.[0];
      return provider?.extra_config?.aspect_ratio || provider?.extra_config?.default_ratio || provider?.extra_config?.ratio || null;
    },

    handleImageMediaLoaded({ storyboardId, width, height }) {
      if (!storyboardId || !(width > 0) || !(height > 0)) {
        return;
      }

      const current = this.runtimeMediaDimensions[storyboardId];
      if (current?.width === width && current?.height === height) {
        return;
      }

      this.$set(this.runtimeMediaDimensions, storyboardId, { width, height });
    },

    getStoryboardMediaDimensions(storyboard) {
      const runtimeDimensions = storyboard?.id
        ? this.runtimeMediaDimensions[storyboard.id]
        : null;

      if (runtimeDimensions?.width > 0 && runtimeDimensions?.height > 0) {
        return runtimeDimensions;
      }

      const image = storyboard?.image_generation?.images?.[0];
      const multiGridSource = storyboard?.multi_grid_image?.tasks?.[0];
      const imageEdit = storyboard?.image_edit?.results?.[0];
      const video = storyboard?.video_generation?.videos?.[0];
      const width = Number(imageEdit?.width || multiGridSource?.split_config?.source_width || image?.width || video?.width);
      const height = Number(imageEdit?.height || multiGridSource?.split_config?.source_height || image?.height || video?.height);

      if (width > 0 && height > 0) {
        return { width, height };
      }

      const inferredRatio = image?.generation_params?.ratio ||
        image?.generation_params?.aspect_ratio ||
        video?.generation_params?.aspect_ratio ||
        video?.generation_params?.ratio ||
        this.getDefaultImageRatio() ||
        this.getDefaultVideoRatio() ||
        storyboard?.generation_metadata?.ratio ||
        storyboard?.generation_metadata?.aspect_ratio;

      const inferredDimensions = this.parseMediaRatio(inferredRatio);
      if (inferredDimensions) {
        return inferredDimensions;
      }

      return { width: 1080, height: 1080 };
    },

    getMediaPreviewHeight(storyboard) {
      const { width, height } = this.getStoryboardMediaDimensions(storyboard);
      const safeWidth = width > 0 ? width : 1;
      const safeHeight = height > 0 ? height : 1;
      const previewHeight = this.nodeMetrics.media.width * (safeHeight / safeWidth);

      return Math.max(this.nodeMetrics.media.minPreviewHeight, Math.round(previewHeight));
    },

    getImageNodeHeight(storyboard) {
      return this.nodeMetrics.media.headerHeight + this.getMediaPreviewHeight(storyboard);
    },

    getMultiGridNodeHeight(storyboard) {
      return this.nodeMetrics.multiGrid.headerHeight + this.getMediaPreviewHeight(storyboard) + this.nodeMetrics.multiGrid.minTilesHeight;
    },

    getImageEditNodeHeight(storyboard) {
      return this.nodeMetrics.imageEdit.headerHeight + this.getMediaPreviewHeight(storyboard) + this.nodeMetrics.imageEdit.minResultsHeight;
    },

    getVideoNodeHeight(storyboard) {
      return this.nodeMetrics.media.headerHeight + this.getMediaPreviewHeight(storyboard);
    },

    getBranchNodeX(index, nodeWidth) {
      return this.nodeMetrics.startX
        + index * (this.treeLayout.branchWidth + this.nodeMetrics.columnGap)
        + ((this.treeLayout.branchWidth - nodeWidth) / 2);
    },

    // 计算分镜节点位置（第二行横向排列）
    calculateStoryboardPosition(index) {
      return {
        x: this.getBranchNodeX(index, this.nodeMetrics.storyboard.width),
        y: this.treeLayout.rowY.storyboard || this.nodeMetrics.startY
      };
    },

    // 计算文生图节点位置（第三行横向排列）
    calculateImagePosition(index) {
      return {
        x: this.getBranchNodeX(index, this.nodeMetrics.media.width),
        y: this.treeLayout.rowY.image || this.nodeMetrics.startY
      };
    },

    // 计算运镜节点位置（第四行横向排列）
    calculateMultiGridPosition(index) {
      return {
        x: this.getBranchNodeX(index, this.nodeMetrics.multiGrid.width),
        y: this.treeLayout.rowY.multiGrid || this.nodeMetrics.startY
      };
    },

    calculateImageEditPosition(index) {
      return {
        x: this.getBranchNodeX(index, this.nodeMetrics.imageEdit.width),
        y: this.treeLayout.rowY.imageEdit || this.nodeMetrics.startY
      };
    },

    calculateCameraPosition(index) {
      return {
        x: this.getBranchNodeX(index, this.nodeMetrics.camera.width),
        y: this.treeLayout.rowY.camera || this.nodeMetrics.startY
      };
    },

    // 计算视频生成节点位置（第五行横向排列）
    calculateVideoPosition(index) {
      return {
        x: this.getBranchNodeX(index, this.nodeMetrics.media.width),
        y: this.treeLayout.rowY.video || this.nodeMetrics.startY
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

    getMultiGridStatus(storyboard) {
      if (this.executingStages.multi_grid_image && this.executingNodes.multiGridImages[storyboard.id]) {
        return 'processing';
      }
      if (this.executingNodes.multiGridImages[storyboard.id]) {
        return 'processing';
      }
      if (storyboard.multi_grid_image?.tasks && storyboard.multi_grid_image.tasks.length > 0) {
        return 'completed';
      }
      return 'pending';
    },

    getMultiGridTasks(storyboard) {
      return storyboard.multi_grid_image?.tasks || [];
    },

    getMultiGridSourceUrl(storyboard) {
      return storyboard.multi_grid_image?.tasks?.[0]?.source_image_url || '';
    },

    getImageEditStatus(storyboard) {
      if (this.executingStages.image_edit && this.executingNodes.imageEdits[storyboard.id]) {
        return 'processing';
      }
      if (this.executingNodes.imageEdits[storyboard.id]) {
        return 'processing';
      }
      if (storyboard.image_edit?.results && storyboard.image_edit.results.length > 0) {
        return 'completed';
      }
      return 'pending';
    },

    getImageEditResults(storyboard) {
      return storyboard.image_edit?.results || [];
    },

    getCameraInputStatus(storyboard) {
      if (this.showImageEditNode(storyboard)) {
        return this.getImageEditStatus(storyboard);
      }
      if (this.showMultiGridNode(storyboard)) {
        return this.getMultiGridStatus(storyboard);
      }
      return this.getImageStatus(storyboard);
    },

    getCameraInputUrl(storyboard) {
      if (this.showImageEditNode(storyboard)) {
        return storyboard.image_edit?.results?.[0]?.edited_image_url || '';
      }
      if (this.showMultiGridNode(storyboard)) {
        return storyboard.multi_grid_image?.tasks?.[0]?.tiles?.[0]?.tile_image_url || '';
      }
      return storyboard.image_generation?.images?.[0]?.image_url || '';
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

    focusCanvasNode(nodeKey) {
      this.$refs.flowCanvas?.focusNode(nodeKey);
    },

    handleExecuteStage({ stageType, inputData }) {
      this.$emit('execute-stage', { stageType, inputData });
    },

    handleSaveStage({ stageType, outputData, silent, skipRefresh }) {
      this.$emit('save-stage', { stageType, outputData, silent, skipRefresh });
    },

    findStoryboardById(storyboardId) {
      return this.storyboards.find(item => item.id === storyboardId) || null;
    },

    applyLocalStoryboardPatch(storyboardId, patch = {}) {
      const storyboard = this.findStoryboardById(storyboardId);
      if (!storyboard) {
        return;
      }

      Object.keys(patch).forEach((key) => {
        this.$set(storyboard, key, patch[key]);
      });
    },

    applyLocalCameraPatch({ cameraId = null, storyboardId = null, patch = {} }) {
      const storyboard = storyboardId
        ? this.findStoryboardById(storyboardId)
        : this.storyboards.find(item => item.camera_movement?.data?.id === cameraId) || null;

      if (!storyboard || !storyboard.camera_movement?.data) {
        return;
      }

      const cameraData = storyboard.camera_movement.data;
      if (Object.prototype.hasOwnProperty.call(patch, 'movement_type')) {
        this.$set(cameraData, 'movement_type', patch.movement_type);
      }
      if (Object.prototype.hasOwnProperty.call(patch, 'movement_params')) {
        this.$set(cameraData, 'movement_params', patch.movement_params);
      }
    },

    flashNodeHighlight(type, key) {
      if (!type || !key) {
        return;
      }
      this.$set(this.nodeHighlights[type], key, true);
      window.setTimeout(() => {
        this.$delete(this.nodeHighlights[type], key);
      }, 1400);
    },

    async handleGenerateImage({ storyboardId, prompt, forceRegenerate = false }) {
      console.log('[ProjectCanvas] 生成图片:', { storyboardId, prompt, forceRegenerate });

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

        if (forceRegenerate) {
          inputData.force_regenerate = true;
        }

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

    async handleGenerateMultiGridImage({ storyboardId, forceRegenerate = false }) {
      try {
        const storyboard = this.storyboards.find(s => s.id === storyboardId);
        if (!storyboard) {
          this.$message?.error(`未找到分镜 ${storyboardId}`);
          return;
        }
        this.$set(this.executingNodes.multiGridImages, storyboardId, true);
        const inputData = {
          storyboard_ids: [storyboardId],
          scenes: [{
            scene_number: storyboard.sequence_number,
            narration: storyboard.narration_text,
            visual_prompt: storyboard.image_prompt,
            shot_type: storyboard.shot_type || '标准镜头',
          }]
        };
        if (forceRegenerate) {
          inputData.force_regenerate = true;
        }
        this.$emit('execute-stage', {
          stageType: 'multi_grid_image',
          inputData,
          storyboardId
        });
      } catch (error) {
        console.error('[ProjectCanvas] 生成多宫格图片失败:', error);
        this.$message?.error(error.message || '生成多宫格图片失败');
        this.$set(this.executingNodes.multiGridImages, storyboardId, false);
      }
    },

    async handleGenerateImageEdit({ storyboardId, forceRegenerate = false }) {
      try {
        const storyboard = this.storyboards.find(s => s.id === storyboardId);
        if (!storyboard) {
          this.$message?.error(`未找到分镜 ${storyboardId}`);
          return;
        }
        if (this.getMultiGridStatus(storyboard) !== 'completed') {
          this.$message?.warning('请先生成多宫格切片');
          return;
        }
        this.$set(this.executingNodes.imageEdits, storyboardId, true);
        const inputData = {
          storyboard_ids: [storyboardId],
        };
        if (forceRegenerate) {
          inputData.force_regenerate = true;
        }
        this.$emit('execute-stage', {
          stageType: 'image_edit',
          inputData,
          storyboardId
        });
      } catch (error) {
        console.error('[ProjectCanvas] 执行图片编辑失败:', error);
        this.$message?.error(error.message || '执行图片编辑失败');
        this.$set(this.executingNodes.imageEdits, storyboardId, false);
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
        const imageUrl = this.getCameraInputUrl(storyboard);
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

    async handleGenerateVideo({ storyboardId, forceRegenerate = false }) {
      console.log('[ProjectCanvas] 生成视频:', { storyboardId, forceRegenerate });

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
        if (this.getCameraInputStatus(storyboard) !== 'completed') {
          this.$message?.warning('请先完成上游出图');
          return;
        }

        // 设置执行状态
        this.$set(this.executingNodes.videos, storyboardId, true);

        // 准备输入数据
        const imageUrl = this.getCameraInputUrl(storyboard);
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

        if (forceRegenerate) {
          inputData.force_regenerate = true;
        }

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
      this.applyLocalStoryboardPatch(storyboardId, data);
      this.$emit('save-storyboard', { storyboardId, data, silent });
    },

    handleSaveCamera({ cameraId, data, silent, storyboardId = null }) {
      this.applyLocalCameraPatch({ cameraId, storyboardId, patch: data });
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
      } else if (itemType === 'multi_grid_image') {
        this.$set(this.executingNodes.multiGridImages, storyboardId, isLoading);
      } else if (itemType === 'image_edit') {
        this.$set(this.executingNodes.imageEdits, storyboardId, isLoading);
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
        multi_grid_image: false,
        image_edit: false,
        camera_movement: false,
        video_generation: false
      };
      this.executingNodes = {
        images: {},
        multiGridImages: {},
        imageEdits: {},
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

.asset-drawer-card {
  position: absolute;
  top: calc(100% + 0.75rem);
  right: 0;
  width: 360px;
  max-height: 420px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0.85rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(12px);
  z-index: 260;
  pointer-events: auto;
}

.layout-shell.theme-dark .asset-drawer-card {
  background: rgba(15, 23, 42, 0.96);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 20px 40px rgba(2, 6, 23, 0.72);
}

.asset-drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.asset-drawer-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
}

.layout-shell.theme-dark .asset-drawer-title {
  color: #e2e8f0;
}

.asset-drawer-subtitle {
  margin-top: 0.2rem;
  font-size: 0.76rem;
  color: #64748b;
}

.asset-drawer-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  overflow-y: auto;
  padding-right: 0.15rem;
}

.asset-drawer-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem 0.8rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .asset-drawer-item {
  background: rgba(15, 23, 42, 0.84);
  border-color: rgba(148, 163, 184, 0.18);
}

.asset-drawer-item:hover {
  border-color: rgba(20, 184, 166, 0.28);
  box-shadow: 0 10px 22px rgba(20, 184, 166, 0.1);
  transform: translateY(-1px);
}

.asset-drawer-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.asset-drawer-key-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.asset-drawer-key {
  font-size: 0.82rem;
  font-weight: 700;
  color: #0f172a;
}

.layout-shell.theme-dark .asset-drawer-key {
  color: #e2e8f0;
}

.asset-drawer-group {
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: rgba(20, 184, 166, 0.12);
  color: #0f766e;
  font-size: 0.68rem;
}

.layout-shell.theme-dark .asset-drawer-group {
  color: #99f6e4;
}

.asset-drawer-type,
.asset-drawer-empty {
  font-size: 0.76rem;
  color: #64748b;
}

.asset-drawer-empty {
  padding: 1rem 0.25rem 0.5rem;
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

  .asset-drawer-card {
    width: min(360px, calc(100vw - 2.5rem));
    right: 0;
  }
}
</style>
