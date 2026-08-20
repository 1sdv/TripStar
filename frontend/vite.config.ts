import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 以空前缀加载全部变量，兼容 Docker/CI 直接注入的 VITE_* 环境变量。
  const env = loadEnv(mode, process.cwd(), '')
  const amapSecurityJsCode = env.VITE_AMAP_SECURITY_JS_CODE || ''

  return {
    plugins: [
      vue(),
      {
        // Vite 的 %VAR% 替换在变量未定义时会保留占位符原文。
        // 高德安全密钥未配置时应注入空串，而不是 "%VITE_AMAP_SECURITY_JS_CODE%"。
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
