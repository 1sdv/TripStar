<template>
  <div class="landing-page">
    <NavBar @brand-click="scrollToTop" @cta-click="scrollToForm" />

    <!-- paper grain + warm glow -->
    <div class="sa-grain" aria-hidden="true"></div>

    <!-- ── Hero ─────────────────────────────────────────── -->
    <section class="sa-hero">
      <div class="sa-wrap sa-hero-grid">
        <div class="sa-hero-copy">
          <p class="sa-eyebrow">{{ t('home.heroBadge') }}</p>
          <h1 class="sa-title">
            <span class="sa-wordmark">TRIPSTAR</span>
          </h1>
          <h2 class="sa-subtitle">{{ t('home.titleLine') }}</h2>
          <div class="sa-hero-cta">
            <button type="button" class="sa-btn sa-btn-rust" @click="scrollToForm">
              {{ t('home.nav.cta') }}
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 7h10M8 3l4 4-4 4"/></svg>
            </button>
          </div>
        </div>

        <!-- signature: the night star-chart -->
        <div class="sa-chart-frame">
          <div class="sa-chart">
            <span class="sa-chart-tag tl">KYOTO 35.0°N · TOKYO 35.7°N</span>
            <span class="sa-chart-tag br">ROUTE PLOTTED</span>
            <svg viewBox="0 0 440 432" preserveAspectRatio="xMidYMid slice" class="sa-chart-svg">
              <defs>
                <radialGradient id="saGlow" cx="30%" cy="8%" r="80%">
                  <stop offset="0%" stop-color="#2a4b56" stop-opacity=".6"/>
                  <stop offset="100%" stop-color="#0d181d" stop-opacity="0"/>
                </radialGradient>
              </defs>
              <rect width="440" height="432" fill="url(#saGlow)"/>
              <g stroke="rgba(234,224,203,.06)" stroke-width="1">
                <line x1="0" y1="144" x2="440" y2="144"/>
                <line x1="0" y1="288" x2="440" y2="288"/>
                <line x1="146" y1="0" x2="146" y2="432"/>
                <line x1="293" y1="0" x2="293" y2="432"/>
              </g>
              <!-- background stars -->
              <g class="sa-bgstars" fill="#EAE0CB">
                <circle cx="38" cy="60" r=".9"/><circle cx="110" cy="30" r="1.1"/><circle cx="250" cy="52" r=".8"/>
                <circle cx="330" cy="26" r="1"/><circle cx="400" cy="70" r=".9"/><circle cx="70" cy="120" r=".7"/>
                <circle cx="180" cy="100" r="1"/><circle cx="410" cy="150" r=".8"/><circle cx="30" cy="220" r="1"/>
                <circle cx="130" cy="330" r=".9"/><circle cx="250" cy="360" r="1.1"/><circle cx="380" cy="330" r=".8"/>
                <circle cx="420" cy="270" r=".9"/><circle cx="60" cy="400" r="1"/><circle cx="200" cy="410" r=".8"/>
                <circle cx="350" cy="400" r=".9"/><circle cx="160" cy="200" r=".7"/><circle cx="270" cy="180" r=".8"/>
                <circle cx="90" cy="280" r=".8"/><circle cx="360" cy="250" r=".7"/>
              </g>
              <!-- route: kyoto cluster -> transfer -> tokyo cluster -->
              <path class="sa-route" d="M96,352 L150,258 L86,180 L206,220"/>
              <path class="sa-route sa-transfer" d="M206,220 L296,132"/>
              <path class="sa-route" d="M296,132 L360,204 L322,290"/>
              <!-- nodes -->
              <g>
                <circle class="sa-halo" cx="96" cy="352" r="9"/><circle class="sa-node" cx="96" cy="352" r="3.4"/>
                <text class="sa-nlabel" x="105" y="356">Fushimi Inari</text>
                <circle class="sa-halo" cx="150" cy="258" r="9"/><circle class="sa-node" cx="150" cy="258" r="3.4"/>
                <text class="sa-nlabel" x="159" y="262">Kinkaku-ji</text>
                <circle class="sa-halo" cx="86" cy="180" r="9"/><circle class="sa-node" cx="86" cy="180" r="3.4"/>
                <text class="sa-nlabel" x="95" y="184">Arashiyama</text>
                <circle class="sa-halo" cx="206" cy="220" r="9"/><circle class="sa-node" cx="206" cy="220" r="3.4"/>
                <text class="sa-nlabel" x="215" y="224">Gion</text>
                <circle class="sa-halo" cx="296" cy="132" r="9"/><circle class="sa-node" cx="296" cy="132" r="3.4"/>
                <text class="sa-nlabel" x="305" y="136">Senso-ji</text>
                <circle class="sa-halo" cx="360" cy="204" r="9"/><circle class="sa-node" cx="360" cy="204" r="3.4"/>
                <text class="sa-nlabel end" x="351" y="208">Shibuya</text>
                <circle class="sa-halo" cx="322" cy="290" r="9"/><circle class="sa-node" cx="322" cy="290" r="3.4"/>
                <text class="sa-nlabel end" x="313" y="294">teamLab</text>
              </g>
            </svg>
          </div>
          <div class="sa-chart-foot">
            <div>
              <div class="sa-cap">Kyoto → Tokyo</div>
              <div class="sa-sub">7 stops · 2 cities · 1 reference no.</div>
            </div>
            <div class="sa-n">¥ 42,800</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── Planner ─────────────────────────────────────── -->
    <section ref="formRef" class="sa-form-section">
      <div class="sa-wrap">
        <div
          class="sa-panel"
          ref="panelRef"
          :style="{ minHeight: panelHeight === 'auto' ? 'auto' : panelHeight + 'px' }"
        >
          <a-form v-show="!loading" :model="formData" layout="vertical" @finish="handleSubmit">
            <!-- step 1 -->
            <div class="sa-step">
              <div class="sa-step-head">
                <span class="sa-step-no">01</span>
                <h3>{{ t('home.step1') }}</h3>
              </div>

              <div class="sa-city-list">
                <div v-for="(cs, idx) in formData.cities" :key="idx" class="sa-city-row">
                  <a-form-item class="sa-city-name" :rules="[{ required: true, message: t('home.cityRequired') }]">
                    <template #label>
                      <span class="sa-field-label">{{ t('home.cityNLabel', { n: idx + 1 }) }}</span>
                    </template>
                    <a-input
                      v-model:value="cs.city"
                      :placeholder="t('home.cityPlaceholder')"
                      size="large"
                    />
                  </a-form-item>
                  <a-form-item class="sa-city-days">
                    <template #label>
                      <span class="sa-field-label">{{ t('home.cityStayDays') }}</span>
                    </template>
                    <a-input-number v-model:value="cs.days" :min="1" :max="15" size="large" style="width: 100%" />
                  </a-form-item>
                  <button
                    v-if="formData.cities.length > 1"
                    type="button"
                    class="sa-city-remove"
                    @click="removeCity(idx)"
                  >×</button>
                </div>
                <button type="button" class="sa-city-add" @click="addCity">
                  + {{ t('home.addCity') }}
                </button>
              </div>

              <div class="sa-grid sa-grid-date">
                <a-form-item name="start_date" :rules="formRules.startDate">
                  <template #label>
                    <span class="sa-field-label">{{ t('home.startDateLabel') }}</span>
                  </template>
                  <a-date-picker
                    v-model:value="formData.start_date"
                    style="width: 100%"
                    size="large"
                    :placeholder="t('home.startDatePlaceholder')"
                  />
                </a-form-item>

                <a-form-item>
                  <template #label>
                    <span class="sa-field-label">{{ t('home.travelDaysLabel') }}</span>
                  </template>
                  <div class="sa-days-chip">
                    <span class="sa-days-number">{{ totalDays }}</span>
                    <span class="sa-days-unit">{{ t('home.travelDaysUnit') }}</span>
                  </div>
                </a-form-item>
              </div>
            </div>

            <!-- step 2 -->
            <div class="sa-step">
              <div class="sa-step-head">
                <span class="sa-step-no">02</span>
                <h3>{{ t('home.step2') }}</h3>
              </div>
              <div class="sa-grid sa-grid2">
                <a-form-item name="transportation">
                  <template #label>
                    <span class="sa-field-label">{{ t('home.transportationLabel') }}</span>
                  </template>
                  <a-select v-model:value="formData.transportation" size="large">
                    <a-select-option value="公共交通">{{ t('home.transportation.public') }}</a-select-option>
                    <a-select-option value="自驾">{{ t('home.transportation.drive') }}</a-select-option>
                    <a-select-option value="步行">{{ t('home.transportation.walk') }}</a-select-option>
                    <a-select-option value="混合">{{ t('home.transportation.mixed') }}</a-select-option>
                  </a-select>
                </a-form-item>

                <a-form-item name="accommodation">
                  <template #label>
                    <span class="sa-field-label">{{ t('home.accommodationLabel') }}</span>
                  </template>
                  <a-select v-model:value="formData.accommodation" size="large">
                    <a-select-option value="经济型酒店">{{ t('home.accommodation.budget') }}</a-select-option>
                    <a-select-option value="舒适型酒店">{{ t('home.accommodation.comfort') }}</a-select-option>
                    <a-select-option value="豪华酒店">{{ t('home.accommodation.luxury') }}</a-select-option>
                    <a-select-option value="民宿">{{ t('home.accommodation.homestay') }}</a-select-option>
                  </a-select>
                </a-form-item>
              </div>

              <a-form-item name="preferences">
                <template #label>
                  <span class="sa-field-label">{{ t('home.interestsLabel') }}</span>
                </template>
                <a-checkbox-group v-model:value="formData.preferences" class="sa-interest-group">
                  <label
                    v-for="item in interestOptions"
                    :key="item.value"
                    class="sa-pill"
                    :class="{ on: formData.preferences.includes(item.value) }"
                    @click.prevent="togglePreference(item.value)"
                  >
                    {{ t(item.labelKey) }}
                  </label>
                </a-checkbox-group>
              </a-form-item>
            </div>

            <!-- step 3 -->
            <div class="sa-step">
              <div class="sa-step-head">
                <span class="sa-step-no">03</span>
                <h3>{{ t('home.step3') }}</h3>
              </div>
              <a-form-item name="free_text_input">
                <a-textarea
                  v-model:value="formData.free_text_input"
                  :placeholder="t('home.specialNeedsPlaceholder')"
                  :rows="4"
                  size="large"
                />
              </a-form-item>
            </div>

            <button type="submit" class="sa-submit" :class="{ loading }" :disabled="loading">
              <span v-if="!loading">{{ t('home.submit') }}</span>
              <span v-else class="sa-loading-row">
                <i class="sa-spin"></i>
                {{ t('home.submitting') }}
              </span>
            </button>
          </a-form>

          <!-- constellation loading stepper -->
          <div v-show="loading" class="sa-stepper">
            <div class="sa-stepper-head">
              <h2 class="sa-stepper-title">{{ t('home.loading.planCode', { code: planCode }) }}</h2>
              <p class="sa-stepper-sub">{{ t('home.loading.preparing') }}</p>
            </div>

            <div class="sa-constellation">
              <span class="sa-const-line" :style="{ '--fill': constellationFill }"></span>

              <!-- 01 attractions -->
              <div class="sa-star-node" :class="{ active: loadingProgress >= 0 && loadingProgress <= 30, done: loadingProgress > 30 }">
                <span class="sa-star-mark">
                  <i v-if="loadingProgress >= 0 && loadingProgress <= 30" class="sa-spin-sm"></i>
                  <svg v-else width="16" height="16" viewBox="0 0 16 16"><path d="M8 1l1.9 4.3L14 5.6l-3.2 2.7 1.1 4.4L8 10.5 4.1 12.7l1.1-4.4L2 5.6l4.1-.3z" fill="currentColor"/></svg>
                </span>
                <p class="sa-star-text">{{ loadingProgress > 30 ? t('home.loading.searchedAttractions') : t('home.loading.searchingAttractions') }}</p>
              </div>

              <!-- 02 weather -->
              <div class="sa-star-node" :class="{ active: loadingProgress > 30 && loadingProgress <= 50, done: loadingProgress > 50 }">
                <span class="sa-star-mark">
                  <i v-if="loadingProgress > 30 && loadingProgress <= 50" class="sa-spin-sm"></i>
                  <svg v-else width="16" height="16" viewBox="0 0 16 16"><path d="M8 1l1.9 4.3L14 5.6l-3.2 2.7 1.1 4.4L8 10.5 4.1 12.7l1.1-4.4L2 5.6l4.1-.3z" fill="currentColor"/></svg>
                </span>
                <p class="sa-star-text">{{ loadingProgress > 50 ? t('home.loading.queriedWeather') : t('home.loading.queryingWeather') }}</p>
              </div>

              <!-- 03 hotels -->
              <div class="sa-star-node" :class="{ active: loadingProgress > 50 && loadingProgress <= 70, done: loadingProgress > 70 }">
                <span class="sa-star-mark">
                  <i v-if="loadingProgress > 50 && loadingProgress <= 70" class="sa-spin-sm"></i>
                  <svg v-else width="16" height="16" viewBox="0 0 16 16"><path d="M8 1l1.9 4.3L14 5.6l-3.2 2.7 1.1 4.4L8 10.5 4.1 12.7l1.1-4.4L2 5.6l4.1-.3z" fill="currentColor"/></svg>
                </span>
                <p class="sa-star-text">{{ loadingProgress > 70 ? t('home.loading.recommendedHotels') : t('home.loading.recommendingHotels') }}</p>
              </div>

              <!-- 04 planning -->
              <div class="sa-star-node" :class="{ active: loadingProgress > 70 && loadingProgress < 100, done: loadingProgress >= 100 }">
                <span class="sa-star-mark">
                  <i v-if="loadingProgress > 70 && loadingProgress < 100" class="sa-spin-sm"></i>
                  <svg v-else width="16" height="16" viewBox="0 0 16 16"><path d="M8 1l1.9 4.3L14 5.6l-3.2 2.7 1.1 4.4L8 10.5 4.1 12.7l1.1-4.4L2 5.6l4.1-.3z" fill="currentColor"/></svg>
                </span>
                <p class="sa-star-text">{{ loadingProgress >= 100 ? t('home.loading.done') : t('home.loading.generatingPlan') }}</p>
              </div>
            </div>

            <div class="sa-stepper-foot">
              <h3>{{ loadingStatus }}</h3>
              <p v-if="loadingProgress < 100">{{ t('home.loading.workingTogether') }}</p>
              <p v-else>{{ t('home.loading.donePrepare') }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── History ─────────────────────────────────────── -->
    <section class="sa-history">
      <div class="sa-wrap">
        <div class="sa-history-panel">
          <div class="sa-history-head">
            <div>
              <p class="sa-history-eyebrow">{{ t('home.history.eyebrow') }}</p>
              <h3 class="sa-history-title">{{ t('home.history.title') }}</h3>
            </div>
            <a-button type="link" class="sa-history-refresh" @click="loadHistoryPlans">
              {{ t('home.history.refresh') }}
            </a-button>
          </div>

          <div v-if="historyLoading" class="sa-history-loading">
            {{ t('common.loading') }}
          </div>
          <a-empty v-else-if="historyPlans.length === 0" :description="t('home.history.empty')" />
          <div v-else class="sa-history-list">
            <button
              v-for="item in historyPlans"
              :key="item.plan_id"
              type="button"
              class="sa-history-item"
              @click="openHistoryPlan(item.plan_id)"
            >
              <div class="sa-history-item-main">
                <div class="sa-history-route">
                  <span class="sa-history-city">{{ item.city }}</span>
                  <span class="sa-history-date">{{ item.start_date }} {{ t('common.to') }} {{ item.end_date }}</span>
                </div>
                <p class="sa-history-meta">
                  <span>Plan ID: {{ item.plan_id }}</span>
                  <span>{{ item.travel_days }}{{ t('home.travelDaysUnit') }}</span>
                  <span>{{ t('home.history.updatedAt') }} {{ formatHistoryTime(item.updated_at) }}</span>
                </p>
                <p v-if="item.overall_suggestions" class="sa-history-summary">{{ item.overall_suggestions }}</p>
              </div>
              <span class="sa-history-open">{{ t('home.history.open') }}</span>
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- ── Footer ──────────────────────────────────────── -->
    <footer class="sa-footer">
      <div class="sa-wrap sa-foot-in">
        <div class="sa-foot-brand">
          <svg width="22" height="22" viewBox="0 0 26 26" fill="none"><circle cx="13" cy="13" r="12" stroke="#D9A441" stroke-width="1.2"/><path d="M13 5.5l1.7 4.9 5 .1-4 3 1.5 4.9L13 15.6 8.8 18.4l1.5-4.9-4-3 5-.1z" fill="#D9A441"/></svg>
          <span>TripStar</span>
        </div>
        <p class="sa-foot-co">35.68°N / 139.69°E · A STAR ALMANAC</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { generateTripPlan, getTripHistory } from '@/services/api'
import { getCurrentLocale } from '@/i18n'
import NavBar from '@/components/NavBar.vue'
import type { TripFormData, TripTaskEvent, TripHistoryItem, CityStay } from '@/types'
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
const formRef = ref<HTMLElement | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const panelHeight = ref<number | string>('auto')
const planCode = ref('')
const historyLoading = ref(false)
const historyPlans = ref<TripHistoryItem[]>([])

// 星座连线的点亮比例，跟随后端进度推进（装饰用途）
const constellationFill = computed(() => `${Math.min(Math.max(loadingProgress.value, 0), 100)}%`)

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

const computedEndDate = computed(() => {
  if (!formData.start_date) return null
  return formData.start_date.add(totalDays.value - 1, 'day')
})

const addCity = () => {
  if (formData.cities.length >= 5) return
  formData.cities.push({ city: '', days: 2 })
}

const removeCity = (index: number) => {
  if (formData.cities.length <= 1) return
  formData.cities.splice(index, 1)
}

const togglePreference = (value: string) => {
  const index = formData.preferences.indexOf(value)
  if (index === -1) formData.preferences.push(value)
  else formData.preferences.splice(index, 1)
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

onMounted(() => {
  void loadHistoryPlans()
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
    sessionStorage.removeItem('tripPlan')
    sessionStorage.removeItem('graphData')
    sessionStorage.removeItem('planId')

    const citiesPayload: CityStay[] = validCities.map(cs => ({ city: cs.city.trim(), days: cs.days || 1 }))
    const endDate = computedEndDate.value!

    const requestData: TripFormData = {
      city: citiesPayload[0].city,
      cities: citiesPayload,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: endDate.format('YYYY-MM-DD'),
      travel_days: totalDays.value,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      free_text_input: formData.free_text_input,
      language: getCurrentLocale(),
    }

    const response = await generateTripPlan(requestData, {
      onTaskCreated: (task) => {
        planCode.value = task.plan_id || task.task_id
        loadingProgress.value = 5
        loadingStatus.value = t('home.loading.initializing')
      },
      onTaskEvent: (event) => {
        if (event.plan_id) planCode.value = event.plan_id
        if (Number.isFinite(event.progress)) {
          loadingProgress.value = Math.max(0, Math.min(100, event.progress))
        }
        loadingStatus.value = event.message || getStageStatusText(event.stage)
      }
    })

    loadingProgress.value = 100
    loadingStatus.value = t('home.loading.done')

    if (response.success && response.data) {
      const planId = response.plan_id || planCode.value
      sessionStorage.setItem('tripPlan', JSON.stringify(response.data))
      if (response.graph_data) sessionStorage.setItem('graphData', JSON.stringify(response.graph_data))
      if (planId) sessionStorage.setItem('planId', planId)
      message.success(t('home.messages.generateSuccess'))
      setTimeout(() => {
        if (planId) {
          router.push({ path: '/result', query: { plan_id: planId } })
        } else {
          router.push('/result')
        }
      }, 500)
    } else {
      sessionStorage.removeItem('tripPlan')
      sessionStorage.removeItem('graphData')
      sessionStorage.removeItem('planId')
      message.error(response.message || t('home.messages.generateFailed'))
    }
  } catch (error: any) {
    sessionStorage.removeItem('tripPlan')
    sessionStorage.removeItem('graphData')
    sessionStorage.removeItem('planId')
    message.error(error.message || t('home.messages.generateRetry'))
  } finally {
    setTimeout(() => {
      loading.value = false
      loadingProgress.value = 0
      loadingStatus.value = ''
      panelHeight.value = 'auto'
    }, 1000)
  }
}
</script>

<!-- fonts (global, loaded once) -->
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=IBM+Plex+Mono:wght@400;500&display=swap');
</style>

<style scoped>
.landing-page {
  /* ── Star Almanac tokens ── */
  --paper:#F4EEE1;
  --paper-2:#EBE1CE;
  --card:#FBF7EE;
  --ink:#241D18;
  --ink-soft:#6B5C4C;
  --ink-faint:#A7967D;
  --line:rgba(36,29,24,.14);
  --line-2:rgba(36,29,24,.08);
  --rust:#C0562A;
  --rust-deep:#95401A;
  --teal:#1F5460;
  --night:#132229;
  --brass:#D9A441;
  --brass-soft:#EBCB85;
  --star-ink:#EAE0CB;
  --serif:'Newsreader', Georgia, 'Times New Roman', serif;
  --mono:'IBM Plex Mono', ui-monospace, Menlo, monospace;

  min-height: 100vh;
  background: var(--paper);
  color: var(--ink);
  position: relative;
  isolation: isolate;
  overflow-x: hidden;
  padding-top: 70px; /* clear the fixed NavBar */
}

.sa-grain {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image:
    radial-gradient(circle, rgba(36,29,24,.045) 1px, transparent 1px),
    radial-gradient(ellipse 70% 46% at 50% -4%, rgba(192,86,42,.06), transparent 68%);
  background-size: 24px 24px, 100% 100%;
}

.sa-wrap { max-width: 1180px; margin: 0 auto; padding: 0 22px; position: relative; z-index: 1; }
@media (min-width: 768px) { .sa-wrap { padding: 0 34px; } }

/* ── Hero ── */
.sa-hero-grid { display: grid; gap: 40px; align-items: center; padding: 44px 0 22px; }
@media (min-width: 900px) { .sa-hero-grid { grid-template-columns: 1.02fr .98fr; gap: 52px; padding: 60px 0 30px; } }

.sa-eyebrow {
  font-family: var(--mono); font-size: 11px; letter-spacing: .16em; color: var(--rust);
  display: inline-flex; align-items: center; gap: 10px; margin: 0 0 16px; text-transform: uppercase;
}
.sa-eyebrow::before { content: ""; width: 26px; height: 1px; background: var(--rust); display: inline-block; }

.sa-title { margin: 0; line-height: .96; }
.sa-wordmark {
  font-family: var(--serif); font-weight: 600; letter-spacing: .01em;
  font-size: clamp(3.1rem, 7vw, 5.2rem); color: var(--ink);
}
.sa-subtitle {
  font-family: var(--serif); font-style: italic; font-weight: 400;
  font-size: clamp(1.4rem, 3vw, 2.1rem); color: var(--rust); margin: 12px 0 0; line-height: 1.15;
}
.sa-hero-cta { margin-top: 30px; display: flex; flex-wrap: wrap; gap: 12px; }

.sa-btn {
  display: inline-flex; align-items: center; gap: 8px; border: none; border-radius: 2px;
  padding: 12px 22px; font-size: 14px; font-weight: 500; font-family: inherit; cursor: pointer;
  transition: background .2s, transform .2s;
}
.sa-btn svg { transition: transform .2s; }
.sa-btn:hover svg { transform: translateX(3px); }
.sa-btn-rust { background: var(--rust); color: var(--paper); }
.sa-btn-rust:hover { background: var(--rust-deep); }

/* the night star-chart */
.sa-chart-frame {
  position: relative; border: 1px solid var(--line); background: var(--card); padding: 12px;
  box-shadow: 0 24px 46px -30px rgba(36,29,24,.55);
}
.sa-chart-frame::before {
  content: ""; position: absolute; inset: -14px; z-index: -1;
  background: radial-gradient(closest-side, rgba(192,86,42,.13), transparent 72%);
}
.sa-chart {
  position: relative; overflow: hidden; aspect-ratio: 11/13;
  background: radial-gradient(120% 90% at 30% 8%, #1b333c 0%, var(--night) 46%, #0d181d 100%);
}
@media (min-width: 900px) { .sa-chart { aspect-ratio: auto; height: 432px; } }
.sa-chart-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.sa-chart-tag {
  position: absolute; font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  color: var(--star-ink); background: rgba(9,17,21,.6); padding: 3px 7px;
  border: 1px solid rgba(234,224,203,.14); z-index: 2;
}
.sa-chart-tag.tl { left: 12px; top: 12px; color: var(--brass-soft); }
.sa-chart-tag.br { right: 12px; bottom: 12px; }
.sa-chart-foot { display: flex; align-items: center; justify-content: space-between; padding: 11px 4px 2px; }
.sa-cap { font-family: var(--serif); font-size: 1.15rem; color: var(--ink); }
.sa-sub { font-size: 11.5px; color: var(--ink-faint); margin-top: 1px; }
.sa-n { font-family: var(--mono); font-size: 12px; color: var(--teal); }

.sa-bgstars circle { animation: sa-tw 4s ease-in-out infinite; }
.sa-bgstars circle:nth-child(3n) { animation-delay: 1.3s; }
.sa-bgstars circle:nth-child(3n+1) { animation-delay: 2.6s; }
@keyframes sa-tw { 0%,100% { opacity: .85; } 50% { opacity: .2; } }
.sa-route { fill: none; stroke: var(--brass); stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; opacity: .85; }
.sa-transfer { stroke-dasharray: 2 7; stroke-opacity: .55; }
.sa-node { fill: var(--brass); }
.sa-halo { fill: var(--brass); opacity: .18; }
.sa-nlabel { font-family: var(--mono); font-size: 11px; fill: var(--star-ink); opacity: .82; }
.sa-nlabel.end { text-anchor: end; }

/* ── Planner ── */
.sa-form-section { padding: 30px 0 8px; }
.sa-panel {
  max-width: 860px; margin: 0 auto; border: 1px solid var(--line); background: var(--paper-2);
  box-shadow: 0 24px 46px -30px rgba(36,29,24,.5); padding: 8px 24px 26px;
  transition: min-height .3s ease;
}
@media (min-width: 768px) { .sa-panel { padding: 8px 40px 32px; } }

.sa-step { padding: 22px 0; border-top: 1px solid var(--line-2); }
.sa-step:first-child { border-top: none; }
.sa-step-head { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.sa-step-no {
  font-family: var(--mono); font-size: 12px; color: var(--rust);
  border: 1px solid var(--rust); border-radius: 50%; width: 26px; height: 26px;
  display: grid; place-items: center;
}
.sa-step-head h3 { margin: 0; font-family: var(--serif); font-size: 1.3rem; font-weight: 500; color: var(--ink); }

.sa-field-label { font-size: 12px; color: var(--ink-soft); }

.sa-city-list { margin-bottom: 6px; }
.sa-city-row { display: grid; grid-template-columns: 1fr 118px auto; gap: 12px; align-items: start; }
.sa-city-name, .sa-city-days { margin-bottom: 8px !important; }
.sa-city-remove {
  align-self: center; margin-top: 20px; width: 40px; height: 40px; flex: none;
  border: 1px solid var(--line); background: var(--card); border-radius: 2px;
  color: var(--ink-soft); font-size: 20px; line-height: 1; cursor: pointer; transition: .2s;
}
.sa-city-remove:hover { border-color: var(--rust); color: var(--rust); }
.sa-city-add {
  margin-top: 2px; width: 100%; background: none; border: 1px dashed var(--line); border-radius: 2px;
  color: var(--ink-soft); padding: 10px 14px; font-size: 13px; font-family: inherit; cursor: pointer; transition: .2s;
}
.sa-city-add:hover { border-color: var(--rust); color: var(--rust); }

.sa-grid { display: grid; gap: 14px; }
.sa-grid-date, .sa-grid2 { grid-template-columns: 1fr; }
@media (min-width: 640px) { .sa-grid-date, .sa-grid2 { grid-template-columns: 1fr 1fr; } }

.sa-days-chip {
  display: flex; align-items: baseline; gap: 8px; height: 40px; padding: 0 16px;
  background: var(--card); border: 1px solid var(--line); border-radius: 2px;
}
.sa-days-number { font-family: var(--mono); font-size: 1.5rem; color: var(--rust); }
.sa-days-unit { font-size: 12px; color: var(--ink-faint); }

.sa-interest-group { display: flex; flex-wrap: wrap; gap: 8px; width: 100%; }
.sa-pill {
  border: 1px solid var(--line); background: var(--card); border-radius: 2px;
  padding: 8px 16px; font-size: 13px; color: var(--ink-soft); cursor: pointer; transition: .18s; user-select: none;
}
.sa-pill:hover { border-color: var(--ink-faint); }
.sa-pill.on { background: var(--rust); border-color: var(--rust); color: var(--paper); }

.sa-submit {
  margin-top: 22px; width: 100%; display: inline-flex; align-items: center; justify-content: center;
  gap: 10px; border: none; border-radius: 2px; background: var(--rust); color: var(--paper);
  padding: 15px; font-size: 15px; font-weight: 600; font-family: inherit; cursor: pointer; transition: background .2s;
}
.sa-submit:hover:not(:disabled) { background: var(--rust-deep); }
.sa-submit:disabled { opacity: .8; cursor: default; }
.sa-loading-row { display: inline-flex; align-items: center; gap: 10px; }
.sa-spin { width: 15px; height: 15px; border: 2px solid rgba(244,238,225,.4); border-top-color: var(--paper); border-radius: 50%; animation: sa-sp .7s linear infinite; }
@keyframes sa-sp { to { transform: rotate(360deg); } }

/* ── Constellation stepper ── */
.sa-stepper { padding: 24px 4px 8px; }
.sa-stepper-head { text-align: center; margin-bottom: 30px; }
.sa-stepper-title { margin: 0; font-family: var(--mono); font-size: 1rem; color: var(--rust); letter-spacing: .04em; }
.sa-stepper-sub { margin: 6px 0 0; color: var(--ink-soft); font-size: 13px; }

.sa-constellation {
  position: relative; display: grid; gap: 18px; grid-template-columns: 1fr;
  padding: 8px 0; max-width: 520px; margin: 0 auto;
}
@media (min-width: 680px) {
  .sa-constellation { grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .sa-const-line {
    position: absolute; top: 25px; left: 12%; right: 12%; height: 2px; z-index: 0;
    background: linear-gradient(to right, var(--brass) var(--fill), var(--line) var(--fill));
    transition: background .5s ease;
  }
}
.sa-const-line { display: none; }
@media (min-width: 680px) { .sa-const-line { display: block; } }

.sa-star-node { position: relative; z-index: 1; text-align: center; }
.sa-star-mark {
  width: 50px; height: 50px; margin: 0 auto; display: grid; place-items: center; border-radius: 50%;
  background: var(--card); border: 1px solid var(--line); color: var(--ink-faint); transition: .3s;
}
.sa-star-node.active .sa-star-mark { border-color: var(--rust); color: var(--rust); box-shadow: 0 0 0 4px rgba(192,86,42,.1); }
.sa-star-node.done .sa-star-mark { border-color: var(--brass); color: var(--night); background: var(--brass); }
.sa-star-text { margin: 12px 0 0; font-size: 12.5px; color: var(--ink-soft); line-height: 1.4; padding: 0 4px; }
.sa-star-node.active .sa-star-text, .sa-star-node.done .sa-star-text { color: var(--ink); }
.sa-spin-sm { width: 15px; height: 15px; border: 2px solid rgba(192,86,42,.25); border-top-color: var(--rust); border-radius: 50%; animation: sa-sp .7s linear infinite; }

.sa-stepper-foot { text-align: center; margin-top: 28px; }
.sa-stepper-foot h3 { margin: 0; font-family: var(--serif); font-size: 1.2rem; font-weight: 500; color: var(--ink); }
.sa-stepper-foot p { margin: 6px 0 0; font-size: 13px; color: var(--ink-soft); }

/* ── History ── */
.sa-history { padding: 48px 0 64px; }
.sa-history-panel { max-width: 1120px; margin: 0 auto; background: var(--card); border: 1px solid var(--line); padding: 24px; box-shadow: 0 24px 46px -34px rgba(36,29,24,.4); }
.sa-history-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.sa-history-eyebrow { margin: 0 0 6px; font-family: var(--mono); color: var(--rust); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; }
.sa-history-title { margin: 0; font-family: var(--serif); color: var(--ink); font-size: 1.6rem; font-weight: 500; }
.sa-history-loading { color: var(--ink-soft); padding: 12px 4px; }
.sa-history-list { display: grid; gap: 12px; }
.sa-history-item {
  width: 100%; border: 1px solid var(--line); background: var(--paper-2); color: inherit; padding: 18px 20px;
  text-align: left; display: flex; align-items: center; justify-content: space-between; gap: 18px;
  cursor: pointer; transition: transform .18s ease, border-color .18s ease, background .18s ease;
}
.sa-history-item:hover { transform: translateY(-1px); border-color: var(--rust); background: var(--card); }
.sa-history-item-main { min-width: 0; flex: 1; }
.sa-history-route { display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px; }
.sa-history-city { font-family: var(--serif); color: var(--ink); font-size: 1.3rem; }
.sa-history-date { color: var(--ink-soft); font-size: 14px; }
.sa-history-meta { margin: 8px 0 0; display: flex; flex-wrap: wrap; gap: 12px; font-family: var(--mono); color: var(--ink-faint); font-size: 12px; }
.sa-history-summary { margin: 10px 0 0; color: var(--ink-soft); font-size: 14px; line-height: 1.6; }
.sa-history-open { flex: none; color: var(--rust); font-size: 14px; font-weight: 600; white-space: nowrap; }

/* ── Footer ── */
.sa-footer { background: var(--night); color: var(--star-ink); }
.sa-foot-in { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; padding: 26px 22px; }
@media (min-width: 768px) { .sa-foot-in { padding: 28px 34px; } }
.sa-foot-brand { display: flex; align-items: center; gap: 10px; font-family: var(--serif); font-size: 1.3rem; }
.sa-foot-co { font-family: var(--mono); font-size: 11px; color: rgba(234,224,203,.45); }

@media (prefers-reduced-motion: reduce) {
  .sa-bgstars circle, .sa-spin, .sa-spin-sm { animation: none; }
}

/* ── Ant Design skin (targeted) ── */
:deep(.ant-input),
:deep(.ant-input-number),
:deep(.ant-input-number-input),
:deep(.ant-picker),
:deep(.ant-select .ant-select-selector),
:deep(textarea.ant-input) {
  background: var(--card) !important;
  border: 1px solid var(--line) !important;
  border-radius: 2px !important;
  color: var(--ink) !important;
  box-shadow: none !important;
}
:deep(.ant-input:focus),
:deep(.ant-input-focused),
:deep(.ant-input-number-focused),
:deep(.ant-picker-focused),
:deep(.ant-select-focused .ant-select-selector) {
  border-color: var(--rust) !important;
  box-shadow: 0 0 0 2px rgba(192,86,42,.12) !important;
}
:deep(.ant-input::placeholder),
:deep(textarea.ant-input::placeholder) { color: var(--ink-faint) !important; }
:deep(.ant-select-selection-item),
:deep(.ant-picker-input > input),
:deep(.ant-input-number-input) { color: var(--ink) !important; }
:deep(.ant-select-arrow),
:deep(.ant-picker-suffix) { color: var(--ink-faint) !important; }
:deep(.ant-form-item-explain-error) { color: var(--rust) !important; font-size: 12px; }
:deep(.sa-history-refresh.ant-btn) { color: var(--rust); padding-inline: 0; }
:deep(.ant-empty-description) { color: var(--ink-soft); }

/* ── NavBar skin (functionality untouched, appearance retinted) ── */
:deep(.landing-navbar) {
  background: rgba(244, 238, 225, .86) !important;
  border-bottom: 1px solid var(--line) !important;
  backdrop-filter: blur(10px);
}
:deep(.landing-brand) { color: var(--ink) !important; font-family: var(--serif); letter-spacing: .01em; }
:deep(.landing-nav .nav-link),
:deep(.landing-nav-btn) { color: var(--ink-soft) !important; }
:deep(.landing-nav .nav-link:hover),
:deep(.landing-nav-btn:hover) { color: var(--ink) !important; }
:deep(.landing-cta.btn-danger) {
  background: var(--rust) !important; border-color: var(--rust) !important; color: var(--paper) !important;
}
:deep(.landing-cta.btn-danger:hover) { background: var(--rust-deep) !important; border-color: var(--rust-deep) !important; }
:deep(.navbar-toggler-bar) { background: var(--ink) !important; }
:deep(.lang-select-nav .ant-select-selector) {
  background: var(--card) !important; border: 1px solid var(--line) !important; color: var(--ink) !important;
}
:deep(.lang-select-nav .ant-select-selection-item),
:deep(.lang-select-nav .ant-select-arrow) { color: var(--ink) !important; }
</style>
