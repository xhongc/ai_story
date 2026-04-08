<template>
  <div class="project-detail">
    <loading-container :loading="loading">
      <div class="project-detail__canvas">
        <!-- 只展示工作流画布 -->
        <project-canvas
          v-if="project"
          ref="projectCanvas"
          :project="project"
          :stages="stages"
          :model-config="modelConfig"
          :episodes="seriesEpisodes"
          @execute-stage="handleExecuteStage"
          @save-stage="handleSaveStage"
          @generate-image="handleGenerateImage"
          @generate-camera="handleGenerateCamera"
          @generate-video="handleGenerateVideo"
          @save-storyboard="handleSaveStoryboard"
          @save-camera="handleSaveCamera"
          @delete-storyboard="handleDeleteStoryboard"
          @draft-generated="handleDraftGenerated"
          @pipeline-started="handlePipelineStarted"
          @pipeline-paused="handlePipelinePaused"
          @storyboard-generated="handleStoryboardGenerated"
          @asset-bindings-updated="handleAssetBindingsUpdated"
          @template-updated="handleTemplateUpdated"
        />
      </div>
    </loading-container>
  </div>
</template>

<script>
import { mapActions } from 'vuex';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import ProjectCanvas from '@/components/canvas/ProjectCanvas.vue';
import { formatDate } from '@/utils/helpers';
import { createProjectAllStagesSSE, createProjectStageSSE } from '@/services/sseService';
import { buildProjectDetailAgentContext } from '@/services/pageAgent/contextBuilders';
import { pageAgentActionRegistry } from '@/services/pageAgent/actionRegistry';

