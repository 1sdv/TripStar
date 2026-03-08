<template>
  <div class="landing-page">
    <div class="lower-shade" :style="lowerShadeStyle"></div>
    <nav class="navbar navbar-toggleable-md fixed-top navbar-transparent landing-navbar" :style="navbarStyle">
      <div class="container">
        <div class="navbar-translate">
          <button
            class="navbar-toggler navbar-toggler-right navbar-burger landing-burger"
            type="button"
            aria-label="Toggle navigation"
          >
            <span class="navbar-toggler-bar"></span>
            <span class="navbar-toggler-bar"></span>
            <span class="navbar-toggler-bar"></span>
          </button>
          <button class="navbar-brand landing-brand" type="button" @click="scrollToTop">TripStar</button>
        </div>
        <div class="navbar-collapse landing-navbar-collapse" id="navbarToggler">
          <ul class="navbar-nav ml-auto landing-nav">
            <li class="nav-item">
                <a class="nav-link" rel="tooltip" title="Star on GitHub" data-placement="bottom" href="https://github.com/1sdv/TripStar" target="_blank" style="display:inline-flex;align-items:center;gap:6px;">
                    <svg height="18" width="18" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                    </svg>
                </a>
            </li>
            <li class="nav-item">
              <!-- <button class="nav-link landing-nav-btn fog-toggle" type="button" :aria-pressed="fogEnabled" @click="toggleFog">
                {{ fogEnabled ? t('home.nav.fogOn') : t('home.nav.fogOff') }}
              </button> -->
            </li>
            <li class="nav-item landing-lang-item">
              <a-select v-model:value="locale" class="lang-select-nav" size="small" :aria-label="t('app.language.label')">
                <a-select-option value="zh-CN">{{ t('app.language.zh') }}</a-select-option>
                <a-select-option value="ja-JP">{{ t('app.language.ja') }}</a-select-option>
                <a-select-option value="en-US">{{ t('app.language.en') }}</a-select-option>
              </a-select>
            </li>
            <li class="nav-item">
              <button type="button" class="btn btn-danger btn-round landing-cta" @click="scrollToForm">
                {{ t('home.nav.cta') }}
              </button>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <div class="wrapper">
      <div class="page-header section-dark landing-header" :style="pageHeaderStyle">
        <div class="filter"></div>
        <div class="content-center" :style="heroContentStyle">
          <div class="container">
            <!-- <p class="landing-hero-badge text-center">{{ t('home.heroBadge') }}</p> -->
            <div class="title-brand">
              <h1 class="presentation-title">
                TRIPSTAR
              </h1>
            </div>
            <h2 class="presentation-subtitle text-center">{{ t('home.titleLine') }}</h2>
          </div>
        </div>
        <div class="moving-clouds" :style="movingCloudsStyle"></div>
        <div class="fog-low" :style="fogLowStyle">
          <img src="https://demos.creative-tim.com/paper-kit-2/assets/img/clouds.png" alt="fog" />
        </div>
        <div class="fog-low right" :style="fogLowRightStyle">
          <img src="https://demos.creative-tim.com/paper-kit-2/assets/img/clouds.png" alt="fog" />
        </div>
        <div class="hero-bottom-shade" :style="heroBottomShadeStyle"></div>
      </div>
    </div>

    <section ref="formRef" class="form-section">
      <div class="form-panel" :style="formRevealStyle">
        <a-form :model="formData" layout="vertical" @finish="handleSubmit">
          <div class="step">
            <div class="step-head">
              <span>01</span>
              <h3>{{ t('home.step1') }}</h3>
            </div>
            <div class="grid grid4">
              <a-form-item name="city" :rules="formRules.city">
                <template #label>
                  <span class="field-label">{{ t('home.cityLabel') }}</span>
                </template>
                <a-input
                  v-model:value="formData.city"
                  :placeholder="t('home.cityPlaceholder')"
                  size="large"
                  class="field-input"
                />
              </a-form-item>

              <a-form-item name="start_date" :rules="formRules.startDate">
                <template #label>
                  <span class="field-label">{{ t('home.startDateLabel') }}</span>
                </template>
                <a-date-picker
                  v-model:value="formData.start_date"
                  style="width: 100%"
                  size="large"
                  class="field-input"
                  :placeholder="t('home.startDatePlaceholder')"
                />
              </a-form-item>

              <a-form-item name="end_date" :rules="formRules.endDate">
                <template #label>
                  <span class="field-label">{{ t('home.endDateLabel') }}</span>
                </template>
                <a-date-picker
                  v-model:value="formData.end_date"
                  style="width: 100%"
                  size="large"
                  class="field-input"
                  :placeholder="t('home.endDatePlaceholder')"
                />
              </a-form-item>

              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('home.travelDaysLabel') }}</span>
                </template>
                <div class="days-chip">
                  <span class="days-number">{{ formData.travel_days }}</span>
                  <span class="days-unit">{{ t('home.travelDaysUnit') }}</span>
                </div>
              </a-form-item>
            </div>
          </div>

          <div class="step">
            <div class="step-head">
              <span>02</span>
              <h3>{{ t('home.step2') }}</h3>
            </div>
            <div class="grid grid2">
              <a-form-item name="transportation">
                <template #label>
                  <span class="field-label">{{ t('home.transportationLabel') }}</span>
                </template>
                <a-select v-model:value="formData.transportation" size="large" class="field-select">
                  <a-select-option value="公共交通">{{ t('home.transportation.public') }}</a-select-option>
                  <a-select-option value="自驾">{{ t('home.transportation.drive') }}</a-select-option>
                  <a-select-option value="步行">{{ t('home.transportation.walk') }}</a-select-option>
                  <a-select-option value="混合">{{ t('home.transportation.mixed') }}</a-select-option>
                </a-select>
              </a-form-item>

              <a-form-item name="accommodation">
                <template #label>
                  <span class="field-label">{{ t('home.accommodationLabel') }}</span>
                </template>
                <a-select v-model:value="formData.accommodation" size="large" class="field-select">
                  <a-select-option value="经济型酒店">{{ t('home.accommodation.budget') }}</a-select-option>
                  <a-select-option value="舒适型酒店">{{ t('home.accommodation.comfort') }}</a-select-option>
                  <a-select-option value="豪华酒店">{{ t('home.accommodation.luxury') }}</a-select-option>
                  <a-select-option value="民宿">{{ t('home.accommodation.homestay') }}</a-select-option>
                </a-select>
              </a-form-item>
            </div>

            <a-form-item name="preferences">
              <template #label>
                <span class="field-label">{{ t('home.interestsLabel') }}</span>
              </template>
              <div class="interest-grid">
                <a-checkbox-group v-model:value="formData.preferences" class="interest-group">
                  <label
                    v-for="item in interestOptions"
                    :key="item.value"
                    class="interest-pill"
                    :class="{ active: formData.preferences.includes(item.value) }"
                    @click.prevent="togglePreference(item.value)"
                  >
                    {{ t(item.labelKey) }}
                  </label>
                </a-checkbox-group>
              </div>
            </a-form-item>
          </div>

          <div class="step">
            <div class="step-head">
              <span>03</span>
              <h3>{{ t('home.step3') }}</h3>
            </div>
            <a-form-item name="free_text_input">
              <div class="field-textarea">
                <a-textarea
                  v-model:value="formData.free_text_input"
                  :placeholder="t('home.specialNeedsPlaceholder')"
                  :rows="4"
                  size="large"
                  class="special-textarea"
                />
              </div>
            </a-form-item>
          </div>

          <a-form-item>
            <button type="submit" class="btn btn-danger btn-round submit-btn" :class="{ loading }" :disabled="loading">
              <span v-if="!loading">{{ t('home.submit') }}</span>
              <span v-else class="loading-row">
                <i class="spinner"></i>
                {{ t('home.submitting') }}
              </span>
            </button>
          </a-form-item>

          <div v-if="loading" class="progress">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${loadingProgress}%` }"></div>
            </div>
            <p>{{ loadingStatus }}</p>
          </div>
        </a-form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { generateTripPlan } from '@/services/api'
import type { TripFormData } from '@/types'
import type { Dayjs } from 'dayjs'

type LandingFormData = Omit<TripFormData, 'start_date' | 'end_date'> & {
  start_date: Dayjs | null
  end_date: Dayjs | null
}

const router = useRouter()
const { t, locale } = useI18n()

const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')
const scrollY = ref(0)
const formRef = ref<HTMLElement | null>(null)
const fogEnabled = ref(true)

const interestOptions = [
  { value: '历史文化', labelKey: 'home.interests.history' },
  { value: '自然风光', labelKey: 'home.interests.nature' },
  { value: '美食', labelKey: 'home.interests.food' },
  { value: '购物', labelKey: 'home.interests.shopping' },
  { value: '艺术', labelKey: 'home.interests.art' },
  { value: '休闲', labelKey: 'home.interests.leisure' },
]

const formRules = computed(() => ({
  city: [{ required: true, message: t('home.cityRequired') }],
  startDate: [{ required: true, message: t('home.startDateRequired') }],
  endDate: [{ required: true, message: t('home.endDateRequired') }],
}))

const formData = reactive<LandingFormData>({
  city: '',
  start_date: null,
  end_date: null,
  travel_days: 1,
  transportation: '公共交通',
  accommodation: '经济型酒店',
  preferences: [],
  free_text_input: '',
})

const heroProgress = computed(() => Math.min(scrollY.value / 320, 1))
const toneProgress = computed(() => Math.min(Math.max((scrollY.value - 20) / 360, 0), 1))
const pageHeaderStyle = computed(() => ({
  backgroundImage: "url('http://demos.creative-tim.com/paper-kit-2/assets/img/antoine-barres.jpg')",
  backgroundPosition: `center ${Math.max(-scrollY.value * 0.08, -120)}px`,
  backgroundSize: 'cover',
  backgroundRepeat: 'no-repeat',
}))
const navbarStyle = computed(() => ({
  background: 'transparent',
  backgroundColor: 'transparent',
  borderBottomColor: 'transparent',
  boxShadow: 'none',
  backdropFilter: 'none',
}))
const movingCloudsStyle = computed(() => ({
  backgroundImage: "url('https://demos.creative-tim.com/paper-kit-2/assets/img/clouds.png')",
  opacity: fogEnabled.value ? '0.55' : '0',
}))
const fogLowStyle = computed(() => ({
  opacity: fogEnabled.value ? '0.82' : '0',
}))
const fogLowRightStyle = computed(() => ({
  opacity: fogEnabled.value ? '0.72' : '0',
}))
const heroContentStyle = computed(() => ({
  opacity: `${1 - heroProgress.value * 0.95}`,
  transform: `translate3d(0, ${-heroProgress.value * 46}px, 0)`,
}))
const heroBottomShadeStyle = computed(() => ({
  opacity: `${(0.48 + toneProgress.value * 0.44) * (fogEnabled.value ? 1 : 0)}`,
}))
const lowerShadeStyle = computed(() => ({
  opacity: `${(0.34 + toneProgress.value * 0.52) * (fogEnabled.value ? 1 : 0)}`,
}))
const formRevealStyle = computed(() => {
  const progress = Math.min(Math.max((scrollY.value - 80) / 340, 0), 1)
  return {
    opacity: `${0.2 + progress * 0.8}`,
    transform: `translate3d(0, ${(1 - progress) * 56}px, 0)`,
  }
})

const togglePreference = (value: string) => {
  const index = formData.preferences.indexOf(value)
  if (index === -1) formData.preferences.push(value)
  else formData.preferences.splice(index, 1)
}

const onScroll = () => {
  scrollY.value = window.scrollY || 0
}
const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })
const scrollToForm = () => formRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
const toggleFog = () => {
  fogEnabled.value = !fogEnabled.value
}

onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})
onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})

watch([() => formData.start_date, () => formData.end_date], ([start, end]) => {
  if (start && end) {
    const days = end.diff(start, 'day') + 1
    if (days > 0 && days <= 30) formData.travel_days = days
    else if (days > 30) {
      message.warning(t('home.messages.travelDaysTooLong'))
      formData.end_date = null
    } else {
      message.warning(t('home.messages.endDateEarlier'))
      formData.end_date = null
    }
  }
})

const handleSubmit = async () => {
  if (!formData.start_date || !formData.end_date) {
    message.error(t('home.messages.selectDate'))
    return
  }

  loading.value = true
  loadingProgress.value = 0
  loadingStatus.value = t('home.loading.initializing')

  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
      if (loadingProgress.value <= 30) loadingStatus.value = t('home.loading.searchingAttractions')
      else if (loadingProgress.value <= 50) loadingStatus.value = t('home.loading.queryingWeather')
      else if (loadingProgress.value <= 70) loadingStatus.value = t('home.loading.recommendingHotels')
      else loadingStatus.value = t('home.loading.generatingPlan')
    }
  }, 500)

  try {
    const requestData: TripFormData = {
      city: formData.city,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: formData.end_date.format('YYYY-MM-DD'),
      travel_days: formData.travel_days,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      free_text_input: formData.free_text_input,
    }

    const response = await generateTripPlan(requestData)
    clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = t('home.loading.done')

    if (response.success && response.data) {
      sessionStorage.setItem('tripPlan', JSON.stringify(response.data))
      if (response.graph_data) sessionStorage.setItem('graphData', JSON.stringify(response.graph_data))
      message.success(t('home.messages.generateSuccess'))
      setTimeout(() => router.push('/result'), 500)
    } else {
      message.error(response.message || t('home.messages.generateFailed'))
    }
  } catch (error: any) {
    clearInterval(progressInterval)
    message.error(error.message || t('home.messages.generateRetry'))
  } finally {
    setTimeout(() => {
      loading.value = false
      loadingProgress.value = 0
      loadingStatus.value = ''
    }, 1000)
  }
}
</script>

<style scoped>
.landing-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #0d171d 0%, #142430 58%, #0f1a22 100%);
  color: #ecf3fa;
  position: relative;
  isolation: isolate;
}

.lower-shade {
  position: fixed;
  inset: 0% 0 -1px 0;
  z-index: 0;
  pointer-events: none;
  background: rgba(6, 14, 20, 0.7);
  transition: opacity 0.18s linear;
}

.lower-shade::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -28px;
  height: 28px;
  background: linear-gradient(to bottom, rgba(6, 14, 20, 0), rgba(6, 14, 20, 0.92));
}

.landing-navbar {
  /* Bootstrap fixed-top 类在 global.css 中不存在，手动强制 fixed 定位 */
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  width: 100% !important;
  z-index: 1030 !important;
  min-height: 70px;
  padding: 0 !important;
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
  border: none !important;
  border-bottom: 1px solid transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  transition: background 0.3s;
}

.landing-navbar:not(.navbar-transparent) {
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  border-color: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}

.landing-navbar.navbar-transparent {
  padding-top: 0 !important;
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
}

/* 确保 Ant Design Layout 的 header 样式不干扰 landing 导航栏 */
.landing-page .landing-navbar *,
.landing-page .landing-navbar::before,
.landing-page .landing-navbar::after {
  box-sizing: border-box;
}

.landing-navbar .container {
  /* max-width: 1160px;
  width: min(100%, 1160px); */
  min-height: 70px;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  padding-left: 20px;
  padding-right: 20px;
}

.landing-navbar .navbar-translate {
  display: flex !important;
  align-items: center !important;
  min-height: 70px;
  flex: 0 0 auto;
}

.landing-navbar .navbar-brand {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
}

.landing-burger {
  display: none !important;
}

.landing-brand {
  background: transparent !important;
  border: 0;
  color: #f4f8fc !important;
  font-weight: 700 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase;
  font-size: 13px !important;
  cursor: pointer;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.landing-navbar-collapse {
  display: flex !important;
  justify-content: flex-end;
  align-items: center;
  flex: 1;
  position: static !important;
  transform: none !important;
  width: auto !important;
  height: auto !important;
  background: transparent !important;
  border: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
}

.landing-navbar-collapse::before,
.landing-navbar-collapse::after {
  display: none !important;
  content: none !important;
  background: transparent !important;
}

.landing-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 0 auto !important;
  padding: 0;
  list-style: none;
}

.landing-nav .nav-item {
  margin: 0;
  padding: 0;
  display: inline-flex;
  align-items: center;
}

.landing-nav .nav-item .nav-link {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
  opacity: 1 !important;
}

.landing-nav-btn {
  border: 1px solid rgba(236, 243, 250, 0.24);
  background: rgba(12, 23, 32, 0.56);
  color: #ecf3fa;
  border-radius: 999px;
  padding: 0 12px;
  min-height: 34px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  text-transform: uppercase;
}

.fog-toggle[aria-pressed='true'] {
  border-color: rgba(215, 110, 66, 0.55);
  background: rgba(215, 110, 66, 0.2);
  color: #ffe3d6;
}

.landing-lang-item {
  display: flex;
  align-items: center;
}

.lang-select-nav {
  width: 110px;
}

.lang-select-nav :deep(.ant-select-selector) {
  height: 34px !important;
  padding: 0 12px !important;
  border: 1px solid rgba(236, 243, 250, 0.24) !important;
  background: rgba(12, 23, 32, 0.56) !important;
  border-radius: 999px !important;
  display: flex !important;
  align-items: center !important;
}

.lang-select-nav :deep(.ant-select-selection-item) {
  line-height: 32px !important;
  font-size: 12px !important;
}

.lang-select-nav :deep(.ant-select-selection-item),
.lang-select-nav :deep(.ant-select-arrow) {
  color: #ecf3fa !important;
}

.landing-cta {
  min-height: 32px;
  padding: 0 14px !important;
  font-size: 12px !important;
  border: none !important;
  letter-spacing: 0.06em;
  display: inline-flex !important;
  align-items: center;
  justify-content: center;
  margin: 0 !important;
}

.landing-navbar .btn {
  margin: 0 !important;
}

.landing-header {
  /* 确保 hero 区域占满全屏高度，背景图不重复 */
  height: 100vh;
  min-height: 100vh;
  position: relative;
  display: block;
  background-size: cover !important;
  background-repeat: no-repeat !important;
  background-position: center center !important;
  overflow: hidden;
  z-index: 1;
}

.landing-header .content-center {
  margin-top: 0 !important;
  height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 内容垂直居中，确保在 .filter::after 霁罩和 hero-bottom-shade 之上 */
  position: relative;
  z-index: 3;
}

.landing-header .content-center .container {
  transform: translate3d(0, 45px, 0);
}

/* moving-clouds: 依赖 global.css 的定位 (bottom:0, width:250em, cloudLoop 80s) */
/* .landing-header .moving-clouds {
  transition: opacity 0.2s ease;
  pointer-events: none;
  z-index: 2;
} */

/* fog-low: 依赖 global.css 的定位 (margin-left:-35%, width:110%, bottom:0) */
.fog-low {
  pointer-events: none;
  z-index: 2;
  transition: opacity 0.2s ease;
  /* margin-bottom: -35px; */
}

/* fog-low.right: 依赖 global.css 的 margin-left:30%; opacity:1 */

.landing-hero-badge {
  margin: 0 0 18px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(236, 243, 250, 0.78);
}

.landing-header .presentation-title {
  font-size: clamp(44px, 7vw, 90px);
  font-weight: 800;
}

.landing-header .presentation-subtitle {
  max-width: 620px;
  /* margin: 22px auto 0; */
  color: rgba(224, 233, 242, 0.78);
  font-size: clamp(15px, 1.8vw, 19px);
  line-height: 1.75;
  /* font-weight: 500; */
  justify-self: center;
}

.hero-bottom-shade {
  position: absolute;
  inset: auto 0 0 0;
  height: 56%;
  z-index: 1;
  pointer-events: none;
  background: linear-gradient(
    to top,
    rgba(6, 14, 20, 0.92) 0%,
    rgba(6, 14, 20, 0.66) 46%,
    rgba(6, 14, 20, 0) 100%
  );
  transition: opacity 0.18s linear;
}


.form-section {
  margin-top: -112px;
  padding: 0 20px 86px;
  position: relative;
  z-index: 3;
}

.form-panel {
  max-width: 1040px;
  margin: 0 auto;
  border: 1px solid rgba(236, 243, 250, 0.2);
  border-radius: 22px;
  background: rgba(12, 23, 32, 0.56);
  backdrop-filter: blur(18px);
  box-shadow: 0 24px 80px rgba(4, 11, 18, 0.52);
  padding: 32px;
  transition: 0.25s;
}

.step {
  margin-bottom: 30px;
}

.step-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.step-head span {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(215, 110, 66, 0.2);
  border: 1px solid rgba(215, 110, 66, 0.4);
  color: rgba(253, 225, 211, 0.95);
  font-size: 13px;
  font-weight: 700;
}

.step-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: rgba(240, 246, 252, 0.94);
}

.grid {
  display: grid;
  gap: 18px;
}

.grid4 {
  grid-template-columns: 1.5fr 1fr 1fr 0.8fr;
}

.grid2 {
  grid-template-columns: 1fr 1fr;
}

.field-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(228, 236, 245, 0.72);
}

.field-input.ant-input,
.field-input.ant-picker,
.field-select :deep(.ant-select-selector),
.field-textarea :deep(textarea) {
  border: 1px solid rgba(236, 243, 250, 0.2) !important;
  border-radius: 12px !important;
  background: rgba(14, 27, 38, 0.66) !important;
  color: #ecf3fa !important;
}

/* 穿透 AntD textarea 包裹层，直接设置 textarea 元素样式 */
.field-textarea :deep(textarea),
.field-textarea :deep(.ant-input),
.field-textarea.ant-input,
.field-textarea.ant-input-lg {
  background: rgba(14, 27, 38, 0.66) !important;
  border: 1px solid rgba(236, 243, 250, 0.2) !important;
  border-radius: 12px !important;
  color: #ecf3fa !important;
}

.field-input.ant-input::placeholder,
:deep(.field-input .ant-picker-input > input::placeholder),
.field-textarea :deep(textarea::placeholder),
.field-textarea.ant-input::placeholder {
  color: rgba(228, 236, 245, 0.4) !important;
}

.field-input.ant-input:hover,
.field-input.ant-picker:hover,
.field-select:hover :deep(.ant-select-selector),
.field-textarea :deep(textarea:hover),
.field-textarea.ant-input:hover {
  border-color: rgba(236, 243, 250, 0.42) !important;
}

.field-input.ant-input:focus,
.field-input.ant-picker-focused,
.field-textarea :deep(textarea:focus),
.field-textarea.ant-input:focus {
  border-color: rgba(215, 110, 66, 0.88) !important;
  box-shadow: 0 0 0 3px rgba(215, 110, 66, 0.2) !important;
  background: rgba(14, 27, 38, 0.66) !important;
  outline: none !important;
}

:deep(.field-input .ant-picker-input > input),
.field-select :deep(.ant-select-selection-item),
:deep(.field-input .ant-picker-suffix),
:deep(.field-input .ant-picker-clear),
.field-select :deep(.ant-select-arrow) {
  color: #ecf3fa !important;
}

.days-chip {
  min-height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(215, 110, 66, 0.42);
  background: rgba(19, 34, 46, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.days-number {
  color: rgba(236, 243, 250, 0.72);
  font-size: 24px;
  line-height: 1;
  font-weight: 700;
}

.days-unit {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(224, 233, 242, 0.74);
}

.interest-grid {
  width: 100%;
}

.interest-group {
  display: grid !important;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
  width: 100%;
}

.interest-group :deep(.ant-checkbox-wrapper) {
  display: none !important;
}

.interest-pill {
  min-height: 44px;
  border-radius: 12px;
  border: 1px solid rgba(236, 243, 250, 0.16);
  background: rgba(15, 28, 38, 0.6);
  color: rgba(232, 239, 247, 0.84);
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  user-select: none;
}

.interest-pill.active {
  border-color: rgba(215, 110, 66, 0.8);
  background: rgba(215, 110, 66, 0.2);
}

.submit-btn {
  width: 100%;
  min-height: 52px;
  border-radius: 14px;
  /* border: 1px solid rgba(236, 243, 250, 0.28);
  background: linear-gradient(135deg, #d76e42, #a14625);
  color: #fff; */
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
}

.submit-btn.loading {
  background: rgba(14, 27, 38, 0.66);
  cursor: wait;
}

.loading-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(236, 243, 250, 0.24);
  border-top-color: #fff;
  animation: spin 0.8s linear infinite;
}

.progress {
  margin-top: 14px;
}

.progress-track {
  width: 100%;
  height: 6px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(236, 243, 250, 0.14);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #f0946b 0%, #d76e42 45%, #b44d28 100%);
  transition: width 0.35s ease;
}

.progress p {
  margin: 10px 0 0;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(236, 243, 250, 0.8);
}

:deep(.ant-form-item-label > label) {
  color: transparent !important;
}

:deep(.ant-form-item-explain-error) {
  color: #ff9478 !important;
}

/* @keyframes cloudLoop {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(-50%, 0, 0);
  }
} */

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1080px) {
  .grid4 {
    grid-template-columns: 1fr 1fr;
  }

  .interest-group {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 991px) {
  .landing-navbar {
    min-height: 64px;
  }

  .landing-navbar .container {
    padding-left: 14px;
    padding-right: 14px;
    min-height: 64px;
  }

  .landing-navbar .navbar-translate {
    min-height: 64px;
  }

  .lang-select-nav {
    width: 92px;
  }

  .landing-cta {
    min-height: 34px;
    padding: 0 10px !important;
  }

  .landing-nav {
    gap: 6px;
  }

  .form-section {
    padding: 0 14px 72px;
  }

  .form-panel {
    padding: 22px 18px;
  }

  .grid4,
  .grid2 {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .landing-header .presentation-title {
    font-size: clamp(34px, 10vw, 52px);
  }

  .landing-header .presentation-subtitle {
    font-size: 14px;
  }

  .landing-header .content-center .container {
    transform: translate3d(0, 16px, 0);
  }

  .interest-group {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
