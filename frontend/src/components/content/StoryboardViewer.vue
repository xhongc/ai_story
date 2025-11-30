<template>
  <div class="storyboard-viewer">
    <!-- 视图切换工具栏 -->
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-3">
        <div class="btn-group">
          <button
            class="btn btn-sm"
            :class="{ 'btn-active': viewMode === 'cards' }"
            @click="viewMode = 'cards'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z" />
            </svg>
            卡片视图
          </button>
          <button
            class="btn btn-sm"
            :class="{ 'btn-active': viewMode === 'markdown' }"
            @click="viewMode = 'markdown'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Markdown格式
          </button>
        </div>

        <!-- 新增空白卡片按钮 -->
        <button
          v-if="viewMode === 'cards'"
          class="btn btn-sm btn-primary gap-2"
          @click="addBlankCard"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          新增空白卡片
        </button>
      </div>

      <!-- 统计信息 -->
      <div v-if="scenes && scenes.length > 0" class="badge badge-primary badge-lg">
        共 {{ scenes.length }} 个分镜
      </div>
    </div>

    <!-- 卡片视图 -->
    <div v-if="viewMode === 'cards'" class="cards-container">
      <div v-if="scenes && scenes.length > 0" class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div
          v-for="(scene, index) in scenes"
          :key="scene.scene_number"
          class="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow duration-300"
        >
          <!-- 卡片头部 -->
          <div class="card-body p-4">
            <div class="flex justify-between items-center mb-3">
              <div class="badge badge-lg badge-secondary">
                场景 {{ scene.scene_number }}
              </div>
              <div class="flex items-center gap-2">
                <!-- 镜头类型 - 可编辑 -->
                <select
                  v-if="isSceneEditable(scene) && isEditing(scene.scene_number, 'shot_type')"
                  v-model="scene.shot_type"
                  class="select select-xs select-bordered"
                  @change="saveEdit(scene.scene_number, 'shot_type')"
                >
                  <option value="标准镜头">标准镜头</option>
                  <option value="特写">特写</option>
                  <option value="中景">中景</option>
                  <option value="远景">远景</option>
                  <option value="全景">全景</option>
                  <option value="俯视">俯视</option>
                  <option value="仰视">仰视</option>
                </select>
                <div
                  v-else
                  class="badge badge-outline cursor-pointer"
                  :class="{ 'hover:badge-primary': isSceneEditable(scene) }"
                  @click="isSceneEditable(scene) && toggleEditMode(scene.scene_number, 'shot_type')"
                  :title="isSceneEditable(scene) ? '点击编辑镜头类型' : ''"
                >
                  {{ scene.shot_type || '标准镜头' }}
                </div>
                <!-- 在此位置插入卡片按钮 -->
                <div class="dropdown dropdown-end">
                  <label tabindex="0" class="btn btn-xs btn-ghost gap-1" title="插入卡片">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                  </label>
                  <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-40">
                    <li><a @click="insertBlankCard(index, 'before')">在此之前插入</a></li>
                    <li><a @click="insertBlankCard(index, 'after')">在此之后插入</a></li>
                  </ul>
                </div>
                <!-- 删除卡片按钮 -->
                <button
                  v-if="scenes.length > 1"
                  class="btn btn-xs btn-ghost btn-error gap-1"
                  @click="removeCard(index)"
                  title="删除此卡片"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
                <!-- AI生成执行按钮 -->
                <button
                  class="btn btn-xs btn-primary gap-1"
                  :class="{ 'loading': executingScenes[scene.scene_number] }"
                  :disabled="executingScenes[scene.scene_number] || !projectId"
                  @click="executeSceneGeneration(scene.scene_number)"
                  title="执行AI生成图片"
                >
                  <svg v-if="!executingScenes[scene.scene_number]" xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  {{ executingScenes[scene.scene_number] ? '生成中...' : '执行' }}
                </button>
              </div>
            </div>

            <!-- 图片列表 -->
            <div v-if="!scene.video_urls || scene.video_urls.length === 0">
            <div v-if="scene.urls && scene.urls.length > 0" class="mb-3">
              <div class="text-xs font-semibold text-base-content/60 mb-2 flex items-center gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                生成图片 ({{ getSelectedImageIndex(scene.scene_number) + 1 }}/{{ scene.urls.length }})
              </div>

              <!-- 当前选中的图片预览 -->
              <div class="relative rounded-lg overflow-hidden bg-base-200 mb-2">
                <img
                  :src="getSelectedImage(scene.scene_number)"
                  :alt="`场景 ${scene.scene_number} - 图片 ${getSelectedImageIndex(scene.scene_number) + 1}`"
                  class="w-full object-cover cursor-pointer hover:opacity-90 transition-opacity"
                  @click="openImageModal(scene.scene_number)"
                />
                <div class="absolute top-2 right-2 badge badge-sm bg-black/50 text-white border-0">
                  {{ getSelectedImageIndex(scene.scene_number) + 1 }}/{{ scene.urls.length }}
                </div>
              </div>

              <!-- 图片缩略图选择器 -->
              <div v-if="scene.urls.length > 1" class="flex gap-2 overflow-x-auto pb-2">
                <div
                  v-for="(url, index) in scene.urls"
                  :key="index"
                  class="flex-shrink-0 cursor-pointer rounded border-2 transition-all"
                  :class="getSelectedImageIndex(scene.scene_number) === index ? 'border-primary ring-2 ring-primary/50' : 'border-base-300 hover:border-primary/50'"
                  @click="selectImage(scene.scene_number, index)"
                >
                  <img
                    :src="url.url"
                    :alt="`缩略图 ${index + 1}`"
                    class="w-16 h-16 object-cover rounded"
                  />
                </div>
              </div>
            </div>
            </div>
            <!-- 视频列表 -->
            <div v-if="scene.video_urls && scene.video_urls.length > 0" class="mb-3">
              <div class="text-xs font-semibold text-base-content/60 mb-2 flex items-center gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                生成视频 ({{ getSelectedVideoIndex(scene.scene_number) + 1 }}/{{ scene.video_urls.length }})
              </div>

              <!-- 当前选中的视频预览 -->
              <div class="relative rounded-lg overflow-hidden bg-base-200 mb-2">
                <video
                  :src="getSelectedVideo(scene.scene_number)"
                  class="w-full cursor-pointer hover:opacity-90 transition-opacity"
                  controls
                  preload="metadata"
                >
                  您的浏览器不支持视频播放
                </video>
                <div class="absolute top-2 right-2 badge badge-sm bg-black/50 text-white border-0">
                  {{ getSelectedVideoIndex(scene.scene_number) + 1 }}/{{ scene.video_urls.length }}
                </div>
              </div>

              <!-- 视频缩略图选择器 -->
              <div v-if="scene.video_urls.length > 1" class="flex gap-2 overflow-x-auto pb-2">
                <div
                  v-for="(video, index) in scene.video_urls"
                  :key="index"
                  class="flex-shrink-0 cursor-pointer rounded border-2 transition-all relative"
                  :class="getSelectedVideoIndex(scene.scene_number) === index ? 'border-primary ring-2 ring-primary/50' : 'border-base-300 hover:border-primary/50'"
                  @click="selectVideo(scene.scene_number, index)"
                >
                  <video
                    :src="video.url"
                    class="w-16 h-16 object-cover rounded"
                    preload="metadata"
                  ></video>
                  <!-- 播放图标叠加层 -->
                  <div class="absolute inset-0 flex items-center justify-center bg-black/30 rounded">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <!-- 旁白 -->
            <div class="mb-3">
              <div class="text-xs font-semibold text-base-content/60 mb-1 flex items-center justify-between">
                <div class="flex items-center gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                  旁白文本
                </div>
                <button
                  class="btn btn-xs btn-ghost gap-1"
                  @click="toggleEditMode(scene.scene_number, 'narration')"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                  {{ isEditing(scene.scene_number, 'narration') ? '完成' : '编辑' }}
                </button>
              </div>
              <textarea
                v-if="isEditing(scene.scene_number, 'narration')"
                v-model="scene.narration"
                class="textarea textarea-bordered w-full text-sm"
                rows="3"
                @blur="saveEdit(scene.scene_number, 'narration')"
              ></textarea>
              <p v-else class="text-sm leading-relaxed">{{ scene.narration }}</p>
            </div>

            <!-- 视觉描述 -->
            <div class="mb-3">
              <div class="text-xs font-semibold text-base-content/60 mb-1 flex items-center justify-between">
                <div class="flex items-center gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  视觉提示词
                </div>
                <div class="flex items-center gap-1">
                  <button
                    class="btn btn-xs btn-ghost gap-1"
                    @click="toggleEditMode(scene.scene_number, 'visual_prompt')"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                    {{ isEditing(scene.scene_number, 'visual_prompt') ? '完成' : '编辑' }}
                  </button>
                  <button class="btn btn-xs btn-ghost gap-1" @click="copyPrompt(scene.visual_prompt)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    复制
                  </button>
                </div>
              </div>
              <textarea
                v-if="isEditing(scene.scene_number, 'visual_prompt')"
                v-model="scene.visual_prompt"
                class="textarea textarea-bordered w-full text-sm"
                rows="5"
                @blur="saveEdit(scene.scene_number, 'visual_prompt')"
              ></textarea>
              <div v-else class="collapse collapse-arrow bg-base-200 rounded-lg">
                <input type="checkbox" />
                <div class="collapse-title text-xs font-medium">
                  点击展开完整描述
                </div>
                <div class="collapse-content text-xs">
                  <p class="leading-relaxed whitespace-pre-wrap">{{ scene.visual_prompt }}</p>
                </div>
              </div>
            </div>

            <!-- 运镜提示词 -->
            <div v-if="scene.camera_movement || isSceneEditable(scene)" class="mb-3">
              <div class="text-xs font-semibold text-base-content/60 mb-1 flex items-center justify-between">
                <div class="flex items-center gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  运镜提示词
                </div>
                <div class="flex items-center gap-1">
                  <button
                    class="btn btn-xs btn-ghost gap-1"
                    @click="toggleEditMode(scene.scene_number, 'camera_movement')"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                    {{ isEditing(scene.scene_number, 'camera_movement') ? '完成' : '编辑' }}
                  </button>
                  <button v-if="scene.camera_movement" class="btn btn-xs btn-ghost gap-1" @click="copyPrompt(scene.camera_movement)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    复制
                  </button>
                </div>
              </div>
              <textarea
                v-if="isEditing(scene.scene_number, 'camera_movement')"
                v-model="scene.camera_movement"
                class="textarea textarea-bordered w-full text-sm"
                rows="4"
                placeholder="请输入运镜描述..."
                @blur="saveEdit(scene.scene_number, 'camera_movement')"
              ></textarea>
              <div v-else-if="scene.camera_movement" class="collapse collapse-arrow bg-base-200 rounded-lg">
                <input type="checkbox" />
                <div class="collapse-title text-xs font-medium">
                  点击展开完整描述
                </div>
                <div class="collapse-content text-xs">
                  <p class="leading-relaxed whitespace-pre-wrap">{{ scene.camera_movement }}</p>
                </div>
              </div>
              <p v-else class="text-xs text-base-content/40 italic">暂无运镜描述</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="text-center py-12">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mx-auto text-base-content/20 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
        </svg>
        <p class="text-base-content/60">暂无分镜数据</p>
        <p class="text-sm text-base-content/40 mt-2">请先生成分镜内容</p>
      </div>
    </div>

    <!-- Markdown视图 -->
    <div v-else-if="viewMode === 'markdown'" class="markdown-container">
      <div class="relative">
        <!-- 复制按钮 -->
        <button
          class="btn btn-sm absolute top-2 right-2 z-10"
          @click="copyMarkdown"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          复制文本
        </button>

        <!-- Markdown内容块 -->
        <div class="mockup-code bg-neutral text-neutral-content overflow-auto max-h-[600px] max-w-full">
          <pre class="text-sm whitespace-pre-wrap break-words px-6 py-4"><code>{{ formattedMarkdown }}</code></pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import projectApi from '@/api/projects';
