<template>
  <div class="prompt-template-editor">
    <PageCard :title="isEdit ? '编辑提示词模板' : '创建提示词模板'">
      <PromptTemplateForm
        :template-id="templateId"
        :initial-template-set="initialTemplateSet"
        :initial-stage-type="initialStageType"
        submit-text="保存"
        toolbar-hint="维护当前提示词模板的结构、变量与默认模型。"
        @cancel="handleCancel"
        @saved="handleSaved"
      />
    </PageCard>
  </div>
</template>

<script>
import PageCard from '@/components/common/PageCard.vue';
import PromptTemplateForm from '@/components/prompts/PromptTemplateForm.vue';

export default {
  name: 'PromptTemplateEditor',
  components: {
    PageCard,
    PromptTemplateForm,
  },
  computed: {
    isEdit() {
      return !!this.$route.params.id;
    },
    templateId() {
      return this.$route.params.id || null;
    },
    initialTemplateSet() {
      return this.$route.query.template_set || '';
    },
    initialStageType() {
      return this.$route.query.stage_type || '';
    },
  },
  methods: {
    handleSaved(template) {
      const templateSetId = template?.template_set || this.initialTemplateSet;
      if (templateSetId) {
        this.$router.push(`/prompts/sets/${templateSetId}`);
        return;
      }
      this.$router.push('/prompts');
    },
    handleCancel() {
      if (this.initialTemplateSet) {
        this.$router.push(`/prompts/sets/${this.initialTemplateSet}`);
        return;
      }
      this.$router.push('/prompts');
    },
  },
};
</script>

<style scoped>
.prompt-template-editor {
  min-height: 100%;
}
</style>
