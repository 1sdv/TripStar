<template>
  <div class="home-container">
    <!-- 动态星空粒子背景 -->
    <div class="starfield">
      <div v-for="n in 60" :key="n" class="star" :style="starStyle(n)"></div>
    </div>

    <!-- 渐变光晕装饰 -->
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>
    <div class="glow glow-3"></div>

    <!-- 页面主内容 -->
    <div class="page-content">
      <!-- Hero 区域 -->
      <div class="hero-section">
        <div class="hero-badge">
          <span>{{ t('home.heroBadge') }}</span>
        </div>
        <h1 class="hero-title">
          <span class="title-line">{{ t('home.titleLine1') }}</span>
          <span class="title-line title-accent">{{ t('home.titleLine2') }}</span>
        </h1>
        <p class="hero-desc">{{ t('home.heroDesc') }}</p>
      </div>

      <!-- 表单主体 — 玻璃拟态卡片 -->
      <div class="glass-card">
        <a-form
          :model="formData"
          layout="vertical"
          @finish="handleSubmit"
        >
          <!-- Step 1: 目的地与日期 -->
          <div class="step-section">
            <div class="step-indicator">
              <span class="step-num">01</span>
              <span class="step-label">{{ t('home.step1') }}</span>
              <div class="step-line"></div>
            </div>

            <div class="fields-grid fields-4">
              <a-form-item name="city" :rules="formRules.city">
                <template #label>
                  <span class="field-label">{{ t('home.cityLabel') }}</span>
                </template>
                <a-input
                  v-model:value="formData.city"
                  :placeholder="t('home.cityPlaceholder')"
                  size="large"
                  class="dark-input"
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
                  class="dark-input"
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
                  class="dark-input"
                  :placeholder="t('home.endDatePlaceholder')"
                />
              </a-form-item>

              <a-form-item>
                <template #label>
                  <span class="field-label">{{ t('home.travelDaysLabel') }}</span>
                </template>
                <div class="days-chip">
                  <span class="days-number">{{ formData.travel_days }}</span>
                  <span class="days-text">{{ t('home.travelDaysUnit') }}</span>
                </div>
              </a-form-item>
            </div>
          </div>

          <!-- Step 2: 偏好设置 -->
          <div class="step-section">
            <div class="step-indicator">
              <span class="step-num">02</span>
              <span class="step-label">{{ t('home.step2') }}</span>
              <div class="step-line"></div>
            </div>

            <div class="fields-grid fields-2">
              <a-form-item name="transportation">
                <template #label>
                  <span class="field-label">{{ t('home.transportationLabel') }}</span>
                </template>
                <a-select v-model:value="formData.transportation" size="large" class="dark-select">
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
                <a-select v-model:value="formData.accommodation" size="large" class="dark-select">
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
                    class="interest-card"
                    :class="{ active: formData.preferences.includes(item.value) }"
                    @click.prevent="togglePreference(item.value)"
                  >
                    <span class="interest-name">{{ t(item.labelKey) }}</span>
                  </label>
                </a-checkbox-group>
              </div>
            </a-form-item>
          </div>

          <!-- Step 3: 额外需求 -->
          <div class="step-section">
            <div class="step-indicator">
              <span class="step-num">03</span>
              <span class="step-label">{{ t('home.step3') }}</span>
              <div class="step-line"></div>
            </div>

            <a-form-item name="free_text_input">
              <a-textarea
                v-model:value="formData.free_text_input"
                :placeholder="t('home.specialNeedsPlaceholder')"
                :rows="3"
                size="large"
                class="dark-textarea"
              />
            </a-form-item>
          </div>

          <!-- 提交按钮 -->
          <a-form-item>
            <button
              type="submit"
              class="submit-btn"
              :class="{ loading: loading }"
              :disabled="loading"
            >
              <span v-if="!loading" class="btn-content">
                <span>{{ t('home.submit') }}</span>
              </span>
              <span v-else class="btn-content">
                <span class="btn-spinner"></span>
                <span>{{ t('home.submitting') }}</span>
              </span>
            </button>
          </a-form-item>

          <!-- 加载进度 -->
          <div v-if="loading" class="progress-section">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: loadingProgress + '%' }"></div>
            </div>
            <p class="progress-text">{{ loadingStatus }}</p>
          </div>
        </a-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { generateTripPlan, getOrCreateUserId } from '@/services/api'
