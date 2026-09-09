<script setup lang="ts">
import { ref } from "vue";

// ref 创建一个响应式数据。修改 message.value 后，模板中的 {{ message }} 会自动
// 更新。这里的状态只用于验证页面交互；真正接入后端后会替换为请求状态。
const message = ref("骨架已准备就绪");

// @click 会在按钮点击时调用这个函数。当前只修改页面提示文字，后续可以在这里
// 接入创建会话的 mutation，并根据请求成功/失败显示不同状态。
function startSession(): void {
  message.value = "会话入口将在下一步接入后端";
}
</script>

<template>
  <!-- main 表示页面的主要内容，section 把欢迎区域作为一个有标题的语义区块。
       页面骨架先提供清晰的入口，后续会扩展为对话工作台。 -->
  <main class="app-shell">
    <section class="welcome-panel" aria-labelledby="app-title">
      <p class="eyebrow">Nutrition Agent</p>
      <h1 id="app-title">营养师智能体</h1>
      <p class="intro">从一餐记录开始，逐步建立可执行的饮食建议。</p>
      <p class="service-status" role="status" aria-live="polite">{{ message }}</p>
      <button type="button" class="primary-action" @click="startSession">
        开始体验
      </button>
    </section>
  </main>
</template>