export default {
  name: 'ProjectDetail',
  components: {
    LoadingContainer,
    ProjectCanvas,
  },
  beforeRouteLeave(to, from, next) {
    this.unregisterProjectAssistant(from?.params?.id);
    this.sseRecoveryEnabled = false;
    this.disconnectAllSSE({ clearMarkers: true });
    next();
  },
  data() {
    return {
      loading: false,
      project: null,
      stages: [],
      modelConfig: null,
      seriesEpisodes: [],
      storyboards: [],
      savedScrollPosition: 0, // 保存滚动位置
      // SSE 客户端
      pipelineSSEClient: null,
      // 单阶段 SSE 客户端
      stageSSEClient: null,
      sseRecoveryEnabled: true,
    };
  },
  watch: {
    '$route.params.id'(newId, oldId) {
      this.unregisterProjectAssistant(oldId);
      this.sseRecoveryEnabled = true;
      this.disconnectAllSSE({ projectId: oldId, clearMarkers: true });
      this.fetchData();
    },
  },
  created() {
    this.fetchData();
  },
  beforeDestroy() {
    this.unregisterProjectAssistant();
    this.sseRecoveryEnabled = false;
    this.disconnectAllSSE({ clearMarkers: true });
  },
  methods: {
    ...mapActions('projects', [
      'fetchProject',
      'fetchProjectStages',
      'fetchModelConfig',
      'fetchSeriesDetail',
      'executeStage',
      'updateProject',
      'updateStageData',
      'updateRewrite',
      'updateStoryboard',
      'updateCameraMovement'
    ]),
    formatDate,

    getAssistantScopeKey(projectId = this.project?.id || this.$route.params.id) {
      return `project_detail:${projectId}`;
    },

    unregisterProjectAssistant(projectId = this.project?.id || this.$route.params.id) {
      pageAgentActionRegistry.unregister(this.getAssistantScopeKey(projectId));
    },

    registerProjectAssistant() {
      const context = buildProjectDetailAgentContext({
        route: this.$route,
        project: this.project,
        stages: this.stages,
        seriesEpisodes: this.seriesEpisodes,
      });

      this.$store.dispatch('assistant/registerContext', context);
      this.registerProjectAssistantActions(context.scopeKey);
    },

    registerProjectAssistantActions(scopeKey) {
      pageAgentActionRegistry.register(scopeKey, {
        focus_stage: async ({ stageType }) => {
          const nodeKey = this.resolveStageNodeKey(stageType);
          if (!nodeKey) {
            throw new Error('当前阶段还没有可定位的节点');
          }
          this.$refs.projectCanvas?.focusCanvasNode(nodeKey);
          return `已定位到${this.getStageDisplayName(stageType)}区域。`;
        },
        focus_storyboard: async ({ storyboardId }) => {
          const nodeKey = this.resolveStoryboardNodeKey(storyboardId);
          if (!nodeKey) {
            throw new Error('当前还没有可定位的分镜');
          }
          this.$refs.projectCanvas?.focusCanvasNode(nodeKey);
          return '已定位到目标分镜。';
        },
        open_storyboard_chat: async ({ storyboardId }) => {
          const targetId = storyboardId || this.storyboards[0]?.id;
          if (!targetId) {
            throw new Error('当前没有可微调的分镜');
          }
          this.$refs.projectCanvas?.handleOpenStoryboardChat({ storyboardId: targetId });
          return '已打开分镜微调助手。';
        },
        open_camera_chat: async ({ cameraId, storyboardId }) => {
          const targetStoryboard = storyboardId || this.storyboards.find((item) => item.camera_movement?.data?.id)?.id;
          const targetCameraId = cameraId || this.storyboards.find((item) => item.camera_movement?.data?.id)?.camera_movement?.data?.id;
          if (!targetStoryboard || !targetCameraId) {
            throw new Error('当前还没有可微调的运镜内容');
          }
          this.$refs.projectCanvas?.handleOpenCameraChat({
            cameraId: targetCameraId,
            storyboardId: targetStoryboard,
          });
          return '已打开运镜微调助手。';
        },
        run_pipeline: async () => {
          await this.$refs.projectCanvas?.handleRunPipeline();
          return '已触发运行流程。';
        },
        pause_pipeline: async () => {
          await this.$refs.projectCanvas?.handlePausePipeline();
          return '已触发暂停流程。';
        },
        resume_pipeline: async () => {
          await this.$refs.projectCanvas?.handleResumePipeline();
          return '已触发恢复流程。';
        },
      });
    },

    resolveStoryboardNodeKey(storyboardId) {
      if (!this.storyboards.length) {
        return '';
      }
      const targetIndex = storyboardId
        ? this.storyboards.findIndex((item) => item.id === storyboardId)
        : 0;
      if (targetIndex < 0) {
        return '';
      }
      return `storyboard-${targetIndex}`;
    },

    resolveStageNodeKey(stageType) {
      if (stageType === 'storyboard') {
        return this.resolveStoryboardNodeKey();
      }

      const stageMap = {
        rewrite: 'rewrite',
        asset_extraction: 'assetExtraction',
      };

      return stageMap[stageType] || '';
    },

    getStageDisplayName(stageType) {
      const stageMap = {
        rewrite: '改写',
        asset_extraction: '资产提取',
        storyboard: '分镜',
        image_generation: '图片生成',
        multi_grid_image: '多图生成',
        image_edit: '图片编辑',
        camera_movement: '运镜',
        video_generation: '视频生成',
      };
      return stageMap[stageType] || stageType || '当前';
    },

    getPipelineSSEStorageKey(projectId = this.project?.id || this.$route.params.id) {
      return `project_active_pipeline_sse:${projectId}`;
    },

    getStageSSEStorageKey(projectId = this.project?.id || this.$route.params.id) {
      return `project_active_stage_sse:${projectId}`;
    },

    markPipelineSSEActive() {
      sessionStorage.setItem(this.getPipelineSSEStorageKey(), '1');
      sessionStorage.removeItem(this.getStageSSEStorageKey());
    },

    clearPipelineSSEMarker(projectId) {
      sessionStorage.removeItem(this.getPipelineSSEStorageKey(projectId));
    },

    markStageSSEActive(stageName) {
      sessionStorage.setItem(this.getStageSSEStorageKey(), stageName);
      sessionStorage.removeItem(this.getPipelineSSEStorageKey());
    },

    clearStageSSEMarker(projectId) {
      sessionStorage.removeItem(this.getStageSSEStorageKey(projectId));
    },

    getMarkedStageSSE(projectId) {
      return sessionStorage.getItem(this.getStageSSEStorageKey(projectId));
    },

    hasMarkedPipelineSSE(projectId) {
      return sessionStorage.getItem(this.getPipelineSSEStorageKey(projectId)) === '1';
    },

    async fetchData(preserveScroll = false) {
      // 保存当前滚动位置
      if (preserveScroll) {
        this.savedScrollPosition = window.pageYOffset || document.documentElement.scrollTop;
      }

      this.loading = true;
      try {
        const projectId = this.$route.params.id;
        this.project = await this.fetchProject(projectId);
        this.stages = await this.fetchProjectStages(projectId);
        this.modelConfig = await this.fetchModelConfig(projectId);
        this.seriesEpisodes = [];

        if (this.project?.series) {
          try {
            const series = await this.fetchSeriesDetail(this.project.series);
            this.seriesEpisodes = series?.episodes || [];
          } catch (seriesError) {
            console.error('Failed to fetch series episodes:', seriesError);
          }
        }

        // 获取分镜数据（必须在stages加载后）
        this.fetchStoryboardsFromStages();
        if (this.sseRecoveryEnabled) {
          this.restoreSSEIfNeeded();
        }

        this.registerProjectAssistant();

        // 恢复滚动位置
        if (preserveScroll) {
          this.$nextTick(() => {
            window.scrollTo(0, this.savedScrollPosition);
          });
        }
      } catch (error) {
        console.error('Failed to fetch project:', error);
        this.$message.error('加载项目失败');
      } finally {
        this.loading = false;
      }
    },

    disconnectAllSSE({ projectId = this.project?.id || this.$route.params.id, clearMarkers = false } = {}) {
      if (this.pipelineSSEClient) {
        this.pipelineSSEClient.disconnect();
        this.pipelineSSEClient = null;
      }
      if (this.stageSSEClient) {
        this.stageSSEClient.disconnect();
        this.stageSSEClient = null;
      }

      if (clearMarkers && projectId) {
        this.clearPipelineSSEMarker(projectId);
        this.clearStageSSEMarker(projectId);
      }
    },

    hasRunningStage() {
      return this.stages.some(stage => stage.status === 'processing');
    },

    restoreSSEIfNeeded() {
      if (!this.project?.id || !this.sseRecoveryEnabled) {
        return;
      }

      if (this.pipelineSSEClient || this.stageSSEClient) {
        return;
      }

      const processingStages = this.stages.filter(stage => stage.status === 'processing');
      const markedStageName = this.getMarkedStageSSE(this.project.id);

      if (this.hasMarkedPipelineSSE(this.project.id)) {
        console.log('[ProjectDetail] 恢复项目级 SSE 连接');
        this.connectProjectSSE();
        return;
      }

      if (markedStageName && processingStages.some(stage => stage.stage_type === markedStageName)) {
        console.log('[ProjectDetail] 恢复阶段 SSE 连接:', markedStageName);
        this.connectStageSSE(markedStageName);
        return;
      }

      if (processingStages.length === 1) {
        console.log('[ProjectDetail] 自动恢复单阶段 SSE 连接:', processingStages[0].stage_type);
        this.connectStageSSE(processingStages[0].stage_type);
        return;
      }

      if (this.project.status === 'processing' || processingStages.length > 1) {
        console.log('[ProjectDetail] 检测到项目仍在处理中，自动重连 SSE');
        this.connectProjectSSE();
      }
    },

    fetchStoryboardsFromStages() {
      try {
        // 从分镜阶段的domain_data中获取分镜列表
        const storyboardStage = this.stages.find(s => s.stage_type === 'storyboard');
        console.log('[ProjectDetail] Storyboard stage:', storyboardStage);

        // 优先从 domain_data 获取（后端序列化器返回的真实领域数据）
        // 如果没有则尝试从 output_data 获取（兼容旧数据）
        const storyboardData = storyboardStage?.domain_data || storyboardStage?.output_data;

        if (storyboardData && storyboardData.storyboards && storyboardData.storyboards.length > 0) {
          // 获取每个分镜的详细数据（包括images, camera_movement, videos）
          this.storyboards = storyboardData.storyboards.map((sb, index) => ({
            ...sb,
            sequence_number: sb.sequence_number || index + 1,
            images: sb.images || [],
            camera_movement: sb.camera_movement || null,
            videos: sb.videos || []
          }));
          console.log('[ProjectDetail] Storyboards loaded:', this.storyboards);
        } else {
          this.storyboards = [];
          console.log('[ProjectDetail] No storyboards found');

          // 开发模式：添加模拟数据用于测试画布布局
          if (process.env.NODE_ENV === 'development') {
            console.log('[ProjectDetail] Adding mock storyboards for development');
            this.storyboards = [
              {
                id: 'mock-1',
                sequence_number: 1,
                scene_description: '开场镜头：城市天际线',
                narration_text: '在这座繁华的都市中...',
                image_prompt: 'A beautiful city skyline at sunset',
                duration_seconds: 3,
                images: [],
                camera_movement: null,
                videos: []
              },
              {
                id: 'mock-2',
                sequence_number: 2,
                scene_description: '主角登场',
                narration_text: '我们的故事从这里开始',
                image_prompt: 'A young person walking in the city',
                duration_seconds: 4,
                images: [],
                camera_movement: null,
                videos: []
              },
              {
                id: 'mock-3',
                sequence_number: 3,
                scene_description: '转折点',
                narration_text: '突然，一切都变了',
                image_prompt: 'Dramatic moment in the story',
                duration_seconds: 3,
                images: [],
                camera_movement: null,
                videos: []
              },
              {
                id: 'mock-4',
                sequence_number: 4,
                scene_description: '高潮部分',
                narration_text: '这是最关键的时刻',
                image_prompt: 'Climax scene with tension',
                duration_seconds: 5,
                images: [],
                camera_movement: null,
                videos: []
              }
            ];
          }
        }
      } catch (error) {
        console.error('Failed to fetch storyboards:', error);
        this.storyboards = [];
      }
    },

    async handleExecuteStage({ stageType, inputData }) {
      try {
        const result = await this.executeStage({
          projectId: this.project.id,
          stageName: stageType,
          inputData: inputData
        });

        if (result?.skipped) {
          this.$message.info(result.message || '该阶段已跳过');
          await this.refreshCanvasData();
          return;
        }

        this.$message.success('阶段执行已开始');

        // 如果返回了 task_id，建立 SSE 连接监听任务完成
        if (result && result.task_id) {
          this.connectStageSSE(stageType);
        }
      } catch (error) {
        console.error('Failed to execute stage:', error);
        this.$message.error('执行失败');
      }
    },

    /**
     * 连接单阶段 SSE 监听任务完成
     */
    connectStageSSE(stageName) {
      if (!this.sseRecoveryEnabled) {
        return;
      }

      // 断开之前的连接
      if (this.stageSSEClient) {
        this.stageSSEClient.disconnect();
      }

      this.markStageSSEActive(stageName);

      console.log('[ProjectDetail] 连接阶段 SSE:', stageName);

      this.stageSSEClient = createProjectStageSSE(this.project.id, stageName);

      this.stageSSEClient
        .on('connected', (data) => {
          console.log('[Stage SSE] 已连接:', data);
        })
        .on('stage_update', (data) => {
          console.log('[Stage SSE] 阶段更新:', data);
        })
        .on('progress', (data) => {
          console.log('[Stage SSE] 进度更新:', data);
        })
        .on('done', (data) => {
          console.log('[Stage SSE] 完成:', data);
          this.clearStageSSEMarker();
          this.$message.success(`${stageName} 执行完成`);

          // 刷新画布数据
          this.refreshCanvasData();

          // 断开连接
          if (this.stageSSEClient) {
            this.stageSSEClient.disconnect();
            this.stageSSEClient = null;
          }
        })
        .on('error', (data) => {
          console.error('[Stage SSE] 错误:', data);
          this.clearStageSSEMarker();
          this.$message.error(data.error || `${stageName} 执行失败`);

          // 刷新画布数据
          this.refreshCanvasData();

          // 断开连接
          if (this.stageSSEClient) {
            this.stageSSEClient.disconnect();
            this.stageSSEClient = null;
          }
        })
        .on('close', () => {
          console.log('[Stage SSE] 连接已关闭');
        });
    },

    /**
     * 刷新画布数据（不刷新整个页面）
     */
    async refreshCanvasData() {
      try {
        const projectId = this.$route.params.id;
        this.project = await this.fetchProject(projectId);
        this.stages = await this.fetchProjectStages(projectId);
        this.fetchStoryboardsFromStages();
        this.registerProjectAssistant();

        if (!this.hasRunningStage()) {
          this.clearStageSSEMarker();
        }

        if (!this.hasRunningStage() && this.project?.status !== 'processing' && this.pipelineSSEClient) {
          console.log('[ProjectDetail] 项目已无进行中任务，关闭项目级 SSE');
          this.clearPipelineSSEMarker();
          this.pipelineSSEClient.disconnect();
          this.pipelineSSEClient = null;
        }

        console.log('[ProjectDetail] 画布数据已刷新');
      } catch (error) {
        console.error('[ProjectDetail] 刷新画布数据失败:', error);
      }
    },

    async handleSaveStage({ stageType, inputData, outputData, skipRefresh = false, silent = false }) {
      try {
        if (stageType === 'rewrite') {
          await this.updateRewrite({
            projectId: this.project.id,
            data: {
              rewritten_text: outputData?.rewritten_text ?? ''
            }
          });
          if (!silent) {
            this.$message.success('保存成功');
          }
          if (!skipRefresh) {
            await this.refreshCanvasData();
          }
          return;
        }

        await this.updateStageData({
          projectId: this.project.id,
          stageName: stageType,
          data: { input_data: inputData, output_data: outputData },
        });
        if (!silent) {
          this.$message.success('保存成功');
        }
        if (!skipRefresh) {
          await this.fetchData(true); // 保持滚动位置
        }
      } catch (error) {
        console.error('Failed to save stage:', error);
        if (!silent) {
          this.$message.error('保存失败');
        }
      }
    },

    async handleDraftGenerated(data) {
      console.log('剪映草稿生成成功:', data);
      this.$message.success(`剪映草稿生成成功！包含 ${data.videoCount} 个视频`);
      // 重新加载项目数据以更新草稿路径显示
      await this.fetchData(true); // 保持滚动位置
    },

    // 画布事件处理
    async handleGenerateImage({ stageType, inputData, storyboardId }) {
      try {
        console.log('[ProjectDetail] 生成图片:', { stageType, inputData, storyboardId });
        this.$message.info('开始生成图片...');

        // 调用执行阶段方法
        await this.handleExecuteStage({ stageType, inputData });
      } catch (error) {
        console.error('Failed to generate image:', error);
        this.$message.error('生成图片失败');
      }
    },

    async handleGenerateCamera({ stageType, inputData, storyboardId }) {
      try {
        console.log('[ProjectDetail] 生成运镜:', { stageType, inputData, storyboardId });
        this.$message.info('开始生成运镜...');

        // 调用执行阶段方法
        await this.handleExecuteStage({ stageType, inputData });
      } catch (error) {
        console.error('Failed to generate camera:', error);
        this.$message.error('生成运镜失败');
      }
    },

    async handleGenerateVideo({ stageType, inputData, storyboardId }) {
      try {
        console.log('[ProjectDetail] 生成视频:', { stageType, inputData, storyboardId });
        this.$message.info('开始生成视频...');

        // 调用执行阶段方法
        await this.handleExecuteStage({ stageType, inputData });
      } catch (error) {
        console.error('Failed to generate video:', error);
        this.$message.error('生成视频失败');
      }
    },

    async handleSaveStoryboard({ storyboardId, data, silent = false }) {
      try {
        await this.updateStoryboard({
          projectId: this.project.id,
          storyboardId,
          data
        });
        if (!silent) {
          this.$message.success('保存成功');
        }
        await this.refreshCanvasData();
      } catch (error) {
        console.error('Failed to save storyboard:', error);
        if (!silent) {
          this.$message.error('保存失败');
        }
      }
    },

    async handleSaveCamera({ cameraId, data, silent = false }) {
      try {
        await this.updateCameraMovement({
          projectId: this.project.id,
          cameraId,
          data
        });
        if (!silent) {
          this.$message.success('运镜参数保存成功');
        }
        await this.refreshCanvasData();
      } catch (error) {
        console.error('Failed to save camera movement:', error);
        if (!silent) {
          this.$message.error('运镜参数保存失败');
        }
      }
    },

    async handleDeleteStoryboard(storyboardId) {
      try {
        // TODO: 调用删除分镜API
        console.log('Delete storyboard:', storyboardId);
        this.$message.success('删除成功');
        await this.fetchData(true);
      } catch (error) {
        console.error('Failed to delete storyboard:', error);
        this.$message.error('删除失败');
      }
    },

    async handleStoryboardGenerated() {
      console.log('[ProjectDetail] 分镜生成完成，刷新画布数据');
      // 只刷新 stages 数据，不刷新整个页面
      try {
        const projectId = this.$route.params.id;
        this.stages = await this.fetchProjectStages(projectId);
        this.fetchStoryboardsFromStages();
        console.log('[ProjectDetail] 画布数据已刷新，分镜数量:', this.storyboards.length);
      } catch (error) {
        console.error('[ProjectDetail] 刷新画布数据失败:', error);
      }
    },

    async handleAssetBindingsUpdated() {
      try {
        await this.refreshCanvasData();
      } catch (error) {
        console.error('[ProjectDetail] 刷新项目资产绑定失败:', error);
      }
    },
    async handleTemplateUpdated() {
      try {
        await this.refreshCanvasData();
      } catch (error) {
        console.error('[ProjectDetail] 刷新模板相关画布数据失败:', error);
      }
    },

    handlePipelineStarted({ taskId, channel }) {
      console.log('[ProjectDetail] Pipeline started:', { taskId, channel });

      this.connectProjectSSE();
    },

    async handlePipelinePaused() {
      console.log('[ProjectDetail] Pipeline paused');

      this.disconnectAllSSE({ clearMarkers: true });
      this.$refs.projectCanvas?.resetAllLoading();
      await this.refreshCanvasData();
    },

    connectProjectSSE() {
      if (!this.sseRecoveryEnabled) {
        return;
      }

      if (!this.project?.id) {
        return;
      }

      // 断开之前的连接
      if (this.pipelineSSEClient) {
        this.pipelineSSEClient.disconnect();
        this.pipelineSSEClient = null;
      }

      if (this.stageSSEClient) {
        this.stageSSEClient.disconnect();
        this.stageSSEClient = null;
      }

      this.markPipelineSSEActive();

      console.log('[ProjectDetail] 连接项目级 SSE:', this.project.id);

      this.pipelineSSEClient = createProjectAllStagesSSE(this.project.id, {
        autoReconnect: false,
      });

      // 监听各种事件
      this.pipelineSSEClient
        .on('connected', (data) => {
          console.log('[Pipeline SSE] 已连接:', data);
        })
        .on('stage_update', (data) => {
          console.log('[Pipeline SSE] 阶段更新:', data);

          // 设置阶段的 loading 状态
          if (data.stage && data.stage !== 'pipeline' && data.status === 'processing') {
            this.$refs.projectCanvas?.setStageLoading(data.stage, true);
          }

          // 显示阶段更新消息
          if (data.stage && data.stage !== 'pipeline') {
            const stageNames = {
              'rewrite': '剧本精修',
              'asset_extraction': '资产抽取',
              'storyboard': '分镜生成',
              'image_generation': '图片生成',
              'multi_grid_image': '多宫格图片',
              'image_edit': '图片编辑',
              'camera_movement': '运镜生成',
              'video_generation': '视频生成'
            };
            const stageName = stageNames[data.stage] || data.stage;
            this.$message.info(`${stageName}: ${data.message || '执行中...'}`);
          }

          // 实时刷新画布数据
          this.refreshCanvasData();
        })
        .on('stage_completed', (data) => {
          console.log('[Pipeline SSE] 阶段完成:', data);

          // 清除阶段的 loading 状态
          if (data.stage && data.stage !== 'pipeline') {
            this.$refs.projectCanvas?.setStageLoading(data.stage, false);
          }

          // 显示阶段完成消息
          if (data.stage && data.stage !== 'pipeline') {
            const stageNames = {
              'rewrite': '剧本精修',
              'asset_extraction': '资产抽取',
              'storyboard': '分镜生成',
              'image_generation': '图片生成',
              'multi_grid_image': '多宫格图片',
              'image_edit': '图片编辑',
              'camera_movement': '运镜生成',
              'video_generation': '视频生成'
            };
            const stageName = stageNames[data.stage] || data.stage;
            this.$message.success(`${stageName} 完成`);
          }

          // 刷新画布数据
          this.refreshCanvasData();
        })
        .on('progress', (data) => {
          console.log('[Pipeline SSE] 进度更新:', data);

          // 根据阶段类型设置对应分镜节点的 loading 状态
          if (data.stage && data.current) {
            const stageToItemType = {
              'image_generation': 'image',
              'multi_grid_image': 'multi_grid_image',
              'image_edit': 'image_edit',
              'camera_movement': 'camera',
              'video_generation': 'video'
            };
            const itemType = stageToItemType[data.stage];
            if (itemType) {
              // 设置当前处理的分镜节点为 loading 状态
              this.$refs.projectCanvas?.setItemLoading(itemType, data.current, true);
            }
          }
          // 可以在这里更新进度条
        })
        .on('item_completed', (data) => {
          console.log('[Pipeline SSE] 单项完成:', data);

          // 清除单个分镜节点的 loading 状态
          if (data.item_type && data.sequence_number) {
            this.$refs.projectCanvas?.setItemLoading(data.item_type, data.sequence_number, false);
          }

          // 单个分镜的图片/运镜/视频生成完成，刷新画布
          const itemTypeNames = {
            'image': '图片',
            'multi_grid_image': '多宫格图片',
            'image_edit': '图片编辑',
            'camera': '运镜',
            'video': '视频'
          };
          const itemTypeName = itemTypeNames[data.item_type] || data.item_type;
          console.log(`[Pipeline SSE] 分镜 ${data.sequence_number} ${itemTypeName}生成完成`);

          // 刷新画布数据
          this.refreshCanvasData();
        })
        .on('done', (data) => {
          console.log('[Pipeline SSE] done 消息:', data);

          // 全阶段订阅里偶尔也会收到 done，这里统一做一次轻量刷新
          this.refreshCanvasData();
        })
        .on('pipeline_done', (data) => {
          console.log('[Pipeline SSE] 流程完成:', data);
          this.clearPipelineSSEMarker();
          this.$message.success('工作流执行完成！');

          // 重置所有 loading 状态
          this.$refs.projectCanvas?.resetAllLoading();

          // 刷新项目数据
          this.fetchData(true);

          // 断开连接
          if (this.pipelineSSEClient) {
            this.pipelineSSEClient.disconnect();
            this.pipelineSSEClient = null;
          }
        })
        .on('pipeline_error', (data) => {
          console.error('[Pipeline SSE] 流程错误:', data);
          this.clearPipelineSSEMarker();
          this.$message.error(data.error || '工作流执行失败');

          // 重置所有 loading 状态
          this.$refs.projectCanvas?.resetAllLoading();

          // 刷新项目数据
          this.fetchData(true);

          // 断开连接
          if (this.pipelineSSEClient) {
            this.pipelineSSEClient.disconnect();
            this.pipelineSSEClient = null;
          }
        })
        .on('error', (data) => {
          console.error('[Pipeline SSE] 阶段错误:', data);

          // 显示阶段错误消息
          if (data.stage && data.stage !== 'pipeline') {
            const stageNames = {
              'rewrite': '剧本精修',
              'asset_extraction': '资产抽取',
              'storyboard': '分镜生成',
              'image_generation': '图片生成',
              'multi_grid_image': '多宫格图片',
              'image_edit': '图片编辑',
              'camera_movement': '运镜生成',
              'video_generation': '视频生成'
            };
            const stageName = stageNames[data.stage] || data.stage;
            this.$message.error(`${stageName} 失败: ${data.error || '未知错误'}`);

            // 刷新画布数据
            this.refreshCanvasData();
          }

          if (!data.stage || data.stage === 'pipeline') {
            this.refreshCanvasData();
          }
        })
        .on('stream_end', () => {
          this.pipelineSSEClient = null;
        })
        .on('close', () => {
          console.log('[Pipeline SSE] 连接已关闭');
          this.pipelineSSEClient = null;
        });
    },
  },
};
</script>

<style scoped>
.project-detail {
  width: 100%;
  max-width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.project-detail__canvas {
  height: 100%;
  min-height: 600px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
</style>