import { getCurrentLocale } from '@/i18n'
import type { TripFormData, TripTaskEvent } from '@/types'
import type { Dayjs } from 'dayjs'

const router = useRouter()
const { t } = useI18n()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

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
  city: [{ required: true, message: t('home.cityRequired') }],
  startDate: [{ required: true, message: t('home.startDateRequired') }],
  endDate: [{ required: true, message: t('home.endDateRequired') }],
}))

type HomeFormData = Omit<TripFormData, 'start_date' | 'end_date'> & {
  start_date: Dayjs | null
  end_date: Dayjs | null
}

const formData = reactive<HomeFormData>({
  city: '',
  start_date: null,
  end_date: null,
  travel_days: 1,
  transportation: '公共交通',
  accommodation: '经济型酒店',
  preferences: [],
  free_text_input: ''
})

const togglePreference = (value: string) => {
  const idx = formData.preferences.indexOf(value)
  if (idx === -1) {
    formData.preferences.push(value)
  } else {
    formData.preferences.splice(idx, 1)
  }
}

// 星空粒子随机样式
const starStyle = (_n: number) => {
  const size = Math.random() * 3 + 1
  return {
    width: size + 'px',
    height: size + 'px',
    top: Math.random() * 100 + '%',
    left: Math.random() * 100 + '%',
    animationDelay: Math.random() * 5 + 's',
    animationDuration: (Math.random() * 3 + 2) + 's',
  }
}

// 监听日期变化,自动计算旅行天数
watch([() => formData.start_date, () => formData.end_date], ([start, end]) => {
  if (start && end) {
    const days = end.diff(start, 'day') + 1
    if (days > 0 && days <= 30) {
      formData.travel_days = days
    } else if (days > 30) {
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
  loadingProgress.value = 5
  loadingStatus.value = t('home.loading.initializing')

  try {
    sessionStorage.removeItem('tripPlan')
    sessionStorage.removeItem('graphData')
    sessionStorage.removeItem('planId')

    const requestData: TripFormData = {
      city: formData.city,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: formData.end_date.format('YYYY-MM-DD'),
      travel_days: formData.travel_days,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      free_text_input: formData.free_text_input,
      language: getCurrentLocale(),
      user_id: getOrCreateUserId(),
    }

    const response = await generateTripPlan(requestData, {
      onTaskEvent: (event) => {
        if (Number.isFinite(event.progress)) {
          loadingProgress.value = Math.max(0, Math.min(100, event.progress))
        }
        loadingStatus.value = event.message || getStageStatusText(event.stage)
      }
    })

    loadingProgress.value = 100
    loadingStatus.value = t('home.loading.done')

    if (response.success && response.data) {
      const planId = response.plan_id || ''
      // 保存到sessionStorage
      sessionStorage.setItem('tripPlan', JSON.stringify(response.data))
      // 保存知识图谱数据
      if (response.graph_data) {
        sessionStorage.setItem('graphData', JSON.stringify(response.graph_data))
      }
      if (planId) {
        sessionStorage.setItem('planId', planId)
      }

      message.success(t('home.messages.generateSuccess'))

      // 短暂延迟后跳转
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
    }, 1000)
  }
}
</script>

<style scoped>
/* ===== 暗黑奢华主题 - 首页 ===== */

.home-container {
  min-height: 100vh;
  background: linear-gradient(160deg, #0a0a0f 0%, #12101f 30%, #1a1530 60%, #0f0d1a 100%);
  padding: 60px 24px 80px;
  position: relative;
  overflow: hidden;
}

/* 星空粒子 */
.starfield {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.star {
  position: absolute;
  background: #fff;
  border-radius: 50%;
  opacity: 0;
  animation: twinkle linear infinite;
}

@keyframes twinkle {
  0%, 100% { opacity: 0; }
  50% { opacity: 0.8; }
}

/* 渐变光晕 */
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
}

.glow-1 {
  width: 500px;
  height: 500px;
  top: -150px;
  left: -100px;
  background: rgba(255, 152, 0, 0.08);
}

.glow-2 {
  width: 400px;
  height: 400px;
  top: 40%;
  right: -80px;
  background: rgba(156, 39, 176, 0.06);
}

.glow-3 {
  width: 350px;
  height: 350px;
  bottom: -80px;
  left: 30%;
  background: rgba(0, 188, 212, 0.05);
}

/* 页面内容 */
.page-content {
  max-width: 900px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

/* Hero 区域 */
.hero-section {
  text-align: center;
  margin-bottom: 56px;
  animation: fadeUp 0.8s ease-out;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 179, 71, 0.08);
  border: 1px solid rgba(255, 179, 71, 0.2);
  padding: 8px 20px;
  border-radius: 24px;
  color: #FFD699;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 28px;
  letter-spacing: 0.05em;
}

.hero-title {
  margin: 0 0 20px;
  line-height: 1.15;
}

.title-line {
  display: block;
  font-size: 52px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.92);
  letter-spacing: -0.02em;
}

.title-accent {
  background: linear-gradient(135deg, #FFB347 0%, #FF6B6B 50%, #C084FC 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-desc {
  font-size: 17px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
  font-weight: 400;
  letter-spacing: 0.02em;
}

/* 玻璃拟态卡片 */
.glass-card {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  padding: 48px;
  box-shadow:
    0 24px 80px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  animation: fadeUp 0.8s ease-out 0.2s both;
}

/* Step 分区 */
.step-section {
  margin-bottom: 40px;
}

.step-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.step-num {
  font-size: 14px;
  font-weight: 700;
  color: #FFB347;
  background: rgba(255, 179, 71, 0.12);
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.step-label {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.02em;
}

.step-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(255, 179, 71, 0.3) 0%, transparent 100%);
}

/* 字段网格 */
.fields-grid {
  display: grid;
  gap: 20px;
}

.fields-4 {
  grid-template-columns: 1.5fr 1fr 1fr 0.8fr;
}

.fields-2 {
  grid-template-columns: 1fr 1fr;
}

/* 表单标签 */
.field-label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.55);
  letter-spacing: 0.04em;
}

