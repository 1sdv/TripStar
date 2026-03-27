<template>
  <div id="app">
    <a-config-provider :locale="antdLocale">
    <a-layout style="min-height: 100vh">
      <!-- <a-layout-header v-if="!isLandingRoute" class="app-header">
        <div class="header-inner">
          <div class="header-brand" @click="$router.push('/')">
            <div class="brand-logo">
              <span class="logo-icon"></span>
              <div class="logo-ring"></div>
            </div>
            <div class="brand-text-group">
              <span class="brand-text">{{ t('app.brand') }}</span>
              <span class="brand-sub">{{ t('app.subBrand') }}</span>
            </div>
          </div>
          <div class="header-right">
            <a-select
              v-model:value="locale"
              class="lang-select"
              size="small"
              :aria-label="t('app.language.label')"
            >
              <a-select-option value="zh-CN">{{ t('app.language.zh') }}</a-select-option>
              <a-select-option value="ja-JP">{{ t('app.language.ja') }}</a-select-option>
              <a-select-option value="en-US">{{ t('app.language.en') }}</a-select-option>
            </a-select>
            <div class="header-badge">
              <span class="badge-dot"></span>
              <span>{{ t('app.badge') }}</span>
            </div>
          </div>
        </div>
      </a-layout-header> -->
      <a-layout-content style="padding: 0">
        <router-view />
      </a-layout-content>
      <!-- <a-layout-footer v-if="!isLandingRoute" class="app-footer">
        <div class="footer-inner">
          <div class="footer-left">
            <span class="footer-brand">{{ t('app.footerBrand') }}</span>
            <span class="footer-copy">{{ t('app.footerCopy', { year }) }}</span>
          </div>
          <div class="footer-right">
            <span class="footer-tech">{{ t('app.footerTech') }}</span>
          </div>
        </div>
      </a-layout-footer> -->
    </a-layout>
    </a-config-provider>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import 'dayjs/locale/ja'
import { setAppLocale, type AppLocale } from '@/i18n'
import { getAntdLocale, getDayjsLocaleKey } from '@/i18n/antd-locale'

const { t, locale } = useI18n()
const route = useRoute()
const year = new Date().getFullYear()
const isLandingRoute = computed(() => route.name === 'Landing')

const antdLocale = computed(() => getAntdLocale(locale.value as AppLocale))

watch(
  locale,
  (nextLocale) => {
    const appLocale = nextLocale as AppLocale
    setAppLocale(appLocale)
    dayjs.locale(getDayjsLocaleKey(appLocale))
    document.title = t('app.title')
  },
  { immediate: true }
)
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

* {
  box-sizing: border-box;
}

#app {
  font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-header {
  background: linear-gradient(135deg, #0a0a0f 0%, #15132b 40%, #1a1035 100%) !important;
  padding: 0 48px !important;
  height: 72px !important;
  line-height: 72px !important;
  border-bottom: 1px solid rgba(255, 179, 71, 0.15);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(20px);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  max-width: 1400px;
  margin: 0 auto;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: transform 0.3s ease;
}

.header-brand:hover {
  transform: scale(1.03);
}

.brand-logo {
  position: relative;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon {
  font-size: 28px;
  z-index: 1;
  filter: drop-shadow(0 0 8px rgba(255, 179, 71, 0.5));
}

.logo-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(255, 179, 71, 0.4);
  animation: ringPulse 3s ease-in-out infinite;
}

@keyframes ringPulse {
  0%, 100% { transform: scale(1); opacity: 0.4; }
  50% { transform: scale(1.15); opacity: 0.8; }
}

.brand-text-group {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-text {
  color: #FFD699;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.brand-sub {
  color: rgba(255, 255, 255, 0.35);
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.lang-select {
  width: 120px;
}

.lang-select .ant-select-selector {
  background: rgba(255, 255, 255, 0.06) !important;
  border: 1px solid rgba(255, 179, 71, 0.2) !important;
  border-radius: 20px !important;
  color: #FFD699 !important;
}

.lang-select .ant-select-selection-item {
  color: #FFD699 !important;
  font-size: 12px;
}

.lang-select .ant-select-arrow {
  color: rgba(255, 214, 153, 0.7) !important;
}

.header-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 179, 71, 0.1);
  border: 1px solid rgba(255, 179, 71, 0.2);
  color: #FFD699;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 18px;
  border-radius: 24px;
  letter-spacing: 0.05em;
  line-height: 1.2;
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4ade80;
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.6);
  animation: dotBlink 2s ease-in-out infinite;
}

@keyframes dotBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.app-footer {
  background: linear-gradient(135deg, #0a0a0f 0%, #15132b 40%, #1a1035 100%) !important;
  padding: 24px 48px !important;
  border-top: 1px solid rgba(255, 179, 71, 0.1);
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1400px;
  margin: 0 auto;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.footer-brand {
  color: #FFD699;
  font-size: 15px;
  font-weight: 600;
}

.footer-copy {
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
}

.footer-right {
  display: flex;
  align-items: center;
}

.footer-tech {
  color: rgba(255, 255, 255, 0.25);
  font-size: 12px;
  font-weight: 400;
  letter-spacing: 0.03em;
}
</style>
