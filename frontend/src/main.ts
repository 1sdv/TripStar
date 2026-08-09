import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './styles/global.css'
import App from './App.vue'
import { i18n } from './i18n'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Landing',
      // 懒加载：结果页会带上 echarts / html2canvas / swiper / 两个地图 SDK，
      // 只看首页的访客不应该为这些资源付出首屏时间。
      component: () => import('./views/Landing.vue')
    },
    {
      path: '/result',
      name: 'Result',
      component: () => import('./views/Result.vue')
    }
  ]
})

const app = createApp(App)

app.use(router)
app.use(Antd)
app.use(i18n)

app.mount('#app')

