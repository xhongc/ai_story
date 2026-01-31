<template>
  <div class="project-detail">
    <loading-container :loading="loading">
      <!-- 只展示工作流画布 -->
      <project-canvas
        v-if="project"
        :project="project"
        :stages="stages"
        @execute-stage="handleExecuteStage"
        @save-stage="handleSaveStage"
        @generate-image="handleGenerateImage"
        @generate-camera="handleGenerateCamera"
        @generate-video="handleGenerateVideo"
        @save-storyboard="handleSaveStoryboard"
        @delete-storyboard="handleDeleteStoryboard"
        @draft-generated="handleDraftGenerated"
        @pipeline-started="handlePipelineStarted"
        @storyboard-generated="handleStoryboardGenerated"
      />
    </loading-container>
  </div>
</template>

<script>
import { mapActions } from 'vuex';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import ProjectCanvas from '@/components/canvas/ProjectCanvas.vue';
import { formatDate } from '@/utils/helpers';
import { SSEClient, createProjectStageSSE } from '@/services/sseService';

export default {
  name: 'ProjectDetail',
  components: {
    LoadingContainer,
    ProjectCanvas,
  },
  data() {
    return {
      loading: false,
      project: null,
      stages: [],
      storyboards: [],
      savedScrollPosition: 0, // 保存滚动位置
      // SSE 客户端
      pipelineSSEClient: null,
      // 单阶段 SSE 客户端
      stageSSEClient: null,
    };
  },
  created() {
    this.fetchData();
  },
  beforeDestroy() {
    // 组件销毁时断开 SSE 连接
    if (this.pipelineSSEClient) {
      this.pipelineSSEClient.disconnect();
    }
    if (this.stageSSEClient) {
      this.stageSSEClient.disconnect();
    }
  },
  methods: {
    ...mapActions('projects', ['fetchProject', 'fetchProjectStages', 'executeStage', 'updateProject', 'updateStageData']),
    formatDate,

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

        // 获取分镜数据（必须在stages加载后）
        this.fetchStoryboardsFromStages();

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

    fetchStoryboardsFromStages() {
      try {
        // 从分镜阶段的output_data中获取分镜列表
        const storyboardStage = this.stages.find(s => s.stage_type === 'storyboard');
        console.log('[ProjectDetail] Storyboard stage:', storyboardStage);

        if (storyboardStage && storyboardStage.output_data && storyboardStage.output_data.storyboards) {
          // 获取每个分镜的详细数据（包括images, camera_movement, videos）
          this.storyboards = storyboardStage.output_data.storyboards.map((sb, index) => ({
            ...sb,
            sequence_number: index + 1,
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
      // 断开之前的连接
      if (this.stageSSEClient) {
        this.stageSSEClient.disconnect();
      }

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
        this.stages = await this.fetchProjectStages(projectId);
        this.fetchStoryboardsFromStages();
        console.log('[ProjectDetail] 画布数据已刷新');
      } catch (error) {
        console.error('[ProjectDetail] 刷新画布数据失败:', error);
      }
    },

    async handleSaveStage({ stageType, inputData, outputData, skipRefresh = false }) {
      try {
        await this.updateStageData({
          projectId: this.project.id,
          stageName: stageType,
          data: { input_data: inputData, output_data: outputData },
        });
        this.$message.success('保存成功');
        // 只有在非流式生成期间才刷新数据，避免断开SSE连接
        if (!skipRefresh) {
          await this.fetchData(true); // 保持滚动位置
        }
      } catch (error) {
        console.error('Failed to save stage:', error);
        this.$message.error('保存失败');
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

    async handleSaveStoryboard({ storyboardId, data }) {
      try {
        // TODO: 调用保存分镜API
        console.log('Save storyboard:', storyboardId, data);
        this.$message.success('保存成功');
        await this.fetchData(true);
      } catch (error) {
        console.error('Failed to save storyboard:', error);
        this.$message.error('保存失败');
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

    handlePipelineStarted({ taskId, channel }) {
      console.log('[ProjectDetail] Pipeline started:', { taskId, channel });

      // 断开之前的连接
      if (this.pipelineSSEClient) {
        this.pipelineSSEClient.disconnect();
      }

      // 创建 SSE 客户端监听所有阶段
      // 注意：URL 路径是 /api/v1/projects/sse/projects/{id}/
      const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8010';
      const sseUrl = `${API_BASE_URL}/api/v1/projects/sse/projects/${this.project.id}/`;

      console.log('[ProjectDetail] 连接 SSE:', sseUrl);

      this.pipelineSSEClient = new SSEClient();
      this.pipelineSSEClient.connect(sseUrl);

      // 监听各种事件
      this.pipelineSSEClient
        .on('connected', (data) => {
          console.log('[Pipeline SSE] 已连接:', data);
        })
        .on('stage_update', (data) => {
          console.log('[Pipeline SSE] 阶段更新:', data);

          // 显示阶段更新消息
          if (data.stage && data.stage !== 'pipeline') {
            const stageNames = {
              'rewrite': '文案改写',
              'storyboard': '分镜生成',
              'image_generation': '图片生成',
              'camera_movement': '运镜生成',
              'video_generation': '视频生成'
            };
            const stageName = stageNames[data.stage] || data.stage;
            this.$message.info(`${stageName}: ${data.message || '执行中...'}`);
          }

          // 实时刷新画布数据
          this.refreshCanvasData();
        })
        .on('progress', (data) => {
          console.log('[Pipeline SSE] 进度更新:', data);
          // 可以在这里更新进度条
        })
        .on('done', (data) => {
          console.log('[Pipeline SSE] 完成:', data);

          // 显示阶段完成消息
          if (data.stage && data.stage !== 'pipeline') {
            const stageNames = {
              'rewrite': '文案改写',
              'storyboard': '分镜生成',
              'image_generation': '图片生成',
              'camera_movement': '运镜生成',
              'video_generation': '视频生成'
            };
            const stageName = stageNames[data.stage] || data.stage;
            this.$message.success(`${stageName} 完成`);

            // 实时刷新画布数据
            this.refreshCanvasData();
          }

          // 处理 pipeline 整体完成
          if (data.stage === 'pipeline') {
            this.$message.success('工作流执行完成！');

            // 刷新项目数据
            this.fetchData(true);

            // 断开连接
            if (this.pipelineSSEClient) {
              this.pipelineSSEClient.disconnect();
              this.pipelineSSEClient = null;
            }
          }
        })
        .on('error', (data) => {
          console.error('[Pipeline SSE] 错误:', data);

          // 显示阶段错误消息
          if (data.stage && data.stage !== 'pipeline') {
            const stageNames = {
              'rewrite': '文案改写',
              'storyboard': '分镜生成',
              'image_generation': '图片生成',
              'camera_movement': '运镜生成',
              'video_generation': '视频生成'
            };
            const stageName = stageNames[data.stage] || data.stage;
            this.$message.error(`${stageName} 失败: ${data.error || '未知错误'}`);

            // 刷新画布数据
            this.refreshCanvasData();
          }

          // 处理 pipeline 整体错误
          if (data.stage === 'pipeline') {
            this.$message.error(data.error || '工作流执行失败');

            // 刷新项目数据
            this.fetchData(true);

            // 断开连接
            if (this.pipelineSSEClient) {
              this.pipelineSSEClient.disconnect();
              this.pipelineSSEClient = null;
            }
          }
        })
        .on('close', () => {
          console.log('[Pipeline SSE] 连接已关闭');
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
}
</style>
