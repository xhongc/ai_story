<template>
  <div class="page-shell project-series-detail">
    <div class="page-header">
      <div class="page-header-main">
        <button class="back-link" @click="$router.push({ name: 'SeriesList' })">← 返回作品列表</button>
        <h1 class="page-title">{{ currentSeries?.name || '作品详情' }}</h1>
        <p class="page-subtitle">{{ currentSeries?.description || '管理作品下的全部分集' }}</p>
      </div>
      <button class="primary-action" @click="goCreateEpisode">
        <span>创建分集</span>
      </button>
    </div>

    <LoadingContainer :loading="loading">
      <div v-if="!loading && episodes.length === 0" class="empty-state">
        <div class="empty-hero">这个作品还没有分集</div>
        <p class="empty-hint">先创建第一集，再进入分集详情继续生成文案、分镜和视频。</p>
        <button class="secondary-action" @click="goCreateEpisode">创建第一集</button>
      </div>

      <div v-else class="card-grid">
        <article
          v-for="episode in episodes"
          :key="episode.id"
          class="data-card"
          role="button"
          tabindex="0"
          @click="goEpisode(episode.id)"
          @keyup.enter="goEpisode(episode.id)"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                {{ episode.display_name || episode.name }}
                <span class="pill">第{{ episode.episode_number || '-' }}集</span>
              </h2>
              <p class="card-desc">{{ episode.description || '暂无分集描述' }}</p>
            </div>
            <span class="status-pill">{{ episode.status_display }}</span>
          </div>

          <div class="card-meta">
            <div class="meta-item">
              <span class="meta-label">阶段进度</span>
              <span class="meta-value">{{ episode.completed_stages_count }}/{{ episode.stages_count }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">所属作品</span>
              <span class="meta-value">{{ currentSeries?.name || '-' }}</span>
            </div>
          </div>

          <div class="card-footer">
            <span class="meta-time">更新于 {{ formatDate(episode.updated_at) }}</span>
            <div class="card-actions">
              <button class="ghost-action" @click.stop="goEpisode(episode.id)">进入分集</button>
            </div>
          </div>
        </article>
      </div>
    </LoadingContainer>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import { formatDate } from '@/utils/helpers';

export default {
  name: 'SeriesDetail',
  components: { LoadingContainer },
  data() {
    return {
      loading: false,
    };
  },
  computed: {
    ...mapState('projects', ['currentSeries']),
    episodes() {
      return this.currentSeries?.episodes || [];
    },
  },
  created() {
    this.fetchData();
  },
  methods: {
    ...mapActions('projects', ['fetchSeriesDetail']),
    formatDate,
    async fetchData() {
      this.loading = true;
      try {
        await this.fetchSeriesDetail(this.$route.params.id);
      } finally {
        this.loading = false;
      }
    },
    goCreateEpisode() {
      this.$router.push({
        name: 'ProjectCreate',
        query: { series_id: this.$route.params.id },
      });
    },
    goEpisode(id) {
      this.$router.push({ name: 'ProjectDetail', params: { id } });
    },
  },
};
</script>

<style scoped>
.page-shell {
  min-height: 100%;
  padding: 2.5rem 3.5rem 3rem;
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

.back-link {
  border: none;
  background: transparent;
  padding: 0;
  text-align: left;
  color: #64748b;
  cursor: pointer;
}

.page-title {
  font-size: 2.2rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}

.layout-shell.theme-dark .page-title {
  color: #e2e8f0;
}

.page-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0;
}

.primary-action {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #ffffff;
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 999px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .primary-action {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.primary-action:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.layout-shell.theme-dark .primary-action:hover {
  border-color: rgba(94, 234, 212, 0.6);
  box-shadow: 0 12px 24px rgba(2, 6, 23, 0.55);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.data-card {
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.7) 0%, rgba(14, 165, 233, 0.7) 100%)
      0 0 / 0 3px no-repeat,
    rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 1.5rem;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.layout-shell.theme-dark .data-card {
  background: linear-gradient(90deg, rgba(94, 234, 212, 0.5) 0%, rgba(56, 189, 248, 0.5) 100%)
      0 0 / 0 3px no-repeat,
    rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.55);
}

.data-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
  border-color: rgba(148, 163, 184, 0.35);
  background-size: 100% 3px, auto;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin: 0;
}

.layout-shell.theme-dark .card-title {
  color: #e2e8f0;
}

.card-desc {
  margin: 0.5rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
  line-height: 1.65;
}

.layout-shell.theme-dark .card-desc {
  color: #94a3b8;
}

.pill,
.status-pill {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
}

.pill {
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
}

.status-pill {
  background: rgba(148, 163, 184, 0.14);
  color: #334155;
}

.layout-shell.theme-dark .pill {
  background: rgba(94, 234, 212, 0.22);
  color: #e2e8f0;
}

.layout-shell.theme-dark .status-pill {
  background: rgba(148, 163, 184, 0.2);
  color: #e2e8f0;
}

.card-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 14px;
  padding: 0.75rem 1rem;
}

.layout-shell.theme-dark .card-meta {
  background: rgba(30, 41, 59, 0.6);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.meta-label {
  font-size: 0.75rem;
  color: #94a3b8;
}

.meta-value {
  font-size: 0.95rem;
  color: #0f172a;
  font-weight: 600;
}

.layout-shell.theme-dark .meta-value {
  color: #e2e8f0;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta-time {
  font-size: 0.8rem;
  color: #94a3b8;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.data-card:hover .card-actions {
  opacity: 1;
}

.ghost-action {
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(15, 23, 42, 0.04);
  color: #0f172a;
  font-size: 0.85rem;
}

.layout-shell.theme-dark .ghost-action {
  background: rgba(148, 163, 184, 0.16);
  color: #e2e8f0;
}

.empty-state {
  text-align: center;
  padding: 4rem 1rem;
}

.empty-hero {
  font-size: 1.3rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .empty-hero {
  color: #e2e8f0;
}

.empty-hint {
  color: #94a3b8;
  margin: 0.6rem 0 1.6rem;
}

.secondary-action {
  padding: 0.75rem 1.75rem;
  border-radius: 999px;
  background: #0f172a;
  color: #ffffff;
  border: none;
}

.layout-shell.theme-dark .secondary-action {
  background: #e2e8f0;
  color: #0f172a;
}

@media (max-width: 768px) {
  .page-shell {
    padding: 2rem 1.5rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .primary-action {
    width: 100%;
  }

  .card-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .card-actions {
    opacity: 1;
  }
}
</style>
