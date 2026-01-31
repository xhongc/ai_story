<template>
  <div class="asset-form">
    <PageCard :title="isEdit ? '编辑资产' : '新建资产'">
      <template slot="header-right">
        <button class="btn btn-ghost btn-sm" @click="goBack">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          返回列表
        </button>
      </template>

      <LoadingContainer :loading="pageLoading">
        <form @submit.prevent="handleSubmit" class="max-w-2xl">
          <!-- 资产键 -->
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">资产键 <span class="text-error">*</span></span>
            </label>
            <input
              v-model="form.key"
              type="text"
              placeholder="例如: brand_logo"
              class="input input-bordered"
              :class="{ 'input-error': errors.key }"
              :disabled="isEdit"
              @blur="validateKey"
            />
            <label v-if="errors.key" class="label">
              <span class="label-text-alt text-error">{{ errors.key }}</span>
            </label>
            <label v-else class="label">
              <span class="label-text-alt">只能包含字母、数字、下划线，且必须以字母或下划线开头</span>
            </label>
          </div>

          <!-- 资产类型 -->
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">资产类型 <span class="text-error">*</span></span>
            </label>
            <select
              v-model="form.variable_type"
              class="select select-bordered"
              @change="handleTypeChange"
            >
              <option value="string">字符串</option>
              <option value="number">数字</option>
              <option value="boolean">布尔值</option>
              <option value="json">JSON对象</option>
              <option value="image">图片</option>
            </select>
          </div>

          <!-- 图片上传（仅图片类型显示） -->
          <div v-if="form.variable_type === 'image'" class="form-control mb-4">
            <label class="label">
              <span class="label-text">图片文件 <span class="text-error">*</span></span>
            </label>

            <!-- 图片预览 -->
            <div v-if="imagePreview || form.image_url" class="mb-4">
              <img
                :src="imagePreview || form.image_url"
                alt="预览"
                class="max-w-xs max-h-48 object-contain rounded border border-base-300"
              />
            </div>

            <!-- 上传按钮 -->
            <div class="flex items-center gap-4">
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                class="file-input file-input-bordered w-full max-w-xs"
                @change="handleFileChange"
              />
              <button
                v-if="imagePreview || selectedFile"
                type="button"
                class="btn btn-ghost btn-sm text-error"
                @click="clearImage"
              >
                清除
              </button>
            </div>
            <label v-if="errors.image" class="label">
              <span class="label-text-alt text-error">{{ errors.image }}</span>
            </label>
            <label class="label">
              <span class="label-text-alt">支持 JPG、PNG、GIF 格式，最大 5MB</span>
            </label>
          </div>

          <!-- 资产值（非图片类型显示） -->
          <div v-else class="form-control mb-4">
            <label class="label">
              <span class="label-text">资产值 <span class="text-error">*</span></span>
            </label>
            <textarea
              v-if="form.variable_type === 'json'"
              v-model="form.value"
              placeholder='例如: {"name": "test"}'
              class="textarea textarea-bordered h-32"
              :class="{ 'textarea-error': errors.value }"
            ></textarea>
            <input
              v-else
              v-model="form.value"
              type="text"
              :placeholder="getValuePlaceholder()"
              class="input input-bordered"
              :class="{ 'input-error': errors.value }"
            />
            <label v-if="errors.value" class="label">
              <span class="label-text-alt text-error">{{ errors.value }}</span>
            </label>
          </div>

          <!-- 作用域 -->
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">作用域 <span class="text-error">*</span></span>
            </label>
            <select
              v-model="form.scope"
              class="select select-bordered"
              :disabled="!isAdmin && form.scope === 'system'"
            >
              <option value="user">用户级（仅自己可见）</option>
              <option value="system" :disabled="!isAdmin">系统级（所有用户可见，需管理员权限）</option>
            </select>
          </div>

          <!-- 分组 -->
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">分组</span>
            </label>
            <div class="flex gap-2">
              <input
                v-if="showNewGroup"
                v-model="newGroup"
                type="text"
                placeholder="输入新分组名称"
                class="input input-bordered flex-1"
                @keyup.enter="addNewGroup"
              />
              <select
                v-else
                v-model="form.group"
                class="select select-bordered flex-1"
              >
                <option value="">无分组</option>
                <option v-for="group in groups" :key="group" :value="group">
                  {{ group }}
                </option>
              </select>
              <button
                type="button"
                class="btn btn-outline"
                @click="toggleNewGroup"
              >
                {{ showNewGroup ? '取消' : '新建' }}
              </button>
            </div>
          </div>

          <!-- 描述 -->
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">描述</span>
            </label>
            <textarea
              v-model="form.description"
              placeholder="资产的用途说明..."
              class="textarea textarea-bordered h-20"
            ></textarea>
          </div>

          <!-- 是否激活 -->
          <div class="form-control mb-6">
            <label class="label cursor-pointer justify-start gap-4">
              <input
                v-model="form.is_active"
                type="checkbox"
                class="checkbox checkbox-primary"
              />
              <span class="label-text">激活此资产</span>
            </label>
          </div>

          <!-- 按钮 -->
          <div class="flex gap-4">
            <button
              type="button"
              class="btn btn-ghost"
              @click="goBack"
              :disabled="submitting"
            >
              取消
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="submitting || !isFormValid"
            >
              <span v-if="submitting" class="loading loading-spinner loading-sm"></span>
              {{ submitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </LoadingContainer>
    </PageCard>
  </div>
</template>

<script>
import { globalVariableAPI } from '@/api/prompts';
import PageCard from '@/components/common/PageCard.vue';
import LoadingContainer from '@/components/common/LoadingContainer.vue';

export default {
  name: 'AssetForm',
  components: {
    PageCard,
    LoadingContainer,
  },
  data() {
    return {
      pageLoading: false,
      form: {
        key: '',
        value: '',
        variable_type: 'string',
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
    isFormValid() {
      if (this.form.variable_type === 'image') {
        // 图片类型：需要有图片文件或已有图片URL
        return this.form.key && (this.selectedFile || this.form.image_url) && !this.errors.key && !this.errors.image;
      }
      return this.form.key && this.form.value && !this.errors.key && !this.errors.value;
    },
  },
  created() {
    this.loadGroups();
    if (this.isEdit) {
      this.loadAsset();
    }
  },
  methods: {
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
      if (!this.form.key) {
        this.errors.key = '请输入资产键';
        return false;
      }

      const keyPattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
      if (!keyPattern.test(this.form.key)) {
        this.errors.key = '资产键只能包含字母、数字、下划线，且必须以字母或下划线开头';
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
        if (!this.selectedFile && !this.form.image_url) {
          this.errors.image = '请上传图片';
          return false;
        }
        this.errors.image = '';
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
        if (!validValues.includes(this.form.value.toLowerCase())) {
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
    },

    handleFileChange(event) {
      const file = event.target.files[0];
      if (!file) return;

      // 验证文件类型
      if (!file.type.startsWith('image/')) {
        this.errors.image = '请选择图片文件';
        return;
      }

      // 验证文件大小（5MB）
      if (file.size > 5 * 1024 * 1024) {
        this.errors.image = '图片大小不能超过 5MB';
        return;
      }

      this.selectedFile = file;
      this.errors.image = '';

      // 创建预览
      const reader = new FileReader();
      reader.onload = (e) => {
        this.imagePreview = e.target.result;
      };
      reader.readAsDataURL(file);
    },

    clearImage() {
      this.selectedFile = null;
      this.imagePreview = null;
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
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
        // 使用 FormData 支持文件上传
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
          formData.append('value', '');
        } else {
          formData.append('value', this.form.value);
        }

        if (this.isEdit) {
          await globalVariableAPI.updateWithFile(this.assetId, formData);
        } else {
          await globalVariableAPI.createWithFile(formData);
        }

        this.$message?.success(this.isEdit ? '更新成功' : '创建成功');
        this.goBack();
      } catch (error) {
        console.error('保存失败:', error);
        const errorMsg = error.response?.data?.detail || error.response?.data?.key?.[0] || '保存失败';
        this.$message?.error(errorMsg);
      } finally {
        this.submitting = false;
      }
    },
  },
};
</script>

<style scoped>
.asset-form {
  padding: 1.5rem;
}

code {
  font-family: 'Courier New', monospace;
}
</style>