/* 暗色输入框 */
.dark-input.ant-input,
.dark-input.ant-picker {
  background: rgba(255, 255, 255, 0.06) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 12px !important;
  color: rgba(255, 255, 255, 0.9) !important;
  transition: all 0.3s ease;
}

.dark-input.ant-input::placeholder,
:deep(.dark-input .ant-picker-input > input::placeholder) {
  color: rgba(255, 255, 255, 0.25) !important;
}

.dark-input.ant-input:hover,
.dark-input.ant-picker:hover {
  border-color: rgba(255, 179, 71, 0.3) !important;
  background: rgba(255, 255, 255, 0.08) !important;
}

.dark-input.ant-input:focus,
.dark-input.ant-picker-focused {
  border-color: #FFB347 !important;
  background: rgba(255, 255, 255, 0.08) !important;
  box-shadow: 0 0 0 3px rgba(255, 179, 71, 0.12) !important;
}

.dark-input.ant-input:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 1000px #1a1530 inset !important;
  -webkit-text-fill-color: rgba(255, 255, 255, 0.9) !important;
}

:deep(.dark-input .ant-picker-suffix),
:deep(.dark-input .ant-picker-clear) {
  color: rgba(255, 255, 255, 0.3) !important;
}

:deep(.dark-input .ant-picker-input > input) {
  color: rgba(255, 255, 255, 0.9) !important;
}

:deep(.dark-input .ant-picker-input > input:-webkit-autofill) {
  -webkit-box-shadow: 0 0 0 1000px #1a1530 inset !important;
  -webkit-text-fill-color: rgba(255, 255, 255, 0.9) !important;
}

/* 暗色选择框 */
.dark-select :deep(.ant-select-selector) {
  background: rgba(255, 255, 255, 0.06) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 12px !important;
  color: rgba(255, 255, 255, 0.9) !important;
  transition: all 0.3s ease;
}

.dark-select :deep(.ant-select-selection-item) {
  color: rgba(255, 255, 255, 0.9) !important;
}

.dark-select :deep(.ant-select-arrow) {
  color: rgba(255, 255, 255, 0.3) !important;
}

.dark-select:hover :deep(.ant-select-selector) {
  border-color: rgba(255, 179, 71, 0.3) !important;
}

