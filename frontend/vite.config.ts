import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 以 '' 为前缀加载全部变量，这样 Docker 通过 ENV 传入的值也能读到
  const env = loadEnv(mode, process.cwd(), '')
  const amapSecurityJsCode = env.VITE_AMAP_SECURITY_JS_CODE || ''

  return {
    plugins: [
      vue(),
      {
        // Vite 内置的 %VAR% 替换只在变量已定义时生效，未定义时会把占位符原样留在
        // index.html 里，高德拿到的就是字面量 "%VITE_AMAP_SECURITY_JS_CODE%"。
        // 这里显式替换，未配置时替换为空串。
        name: 'tripstar-inject-amap-security-code',
        transformIndexHtml(html: string) {
          return html.replaceAll('%VITE_AMAP_SECURITY_JS_CODE%', amapSecurityJsCode)
        },
      },
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    build: {
      rollupOptions: {
        output: {
          // 这几个库体积大且只在结果页用到，独立分包便于浏览器单独缓存。
          // 用函数而非对象形式：echarts 是按子路径 (echarts/core 等) 引入的，
          // 对象形式按模块 id 精确匹配会漏掉这些子路径以及它依赖的 zrender。
          manualChunks(id: string) {
            if (!id.includes('node_modules')) return
            if (id.includes('echarts') || id.includes('zrender')) return 'echarts'
            if (id.includes('html2canvas')) return 'html2canvas'
            if (id.includes('swiper')) return 'swiper'
            if (id.includes('amap-jsapi-loader') || id.includes('@googlemaps')) return 'maps'
          },
        },
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true
        }
      }
    }
  }
})
