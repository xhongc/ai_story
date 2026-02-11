<template>
  <div class="status-badge">
    <div :class="['badge', statusInfo.badgeClass]">
      {{ statusInfo.label }}
    </div>
  </div>
</template>

<script>
import { getProjectStatusTag, getStageStatusTag } from '@/utils/helpers';

export default {
  name: 'StatusBadge',
  props: {
    status: {
      type: String,
      required: true,
    },
    type: {
      type: String,
      default: 'project', // 'project' or 'stage'
    },
  },
  computed: {
    statusInfo() {
      const info = this.type === 'stage'
        ? getStageStatusTag(this.status)
        : getProjectStatusTag(this.status);

      const rawStatus = String(this.status || '').trim();
      const normalizedStatus = rawStatus.toLowerCase();
      const overrideTypes = {
        active: 'success',
        inactive: 'info',
        '激活': 'success',
        '未激活': 'info',
        '停用': 'info',
        '已停用': 'info',
        paused: 'paused',
        '已暂停': 'paused',
        skipped: 'paused',
        '已跳过': 'paused',
      };
      const resolvedType = overrideTypes[normalizedStatus] || info.type;

      // 将 Element UI 的 type 映射到 daisyUI 的 badge 类
      const typeMapping = {
        success: 'badge-success',
        warning: 'badge-warning',
        danger: 'badge-error',
        info: 'badge-info',
        primary: 'badge-primary',
        paused: 'badge-paused',
      };

      return {
        ...info,
        badgeClass: typeMapping[resolvedType] || 'badge-ghost',
      };
    },
  },
};
</script>

<style scoped>
.status-badge {
  display: inline-block;
}

.badge {
  border: 1px solid transparent;
}

.badge-info {
  background: rgba(148, 163, 184, 0.16);
  border-color: rgba(148, 163, 184, 0.35);
  color: #475569;
}

.badge-warning {
  background: rgba(59, 130, 246, 0.16);
  border-color: rgba(59, 130, 246, 0.3);
  color: #1d4ed8;
}

.badge-success {
  background: rgba(16, 185, 129, 0.16);
  border-color: rgba(16, 185, 129, 0.3);
  color: #047857;
}

.badge-error {
  background: rgba(239, 68, 68, 0.16);
  border-color: rgba(239, 68, 68, 0.3);
  color: #b91c1c;
}

.badge-primary {
  background: rgba(20, 184, 166, 0.16);
  border-color: rgba(20, 184, 166, 0.35);
  color: #0f766e;
}

.badge-paused {
  background: rgba(245, 158, 11, 0.18);
  border-color: rgba(245, 158, 11, 0.35);
  color: #b45309;
}
</style>
