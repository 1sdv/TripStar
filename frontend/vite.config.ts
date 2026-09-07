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
        // 使用普通占位符，避免触发 Vite 对 %ENV% 的内置扫描告警。
        name: 'tripstar-inject-amap-security-code',
        transformIndexHtml(html: string) {
          return html.replaceAll('__AMAP_SECURITY_JS_CODE__', amapSecurityJsCode)
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
