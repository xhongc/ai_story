<template>
  <div class="page-shell asset-form-page">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">
          {{ isEdit ? '编辑资产' : '新建资产' }}
        </h1>
        <p class="page-subtitle">
          图片资产支持卡片预览、AI 生图和手动上传
        </p>
      </div>
      <button
        class="secondary-action"
        type="button"
        @click="goBack"
      >
        返回列表
      </button>
    </div>

    <LoadingContainer :loading="pageLoading">
      <form
        class="asset-form-layout"
        @submit.prevent="handleSubmit"
      >
        <section class="content-card form-card hero-card">
          <div class="card-top">
            <div>
              <h2 class="card-title">
                基础信息
              </h2>
              <p class="card-desc">
                统一维护资产键、类型、作用域和描述信息。
              </p>
            </div>
          </div>

          <div class="field-grid two-columns">
            <label class="field-block">
              <span class="field-label">资产键 <span class="text-error">*</span></span>
              <input
                v-model="form.key"
                type="text"
                placeholder="例如: 主角形象"
                class="field-input"
                :class="{ 'has-error': errors.key }"
                :disabled="isEdit"
                @blur="validateKey"
              >
              <span
                v-if="errors.key"
                class="field-error"
              >{{ errors.key }}</span>
              <span
                v-else
                class="field-hint"
              >支持中文、英文和数字，保存时只校验不能为空及是否重名</span>
            </label>

            <label class="field-block">
              <span class="field-label">资产类型 <span class="text-error">*</span></span>
              <select
                v-model="form.variable_type"
                class="field-input"
                @change="handleTypeChange"
              >
                <option value="string">字符串</option>
                <option value="number">数字</option>
                <option value="boolean">布尔值</option>
                <option value="json">JSON对象</option>
                <option value="image">图片</option>
              </select>
            </label>

            <label class="field-block">
              <span class="field-label">作用域 <span class="text-error">*</span></span>
              <select
                v-model="form.scope"
                class="field-input"
                :disabled="!isAdmin && form.scope === 'system'"
              >
                <option value="user">用户级（仅自己可见）</option>
                <option
                  value="system"
                  :disabled="!isAdmin"
                >
                  系统级（所有用户可见，需管理员权限）
                </option>
              </select>
            </label>

            <div class="field-block">
              <span class="field-label">分组</span>
              <div class="inline-field-group">
                <input
                  v-if="showNewGroup"
                  v-model="newGroup"
                  type="text"
                  placeholder="输入新分组名称"
                  class="field-input"
                  @keyup.enter="addNewGroup"
                >
                <select
                  v-else
                  v-model="form.group"
                  class="field-input"
                >
                  <option value="">无分组</option>
                  <option
                    v-for="group in groups"
                    :key="group"
                    :value="group"
                  >
                    {{ group }}
                  </option>
                </select>
                <button
                  type="button"
                  class="mini-action"
                  @click="toggleNewGroup"
                >
                  {{ showNewGroup ? '取消' : '新建' }}
                </button>
              </div>
            </div>
          </div>

          <label class="field-block">
            <span class="field-label">描述</span>
            <textarea
              v-model="form.description"
              class="field-textarea compact"
              placeholder="资产的用途说明..."
            />
          </label>
        </section>

        <section
          v-if="form.variable_type === 'image'"
          class="content-card form-card image-card"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                图片资产
              </h2>
              <p class="card-desc">
                可以直接上传图片，也可以根据提示文本调用文生图生成资产图。
              </p>
            </div>
            <span class="mode-pill">
              {{ imageModeLabel }}
            </span>
          </div>

          <div class="image-card-layout">
            <button
              type="button"
              class="preview-card"
              :class="{ empty: !currentImageUrl }"
              @click="handlePreviewCardClick"
            >
              <img
                v-if="currentImageUrl"
                :src="currentImageUrl"
                :alt="form.key || '图片资产预览'"
                class="preview-card-image"
              >
              <div
                v-else
                class="preview-card-empty"
              >
                <span class="empty-title">等待图片</span>
                <span class="empty-copy">上传本地图片，或使用提示文本生成预览</span>
              </div>
              <span
                v-if="currentImageUrl"
                class="preview-chip"
              >点击查看大图</span>
            </button>

            <div class="image-actions-panel">
              <label class="field-block">
                <span class="field-label">文生图模型</span>
                <select
                  v-model="selectedProviderId"
                  class="field-input"
                >
                  <option value="">
                    自动选择默认模型
                  </option>
                  <option
                    v-for="provider in imageProviders"
                    :key="provider.id"
                    :value="provider.id"
                  >
                    {{ provider.name }} / {{ provider.model_name }}
                  </option>
                </select>
                <span class="field-hint">生图时使用当前选中的文生图提供商。</span>
              </label>

              <label class="field-block stretch">
                <span class="field-label">提示文本</span>
                <textarea
                  v-model="form.value"
                  class="field-textarea"
                  :class="{ 'has-error': errors.value }"
                  placeholder="例如：主体设定、风格、镜头、构图、材质、背景氛围"
                />
                <span class="field-hint">使用 AI 生图时，会直接拿这段文本作为提示词。</span>
              </label>

              <div class="action-row">
                <button
                  type="button"
                  class="primary-action"
                  :disabled="generatingImage"
                  @click="handleGenerateImage"
                >
                  <span
                    v-if="generatingImage"
                    class="loading loading-spinner loading-sm"
                  />
                  {{ generatingImage ? '生成中...' : 'AI 生图' }}
                </button>

                <label class="upload-action">
                  <input
                    ref="fileInput"
                    type="file"
                    accept="image/*"
                    class="hidden-file-input"
                    @change="handleFileChange"
                  >
                  <span>手动上传</span>
                </label>

                <button
                  v-if="currentImageUrl || selectedFile || generatedPreview"
                  type="button"
                  class="ghost-action"
                  @click="clearImage"
                >
                  清除当前图片
                </button>
              </div>

              <div class="card-meta image-meta-grid">
                <div class="meta-item">
                  <span class="meta-label">当前来源</span>
                  <span class="meta-value">{{ imageModeLabel }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">保存方式</span>
                  <span class="meta-value">{{ imageSaveHint }}</span>
                </div>
              </div>

              <span
                v-if="errors.image"
                class="field-error"
              >{{ errors.image }}</span>
            </div>
          </div>
        </section>

        <section
          v-else
          class="content-card form-card"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                资产值
              </h2>
              <p class="card-desc">
                非图片资产使用文本、数字、布尔值或 JSON 内容。
              </p>
            </div>
          </div>

          <label class="field-block">
            <span class="field-label">资产值 <span class="text-error">*</span></span>
            <textarea
              v-if="form.variable_type === 'json'"
              v-model="form.value"
              class="field-textarea"
              :class="{ 'has-error': errors.value }"
              placeholder="例如: {&quot;name&quot;: &quot;test&quot;}"
            />
            <input
              v-else
              v-model="form.value"
              type="text"
              class="field-input"
              :class="{ 'has-error': errors.value }"
              :placeholder="getValuePlaceholder()"
            >
            <span
              v-if="errors.value"
              class="field-error"
            >{{ errors.value }}</span>
          </label>
        </section>

        <section class="content-card form-card footer-card">
          <div class="footer-controls">
            <label class="toggle-line">
              <input
                v-model="form.is_active"
                type="checkbox"
                class="checkbox checkbox-primary"
              >
              <span>激活此资产</span>
            </label>

            <div class="submit-actions">
              <button
                type="button"
                class="ghost-action"
                :disabled="submitting"
                @click="goBack"
              >
                取消
              </button>
              <button
                type="submit"
                class="primary-action"
                :disabled="submitting || !isFormValid"
              >
                <span
                  v-if="submitting"
                  class="loading loading-spinner loading-sm"
                />
                {{ submitting ? '保存中...' : '保存资产' }}
              </button>
            </div>
          </div>
        </section>
      </form>
    </LoadingContainer>

    <div
      v-if="previewImageUrl"
      class="modal modal-open"
      @click="previewImageUrl = null"
    >
      <div
        class="modal-box image-modal-box"
        @click.stop
      >
        <img
          :src="previewImageUrl"
          alt="预览"
          class="preview-modal-image"
        >
        <div class="modal-action">
          <button
            class="ghost-action"
            type="button"
            @click="previewImageUrl = null"
          >
            关闭
          </button>
        </div>
      </div>
      <div
        class="modal-backdrop"
        @click="previewImageUrl = null"
      />
    </div>
  </div>
</template>

<script>
import { globalVariableAPI } from '@/api/prompts';
import LoadingContainer from '@/components/common/LoadingContainer.vue';

export default {
  name: 'AssetForm',
  components: {
    LoadingContainer,
  },
  data() {
    return {
      pageLoading: false,
      form: {
        key: '',
        value: '',
        variable_type: 'image',
        scope: 'user',
        group: '',
        description: '',
        is_active: true,
        image_url: null,
      },
      errors: {},
      submitting: false,
      showNewGroup: false,
      newGroup: '',
      groups: [],
      selectedFile: null,
      imagePreview: null,
      generatedPreview: null,
      generatingImage: false,
      previewImageUrl: null,
      imageProviders: [],
      selectedProviderId: '',
    };
  },
  computed: {
    isEdit() {
      return !!this.$route.params.id;
    },
    assetId() {
      return this.$route.params.id;
    },
    isAdmin() {
      return this.$store.getters['auth/isAdmin'];
    },
    currentImageUrl() {
      if (this.generatedPreview && this.generatedPreview.url) {
        return this.generatedPreview.url;
      }
      if (this.imagePreview) {
        return this.imagePreview;
      }
      return this.form.image_url || '';
    },
    imageModeLabel() {
      if (this.generatedPreview && this.generatedPreview.url) {
        return 'AI 生成预览';
      }
      if (this.selectedFile) {
        return '本地上传图片';
      }
      if (this.form.image_url) {
        return '已有图片资产';
      }
      return '未设置图片';
    },
    imageSaveHint() {
      if (this.generatedPreview && this.generatedPreview.url && !this.selectedFile) {
        return this.isEdit ? '保存时会替换为新生成图片' : '保存时会创建生成图片资产';
      }
      if (this.selectedFile) {
        return '保存时上传本地文件';
      }
      if (this.form.image_url) {
        return '沿用当前图片';
      }
      return '请先上传或生成';
    },
    isFormValid() {
      if (this.form.variable_type === 'image') {
        return this.form.key && (this.selectedFile || this.generatedPreview?.url || this.form.image_url) && !this.errors.key && !this.errors.image;
      }
      return this.form.key && this.form.value && !this.errors.key && !this.errors.value;
    },
  },
  created() {
    this.loadGroups();
    this.loadImageProviders();
    if (this.isEdit) {
      this.loadAsset();
    }
  },
  methods: {
    async loadImageProviders() {
      try {
        const response = await this.$store.dispatch('models/fetchActiveProviders', 'text2image');
        this.imageProviders = response.results || response || [];
        if (!this.selectedProviderId && this.imageProviders.length) {
          this.selectedProviderId = this.imageProviders[0].id;
        }
      } catch (error) {
        console.error('加载文生图模型失败:', error);
      }
    },

    async loadAsset() {
      this.pageLoading = true;
      try {
        const asset = await globalVariableAPI.getDetail(this.assetId);
        this.form = {
          key: asset.key,
          value: asset.value || '',
          variable_type: asset.variable_type,
          scope: asset.scope,
          group: asset.group || '',
          description: asset.description || '',
          is_active: asset.is_active,
          image_url: asset.image_url,
        };
      } catch (error) {
        console.error('加载资产失败:', error);
        this.$message?.error('加载资产失败');
        this.goBack();
      } finally {
        this.pageLoading = false;
      }
    },

    async loadGroups() {
      try {
        const response = await globalVariableAPI.getGroups();
        this.groups = response.groups || [];
      } catch (error) {
        console.error('加载分组失败:', error);
      }
    },

    async validateKey() {
      const normalizedKey = String(this.form.key || '').trim();
      this.form.key = normalizedKey;

      if (!normalizedKey) {
        this.errors.key = '请输入资产键';
        return false;
      }

      if (this.isEdit) {
        this.errors.key = '';
        return true;
      }

      try {
        const response = await globalVariableAPI.validateKey(this.form.key, this.form.scope);
        if (!response.valid) {
          this.errors.key = response.message;
          return false;
        }
        this.errors.key = '';
        return true;
      } catch (error) {
        console.error('验证失败:', error);
        return false;
      }
    },

    validateValue() {
      if (this.form.variable_type === 'image') {
        if (!this.selectedFile && !(this.generatedPreview && this.generatedPreview.url) && !this.form.image_url) {
          this.errors.image = '请上传图片或先生成预览图';
          return false;
        }
        this.errors.image = '';
        this.errors.value = '';
        return true;
      }

      if (!this.form.value) {
        this.errors.value = '请输入资产值';
        return false;
      }

      if (this.form.variable_type === 'number') {
        if (isNaN(this.form.value)) {
          this.errors.value = '请输入有效的数字';
          return false;
        }
      } else if (this.form.variable_type === 'boolean') {
        const validValues = ['true', 'false', '1', '0', 'yes', 'no', 'on', 'off'];
        if (!validValues.includes(String(this.form.value).toLowerCase())) {
          this.errors.value = '布尔值必须是: true/false, 1/0, yes/no, on/off';
          return false;
        }
      } else if (this.form.variable_type === 'json') {
        try {
          JSON.parse(this.form.value);
        } catch {
          this.errors.value = 'JSON格式错误';
          return false;
        }
      }

      this.errors.value = '';
      return true;
    },

    handleTypeChange() {
      this.form.value = '';
      this.errors.value = '';
      this.errors.image = '';
      this.selectedFile = null;
      this.imagePreview = null;
      this.generatedPreview = null;
      if (this.form.variable_type !== 'image') {
        this.previewImageUrl = null;
      }
    },

    handleFileChange(event) {
      const file = event.target.files[0];
      if (!file) return;

      if (!file.type.startsWith('image/')) {
        this.errors.image = '请选择图片文件';
        return;
      }

      if (file.size > 5 * 1024 * 1024) {
        this.errors.image = '图片大小不能超过 5MB';
        return;
      }

      this.selectedFile = file;
      this.generatedPreview = null;
      this.errors.image = '';

      const reader = new FileReader();
      reader.onload = (e) => {
        this.imagePreview = e.target.result;
      };
      reader.readAsDataURL(file);
    },

    clearImage() {
      this.selectedFile = null;
      this.imagePreview = null;
      this.generatedPreview = null;
      this.form.image_url = null;
      this.errors.image = '';
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
    },

    async handleGenerateImage() {
      const prompt = String(this.form.value || '').trim();
      if (!prompt) {
        this.errors.value = '请先填写提示文本';
        this.$message?.warning('请先填写提示文本');
        return;
      }

      this.errors.value = '';
      this.generatingImage = true;
      try {
        const response = await globalVariableAPI.generateImage({
          prompt,
          provider_id: this.selectedProviderId || undefined,
        });
        this.generatedPreview = response.preview || null;
        this.selectedFile = null;
        this.imagePreview = null;
        this.errors.image = '';
        this.$message?.success('图片预览已生成');
      } catch (error) {
        console.error('生成图片失败:', error);
        this.$message?.error(error.response?.data?.error || error.message || '生成图片失败');
      } finally {
        this.generatingImage = false;
      }
    },

    handlePreviewCardClick() {
      if (!this.currentImageUrl) {
        return;
      }
      this.previewImageUrl = this.currentImageUrl;
    },

    toggleNewGroup() {
      this.showNewGroup = !this.showNewGroup;
      if (!this.showNewGroup) {
        this.newGroup = '';
      }
    },

    addNewGroup() {
      if (this.newGroup.trim()) {
        this.form.group = this.newGroup.trim();
        this.showNewGroup = false;
        this.newGroup = '';
      }
    },

    getValuePlaceholder() {
      const placeholders = {
        string: '例如: 我的品牌',
        number: '例如: 100',
        boolean: '例如: true 或 false',
        json: '例如: {"name": "test"}',
      };
      return placeholders[this.form.variable_type] || '';
    },

    goBack() {
      this.$router.push({ name: 'AssetList' });
    },

    async handleSubmit() {
      if (this.showNewGroup && this.newGroup.trim()) {
        this.form.group = this.newGroup.trim();
        this.showNewGroup = false;
        this.newGroup = '';
      }

      const keyValid = await this.validateKey();
      const valueValid = this.validateValue();

      if (!keyValid || !valueValid) {
        return;
      }

      if (this.form.scope === 'system' && !this.isAdmin) {
        return;
      }

      this.submitting = true;

      try {
        if (this.form.variable_type === 'image' && this.generatedPreview && this.generatedPreview.url && !this.selectedFile) {
          await globalVariableAPI.createImageAsset({
            asset_id: this.isEdit ? this.assetId : undefined,
            key: this.form.key,
            prompt: this.form.value || '',
            value: this.form.value || '',
            preview_url: this.generatedPreview.url,
            scope: this.form.scope,
            group: this.form.group,
            description: this.form.description,
            is_active: this.form.is_active,
          });
        } else {
          const formData = new FormData();
          formData.append('key', this.form.key);
          formData.append('variable_type', this.form.variable_type);
          formData.append('scope', this.form.scope);
          formData.append('group', this.form.group);
          formData.append('description', this.form.description);
          formData.append('is_active', this.form.is_active);

          if (this.form.variable_type === 'image') {
            if (this.selectedFile) {
              formData.append('image_file', this.selectedFile);
            }
            formData.append('value', this.form.value || '');
          } else {
            formData.append('value', this.form.value);
          }

          if (this.isEdit) {
            await globalVariableAPI.updateWithFile(this.assetId, formData);
          } else {
            await globalVariableAPI.createWithFile(formData);
          }
        }

        this.$message?.success(this.isEdit ? '更新成功' : '创建成功');
        this.goBack();
      } catch (error) {
        console.error('保存失败:', error);
        const errorMsg = error.response?.data?.detail || error.response?.data?.error || error.response?.data?.key?.[0] || '保存失败';
        this.$message?.error(errorMsg);
      } finally {
        this.submitting = false;
      }
    },
  },
};
</script>

<style scoped>
.page-shell {
  min-height: 100vh;
  padding: 2.5rem 3.5rem 3rem;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.page-header-main {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.page-title {
  margin: 0;
  font-size: 2.2rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: #0f172a;
}

.page-subtitle {
  margin: 0;
  color: #64748b;
  font-size: 0.96rem;
}

.asset-form-layout {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.content-card {
  position: relative;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(14px);
  overflow: hidden;
  transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
}

.content-card::before {
  content: '';
  display: block;
  height: 3px;
  width: 100%;
  background: linear-gradient(90deg, rgba(34, 197, 94, 0.95), rgba(14, 165, 233, 0.92), rgba(56, 189, 248, 0.7));
}

.content-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 28px 48px rgba(15, 23, 42, 0.12);
}

.form-card {
  padding: 1.4rem 1.5rem 1.5rem;
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.2rem;
}

.card-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
}

.card-desc {
  margin: 0.35rem 0 0;
  color: #64748b;
  line-height: 1.6;
  font-size: 0.93rem;
}

.field-grid {
  display: grid;
  gap: 1rem;
}

.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.field-label {
  font-size: 0.92rem;
  font-weight: 600;
  color: #334155;
}

.field-input,
.field-textarea {
  width: 100%;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: rgba(255, 255, 255, 0.94);
  color: #0f172a;
  padding: 0.9rem 1rem;
  font-size: 0.95rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.field-textarea {
  min-height: 128px;
  resize: vertical;
}

.field-textarea.compact {
  min-height: 96px;
}

.field-input:focus,
.field-textarea:focus {
  outline: none;
  border-color: rgba(14, 165, 233, 0.55);
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.12);
}

.field-input.has-error,
.field-textarea.has-error {
  border-color: rgba(239, 68, 68, 0.5);
}

.field-hint,
.field-error {
  font-size: 0.83rem;
  line-height: 1.5;
}

.field-hint {
  color: #64748b;
}

.field-error,
.text-error {
  color: #dc2626;
}

.inline-field-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.inline-field-group .field-input {
  flex: 1;
}

.image-card-layout {
  display: grid;
  grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
  gap: 1.25rem;
  align-items: stretch;
}

.preview-card {
  position: relative;
  min-height: 360px;
  padding: 0;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 22px;
  overflow: hidden;
  background:
    radial-gradient(circle at top right, rgba(34, 211, 238, 0.18), transparent 38%),
    linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(226, 232, 240, 0.88));
  cursor: pointer;
  transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
}

.preview-card:hover {
  transform: translateY(-4px);
  border-color: rgba(14, 165, 233, 0.42);
  box-shadow: 0 24px 40px rgba(14, 165, 233, 0.16);
}

.preview-card.empty {
  cursor: default;
}

.preview-card-image {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 360px;
  object-fit: cover;
}

.preview-card-empty {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 0.75rem;
  min-height: 360px;
  padding: 2rem;
  color: #475569;
  text-align: center;
}

.empty-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: #0f172a;
}

