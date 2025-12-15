<template>
  <div class="modal modal-open">
    <div class="modal-box max-w-2xl">
      <h3 class="font-bold text-lg mb-4">
        {{ isEdit ? '编辑变量' : '创建变量' }}
      </h3>

      <form @submit.prevent="handleSubmit">
        <!-- 变量键 -->
        <div class="form-control mb-4">
          <label class="label">
            <span class="label-text">变量键 <span class="text-error">*</span></span>
          </label>
          <input
            v-model="form.key"
            type="text"
            placeholder="例如: brand_name"
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

        <!-- 变量值 -->
        <div class="form-control mb-4">
          <label class="label">
            <span class="label-text">变量值 <span class="text-error">*</span></span>
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

        <!-- 变量类型 -->
        <div class="form-control mb-4">
          <label class="label">
            <span class="label-text">变量类型 <span class="text-error">*</span></span>
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
          </select>
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
            placeholder="变量的用途说明..."
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
            <span class="label-text">激活此变量</span>
          </label>
        </div>

        <!-- 按钮 -->
        <div class="modal-action">
          <button
            type="button"
            class="btn btn-ghost"
            @click="$emit('close')"
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
    </div>
    <div class="modal-backdrop" @click="$emit('close')"></div>
  </div>
</template>

<script>
import { globalVariableAPI } from '@/api/prompts';

export default {
  name: 'VariableFormModal',
  props: {
    variable: {
      type: Object,
      default: null,
    },
    groups: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      form: {
        key: '',
        value: '',
        variable_type: 'string',
        scope: 'user',
        group: '',
        description: '',
        is_active: true,
      },
      errors: {},
      submitting: false,
      showNewGroup: false,
      newGroup: '',
    };
  },
  computed: {
    isEdit() {
      return !!this.variable;
    },
    isAdmin() {
      return this.$store.getters['auth/isAdmin'];
    },
    isFormValid() {
      return this.form.key && this.form.value && !this.errors.key && !this.errors.value;
    },
  },
  created() {
    if (this.variable) {
      this.form = {
        key: this.variable.key,
        value: this.variable.value,
        variable_type: this.variable.variable_type,
        scope: this.variable.scope,
        group: this.variable.group || '',
        description: this.variable.description || '',
        is_active: this.variable.is_active,
      };
    }
  },
  methods: {
    async validateKey() {
      if (!this.form.key) {
        this.errors.key = '请输入变量键';
        return false;
      }

      // 验证格式
      const keyPattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
      if (!keyPattern.test(this.form.key)) {
        this.errors.key = '变量键只能包含字母、数字、下划线，且必须以字母或下划线开头';
        return false;
      }

      // 如果是编辑模式，不需要验证唯一性
      if (this.isEdit) {
        this.errors.key = '';
        return true;
      }

      // 验证唯一性
      try {
        const response = await globalVariableAPI.validateKey(this.form.key, this.form.scope);
        if (!response.valid) {
          this.errors.key = response.data.message;
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
      if (!this.form.value) {
        this.errors.value = '请输入变量值';
        return false;
      }

      // 根据类型验证值
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
      // 类型改变时清空值和错误
      this.form.value = '';
      this.errors.value = '';
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

    async handleSubmit() {
      // 验证表单
      const keyValid = await this.validateKey();
      const valueValid = this.validateValue();

      if (!keyValid || !valueValid) {
        return;
      }

      // 检查权限
      if (this.form.scope === 'system' && !this.isAdmin) {
        return;
      }

      this.submitting = true;

      try {
        if (this.isEdit) {
          await globalVariableAPI.update(this.variable.id, this.form);
        } else {
          await globalVariableAPI.create(this.form);
        }
        this.$emit('success');
      } catch (error) {
        console.error('保存失败:', error);
        const errorMsg = error.response?.data?.detail || error.response?.data?.key?.[0] || '保存失败';
      } finally {
        this.submitting = false;
      }
    },
  },
};
</script>

<style scoped>
.modal-backdrop {
  background-color: rgba(0, 0, 0, 0.5);
}
</style>
