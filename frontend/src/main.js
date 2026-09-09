import { VueQueryPlugin, QueryClient } from "@tanstack/vue-query";
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";
// QueryClient 是 Vue Query 的核心对象。它统一管理来自后端的数据缓存、加载中、
// 失败和重新请求状态，避免每个页面都手写一套重复的请求状态逻辑。
const queryClient = new QueryClient();
// createApp 创建 Vue 根应用；use() 注册插件；mount() 把应用挂到 index.html
// 中的 #app 元素上。Pinia 管理前端本地状态，Vue Query 管理后端状态，两者职责分开。
createApp(App)
    .use(createPinia())
    .use(VueQueryPlugin, { queryClient })
    .mount("#app");
