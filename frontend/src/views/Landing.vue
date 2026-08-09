<template>
  <div class="landing-page">
    <div class="lower-shade" :style="lowerShadeStyle"></div>
    <NavBar @brand-click="scrollToTop" @cta-click="scrollToForm" />

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
      <div class="form-panel" :style="[formRevealStyle, { minHeight: panelHeight === 'auto' ? 'auto' : panelHeight + 'px' }]" ref="panelRef">
        <a-form v-show="!loading" :model="formData" layout="vertical" @finish="handleSubmit">
          <div class="step">
            <div class="step-head">
              <span>01</span>
              <h3>{{ t('home.step1') }}</h3>
            </div>

            <!-- 多城市动态列表 -->
            <div class="city-list">
              <div v-for="(cs, idx) in formData.cities" :key="idx" class="city-row">
                <a-form-item class="city-row-name" :rules="[{ required: true, message: t('home.cityRequired') }]">
                  <template #label>
                    <span class="field-label">{{ t('home.cityNLabel', { n: idx + 1 }) }}</span>
                  </template>
                  <a-input
                    v-model:value="cs.city"
                    :placeholder="t('home.cityPlaceholder')"
                    size="large"
                    class="field-input"
                  />
                </a-form-item>
                <a-form-item class="city-row-days">
                  <template #label>
                    <span class="field-label">{{ t('home.cityStayDays') }}</span>
                  </template>
                  <a-input-number
                    v-model:value="cs.days"
                    :min="1"
                    :max="15"
                    size="large"
                    class="field-input"
                    style="width: 100%"
                  />
                </a-form-item>
                <button
                  v-if="formData.cities.length > 1"
                  type="button"
                  class="city-remove-btn"
                  @click="removeCity(idx)"
                >×</button>
              </div>
              <button type="button" class="city-add-btn" @click="addCity">
                + {{ t('home.addCity') }}
              </button>
            </div>

            <!-- 日期与天数 -->
            <div class="grid grid-date">
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

              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('home.travelDaysLabel') }}</span>
                </template>
                <div class="days-chip">
                  <span class="days-number">{{ totalDays }}</span>
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
        </a-form>

        <!-- Node Loading Stepper -->
        <div v-show="loading" class="stepper-wrapper">
          <div class="stepper-header">
            <h2 class="stepper-title">{{ t('home.loading.planCode', { code: planCode }) }}</h2>
            <p class="stepper-subtitle">{{ t('home.loading.preparing') }}</p>
          </div>
          
          <div class="stepper-container">
            <!-- Step 1: Searching Attractions -->
            <div class="step-node" :class="{ active: loadingProgress >= 0 && loadingProgress <= 30, completed: loadingProgress > 30 }">
              <div class="node-icon">
                <i v-if="loadingProgress >= 0 && loadingProgress <= 30" class="spinner-small"></i>
                <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
              </div>
              <p class="node-text">{{ loadingProgress > 30 ? t('home.loading.searchedAttractions') : t('home.loading.searchingAttractions') }}</p>
            </div>
            <div class="step-divider" :class="{ completed: loadingProgress > 30 }"></div>

            <!-- Step 2: Weather -->
            <div class="step-node" :class="{ active: loadingProgress > 30 && loadingProgress <= 50, completed: loadingProgress > 50 }">
              <div class="node-icon">
                <i v-if="loadingProgress > 30 && loadingProgress <= 50" class="spinner-small"></i>
                <svg v-else width="20px" height="20px" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                  <path d="M10.5 1.5V3.1M3.6 10H2M5.4512 4.95137L4.31982 3.82M15.5498 4.95137L16.6812 3.82M19 10H17.4M6.50007 10.0001C6.50007 7.79093 8.29093 6.00007 10.5001 6.00007C12.0061 6.00007 13.3177 6.83235 14.0001 8.06206M6 22C3.79086 22 2 20.2091 2 18C2 15.7909 3.79086 14 6 14C6.46419 14 6.90991 14.0791 7.32442 14.2245C8.04061 12.3396 9.86387 11 12 11C14.1361 11 15.9594 12.3396 16.6756 14.2245C17.0901 14.0791 17.5358 14 18 14C20.2091 14 22 15.7909 22 18C22 20.2091 20.2091 22 18 22C13.3597 22 9.87921 22 6 22Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <p class="node-text">{{ loadingProgress > 50 ? t('home.loading.queriedWeather') : t('home.loading.queryingWeather') }}</p>
            </div>
            <div class="step-divider" :class="{ completed: loadingProgress > 50 }"></div>

            <!-- Step 3: Hotels -->
            <div class="step-node" :class="{ active: loadingProgress > 50 && loadingProgress <= 70, completed: loadingProgress > 70 }">
              <div class="node-icon">
                <i v-if="loadingProgress > 50 && loadingProgress <= 70" class="spinner-small"></i>
                <svg v-else fill="currentColor" width="25px" height="25px" viewBox="0 0 24 24" version="1.1" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
                    <g id="Layer_Grid"/><g id="Layer_2">
                    <path d="M21,8c0-2.2-1.8-4-4-4H7C4.8,4,3,5.8,3,8v3.8c-0.6,0.5-1,1.3-1,2.2v2.7V17v2c0,0.6,0.4,1,1,1s1-0.4,1-1v-1h16v1   c0,0.6,0.4,1,1,1s1-0.4,1-1v-2v-0.3V14c0-0.9-0.4-1.7-1-2.2V8z M5,8c0-1.1,0.9-2,2-2h10c1.1,0,2,0.9,2,2v3h-1v-1c0-1.7-1.3-3-3-3   h-1c-0.8,0-1.5,0.3-2,0.8C11.5,7.3,10.8,7,10,7H9c-1.7,0-3,1.3-3,3v1H5V8z M16,10v1h-3v-1c0-0.6,0.4-1,1-1h1C15.6,9,16,9.4,16,10z    M11,10v1H8v-1c0-0.6,0.4-1,1-1h1C10.6,9,11,9.4,11,10z M20,16H4v-2c0-0.6,0.4-1,1-1h3h3h2h3h3c0.6,0,1,0.4,1,1V16z"/></g>
                </svg>
              </div>
              <p class="node-text">{{ loadingProgress > 70 ? t('home.loading.recommendedHotels') : t('home.loading.recommendingHotels') }}</p>
            </div>
            <div class="step-divider" :class="{ completed: loadingProgress > 70 }"></div>

            <!-- Step 4: Planning -->
            <div class="step-node" :class="{ active: loadingProgress > 70 && loadingProgress < 100, completed: loadingProgress >= 100 }">
              <div class="node-icon">
                <i v-if="loadingProgress > 70 && loadingProgress < 100" class="spinner-small"></i>
                <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
              </div>
              <p class="node-text">{{ loadingProgress >= 100 ? t('home.loading.done') : t('home.loading.generatingPlan') }}</p>
            </div>
          </div>
          
          <div class="stepper-footer">
            <h3>{{ loadingStatus }}</h3>
            <p v-if="loadingProgress < 100">{{ t('home.loading.workingTogether') }}</p>
            <p v-else>{{ t('home.loading.donePrepare') }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="history-section">
      <div class="history-panel">
        <div class="history-head">
          <div>
            <p class="history-eyebrow">{{ t('home.history.eyebrow') }}</p>
            <h3 class="history-title">{{ t('home.history.title') }}</h3>
          </div>
          <a-button type="link" class="history-refresh" @click="loadHistoryPlans">
            {{ t('home.history.refresh') }}
          </a-button>
        </div>

        <div v-if="historyLoading" class="history-loading">
          {{ t('common.loading') }}
        </div>
        <a-empty v-else-if="historyPlans.length === 0" :description="t('home.history.empty')" />
        <div v-else class="history-list">
          <button
            v-for="item in historyPlans"
            :key="item.plan_id"
            type="button"
            class="history-item"
            @click="openHistoryPlan(item.plan_id)"
          >
            <div class="history-item-main">
              <div class="history-route">
                <span class="history-city">{{ item.city }}</span>
                <span class="history-date">{{ item.start_date }} {{ t('common.to') }} {{ item.end_date }}</span>
              </div>
              <p class="history-meta">
                <span>Plan ID: {{ item.plan_id }}</span>
                <span>{{ item.travel_days }}{{ t('home.travelDaysUnit') }}</span>
                <span>{{ t('home.history.updatedAt') }} {{ formatHistoryTime(item.updated_at) }}</span>
              </p>
              <p v-if="item.overall_suggestions" class="history-summary">{{ item.overall_suggestions }}</p>
            </div>
            <span class="history-open">{{ t('home.history.open') }}</span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { generateTripPlan, getTripHistory, resumeTripPlan } from '@/services/api'
import { getCurrentLocale } from '@/i18n'
import NavBar from '@/components/NavBar.vue'
import type { TripFormData, TripPlanResponse, TripTaskEvent, TripHistoryItem, CityStay } from '@/types'
import type { Dayjs } from 'dayjs'

type LandingFormData = {
  cities: Array<{ city: string; days: number }>
  start_date: Dayjs | null
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input: string
}

const router = useRouter()
const { t } = useI18n()

const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')
const scrollY = ref(0)
const formRef = ref<HTMLElement | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const panelHeight = ref<number | string>('auto')
const fogEnabled = ref(true)
const planCode = ref('')
const historyLoading = ref(false)
const historyPlans = ref<TripHistoryItem[]>([])

const getStageStatusText = (stage: TripTaskEvent['stage']) => {
  if (stage === 'submitted' || stage === 'initializing') return t('home.loading.initializing')
  if (stage === 'attraction_search') return t('home.loading.searchingAttractions')
  if (stage === 'weather_search') return t('home.loading.queryingWeather')
  if (stage === 'hotel_search') return t('home.loading.recommendingHotels')
  if (stage === 'planning') return t('home.loading.generatingPlan')
  if (stage === 'graph_building') return t('home.loading.generatingPlan')
  if (stage === 'completed') return t('home.loading.done')
  return t('home.loading.initializing')
}

const interestOptions = [
  { value: '历史文化', labelKey: 'home.interests.history' },
  { value: '自然风光', labelKey: 'home.interests.nature' },
  { value: '美食', labelKey: 'home.interests.food' },
  { value: '购物', labelKey: 'home.interests.shopping' },
  { value: '艺术', labelKey: 'home.interests.art' },
  { value: '休闲', labelKey: 'home.interests.leisure' },
]

const formRules = computed(() => ({
  startDate: [{ required: true, message: t('home.startDateRequired') }],
}))

const formData = reactive<LandingFormData>({
  cities: [{ city: '', days: 2 }],
  start_date: null,
  transportation: '公共交通',
  accommodation: '经济型酒店',
  preferences: [],
  free_text_input: '',
})

const totalDays = computed(() => formData.cities.reduce((sum, cs) => sum + (cs.days || 1), 0))

const addCity = () => {
  if (formData.cities.length >= 5) return
  formData.cities.push({ city: '', days: 2 })
}

const removeCity = (index: number) => {
  if (formData.cities.length <= 1) return
  formData.cities.splice(index, 1)
}

const heroProgress = computed(() => Math.min(scrollY.value / 320, 1))
const toneProgress = computed(() => Math.min(Math.max((scrollY.value - 20) / 360, 0), 1))
const pageHeaderStyle = computed(() => ({
  backgroundImage: "url('http://demos.creative-tim.com/paper-kit-2/assets/img/antoine-barres.jpg')",
  backgroundPosition: `center ${Math.max(-scrollY.value * 0.08, -120)}px`,
  backgroundSize: 'cover',
  backgroundRepeat: 'no-repeat',
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
const scrollToForm = () => {
  if (formRef.value) {
    const y = formRef.value.getBoundingClientRect().top + window.scrollY - 65
    window.scrollTo({ top: y, behavior: 'smooth' })
  }
}

const formatHistoryTime = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

const openHistoryPlan = (planId: string) => {
  if (!planId) return
  sessionStorage.removeItem('tripPlan')
  sessionStorage.removeItem('graphData')
  sessionStorage.setItem('planId', planId)
  router.push({ path: '/result', query: { plan_id: planId } })
}

const loadHistoryPlans = async () => {
  historyLoading.value = true
  try {
    historyPlans.value = await getTripHistory(8)
  } catch (error: any) {
    historyPlans.value = []
    message.error(error.message || t('home.history.loadFailed'))
  } finally {
    historyLoading.value = false
  }
}

// 已提交但尚未出结果的任务 id。刷新页面后据此重新挂接，
// 否则后端仍在跑而用户已经永久看不到这份计划了。
const PENDING_TASK_STORAGE_KEY = 'tripstar.pendingTaskId'

let navigateTimer: ReturnType<typeof setTimeout> | null = null
let resetLoadingTimer: ReturnType<typeof setTimeout> | null = null

const clearPlanCache = () => {
  sessionStorage.removeItem('tripPlan')
  sessionStorage.removeItem('graphData')
  sessionStorage.removeItem('planId')
}

const trackTaskEvent = (event: TripTaskEvent) => {
  if (event.plan_id) planCode.value = event.plan_id
  if (Number.isFinite(event.progress)) {
    loadingProgress.value = Math.max(0, Math.min(100, event.progress))
  }
  loadingStatus.value = event.message || getStageStatusText(event.stage)
}

const applyGeneratedPlan = (response: TripPlanResponse) => {
  loadingProgress.value = 100
  loadingStatus.value = t('home.loading.done')

  if (response.success && response.data) {
    const planId = response.plan_id || planCode.value
    sessionStorage.setItem('tripPlan', JSON.stringify(response.data))
    if (response.graph_data) sessionStorage.setItem('graphData', JSON.stringify(response.graph_data))
    if (planId) sessionStorage.setItem('planId', planId)
    message.success(t('home.messages.generateSuccess'))
    navigateTimer = setTimeout(() => {
      navigateTimer = null
      if (planId) {
        router.push({ path: '/result', query: { plan_id: planId } })
      } else {
        router.push('/result')
      }
    }, 500)
  } else {
    clearPlanCache()
    message.error(response.message || t('home.messages.generateFailed'))
  }
}

const finishLoadingState = () => {
  resetLoadingTimer = setTimeout(() => {
    resetLoadingTimer = null
    loading.value = false
    loadingProgress.value = 0
    loadingStatus.value = ''
    panelHeight.value = 'auto'
  }, 1000)
}

const resumePendingTask = async () => {
  const pendingTaskId = sessionStorage.getItem(PENDING_TASK_STORAGE_KEY)
  if (!pendingTaskId) return

  planCode.value = pendingTaskId
  loading.value = true
  loadingProgress.value = 5
  loadingStatus.value = t('home.loading.initializing')

  try {
    const response = await resumeTripPlan(pendingTaskId, { onTaskEvent: trackTaskEvent })
    applyGeneratedPlan(response)
  } catch (error: any) {
    clearPlanCache()
    message.error(error.message || t('home.messages.generateRetry'))
  } finally {
    sessionStorage.removeItem(PENDING_TASK_STORAGE_KEY)
    finishLoadingState()
  }
}

onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  void loadHistoryPlans()
  void resumePendingTask()
})
onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  if (navigateTimer !== null) clearTimeout(navigateTimer)
  if (resetLoadingTimer !== null) clearTimeout(resetLoadingTimer)
})