.empty-copy {
  max-width: 240px;
  line-height: 1.7;
}

.preview-chip,
.mode-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 0.38rem 0.82rem;
  font-size: 0.8rem;
  font-weight: 600;
}

.preview-chip {
  position: absolute;
  right: 1rem;
  bottom: 1rem;
  background: rgba(15, 23, 42, 0.72);
  color: #f8fafc;
}

.mode-pill {
  background: rgba(14, 165, 233, 0.12);
  color: #0369a1;
}

.image-actions-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stretch {
  flex: 1;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
  align-items: center;
}

.primary-action,
.secondary-action,
.ghost-action,
.mini-action,
.upload-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-radius: 999px;
  font-size: 0.92rem;
  font-weight: 600;
  transition: all 0.2s ease;
  cursor: pointer;
}

.primary-action,
.secondary-action,
.upload-action {
  padding: 0.78rem 1.3rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #ffffff;
  color: #0f172a;
}

.primary-action:hover,
.secondary-action:hover,
.upload-action:hover {
  transform: translateY(-1px);
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
}

.ghost-action,
.mini-action {
  padding: 0.72rem 1.1rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(248, 250, 252, 0.8);
  color: #334155;
}

.ghost-action:hover,
.mini-action:hover {
  border-color: rgba(14, 165, 233, 0.35);
  color: #0f172a;
}