import WSClient from '@/utils/wsClient';
import { createProjectStageSSE, SSE_EVENT_TYPES } from '@/services/sseService';

export default {
  name: 'StoryboardViewer',
  props: {
    // 可以接收原始JSON字符串、对象或数组
    data: {
      type: [String, Object, Array],
      default: null,
    },
    // 项目ID - 用于执行AI生成
    projectId: {
      type: String,
      default: null,
    },
    stageType: {
      type: String,
      required: true,
      validator: (value) => ['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation'].includes(value),
    },
  },
  data() {
    return {
      viewMode: 'cards', // 'cards' 或 'json'
      selectedImages: {}, // 记录每个场景选择的图片索引,格式: { scene_number: imageIndex }
      selectedVideos: {}, // 记录每个场景选择的视频索引,格式: { scene_number: videoIndex }
      executingScenes: {}, // 记录正在执行的场景,格式: { scene_number: boolean }
      localScenes: [], // 本地场景数据副本，用于支持新增空白卡片
      editingFields: {}, // 记录正在编辑的字段,格式: { 'scene_number_field': true }
    };
  },
  created() {
  },
  beforeDestroy() {
    this.disconnectSSE();
  },
  watch: {
    // 监听 data prop 的变化
    data: {
      deep: true,
      handler(newData, oldData) {
        console.log('[StoryboardViewer] data prop 更新:', {
          newData,
          oldData,
          scenes: this.scenes
        });
        // 当外部数据更新时，清空本地修改（如果需要保留本地修改，可以注释掉这行）
        // this.localScenes = [];
      }
    },
    // 监听 projectId 变化，重新连接 WebSocket
    projectId(newId, oldId) {
      if (newId !== oldId) {
        console.log('[StoryboardViewer] projectId 变化，重新连接 WebSocket');
      }
    }
  },
  computed: {
    // 解析场景数据
    scenes() {
      // 如果有本地修改的数据，优先使用本地数据
      if (this.localScenes.length > 0) {
        return this.localScenes;
      }

      if (!this.data) return [];
      try {
        let parsedData = this.data;

        // 如果是字符串,尝试解析为JSON
        if (typeof this.data === 'string') {
          parsedData = JSON.parse(this.data);
        }

        // 支持多种数据格式
        if (Array.isArray(parsedData)) {
          // 直接是数组
          return parsedData;
        } else if (parsedData.scenes && Array.isArray(parsedData.scenes)) {
          // 包含scenes字段的对象
          return parsedData.scenes;
        } else if (parsedData.storyboards && Array.isArray(parsedData.storyboards)) {
          // 包含storyboards字段的对象
          return parsedData.storyboards;
        }

        return [];
      } catch (error) {
        console.error('解析分镜数据失败:', error);
        return [];
      }
    },

    // 格式化的JSON字符串
    formattedJSON() {
      if (!this.data) return '{}';

      try {
        let dataToFormat = this.data;

        // 如果已经是字符串,���解析再格式化以确保格式统一
        if (typeof this.data === 'string') {
          dataToFormat = JSON.parse(this.data);
        }

        return JSON.stringify(dataToFormat, null, 2);
      } catch (error) {
        // 如果解析失败,返回原始字符串
        return typeof this.data === 'string' ? this.data : JSON.stringify(this.data, null, 2);
      }
    },

    // 格式化的Markdown字符串
    formattedMarkdown() {
      if (!this.scenes || this.scenes.length === 0) {
        return '暂无分镜数据';
      }

      return this.scenes.map((scene) => {
        const sceneNumber = scene.scene_number || '未知';
        const narration = scene.narration || '无';
        const shotType = scene.shot_type || '标准镜头';
        const visualPrompt = scene.visual_prompt || '无';
        const cameraMovement = scene.camera_movement || null;

        let markdown = `场景 ${sceneNumber}
文案: ${narration}
镜头类型: ${shotType}
画面描述: ${visualPrompt}`;

        if (cameraMovement) {
          markdown += `\n运镜描述: ${cameraMovement}`;
        }

        return markdown;
      }).join('\n\n---\n\n');
    },
  },
  methods: {
    // 新增空白卡片（添加到末尾）
    addBlankCard() {
      this.insertBlankCard(this.scenes.length - 1, 'after');
    },

    // 在指定位置插入空白卡片
    insertBlankCard(index, position) {
      // 如果本地数据为空，先从原始数据初始化
      if (this.localScenes.length === 0 && this.scenes.length > 0) {
        this.localScenes = JSON.parse(JSON.stringify(this.scenes));
      }

      // 计算插入位置
      let insertIndex;
      if (position === 'before') {
        insertIndex = index;
      } else if (position === 'after') {
        insertIndex = index + 1;
      } else {
        insertIndex = this.localScenes.length; // 默认添加到末尾
      }

      // 计算新的场景编号（基于插入位置）
      let newSceneNumber;
      if (this.localScenes.length === 0) {
        newSceneNumber = 1;
      } else if (insertIndex === 0) {
        // 插入到最前面
        newSceneNumber = this.localScenes[0].scene_number - 1;
        if (newSceneNumber < 1) newSceneNumber = 1;
      } else if (insertIndex >= this.localScenes.length) {
        // 插入到最后面
        const maxSceneNumber = Math.max(...this.localScenes.map(s => s.scene_number || 0));
        newSceneNumber = maxSceneNumber + 1;
      } else {
        // 插入到中间，使用前后场景编号的平均值（小数）
        const prevNumber = this.localScenes[insertIndex - 1].scene_number;
        const nextNumber = this.localScenes[insertIndex].scene_number;
        newSceneNumber = (prevNumber + nextNumber) / 2;
      }

      // 创建空白卡片模板
      const blankCard = {
        scene_number: newSceneNumber,
        narration: '请输入旁白文本...',
        visual_prompt: '请输入视觉提示词...',
        shot_type: '标准镜头',
        camera_movement: '',
        urls: [],
        video_urls: [],
      };

      // 插入到指定位置
      this.localScenes.splice(insertIndex, 0, blankCard);

      // 重新排序场景编号（确保编号连续）
      this.reorderSceneNumbers();

      // 触发事件通知父组件数据已更新
      this.$emit('scenes-updated', this.localScenes);

      const positionText = position === 'before' ? '之前' : '之后';
      this.$message?.success(`已在场景 ${this.localScenes[insertIndex === 0 ? 0 : insertIndex - 1].scene_number} ${positionText}插入新场景`);
    },

    // 重新排序场景编号
    reorderSceneNumbers() {
      this.localScenes.forEach((scene, index) => {
        scene.scene_number = index + 1;
      });
    },

    // 删除卡片
    removeCard(index) {
      // 如果本地数据为空，先从原始数据初始化
      if (this.localScenes.length === 0 && this.scenes.length > 0) {
        this.localScenes = JSON.parse(JSON.stringify(this.scenes));
        console.log('[StoryboardViewer] 删除前初始化本地场景数据');
      }

      // 至少保留一个场景
      if (this.localScenes.length <= 1) {
        this.$message?.warning('至少需要保留一个场景');
        return;
      }

      // 获取要删除的场景信息
      const sceneToRemove = this.localScenes[index];
      const sceneNumber = sceneToRemove.scene_number;

      // 确认删除
      if (confirm(`确定要删除场景 ${sceneNumber} 吗？此操作不可恢复。`)) {
        // 从数组中删除
        this.localScenes.splice(index, 1);

        // 重新排序场景编号
        this.reorderSceneNumbers();

        // 清除该场景的编辑状态
        Object.keys(this.editingFields).forEach(key => {
          if (key.startsWith(`${sceneNumber}_`)) {
            this.$delete(this.editingFields, key);
          }
        });

        // 触发事件通知父组件数据已更新
        this.$emit('scenes-updated', this.localScenes);

        this.$message?.success(`已删除场景 ${sceneNumber}`);

        console.log('[StoryboardViewer] 删除场景:', sceneNumber);
      }
    },

    // 判断场景是否可编辑（所有场景都可编辑）
    isSceneEditable(scene) {
      // 所有场景都可以编辑
      return true;
    },

    // 切换编辑模式
    toggleEditMode(sceneNumber, field) {
      // 如果本地数据为空，先从原始数据初始化（进入编辑模式）
      if (this.localScenes.length === 0 && this.scenes.length > 0) {
        this.localScenes = JSON.parse(JSON.stringify(this.scenes));
        console.log('[StoryboardViewer] 初始化本地场景数据，进入编辑模式');
      }

      const key = `${sceneNumber}_${field}`;
      if (this.editingFields[key]) {
        // 如果正在编辑，则保存并退出编辑模式
        this.saveEdit(sceneNumber, field);
      } else {
        // 进入编辑模式
        this.$set(this.editingFields, key, true);
      }
    },

    // 判断字段是否正在编辑
    isEditing(sceneNumber, field) {
      const key = `${sceneNumber}_${field}`;
      return this.editingFields[key] === true;
    },

    // 保存编辑
    saveEdit(sceneNumber, field) {
      const key = `${sceneNumber}_${field}`;
      this.$set(this.editingFields, key, false);

      // 确保本地数据已初始化
      if (this.localScenes.length === 0 && this.scenes.length > 0) {
        this.localScenes = JSON.parse(JSON.stringify(this.scenes));
        console.log('[StoryboardViewer] 保存时初始化本地场景数据');
      }

      // 触发事件通知父组件数据已更新
      if (this.localScenes.length > 0) {
        console.log('[StoryboardViewer] 保存编辑，触发 scenes-updated 事件:', this.localScenes);
        this.$emit('scenes-updated', this.localScenes);
      } else {
        console.warn('[StoryboardViewer] 本地场景数据为空，无法保存编辑');
      }

      console.log(`[StoryboardViewer] 保存编辑: 场景 ${sceneNumber}, 字段 ${field}`);
    },

    // 获取当前场景选中的图片索引(默认第一张)
    getSelectedImageIndex(sceneNumber) {
      if (this.selectedImages[sceneNumber] !== undefined) {
        return this.selectedImages[sceneNumber];
      }
      return 0; // 默认选择第一张
    },

    // 获取当前场景选中的图片URL
    getSelectedImage(sceneNumber) {
      const scene = this.scenes.find(s => s.scene_number === sceneNumber);
      if (!scene || !scene.urls || scene.urls.length === 0) {
        return '';
      }
      const index = this.getSelectedImageIndex(sceneNumber);
      return scene.urls[index].url || scene.urls[0].url;
    },

    // 选择指定索引的图片
    selectImage(sceneNumber, imageIndex) {
      this.$set(this.selectedImages, sceneNumber, imageIndex);
    },

    // 获取当前场景选中的视频索引(默认第一个)
    getSelectedVideoIndex(sceneNumber) {
      if (this.selectedVideos[sceneNumber] !== undefined) {
        return this.selectedVideos[sceneNumber];
      }
      return 0; // 默认选择第一个
    },

    // 获取当前场景选中的视频URL
    getSelectedVideo(sceneNumber) {
      const scene = this.scenes.find(s => s.scene_number === sceneNumber);
      if (!scene || !scene.video_urls || scene.video_urls.length === 0) {
        return '';
      }
      const index = this.getSelectedVideoIndex(sceneNumber);
      return scene.video_urls[index].url || scene.video_urls[0].url;
    },

    // 选择指定索引的视频
    selectVideo(sceneNumber, videoIndex) {
      this.$set(this.selectedVideos, sceneNumber, videoIndex);
    },

    // 打开图片查看模态框(可选功能,暂时只是占位)
    openImageModal(sceneNumber) {
      // TODO: 实现图片放大查看功能
      console.log('打开场景', sceneNumber, '的图片查看器');
    },

    // 复制提示词到剪贴板
    async copyPrompt(prompt) {
      try {
        await navigator.clipboard.writeText(prompt);
        this.$message?.success('提示词已复制到剪贴板');
      } catch (error) {
        console.error('复制失败:', error);
        this.$message?.error('复制失败,请手动复制');
      }
    },

    // 复制JSON到剪贴板
    async copyJSON() {
      try {
        await navigator.clipboard.writeText(this.formattedJSON);
        this.$message?.success('JSON已复制到剪贴板');
      } catch (error) {
        console.error('复制失败:', error);
        this.$message?.error('复制失败,请手动复制');
      }
    },
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
    // 复制Markdown到剪贴板
    async copyMarkdown() {
      try {
        await navigator.clipboard.writeText(this.formattedMarkdown);
        this.$message?.success('文本已复制到剪贴板');
      } catch (error) {
        console.error('复制失败:', error);
        this.$message?.error('复制失败,请手动复制');
      }
    },

    // 执行单个场景的AI生成
    async executeSceneGeneration(sceneNumber) {
      if (!this.projectId) {
        this.$message?.error('缺少项目ID,无法执行生成');
        return;
      }

      // 查找对应的场景数据
      const scene = this.scenes.find(s => s.scene_number === sceneNumber);
      if (!scene) {
        this.$message?.error(`未找到场景 ${sceneNumber} 的数据`);
        return;
      }

      // 设置加载状态
      this.$set(this.executingScenes, sceneNumber, true);

      try {
        // 准备输入数据 - 单个场景的分镜数据
        const inputData = {
          storyboard_ids: [sceneNumber],
          narration: scene.narration,
          visual_prompt: scene.visual_prompt,
          shot_type: scene.shot_type,
          camera_movement: scene.camera_movement,
        };
        this.connectSSE();
        // 调用API执行图片生成阶段
        const response = await projectApi.executeStage(
          this.projectId,
          this.stageType,
          inputData
        );

        this.$message?.success(`场景 ${sceneNumber} AI生成已启动，请等待实时更新`);

        // WebSocket 会自动监听完成消息并触发刷新

      } catch (error) {
        console.error('执行场景生成失败:', error);
        const errorMsg = error.response?.data?.error || error.message || '生成失败';
        this.$message?.error(`场景 ${sceneNumber} 生成失败: ${errorMsg}`);
        // 清除加载状态
        this.$set(this.executingScenes, sceneNumber, false);
      }
    },


    // 处理阶段更新事件
    handleStageUpdate(data) {
      console.log('[StoryboardViewer] 收到阶段更新:', data);

      // 如果是处理中状态，更新进度
      if (data.status === 'processing') {
        console.log('[StoryboardViewer] 阶段处理中...');
        // 可以在这里显示进度条或加载状态
      }
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

    // 处理阶段完成事件
    handleStageDone(data) {
      console.log('[StoryboardViewer] 阶段完成:', data);

      // 清除所有执行状态
      this.executingScenes = {};

      // 触发父组件刷新数据
      this.$emit('scene-generated', {
        sceneNumber: null, // null表示整体刷新
        response: data,
      });

      this.$message?.success('生成完成，页面已自动更新');
    },

    // 处理阶段错误事件
    handleStageError(data) {
      console.error('[StoryboardViewer] 阶段失败:', data);

      // 清除所有执行状态
      this.executingScenes = {};

      this.$message?.error(`生成失败: ${data.error || '未知错误'}`);
    },
  },
};
</script>

<style scoped>
.storyboard-viewer {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
}

.cards-container {
  width: 100%;
  max-width: 100%;
}

.markdown-container {
  width: 100%;
  max-width: 100%;
}

/* 优化代码块显示 */
.mockup-code {
  border-radius: 0.5rem;
  max-width: 100%;
}

.mockup-code code {
  display: block;
  padding: 1rem;
  font-family: 'Courier New', Courier, monospace;
  word-break: break-word;
  overflow-wrap: break-word;
}

/* 卡片hover效果 */
.card {
  transition: all 0.3s;
}

.card:hover {
  transform: translateY(-0.25rem);
}

/* 折叠面板样式优化 */
.collapse-title {
  min-height: 0;
  padding: 0.5rem 0.75rem;
}

.collapse-content {
  padding: 0 0.75rem 0.5rem 0.75rem;
}

/* 图片预览样式 */
.card img {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.card img:hover {
  transform: scale(1.02);
}

/* 缩略图容器滚动优化 */
.overflow-x-auto {
  scrollbar-width: thin;
  scrollbar-color: rgba(155, 155, 155, 0.5) transparent;
}

.overflow-x-auto::-webkit-scrollbar {
  height: 6px;
}

.overflow-x-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-x-auto::-webkit-scrollbar-thumb {
  background-color: rgba(155, 155, 155, 0.5);
  border-radius: 3px;
}

.overflow-x-auto::-webkit-scrollbar-thumb:hover {
  background-color: rgba(155, 155, 155, 0.7);
}

/* 缩略图选择器动画 */
.flex-shrink-0 {
  transition: all 0.2s ease;
}

.flex-shrink-0:hover {
  transform: translateY(-2px);
}

/* 下拉菜单样式优化 */
.dropdown-content {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.dropdown-content li a {
  font-size: 0.875rem;
  padding: 0.5rem 1rem;
}

.dropdown-content li a:hover {
  background-color: rgba(var(--p), 0.1);
}

/* 编辑模式样式 */
.textarea {
  transition: all 0.2s ease;
}

.textarea:focus {
  border-color: rgba(var(--p), 0.5);
  box-shadow: 0 0 0 3px rgba(var(--p), 0.1);
}

.badge.cursor-pointer:hover {
  transform: scale(1.05);
  transition: transform 0.2s ease;
}

.select-xs {
  min-width: 100px;
}

/* 删除按钮样式 */
.btn-error:hover {
  background-color: rgba(239, 68, 68, 0.1);
  border-color: rgb(239, 68, 68);
  color: rgb(239, 68, 68);
}

.btn-error:hover svg {
  transform: scale(1.1);
  transition: transform 0.2s ease;
}
</style>