const handleSubmit = async () => {
  // 校验：至少一个城市名非空
  const validCities = formData.cities.filter(cs => cs.city.trim())
  if (validCities.length === 0) {
    message.error(t('home.atLeastOneCity'))
    return
  }
  if (!formData.start_date) {
    message.error(t('home.messages.selectDate'))
    return
  }
  if (totalDays.value > 30) {
    message.warning(t('home.messages.travelDaysTooLong'))
    return
  }

  if (panelRef.value) {
    panelHeight.value = panelRef.value.offsetHeight
  }

  loading.value = true
  loadingProgress.value = 5
  loadingStatus.value = t('home.loading.initializing')
  planCode.value = ''

  try {
    clearPlanCache()

    const citiesPayload: CityStay[] = validCities.map(cs => ({ city: cs.city.trim(), days: cs.days || 1 }))
    // 天数必须与真正提交的城市列表一致：留空的城市行不参与行程，也不能计入总天数
    const plannedDays = citiesPayload.reduce((sum, cs) => sum + cs.days, 0)
    const endDate = formData.start_date.add(plannedDays - 1, 'day')

    const requestData: TripFormData = {
      city: citiesPayload[0].city,
      cities: citiesPayload,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: endDate.format('YYYY-MM-DD'),
      travel_days: plannedDays,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      free_text_input: formData.free_text_input,
      language: getCurrentLocale(),
    }

    const response = await generateTripPlan(requestData, {
      onTaskCreated: (task) => {
        const taskId = task.task_id || task.plan_id
        planCode.value = task.plan_id || task.task_id
        // 任务已在后端排上队，刷新页面后要能凭它恢复
        if (taskId) sessionStorage.setItem(PENDING_TASK_STORAGE_KEY, taskId)
        loadingProgress.value = 5
        loadingStatus.value = t('home.loading.initializing')
      },
      onTaskEvent: trackTaskEvent,
    })

    applyGeneratedPlan(response)
  } catch (error: any) {
    clearPlanCache()
    message.error(error.message || t('home.messages.generateRetry'))
  } finally {
    sessionStorage.removeItem(PENDING_TASK_STORAGE_KEY)
    finishLoadingState()
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
  overflow-x: hidden; /* 防止水平溢出导致的出界感 */
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

.history-section {
  position: relative;
  z-index: 1;
  padding: 0 24px 72px;
}

.history-panel {
  max-width: 1120px;
  margin: 0 auto;
  background: rgba(10, 20, 28, 0.74);
  border: 1px solid rgba(203, 227, 255, 0.12);
  border-radius: 28px;
  padding: 24px;
  box-shadow: 0 28px 60px rgba(0, 0, 0, 0.24);
  backdrop-filter: blur(14px);
}

.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.history-eyebrow {
  margin: 0 0 6px;
  color: rgba(203, 227, 255, 0.62);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.history-title {
  margin: 0;
  color: #f5fbff;
  font-size: 24px;
  font-weight: 700;
}

.history-refresh {
  padding-inline: 0;
}

.history-loading {
  color: rgba(236, 243, 250, 0.78);
  padding: 12px 4px;
}

.history-list {
  display: grid;
  gap: 14px;
}

.history-item {
  width: 100%;
  border: 1px solid rgba(203, 227, 255, 0.12);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  padding: 18px 20px;
  text-align: left;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.history-item:hover {
  transform: translateY(-1px);
  border-color: rgba(138, 196, 255, 0.28);
  background: rgba(255, 255, 255, 0.06);
}

.history-item-main {
  min-width: 0;
  flex: 1;
}

.history-route {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
}

.history-city {
  color: #f7fbff;
  font-size: 20px;
  font-weight: 700;
}

.history-date {
  color: rgba(236, 243, 250, 0.75);
  font-size: 14px;
}

.history-meta {
  margin: 8px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: rgba(203, 227, 255, 0.64);
  font-size: 13px;
}

.history-summary {
  margin: 10px 0 0;
  color: rgba(236, 243, 250, 0.9);
  font-size: 14px;
  line-height: 1.6;
}

.history-open {
  flex: none;
  color: #8ac4ff;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
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
  max-width: 1000px;
  margin: 0 auto;
  border: 1.2px solid rgba(236, 243, 250, 0.2);
  border-radius: 22px;
  background: rgba(12, 23, 32, 0.56);
  backdrop-filter: blur(18px);
  box-shadow: 0 24px 80px rgba(4, 11, 18, 0.52);
  padding: 20px;
  transition: 0.25s;
}

.step {
  margin-bottom: 8px;
}

.step-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.step-head span {
  width: 26px;
  height: 23px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(215, 110, 66, 0.2);
  border: 1.2px solid rgba(215, 110, 66, 0.4);
  color: rgba(253, 225, 211, 0.95);
  font-size: 12px;
  font-weight: 700;
}

.step-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: rgba(240, 246, 252, 0.94);
}

.grid {
  display: grid;
  gap: 12px;
}

.grid4 {
  grid-template-columns: 1.5fr 1fr 1fr 0.8fr;
}

.grid-date {
  grid-template-columns: 1fr 0.6fr;
  margin-top: 12px;
}

.grid2 {
  grid-template-columns: 1fr 1fr;
}

.city-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 4px;
}

.city-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.city-row-name {
  flex: 2;
  margin-bottom: 0;
}

.city-row-days {
  flex: 0.8;
  margin-bottom: 0;
}

.city-remove-btn {
  flex-shrink: 0;
  width: 36px;
  height: 40px;
  margin-bottom: 0;
  border: 1.2px solid rgba(236, 243, 250, 0.2);
  border-radius: 10px;
  background: rgba(14, 27, 38, 0.66);
  color: rgba(236, 243, 250, 0.6);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.city-remove-btn:hover {
  border-color: rgba(255, 100, 100, 0.6);
  color: #ff6464;
  background: rgba(255, 100, 100, 0.1);
}

.city-add-btn {
  align-self: flex-start;
  padding: 6px 16px;
  border: 1.2px dashed rgba(215, 110, 66, 0.5);
  border-radius: 10px;
  background: transparent;
  color: rgba(215, 110, 66, 0.85);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.city-add-btn:hover {
  border-color: rgba(215, 110, 66, 0.9);
  background: rgba(215, 110, 66, 0.1);
  color: #d76e42;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(228, 236, 245, 0.72);
}

.field-input.ant-input,
.field-input.ant-input-lg,
.field-input.ant-input-number,
.field-input.ant-input-number-lg,
.field-input.ant-picker,
.field-select :deep(.ant-select-selector),
.field-textarea :deep(textarea),
.field-textarea :deep(.ant-input),
.field-textarea.ant-input,
.special-textarea.ant-input {
  border: 1.2px solid rgba(236, 243, 250, 0.2) !important;
  border-radius: 12px !important;
  background: rgba(14, 27, 38, 0.66) !important;
  background-color: rgba(14, 27, 38, 0.66) !important;
  background-image: none !important;
  color: #ecf3fa !important;
}

/* 浏览器自动填充（Autofill）背景色修复 */
:deep(.field-input.ant-input:-webkit-autofill),
:deep(.field-input.ant-input:-webkit-autofill:hover),
:deep(.field-input.ant-input:-webkit-autofill:focus),
:deep(.field-input.ant-input:-webkit-autofill:active),
:deep(.field-input .ant-picker-input > input:-webkit-autofill),
:deep(.field-textarea textarea:-webkit-autofill),
:deep(.special-textarea:-webkit-autofill) {
  -webkit-box-shadow: 0 0 0 1000px #0e1b26 inset !important;
  -webkit-text-fill-color: #ecf3fa !important;
  transition: background-color 5000s ease-in-out 0s !important;
}

.field-input.ant-input-number :deep(.ant-input-number-input),
.field-input.ant-input-number :deep(.ant-input-number-handler-wrap) {
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
  border: 1.2px solid rgba(215, 110, 66, 0.42);
  background: rgba(19, 34, 46, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.days-number {
  color: rgba(236, 243, 250, 0.72);
  font-size: 18px;
  line-height: 1;
  font-weight: 700;
}

.days-unit {
  font-size: 16px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(224, 233, 242, 0.74);
  font-weight: 700;
}

.interest-grid {
  width: 100%;
}

.interest-group {
  display: grid !important;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  width: 100%;
}

.interest-group :deep(.ant-checkbox-wrapper) {
  display: none !important;
}

.interest-pill {
  min-height: 38px;
  border-radius: 10px;
  border: 1.2px solid rgba(236, 243, 250, 0.16);
  background: rgba(15, 28, 38, 0.6);
  color: rgba(232, 239, 247, 0.84);
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  user-select: none;
  transition: all 0.55s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.interest-pill:hover {
  background: rgba(236, 243, 250, 0.08);
  border-color: rgba(236, 243, 250, 0.3);
  /* transform: translateY(-2px); */
  box-shadow: 0 4px 12px rgba(4, 11, 18, 0.3);
}

.interest-pill:active {
  transform: translateY(1px) scale(0.96);
  box-shadow: 0 2px 4px rgba(4, 11, 18, 0.2);
}

.interest-pill.active {
  border-color: rgba(215, 110, 66, 0.8);
  background: rgba(215, 110, 66, 0.2);
}

.interest-pill.active:hover {
  background: rgba(215, 110, 66, 0.28);
  border-color: rgba(215, 110, 66, 1);
}

.submit-btn {
  width: 100%;
  min-height: 48px;
  border-radius: 12px;
  /* border: 1px solid rgba(236, 243, 250, 0.28);
  background: linear-gradient(135deg, #d76e42, #a14625);
  color: #fff; */
  font-size: 13px;
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

.spinner-small {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2.5px solid rgba(215, 110, 66, 0.24);
  border-top-color: #d76e42;
  animation: spin 0.8s linear infinite;
}

/* 节点动画相关样式 */
.stepper-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 480px;
  animation: fadeIn 0.4s ease;
  padding: 30px 20px;
  box-sizing: border-box;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.stepper-header {
  text-align: center;
  margin-bottom: 50px;
}

.stepper-title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 8px;
  letter-spacing: 0.05em;
}

.stepper-subtitle {
  font-size: 15px;
  color: rgba(236, 243, 250, 0.54);
}

.stepper-container {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  width: 100%;
  max-width: 680px;
  margin: 0 auto 50px auto;
}

.step-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100px;
  z-index: 2;
}

.node-icon {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(14, 27, 38, 0.8);
  border: 1.5px solid rgba(236, 243, 250, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  color: rgba(236, 243, 250, 0.4);
  transition: all 0.35s ease;
}

.step-node.active .node-icon {
  border-color: #d76e42;
  background: rgba(215, 110, 66, 0.14);
  color: #d76e42;
  box-shadow: 0 0 16px rgba(215, 110, 66, 0.25);
}

.step-node.completed .node-icon {
  background: #d76e42;
  border-color: #d76e42;
  color: #fff;
  box-shadow: 0 0 12px rgba(215, 110, 66, 0.3);
}

.node-text {
  font-size: 12px;
  font-weight: 600;
  color: rgba(236, 243, 250, 0.4);
  text-align: center;
  transition: color 0.35s ease;
  line-height: 1.3;
}

.step-node.active .node-text {
  color: #d76e42;
}

.step-node.completed .node-text {
  color: rgba(236, 243, 250, 0.85);
}

.step-divider {
  flex: 1;
  height: 3px;
  background: rgba(236, 243, 250, 0.08);
  margin-top: 25px; /* (52px / 2) - 1.5px */
  border-radius: 2px;
  position: relative;
  overflow: hidden;
}

.step-divider::after {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0; width: 0%;
  background: #d76e42;
  transition: width 0.45s ease;
}

.step-divider.completed::after {
  width: 100%;
}

.stepper-footer {
  text-align: center;
  margin-top: 10px;
}

.stepper-footer h3 {
  font-size: 20px;
  font-weight: 600;
  color: #d76e42;
  margin-bottom: 8px;
}

.stepper-footer p {
  font-size: 14px;
  color: rgba(236, 243, 250, 0.54);
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
  .form-section {
    padding: 0 14px 72px;
  }

  .form-panel {
    padding: 22px 18px;
  }

  .grid4,
  .grid2,
  .grid-date {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .landing-header .presentation-title {
    font-size: clamp(34px, 10vw, 52px);
  }

  .landing-header .presentation-subtitle {
    font-size: 14px;
    padding: 0 10px;
  }

  .landing-header .content-center .container {
    transform: translate3d(0, 16px, 0);
  }

  .interest-group {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