.hidden-file-input {
  display: none;
}

.image-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.card-meta {
  display: grid;
}

.meta-item {
  padding: 0.95rem 1rem;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.meta-label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.78rem;
  color: #64748b;
}

.meta-value {
  color: #0f172a;
  font-weight: 600;
}

.footer-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.toggle-line {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  color: #334155;
  font-weight: 500;
}

.submit-actions {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.image-modal-box {
  max-width: min(1100px, calc(100vw - 2rem));
}

.preview-modal-image {
  display: block;
  width: 100%;
  max-height: 76vh;
  object-fit: contain;
  border-radius: 18px;
}

.layout-shell.theme-dark .page-title,
.layout-shell.theme-dark .card-title,
.layout-shell.theme-dark .empty-title,
.layout-shell.theme-dark .meta-value,
.layout-shell.theme-dark .field-label,
.layout-shell.theme-dark .primary-action,
.layout-shell.theme-dark .secondary-action,
.layout-shell.theme-dark .upload-action {
  color: #e2e8f0;
}

.layout-shell.theme-dark .page-subtitle,
.layout-shell.theme-dark .card-desc,
.layout-shell.theme-dark .field-hint,
.layout-shell.theme-dark .meta-label,
.layout-shell.theme-dark .empty-copy,
.layout-shell.theme-dark .toggle-line,
.layout-shell.theme-dark .ghost-action,
.layout-shell.theme-dark .mini-action {
  color: #94a3b8;
}

.layout-shell.theme-dark .content-card {
  background: rgba(15, 23, 42, 0.88);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 20px 40px rgba(2, 6, 23, 0.5);
}

.layout-shell.theme-dark .field-input,
.layout-shell.theme-dark .field-textarea,
.layout-shell.theme-dark .meta-item,
.layout-shell.theme-dark .ghost-action,
.layout-shell.theme-dark .mini-action {
  background: rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.2);
  color: #e2e8f0;
}