.dark-select :deep(.ant-select-focused .ant-select-selector) {
  border-color: #FFB347 !important;
  box-shadow: 0 0 0 3px rgba(255, 179, 71, 0.12) !important;
}

/* 天数芯片 */
.days-chip {
  display: flex;
  align-items: center; /* Changed from baseline to center */
  justify-content: center;
  gap: 4px;
  height: 48px; /* Matched to dark-input's large size */
  padding: 0 20px;
  background: linear-gradient(135deg, #FFB347 0%, #FF6B6B 100%);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(255, 179, 71, 0.3);
}

.days-number {
  font-size: 22px;
  font-weight: 800;
  color: white;
  line-height: 1; /* Reset line-height to fix vertical shift */
}

.days-text {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.2; /* Better alignment with number */
  margin-top: 4px; /* Slight visual tweak offset */
}

/* 兴趣标签卡片 */
.interest-grid {
  width: 100%;
}

.interest-group {
  display: grid !important;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  width: 100%;
}

.interest-group :deep(.ant-checkbox-wrapper) {
  display: none !important;
}

.interest-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.interest-card:hover {
  border-color: rgba(255, 179, 71, 0.3);
  background: rgba(255, 179, 71, 0.06);
  transform: translateY(-2px);
}

.interest-card.active {
  border-color: #FFB347;
  background: rgba(255, 179, 71, 0.12);
  box-shadow: 0 0 20px rgba(255, 179, 71, 0.15);
}

.interest-name {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
}

.interest-card.active .interest-name {
  color: #FFD699;
}

/* 暗色文本域 */
.dark-textarea :deep(.ant-input) {
  background: rgba(255, 255, 255, 0.06) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 12px !important;
  color: rgba(255, 255, 255, 0.9) !important;
  transition: all 0.3s ease;
}

.dark-textarea :deep(.ant-input::placeholder) {
  color: rgba(255, 255, 255, 0.25) !important;
}

.dark-textarea :deep(.ant-input:hover) {
  border-color: rgba(255, 179, 71, 0.3) !important;
}

.dark-textarea :deep(.ant-input:focus) {
  border-color: #FFB347 !important;
  box-shadow: 0 0 0 3px rgba(255, 179, 71, 0.12) !important;
}

/* 提交按钮 */
.submit-btn {
  width: 100%;
  height: 60px;
  border: none;
  border-radius: 16px;
  cursor: pointer;
  font-family: inherit;
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(135deg, #FFB347 0%, #FF6B6B 50%, #C084FC 100%);
  background-size: 200% 200%;
  color: white;
  position: relative;
  overflow: hidden;
  transition: all 0.4s ease;
  box-shadow: 0 8px 32px rgba(255, 107, 107, 0.3);
  animation: gradientShift 4s ease infinite;
}

@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(255, 107, 107, 0.4);
}

.submit-btn:active {
  transform: translateY(0);
}

.submit-btn.loading {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: none;
  cursor: wait;
  animation: none;
}

.btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.btn-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFB347;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 进度条 */
.progress-section {
  margin-top: 24px;
  animation: fadeUp 0.4s ease-out;
}

.progress-track {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #FFB347, #FF6B6B, #C084FC);
  border-radius: 3px;
  transition: width 0.5s ease;
  box-shadow: 0 0 12px rgba(255, 179, 71, 0.4);
}

.progress-text {
  margin-top: 12px;
  text-align: center;
  color: #FFD699;
  font-size: 15px;
  font-weight: 500;
}

/* 动画 */
@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Ant Design 全局暗色适配 */
:deep(.ant-form-item-label > label) {
  color: rgba(255, 255, 255, 0.55) !important;
}

:deep(.ant-form-item-explain-error) {
  color: #FF6B6B !important;
}

/* 响应式 */
@media (max-width: 768px) {
  .home-container {
    padding: 32px 16px;
  }

  .glass-card {
    padding: 28px 20px;
  }

  .title-line {
    font-size: 36px;
  }

  .fields-4 {
    grid-template-columns: 1fr;
  }

  .fields-2 {
    grid-template-columns: 1fr;
  }

  .interest-group {
    grid-template-columns: repeat(3, 1fr) !important;
  }
}
</style>