.layout-shell.theme-dark .primary-action,
.layout-shell.theme-dark .secondary-action,
.layout-shell.theme-dark .upload-action {
  background: rgba(15, 23, 42, 0.94);
  border-color: rgba(148, 163, 184, 0.24);
}

.layout-shell.theme-dark .primary-action:hover,
.layout-shell.theme-dark .secondary-action:hover,
.layout-shell.theme-dark .upload-action:hover {
  border-color: rgba(94, 234, 212, 0.6);
  box-shadow: 0 12px 24px rgba(2, 6, 23, 0.55);
}

.layout-shell.theme-dark .preview-card {
  border-color: rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.18), transparent 38%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.88));
}

.layout-shell.theme-dark .preview-card-empty {
  color: #cbd5e1;
}

@media (max-width: 1080px) {
  .image-card-layout,
  .two-columns,
  .image-meta-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-shell {
    padding: 1.25rem 1rem 2rem;
  }

  .page-header,
  .footer-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .submit-actions,
  .inline-field-group,
  .action-row {
    flex-direction: column;
    align-items: stretch;
  }

  .primary-action,
  .secondary-action,
  .ghost-action,
  .mini-action,
  .upload-action {
    width: 100%;
  }

  .preview-card,
  .preview-card-image,
  .preview-card-empty {
    min-height: 280px;
  }
}
</style>
