<template>
  <div class="result-container">
    <div class="lower-shade"></div>

    <NavBar @brand-click="goBack" @cta-click="goBack" />

    <main class="result-main">
      <div v-if="tripPlan" class="content-wrapper">
        <div class="top-switch-nav">
          <div class="top-switch-menu-wrap">
            <a-menu class="top-switch-menu" mode="horizontal" :selected-keys="[activeSection]" @click="scrollToSection">
              <a-menu-item key="overview">
                <span>{{ t('result.side.overview') }}</span>
              </a-menu-item>
              <a-menu-item key="budget" v-if="tripPlan.budget">
                <span>{{ t('result.side.budget') }}</span>
              </a-menu-item>
              <a-menu-item key="map">
                <span>{{ t('result.side.map') }}</span>
              </a-menu-item>
              <a-menu-item key="days">
                <span>{{ t('result.side.days') }}</span>
              </a-menu-item>
              <a-menu-item key="knowledge-graph">
                <span>{{ t('result.side.graph') }}</span>
              </a-menu-item>
              <a-menu-item key="weather" v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0">
                <span>{{ t('result.side.weather') }}</span>
              </a-menu-item>
            </a-menu>
          </div>

          <div class="top-switch-actions">
            <a-space size="middle" wrap>
              <a-button v-if="!editMode" @click="toggleEditMode" type="default">
                {{ t('result.editTrip') }}
              </a-button>
              <a-button v-else @click="saveChanges" type="primary">
                {{ t('result.saveChanges') }}
              </a-button>
              <a-button v-if="editMode" @click="cancelEdit" type="default">
                {{ t('result.cancelEdit') }}
              </a-button>

              <a-dropdown v-if="!editMode">
                <template #overlay>
                  <a-menu>
                    <a-menu-item key="image" @click="exportAsImage">
                      {{ t('result.exportImage') }}
                    </a-menu-item>
                    <a-menu-item key="pdf" @click="exportAsPDF">
                      {{ t('result.exportPdf') }}
                    </a-menu-item>
                  </a-menu>
                </template>
                <a-button type="default">
                  {{ t('result.exportTrip') }} <DownOutlined />
                </a-button>
              </a-dropdown>
            </a-space>
          </div>
        </div>

      <!-- 主内容区 -->
        <a-card
          v-show="activeSection === 'overview'"
          id="overview"
          :bordered="false"
          class="overview-card section-shellless"
        >
          <div v-if="overviewAttractions.length > 0" ref="overviewSwiperContainerRef" class="overview-swiper">
            <div class="swiper">
              <div class="swiper-wrapper">
                <OverviewAttractionCard
                  v-for="(item, index) in overviewAttractions"
                  :key="`${item.dayArrayIndex}-${item.order}-${item.name}`"
                  :item="item"
                  :image-src="getAttractionImage(item.name, index)"
                  :active="activeOverviewCard === index"
                  @hover="setActiveOverviewCard(index)"
                  @image-error="handleImageError"
                  @select-day="goToDayFromOverview"
                />
              </div>
            </div>
          </div>
          <a-empty v-else :description="t('common.noData')" />
          <div class="overview-meta">
            <span class="overview-meta-item" style="color: #ffd5c6; font-weight: 700;">
              {{ t('result.dateRange', { start: tripPlan.start_date, end: tripPlan.end_date }) }}
            </span>
            <span v-if="tripPlan.overall_suggestions" class="overview-meta-item">
              {{ tripPlan.overall_suggestions }}
            </span>
          </div>
        </a-card>

        <!-- 顶部信息区:预算/地图 -->
        <div class="top-info-section" v-show="['budget', 'map'].includes(activeSection)">
          <div class="left-info" v-show="activeSection === 'budget'">
            <a-card
              v-show="activeSection === 'budget' && !!tripPlan.budget"
              id="budget"
              v-if="tripPlan.budget"
              :bordered="false"
              class="budget-card section-shellless"
            >
              <div class="budget-detail-panel">
                <div class="budget-toolbar">
                  <div class="budget-toolbar-item">
                    <span class="budget-toolbar-label">{{ t('result.budget.filterLabel') }}</span>
                    <a-select v-model:value="budgetFilterType" size="small" class="budget-select">
                      <a-select-option value="all">{{ t('result.budget.filterAll') }}</a-select-option>
                      <a-select-option value="attraction">{{ t('result.budget.attraction') }}</a-select-option>
                      <a-select-option value="hotel">{{ t('result.budget.hotel') }}</a-select-option>
                      <a-select-option value="meal">{{ t('result.budget.meal') }}</a-select-option>
                      <a-select-option value="transport">{{ t('result.budget.transport') }}</a-select-option>
                    </a-select>
                  </div>
                  <div class="budget-toolbar-item">
                    <span class="budget-toolbar-label">{{ t('result.budget.sortLabel') }}</span>
                    <a-select v-model:value="budgetSortMode" size="small" class="budget-select">
                      <a-select-option value="amountDesc">{{ t('result.budget.sortAmountDesc') }}</a-select-option>
                      <a-select-option value="amountAsc">{{ t('result.budget.sortAmountAsc') }}</a-select-option>
                      <a-select-option value="dayAsc">{{ t('result.budget.sortDayAsc') }}</a-select-option>
                      <a-select-option value="dayDesc">{{ t('result.budget.sortDayDesc') }}</a-select-option>
                    </a-select>
                  </div>
                </div>

                <div v-if="filteredBudgetItems.length > 0" class="budget-detail-list">
                  <div class="budget-detail-row budget-detail-header">
                    <span>{{ t('result.budget.detailType') }}</span>
                    <span>{{ t('result.budget.detailDay') }}</span>
                    <span>{{ t('result.budget.detailName') }}</span>
                    <span>{{ t('result.budget.detailAmount') }}</span>
                    <span>{{ t('result.budget.detailAction') }}</span>
                  </div>
                  <div
                    v-for="item in filteredBudgetItems"
                    :key="item.id"
                    class="budget-detail-row"
                  >
                    <span class="budget-detail-type">{{ getBudgetTypeLabel(item.type) }}</span>
                    <span class="budget-detail-day">
                      {{ item.dayNumber ? t('common.dayNumber', { day: item.dayNumber }) : '--' }}
                    </span>
                    <span class="budget-detail-name">{{ item.name }}</span>
                    <span class="budget-detail-amount">¥{{ formatBudgetAmount(item.amount) }}</span>
                    <span class="budget-action-wrap">
                      <button
                        type="button"
                        class="budget-icon-btn budget-edit-btn"
                        :title="t('result.budget.editPrice')"
                        @click="editBudgetItemAmount(item)"
                      >
                        <svg fill="currentColor" width="20px" height="20px" viewBox="0 0 256.00098 256.00098" id="Flat" xmlns="http://www.w3.org/2000/svg">
                          <path d="M216.001,203.833h-76l27.91015-27.90967.00684-.00635.00635-.00683,56.563-56.5625a28.03348,28.03348,0,0,0-.001-39.59766L179.23145,34.49512a28.03347,28.03347,0,0,0-39.59766,0L83.07471,91.0542l-.01026.00928-.00927.01025L26.49609,147.63281a28.03171,28.03171,0,0,0,0,39.59766L63.585,224.31836a12.00286,12.00286,0,0,0,8.48535,3.51465H216.001a12,12,0,0,0,0-24ZM156.60449,51.46582a4.00207,4.00207,0,0,1,5.65625,0L207.51562,96.7207a4.005,4.005,0,0,1,0,5.65723l-48.083,48.083L108.521,99.54932ZM106.05957,203.833H77.041L43.4668,170.25977a4.00385,4.00385,0,0,1,0-5.65625L91.55029,116.52l50.91114,50.91113Z"/>
                        </svg>
                      </button>
                      <button
                        type="button"
                        class="budget-icon-btn budget-delete-btn"
                        :title="t('common.delete')"
                        @click="deleteBudgetItem(item)"
                      >
                        <svg fill="currentColor" width="21px" height="21px" viewBox="0 0 256 256" id="Flat" xmlns="http://www.w3.org/2000/svg">
                          <path d="M215.99609,48H180V36A28.03146,28.03146,0,0,0,152,8H104A28.03146,28.03146,0,0,0,76,36V48H39.99609a12,12,0,0,0,0,24h4V208a20.0226,20.0226,0,0,0,20,20h128a20.0226,20.0226,0,0,0,20-20V72h4a12,12,0,0,0,0-24ZM100,36a4.00458,4.00458,0,0,1,4-4h48a4.00458,4.00458,0,0,1,4,4V48H100Zm87.99609,168h-120V72h120ZM116,104v64a12,12,0,0,1-24,0V104a12,12,0,0,1,24,0Zm48,0v64a12,12,0,0,1-24,0V104a12,12,0,0,1,24,0Z"/>
                        </svg>
                      </button>
                    </span>
                  </div>
                </div>
                <a-empty v-else :description="t('result.budget.noDetails')" />
              </div>
            </a-card>
          </div>

          <div class="right-budget-summary" v-show="activeSection === 'budget' && !!tripPlan.budget">
            <div class="budget-summary-panel">
              <div class="budget-summary-title">{{ t('result.budget.title') }}</div>
              <div class="budget-summary-total-wrap">
                <span class="budget-summary-currency">¥</span>
                <span class="budget-summary-total-value">{{ formatBudgetAmount(tripPlan.budget?.total ?? 0) }}</span>
              </div>
              <div class="budget-summary-sub-grid">
                <div class="budget-summary-sub-item">
                  <div class="budget-summary-sub-value">¥{{ formatBudgetAmount(tripPlan.budget?.total_attractions ?? 0) }}</div>
                  <div class="budget-summary-sub-label">{{ t('result.budget.attraction') }}</div>
                </div>
                <div class="budget-summary-sub-item">
                  <div class="budget-summary-sub-value">¥{{ formatBudgetAmount(tripPlan.budget?.total_hotels ?? 0) }}</div>
                  <div class="budget-summary-sub-label">{{ t('result.budget.hotel') }}</div>
                </div>
                <div class="budget-summary-sub-item">
                  <div class="budget-summary-sub-value">¥{{ formatBudgetAmount(tripPlan.budget?.total_meals ?? 0) }}</div>
                  <div class="budget-summary-sub-label">{{ t('result.budget.meal') }}</div>
                </div>
                <div class="budget-summary-sub-item">
                  <div class="budget-summary-sub-value">¥{{ formatBudgetAmount(tripPlan.budget?.total_transportation ?? 0) }}</div>
                  <div class="budget-summary-sub-label">{{ t('result.budget.transport') }}</div>
                </div>
              </div>

              <div class="budget-pending-wrap">
                <div class="budget-pending-title">{{ t('result.budget.pendingTitle') }}</div>
                <div v-if="pendingBudgetItems.length === 0" class="budget-pending-empty">
                  {{ t('result.budget.pendingEmpty') }}
                </div>
                <div v-else class="budget-pending-list">
                  <div
                    v-for="pendingItem in pendingBudgetItems"
                    :key="pendingItem.uid"
                    class="budget-pending-item"
                  >
                    <span class="budget-pending-name">{{ pendingItem.base.name }}</span>
                    <a-button
                      type="link"
                      size="small"
                      class="budget-restore-btn"
                      @click="restoreBudgetItem(pendingItem)"
                    >
                      {{ t('result.budget.restore') }}
                    </a-button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="right-map" v-show="activeSection === 'map'">
            <a-card id="map" :bordered="false" class="map-card section-shellless">
              <div id="amap-container" style="width: 100%; height: 100%"></div>
            </a-card>
          </div>
        </div>

        <!-- 知识图谱 -->
        <a-card v-show="activeSection === 'knowledge-graph'" id="knowledge-graph" :bordered="false" class="kg-card section-shellless">
          <div id="kg-chart-container" style="width: 100%; height: 600px;"></div>
          <div class="kg-legend">
            <span v-for="cat in graphCategories" :key="cat.name" class="kg-legend-item">
              <span class="kg-legend-dot" :style="{ background: getCategoryColor(cat.name) }"></span>
              {{ getCategoryLabel(cat.name) }}
            </span>
          </div>
        </a-card>

        <!-- 每日行程:可折叠 -->
        <a-card v-show="activeSection === 'days'" :bordered="false" class="days-card section-shellless">
          <a-collapse v-model:activeKey="activeDays" accordion>
            <a-collapse-panel
              v-for="(day, index) in tripPlan.days"
              :key="index"
              :id="`day-${index}`"
            >
              <template #header>
                <div class="day-header">
                  <span class="day-title">{{ t('common.dayNumber', { day: day.day_index + 1 }) }}</span>
                  <span class="day-date">{{ day.date }}</span>
                </div>
              </template>

              <!-- 行程基本信息 -->
              <div class="day-info">
                <div class="info-row">
                  <span class="label">{{ t('result.dayDescription') }}</span>
                  <span class="value">{{ day.description }}</span>
                </div>
                <div class="info-row">
                  <span class="label">{{ t('result.dayTransport') }}</span>
                  <span class="value">{{ day.transportation }}</span>
                </div>
                <div class="info-row">
                  <span class="label">{{ t('result.dayAccommodation') }}</span>
                  <span class="value">{{ day.accommodation }}</span>
                </div>
              </div>

              <!-- 景点安排 -->
              <a-divider orientation="left">{{ t('result.attractionTitle') }}</a-divider>
              <a-list
                :data-source="day.attractions"
                :grid="{ gutter: 16, column: 2 }"
              >
                <template #renderItem="{ item, index }">
                  <a-list-item>
                    <a-card :title="item.name" size="small" class="attraction-card">
                      <!-- 编辑模式下的操作按钮 -->
                      <template #extra v-if="editMode">
                        <a-space>
                          <a-button
                            size="small"
                            @click="moveAttraction(day.day_index, index, 'up')"
                            :disabled="index === 0"
                          >
                            Up
                          </a-button>
                          <a-button
                            size="small"
                            @click="moveAttraction(day.day_index, index, 'down')"
                            :disabled="index === day.attractions.length - 1"
                          >
                            Down
                          </a-button>
                          <a-button
                            size="small"
                            danger
                            @click="deleteAttraction(day.day_index, index)"
                          >
                            {{ t('common.delete') }}
                          </a-button>
                        </a-space>
                      </template>

                      <!-- 景点图片 -->
                      <div class="attraction-image-wrapper">
                        <img
                          :src="getAttractionImage(item.name, index)"
                          :alt="item.name"
                          class="attraction-image"
                          @error="handleImageError"
                        />
                        <div class="attraction-badge">
                          <span class="badge-number">{{ index + 1 }}</span>
                        </div>
                        <div v-if="item.ticket_price" class="price-tag">
                          ¥{{ item.ticket_price }}
                        </div>
                      </div>

                      <!-- 编辑模式下可编辑的字段 -->
                      <div v-if="editMode">
                        <p><strong>{{ t('result.fieldAddress') }}:</strong></p>
                        <a-input v-model:value="item.address" size="small" style="margin-bottom: 8px" />

                        <p><strong>{{ t('result.fieldVisitDurationMinutes') }}:</strong></p>
                        <a-input-number v-model:value="item.visit_duration" :min="10" :max="480" size="small" style="width: 100%; margin-bottom: 8px" />

                        <p><strong>{{ t('result.fieldDescription') }}:</strong></p>
                        <a-textarea v-model:value="item.description" :rows="2" size="small" style="margin-bottom: 8px" />
                      </div>

                      <!-- 查看模式 -->
                      <div v-else>
                        <p><strong>{{ t('result.fieldAddress') }}:</strong> {{ item.address }}</p>
                        <p><strong>{{ t('result.fieldVisitDuration') }}:</strong> {{ item.visit_duration }}{{ t('result.minuteUnit') }}</p>
                        <p><strong>{{ t('result.fieldDescription') }}:</strong> {{ item.description }}</p>
                        <p v-if="item.rating"><strong>{{ t('result.fieldRating') }}:</strong> {{ item.rating }}</p>
                      </div>
                    </a-card>
                  </a-list-item>
                </template>
              </a-list>

              <!-- 酒店推荐 -->
              <a-divider v-if="day.hotel" orientation="left">{{ t('result.hotelTitle') }}</a-divider>
              <a-card v-if="day.hotel" size="small" class="hotel-card">
                <template #title>
                  <span class="hotel-title">{{ day.hotel.name }}</span>
                </template>
                <a-descriptions :column="2" size="small">
                  <a-descriptions-item :label="t('result.fieldAddress')">{{ day.hotel.address }}</a-descriptions-item>
                  <a-descriptions-item :label="t('result.fieldType')">{{ day.hotel.type }}</a-descriptions-item>
                  <a-descriptions-item :label="t('result.fieldPriceRange')">{{ day.hotel.price_range }}</a-descriptions-item>
                  <a-descriptions-item :label="t('result.fieldRating')">{{ day.hotel.rating }}</a-descriptions-item>
                  <a-descriptions-item :label="t('result.fieldDistance')" :span="2">{{ day.hotel.distance }}</a-descriptions-item>
                </a-descriptions>
              </a-card>

              <!-- 餐饮安排 -->
              <a-divider orientation="left">{{ t('result.mealsTitle') }}</a-divider>
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item
                  v-for="meal in day.meals"
                  :key="meal.type"
                  :label="getMealLabel(meal.type)"
                >
                  {{ meal.name }}
                  <span v-if="meal.description"> - {{ meal.description }}</span>
                </a-descriptions-item>
              </a-descriptions>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <a-card
          v-show="activeSection === 'weather' && tripPlan.weather_info && tripPlan.weather_info.length > 0"
          id="weather"
          v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0"
          style="margin-top: 20px"
          :bordered="false"
          class="section-shellless weather-section-card"
        >
        <a-list
          :data-source="tripPlan.weather_info"
          :grid="{ gutter: 16, column: 3 }"
        >
          <template #renderItem="{ item }">
            <a-list-item>
              <a-card size="small" class="weather-card">
                <div class="weather-date">{{ item.date }}</div>
                <div class="weather-info-row">
                  <div>
                    <div class="weather-label">{{ t('result.weatherDay') }}</div>
                    <div class="weather-value">{{ item.day_weather }} {{ item.day_temp }}°C</div>
                  </div>
                </div>
                <div class="weather-info-row">
                  <div>
                    <div class="weather-label">{{ t('result.weatherNight') }}</div>
                    <div class="weather-value">{{ item.night_weather }} {{ item.night_temp }}°C</div>
                  </div>
                </div>
                <div class="weather-wind">
                  {{ item.wind_direction }} {{ item.wind_power }}
                </div>
              </a-card>
            </a-list-item>
          </template>
        </a-list>
        </a-card>
      </div>

      <div v-else class="empty-state-panel">
        <a-empty :description="t('result.noTripPlan')">
          <template #description>
            <span class="empty-desc">{{ t('result.noTripPlanDesc') }}</span>
          </template>
          <a-button class="empty-back-btn" type="primary" @click="goBack">{{ t('result.backCreateTrip') }}</a-button>
        </a-empty>
      </div>
    </main>

    <!-- 回到顶部按钮 -->
    <a-back-top :visibility-height="300">
      <div class="back-top-button">
        Top
      </div>
    </a-back-top>

    <AIChat :trip-plan="tripPlan" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import * as echarts from 'echarts'
import Swiper from 'swiper'
import { EffectCoverflow, Keyboard, Mousewheel } from 'swiper/modules'
import NavBar from '@/components/NavBar.vue'
import OverviewAttractionCard from '@/components/OverviewAttractionCard.vue'
import AIChat from '@/components/AIChat.vue'
import type { TripPlan, KnowledgeGraphData, GraphCategory, Attraction, Meal, Hotel } from '@/types'

const router = useRouter()
const { t } = useI18n()
const tripPlan = ref<TripPlan | null>(null)
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const attractionPhotos = ref<Record<string, string>>({})
const activeSection = ref('overview')
const activeDays = ref<number[]>([0]) // 默认展开第一天
const activeOverviewCard = ref(1)
const overviewSwiperContainerRef = ref<HTMLElement | null>(null)
let map: any = null
let overviewSwiper: Swiper | null = null

type OverviewAttractionItem = {
  name: string
  address: string
  visit_duration: number
  description: string
  ticket_price?: number
  dayNumber: number
  dayArrayIndex: number
  order: number
}

type BudgetItemType = 'attraction' | 'hotel' | 'meal' | 'transport'
type BudgetSortMode = 'amountDesc' | 'amountAsc' | 'dayAsc' | 'dayDesc'

type BudgetDetailItem = {
  id: string
  type: BudgetItemType
  dayIndex: number | null
  dayNumber: number | null
  name: string
  amount: number
  sourceIndex?: number
}

type BudgetRestorePayload =
  | {
      type: 'attraction'
      attraction: Attraction
      insertIndex: number
    }
  | {
      type: 'meal'
      meal: Meal
      insertIndex: number
    }
  | {
      type: 'hotel'
      hotel: Hotel
      accommodation: string
    }
  | {
      type: 'transport'
      transportation: string
    }

type BudgetRestoreItem = {
  uid: string
  base: BudgetDetailItem
  payload: BudgetRestorePayload
}

const budgetFilterType = ref<'all' | BudgetItemType>('all')
const budgetSortMode = ref<BudgetSortMode>('amountDesc')
const pendingBudgetItems = ref<BudgetRestoreItem[]>([])

const overviewAttractions = computed<OverviewAttractionItem[]>(() => {
  if (!tripPlan.value) return []

  const items: OverviewAttractionItem[] = []
  tripPlan.value.days.forEach((day, dayArrayIndex) => {
    const dayNumber =
      typeof day.day_index === 'number' && Number.isFinite(day.day_index)
        ? day.day_index + 1
        : dayArrayIndex + 1

    day.attractions.forEach((attraction, order) => {
      items.push({
        name: attraction.name,
        address: attraction.address,
        visit_duration: attraction.visit_duration,
        description: attraction.description,
        ticket_price: attraction.ticket_price,
        dayNumber,
        dayArrayIndex,
        order,
      })
    })
  })
  return items
})

const destroyOverviewSwiper = () => {
  if (overviewSwiper) {
    overviewSwiper.destroy(true, true)
    overviewSwiper = null
  }
}

const initOverviewSwiper = async () => {
  await nextTick()

  if (!overviewSwiperContainerRef.value || overviewAttractions.value.length === 0) {
    destroyOverviewSwiper()
    return
  }

  const root = overviewSwiperContainerRef.value.querySelector('.swiper') as HTMLElement | null
  if (!root) return

  destroyOverviewSwiper()
  overviewSwiper = new Swiper(root, {
    modules: [EffectCoverflow, Keyboard, Mousewheel],
    effect: 'coverflow',
    grabCursor: true,
    centeredSlides: true,
    coverflowEffect: {
      rotate: 0,
      stretch: 0,
      depth: 100,
      modifier: 2.5,
    },
    keyboard: {
      enabled: true,
    },
    mousewheel: {
      thresholdDelta: 70,
    },
    spaceBetween: 30,
    loop: false,
    breakpoints: {
      640: {
        slidesPerView: 3,
      },
      1024: {
        slidesPerView: 4,
      },
    },
    on: {
      slideChange: (swiper) => {
        activeOverviewCard.value = swiper.activeIndex
      },
    },
  })

  const initialIndex = Math.min(1, overviewAttractions.value.length - 1)
  activeOverviewCard.value = initialIndex
  overviewSwiper.slideTo(initialIndex, 0, false)
}

// 知识图谱相关
const graphData = ref<KnowledgeGraphData | null>(null)
const graphCategories = ref<GraphCategory[]>([])
let kgChart: echarts.ECharts | null = null

const ensureMapReady = async () => {
  await nextTick()
  if (!map) {
    await initMap()
    return
  }

  if (typeof map.resize === 'function') {
    map.resize()
  }
}

const ensureGraphReady = async () => {
  if (!graphData.value) return
  await nextTick()
  if (!kgChart) {
    initKnowledgeGraph()
    return
  }
  kgChart.resize()
}

const CATEGORY_KEY_MAP: Record<string, string> = {
  '城市': 'city',
  '都市': 'city',
  'city': 'city',
  '日程': 'schedule',
  '行程': 'schedule',
  'schedule': 'schedule',
  '景点': 'attraction',
  '観光地': 'attraction',
  'attraction': 'attraction',
  '酒店': 'hotel',
  'ホテル': 'hotel',
  'hotel': 'hotel',
  '餐饮': 'meal',
  '食事': 'meal',
  'meal': 'meal',
  '天气': 'weather',
  '天気': 'weather',
  'weather': 'weather',
  '预算': 'budget',
  '予算': 'budget',
  'budget': 'budget',
  '偏好/建议': 'suggestion',
  '好み/提案': 'suggestion',
  'preference/suggestion': 'suggestion',
}

const CATEGORY_COLORS: Record<string, string> = {
  city: '#4A90D9',
  schedule: '#5B8FF9',
  attraction: '#5AD8A6',
  hotel: '#F6BD16',
  meal: '#E8684A',
  weather: '#6DC8EC',
  budget: '#FF9845',
  suggestion: '#B37FEB',
}

const normalizeCategoryKey = (name: string): string => {
  const key = name.toLowerCase()
  return CATEGORY_KEY_MAP[name] || CATEGORY_KEY_MAP[key] || name
}

const getCategoryColor = (name: string): string => {
  const key = normalizeCategoryKey(name)
  return CATEGORY_COLORS[key] || '#999'
}

const getCategoryLabel = (name: string): string => {
  const key = normalizeCategoryKey(name)
  if (key in CATEGORY_COLORS) {
    return t(`result.graph.categories.${key}`)
  }
  return name
}

onMounted(async () => {
  const data = sessionStorage.getItem('tripPlan')
  if (data) {
    tripPlan.value = JSON.parse(data)
    pendingBudgetItems.value = []
    // 加载景点图片
    await loadAttractionPhotos()
    // 加载知识图谱
    const gd = sessionStorage.getItem('graphData')
    if (gd) {
      graphData.value = JSON.parse(gd)
      graphCategories.value = graphData.value?.categories || []
    }
    if (activeSection.value === 'map') await ensureMapReady()
    if (activeSection.value === 'knowledge-graph') await ensureGraphReady()
    if (activeSection.value === 'overview') await initOverviewSwiper()
  }
})

watch(activeSection, async (section) => {
  if (!tripPlan.value) return
  if (section === 'map') await ensureMapReady()
  if (section === 'knowledge-graph') await ensureGraphReady()
  if (section === 'overview') await initOverviewSwiper()
})

watch(
  overviewAttractions,
  (items) => {
    if (items.length === 0) {
      activeOverviewCard.value = -1
      return
    }
    if (activeOverviewCard.value < 0 || activeOverviewCard.value >= items.length) {
      activeOverviewCard.value = Math.min(1, items.length - 1)
    }
    if (activeSection.value === 'overview') {
      void initOverviewSwiper()
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  destroyOverviewSwiper()
  if (kgChart) {
    kgChart.dispose()
    kgChart = null
  }
})

const goBack = () => {
  router.push('/')
}

// 滚动到指定区域
const scrollToSection = ({ key }: { key: string }) => {
  if (key.startsWith('day-')) {
    const dayIndex = Number(key.replace('day-', ''))
    if (!Number.isNaN(dayIndex)) {
      activeDays.value = [dayIndex]
      activeSection.value = 'days'
      return
    }
  }

  activeSection.value = key
}

const goToDayFromOverview = (dayArrayIndex: number) => {
  activeDays.value = [dayArrayIndex]
  activeSection.value = 'days'
}

const setActiveOverviewCard = (index: number) => {
  activeOverviewCard.value = index
  if (overviewSwiper && overviewSwiper.activeIndex !== index) {
    overviewSwiper.slideTo(index)
  }
}

// 切换编辑模式
const toggleEditMode = () => {
  editMode.value = true
  // 保存原始数据用于取消编辑
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
  message.info(t('result.messages.enterEditMode'))
}

// 保存修改
const saveChanges = () => {
  editMode.value = false
  recalculateBudgetTotals()
  // 更新sessionStorage
  if (tripPlan.value) {
    sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  }
  message.success(t('result.messages.changesSaved'))

  // 重新初始化地图以反映更改
  if (map) {
    map.destroy()
    map = null
  }
  if (activeSection.value === 'map') {
    nextTick(() => {
      initMap()
    })
  }
}

// 取消编辑
const cancelEdit = () => {
  if (originalPlan.value) {
    tripPlan.value = JSON.parse(JSON.stringify(originalPlan.value))
  }
  pendingBudgetItems.value = []
  editMode.value = false
  message.info(t('result.messages.editCanceled'))
}

// 删除景点
const deleteAttraction = (dayIndex: number, attrIndex: number) => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  if (day.attractions.length <= 1) {
    message.warning(t('result.messages.keepOneAttraction'))
    return
  }

  day.attractions.splice(attrIndex, 1)
  recalculateBudgetTotals()
  message.success(t('result.messages.attractionDeleted'))
}

// 移动景点顺序
const moveAttraction = (dayIndex: number, attrIndex: number, direction: 'up' | 'down') => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  const attractions = day.attractions

  if (direction === 'up' && attrIndex > 0) {
    [attractions[attrIndex], attractions[attrIndex - 1]] = [attractions[attrIndex - 1], attractions[attrIndex]]
  } else if (direction === 'down' && attrIndex < attractions.length - 1) {
    [attractions[attrIndex], attractions[attrIndex + 1]] = [attractions[attrIndex + 1], attractions[attrIndex]]
  }
}

const getMealLabel = (type: string): string => {
  const labels: Record<string, string> = {
    breakfast: t('result.meals.breakfast'),
    lunch: t('result.meals.lunch'),
    dinner: t('result.meals.dinner'),
    snack: t('result.meals.snack')
  }
  return labels[type] || type
}

const toBudgetNumber = (value: unknown): number => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) return 0
  return numeric
}

const roundBudgetAmount = (value: number): number => {
  return Math.round((value + Number.EPSILON) * 100) / 100
}

const formatBudgetAmount = (value: number): string => {
  const rounded = roundBudgetAmount(value)
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2)
}

const getBudgetTypeLabel = (type: BudgetItemType): string => {
  const labels: Record<BudgetItemType, string> = {
    attraction: t('result.budget.attraction'),
    hotel: t('result.budget.hotel'),
    meal: t('result.budget.meal'),
    transport: t('result.budget.transport'),
  }
  return labels[type]
}

const cloneData = <T>(data: T): T => JSON.parse(JSON.stringify(data)) as T

const recalculateBudgetTotals = (transportationOverride?: number) => {
  if (!tripPlan.value) return

  let attractionTotal = 0
  let hotelTotal = 0
  let mealTotal = 0

  tripPlan.value.days.forEach((day) => {
    day.attractions.forEach((attraction) => {
      attractionTotal += toBudgetNumber(attraction.ticket_price)
    })

    if (day.hotel) {
      hotelTotal += toBudgetNumber(day.hotel.estimated_cost)
    }

    day.meals.forEach((meal) => {
      mealTotal += toBudgetNumber(meal.estimated_cost)
    })
  })

  const transportationTotal = roundBudgetAmount(
    transportationOverride ?? toBudgetNumber(tripPlan.value.budget?.total_transportation)
  )

  tripPlan.value.budget = {
    total_attractions: roundBudgetAmount(attractionTotal),
    total_hotels: roundBudgetAmount(hotelTotal),
    total_meals: roundBudgetAmount(mealTotal),
    total_transportation: transportationTotal,
    total: roundBudgetAmount(attractionTotal + hotelTotal + mealTotal + transportationTotal),
  }
}

const budgetItems = computed<BudgetDetailItem[]>(() => {
  if (!tripPlan.value) return []

  const items: BudgetDetailItem[] = []

  tripPlan.value.days.forEach((day, dayIndex) => {
    const dayNumber = day.day_index + 1

    day.attractions.forEach((attraction, attractionIndex) => {
      const amount = roundBudgetAmount(toBudgetNumber(attraction.ticket_price))
      if (amount <= 0) return
      items.push({
        id: `attraction-${dayIndex}-${attractionIndex}`,
        type: 'attraction',
        dayIndex,
        dayNumber,
        name: attraction.name,
        amount,
        sourceIndex: attractionIndex,
      })
    })

    if (day.hotel) {
      const amount = roundBudgetAmount(toBudgetNumber(day.hotel.estimated_cost))
      if (amount > 0) {
        items.push({
          id: `hotel-${dayIndex}`,
          type: 'hotel',
          dayIndex,
          dayNumber,
          name: day.hotel.name,
          amount,
        })
      }
    }

    day.meals.forEach((meal, mealIndex) => {
      const amount = roundBudgetAmount(toBudgetNumber(meal.estimated_cost))
      if (amount <= 0) return
      items.push({
        id: `meal-${dayIndex}-${mealIndex}`,
        type: 'meal',
        dayIndex,
        dayNumber,
        name: `${getMealLabel(meal.type)} · ${meal.name}`,
        amount,
        sourceIndex: mealIndex,
      })
    })
  })

  const transportTotal = roundBudgetAmount(toBudgetNumber(tripPlan.value.budget?.total_transportation))
  const transportDays = tripPlan.value.days
    .map((day, dayIndex) => ({ day, dayIndex }))
    .filter(({ day }) => Boolean(day.transportation && day.transportation.trim()))

  if (transportTotal > 0 && transportDays.length > 0) {
    const avg = roundBudgetAmount(transportTotal / transportDays.length)
    let remaining = transportTotal

    transportDays.forEach(({ day, dayIndex }, index) => {
      const amount = index === transportDays.length - 1 ? remaining : Math.min(avg, remaining)
      remaining = roundBudgetAmount(remaining - amount)
      items.push({
        id: `transport-${dayIndex}`,
        type: 'transport',
        dayIndex,
        dayNumber: day.day_index + 1,
        name: day.transportation,
        amount: roundBudgetAmount(amount),
      })
    })
  }

  return items
})

const filteredBudgetItems = computed<BudgetDetailItem[]>(() => {
  let items = budgetItems.value

  if (budgetFilterType.value !== 'all') {
    items = items.filter((item) => item.type === budgetFilterType.value)
  }

  const sorted = [...items]
  sorted.sort((a, b) => {
    const dayA = a.dayNumber ?? Number.MAX_SAFE_INTEGER
    const dayB = b.dayNumber ?? Number.MAX_SAFE_INTEGER

    switch (budgetSortMode.value) {
      case 'amountAsc':
        return a.amount - b.amount
      case 'dayAsc':
        return dayA - dayB || b.amount - a.amount
      case 'dayDesc':
        return dayB - dayA || b.amount - a.amount
      case 'amountDesc':
      default:
        return b.amount - a.amount
    }
  })

  return sorted
})

const editBudgetItemAmount = (item: BudgetDetailItem) => {
  if (!tripPlan.value || item.dayIndex === null) return

  const day = tripPlan.value.days[item.dayIndex]
  if (!day) return

  const input = window.prompt(
    t('result.budget.editPrompt', {
      name: item.name,
      amount: formatBudgetAmount(item.amount),
    }),
    formatBudgetAmount(item.amount)
  )

  if (input === null) return

  const numeric = Number(input.trim())
  if (!Number.isFinite(numeric) || numeric < 0) {
    message.warning(t('result.messages.budgetInvalidAmount'))
    return
  }

  const nextAmount = roundBudgetAmount(numeric)
  if (nextAmount === roundBudgetAmount(item.amount)) return

  const confirmed = window.confirm(
    t('result.budget.editConfirm', {
      name: item.name,
      amount: formatBudgetAmount(nextAmount),
    })
  )
  if (!confirmed) return

  let changed = false

  if (item.type === 'attraction' && typeof item.sourceIndex === 'number' && day.attractions[item.sourceIndex]) {
    day.attractions[item.sourceIndex].ticket_price = nextAmount
    changed = true
  }

  if (item.type === 'meal' && typeof item.sourceIndex === 'number' && day.meals[item.sourceIndex]) {
    day.meals[item.sourceIndex].estimated_cost = nextAmount
    changed = true
  }

  if (item.type === 'hotel' && day.hotel) {
    day.hotel.estimated_cost = nextAmount
    changed = true
  }

  const transportationTotal =
    item.type === 'transport'
      ? Math.max(
          0,
          roundBudgetAmount(toBudgetNumber(tripPlan.value.budget?.total_transportation) - item.amount + nextAmount)
        )
      : undefined

  if (item.type === 'transport' && day.transportation && day.transportation.trim()) {
    changed = true
  }

  if (!changed) return

  recalculateBudgetTotals(transportationTotal)
  sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  message.success(t('result.messages.budgetAmountUpdated'))
}

const deleteBudgetItem = (item: BudgetDetailItem) => {
  if (!tripPlan.value || item.dayIndex === null) return

  const day = tripPlan.value.days[item.dayIndex]
  if (!day) return

  let changed = false
  let restorePayload: BudgetRestorePayload | null = null

  if (item.type === 'attraction' && typeof item.sourceIndex === 'number') {
    const attraction = day.attractions[item.sourceIndex]
    if (attraction) {
      restorePayload = {
        type: 'attraction',
        attraction: cloneData(attraction),
        insertIndex: item.sourceIndex,
      }
      day.attractions.splice(item.sourceIndex, 1)
      changed = true
    }
  }

  if (item.type === 'meal' && typeof item.sourceIndex === 'number') {
    const meal = day.meals[item.sourceIndex]
    if (meal) {
      restorePayload = {
        type: 'meal',
        meal: cloneData(meal),
        insertIndex: item.sourceIndex,
      }
      day.meals.splice(item.sourceIndex, 1)
      changed = true
    }
  }

  if (item.type === 'hotel') {
    if (day.hotel) {
      restorePayload = {
        type: 'hotel',
        hotel: cloneData(day.hotel),
        accommodation: day.accommodation || '',
      }
      day.hotel = undefined
      day.accommodation = ''
      changed = true
    }
  }

  if (item.type === 'transport') {
    if (day.transportation && day.transportation.trim()) {
      restorePayload = {
        type: 'transport',
        transportation: day.transportation,
      }
      day.transportation = ''
      changed = true
    }
  }

  if (!changed || !restorePayload) return

  pendingBudgetItems.value.unshift({
    uid: `${item.id}-${Date.now()}`,
    base: cloneData(item),
    payload: restorePayload,
  })

  const transportationTotal =
    item.type === 'transport'
      ? Math.max(
          0,
          roundBudgetAmount(
            toBudgetNumber(tripPlan.value.budget?.total_transportation) - roundBudgetAmount(item.amount)
          )
        )
      : undefined

  recalculateBudgetTotals(transportationTotal)
  sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))

  if (map) {
    map.destroy()
    map = null
  }

  message.success(t('result.messages.budgetItemDeleted'))
}

const restoreBudgetItem = (pendingItem: BudgetRestoreItem) => {
  if (!tripPlan.value || pendingItem.base.dayIndex === null) return

  const day = tripPlan.value.days[pendingItem.base.dayIndex]
  if (!day) return

  let changed = false

  if (pendingItem.payload.type === 'attraction') {
    const insertAt = Math.max(0, Math.min(pendingItem.payload.insertIndex, day.attractions.length))
    day.attractions.splice(insertAt, 0, cloneData(pendingItem.payload.attraction))
    changed = true
  }

  if (pendingItem.payload.type === 'meal') {
    const insertAt = Math.max(0, Math.min(pendingItem.payload.insertIndex, day.meals.length))
    day.meals.splice(insertAt, 0, cloneData(pendingItem.payload.meal))
    changed = true
  }

  if (pendingItem.payload.type === 'hotel') {
    day.hotel = cloneData(pendingItem.payload.hotel)
    day.accommodation = pendingItem.payload.accommodation
    changed = true
  }

  if (pendingItem.payload.type === 'transport') {
    day.transportation = pendingItem.payload.transportation
    changed = true
  }

  if (!changed) return

  const transportationTotal =
    pendingItem.base.type === 'transport'
      ? roundBudgetAmount(toBudgetNumber(tripPlan.value.budget?.total_transportation) + pendingItem.base.amount)
      : undefined

  recalculateBudgetTotals(transportationTotal)
  pendingBudgetItems.value = pendingBudgetItems.value.filter((item) => item.uid !== pendingItem.uid)
  sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))

  if (map) {
    map.destroy()
    map = null
  }

  message.success(t('result.messages.budgetItemRestored'))
}

// 加载所有景点图片
const loadAttractionPhotos = async () => {
  if (!tripPlan.value) return

  const promises: Promise<void>[] = []
  const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''

  tripPlan.value.days.forEach(day => {
    day.attractions.forEach(attraction => {
      const promise = fetch(`${apiBase}/api/poi/photo?name=${encodeURIComponent(attraction.name)}`)
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data.photo_url) {
            attractionPhotos.value[attraction.name] = data.data.photo_url
          }
        })
        .catch(err => {
          console.error(`获取${attraction.name}图片失败:`, err)
        })

      promises.push(promise)
    })
  })

  await Promise.all(promises)
}

// 获取景点图片
const getAttractionImage = (name: string, _index: number): string => {
  // 如果已加载真实图片,返回真实图片
  if (attractionPhotos.value[name]) {
    return attractionPhotos.value[name]
  }

  // 返回一个统一的深色占位图
  const bg = '#1a262f'
  const textColor = 'rgba(255,255,255,0.4)'

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
    <rect width="400" height="300" fill="${bg}"/>
    <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="24" font-weight="bold" fill="${textColor}">${name}</text>
  </svg>`

  return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`
}

// 图片加载失败时的处理
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  // 使用深色占位图
  const label = encodeURIComponent(t('result.imageLoadFailed'))
  img.src = `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect width="400" height="300" fill="%231a262f"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="18" fill="rgba(255,255,255,0.4)"%3E${label}%3C/text%3E%3C/svg%3E`
}



// ========== 构建导出用的纯净 HTML ==========
const buildExportHTML = (): string => {
  if (!tripPlan.value) return ''
  const tp = tripPlan.value as TripPlan & {
    hotel_recommendations?: Array<{
      name?: string
      price?: number | string
      address?: string
    }>
  }

  const mealLabels: Record<string, string> = {
    breakfast: t('result.meals.breakfast'),
    lunch: t('result.meals.lunch'),
    dinner: t('result.meals.dinner'),
    snack: t('result.meals.snack'),
  }

  // 每日行程 HTML
  let daysHTML = ''
  tp.days.forEach((day) => {
    let attractionsHTML = ''
    day.attractions.forEach((a, ai) => {
      const photoUrl = attractionPhotos.value[a.name] || ''
      const durationText = t('result.export.durationLine', { duration: a.visit_duration || '—' })
      const imgTag = photoUrl
        ? `<img src="${photoUrl}" style="width:100%;height:160px;object-fit:cover;border-radius:8px;margin-bottom:8px;" crossorigin="anonymous" />`
        : `<div style="width:100%;height:80px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:8px;margin-bottom:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px;font-weight:bold;">${a.name}</div>`
      attractionsHTML += `
        <div style="flex:0 0 48%;background:#fff;border-radius:10px;padding:14px;box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:14px;">
          ${imgTag}
          <h4 style="margin:0 0 6px;font-size:15px;color:#1a1a1a;">${ai + 1}. ${a.name}</h4>
          <p style="margin:2px 0;font-size:12px;color:#555;">${a.address || '—'}</p>
          <p style="margin:2px 0;font-size:12px;color:#555;">${durationText}${a.ticket_price ? `  |  ¥${a.ticket_price}` : ''}</p>
          <p style="margin:4px 0;font-size:12px;color:#666;">${a.description || ''}</p>
        </div>`
    })

    // 餐饮推荐
    let mealsHTML = ''
    if (day.meals && day.meals.length) {
      mealsHTML = `<div style="margin-top:10px;"><strong style="color:#333;">${t('result.export.mealTitle')}</strong><div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:6px;">`
      day.meals.forEach(m => {
        mealsHTML += `<div style="background:#fffbe6;padding:8px 14px;border-radius:8px;font-size:12px;color:#333;"><b>${mealLabels[m.type] || m.type}</b>: ${m.name || t('result.export.noMealRecommendation')}${m.estimated_cost ? ` (¥${m.estimated_cost})` : ''}</div>`
      })
      mealsHTML += '</div></div>'
    }

    daysHTML += `
      <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <h3 style="margin:0 0 14px;color:#667eea;font-size:18px;">${t('result.export.dayTitle', { day: day.day_index + 1 })} <span style="font-size:14px;color:#888;margin-left:8px;">${day.date || ''}</span></h3>
        <div style="display:flex;flex-wrap:wrap;gap:12px;">
          ${attractionsHTML}
        </div>
        ${mealsHTML}
      </div>`
  })

  // 预算 HTML
  let budgetHTML = ''
  if (tp.budget) {
    const b = tp.budget
    budgetHTML = `
      <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <h3 style="margin:0 0 14px;color:#667eea;">${t('result.budget.title')}</h3>
        <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
          <div style="flex:1;min-width:120px;background:#f5f7fa;padding:14px;border-radius:10px;text-align:center;">
            <div style="font-size:12px;color:#888;">${t('result.budget.attraction')}</div><div style="font-size:20px;font-weight:bold;color:#333;">¥${b.total_attractions || 0}</div>
          </div>
          <div style="flex:1;min-width:120px;background:#f5f7fa;padding:14px;border-radius:10px;text-align:center;">
            <div style="font-size:12px;color:#888;">${t('result.budget.hotel')}</div><div style="font-size:20px;font-weight:bold;color:#333;">¥${b.total_hotels || 0}</div>
          </div>
          <div style="flex:1;min-width:120px;background:#f5f7fa;padding:14px;border-radius:10px;text-align:center;">
            <div style="font-size:12px;color:#888;">${t('result.budget.meal')}</div><div style="font-size:20px;font-weight:bold;color:#333;">¥${b.total_meals || 0}</div>
          </div>
          <div style="flex:1;min-width:120px;background:#f5f7fa;padding:14px;border-radius:10px;text-align:center;">
            <div style="font-size:12px;color:#888;">${t('result.budget.transport')}</div><div style="font-size:20px;font-weight:bold;color:#333;">¥${b.total_transportation || 0}</div>
          </div>
        </div>
        <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:16px 20px;border-radius:12px;display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:16px;">${t('result.budget.total')}</span>
          <span style="font-size:26px;font-weight:bold;">¥${b.total || 0}</span>
        </div>
      </div>`
  }

  // 天气 HTML
  let weatherHTML = ''
  if (tp.weather_info) {
    if (Array.isArray(tp.weather_info) && tp.weather_info.length > 0) {
      let weatherCards = ''
      tp.weather_info.forEach((w: any) => {
        weatherCards += `
          <div style="flex:1;min-width:180px;background:#2b2d3c;padding:16px;border-radius:12px;margin:5px;">
            <div style="text-align:center;color:#00e5ff;font-weight:bold;margin-bottom:12px;font-size:15px;">${w.date}</div>
            <div style="display:flex;align-items:center;margin-bottom:10px;">
              <div style="line-height:1.2;">
                <div style="font-size:12px;color:#99b0c9;margin-bottom:2px;">${t('result.export.daytime')}</div>
                <div style="font-size:14px;color:#fff;font-weight:600;">${w.day_weather} ${w.day_temp}°C</div>
              </div>
            </div>
            <div style="display:flex;align-items:center;margin-bottom:12px;">
              <div style="line-height:1.2;">
                <div style="font-size:12px;color:#99b0c9;margin-bottom:2px;">${t('result.export.nighttime')}</div>
                <div style="font-size:14px;color:#fff;font-weight:600;">${w.night_weather} ${w.night_temp}°C</div>
              </div>
            </div>
            <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:10px;text-align:center;font-size:12px;color:#99b0c9;">
              ${w.wind_direction} ${w.wind_power}
            </div>
          </div>`
      })
      weatherHTML = `
        <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
          <h3 style="margin:0 0 14px;color:#667eea;">${t('result.export.weatherTitle')}</h3>
          <div style="display:flex;flex-wrap:wrap;gap:10px;">
            ${weatherCards}
          </div>
        </div>`
    } else {
      weatherHTML = `
        <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
          <h3 style="margin:0 0 10px;color:#667eea;">${t('result.export.weatherTitle')}</h3>
          <p style="font-size:14px;color:#333;line-height:1.8;">${typeof tp.weather_info === 'string' ? tp.weather_info : JSON.stringify(tp.weather_info)}</p>
        </div>`
    }
  }

  // 酒店 HTML
  let hotelHTML = ''
  if (tp.hotel_recommendations && tp.hotel_recommendations.length) {
    let hotelItems = ''
    tp.hotel_recommendations.forEach((h) => {
      hotelItems += `<div style="background:#e3f2fd;padding:12px 16px;border-radius:10px;margin-bottom:8px;">
        <b style="color:#1565c0;">${h.name || t('result.export.hotelFallback')}</b>
        ${h.price ? `<span style="float:right;color:#e65100;font-weight:bold;">¥${h.price}${t('result.export.perNight')}</span>` : ''}
        ${h.address ? `<p style="margin:4px 0 0;font-size:12px;color:#555;">${h.address}</p>` : ''}
      </div>`
    })
    hotelHTML = `
      <div style="background:#ffffff;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <h3 style="margin:0 0 14px;color:#1976d2;">${t('result.hotelTitle')}</h3>
        ${hotelItems}
      </div>`
  }

  return `
    <div style="width:800px;padding:30px;background:#f0f2f5;font-family:'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;color:#333;">
      <div style="text-align:center;margin-bottom:24px;">
        <h1 style="margin:0;font-size:28px;color:#333;">${t('result.export.title', { city: tp.city })}</h1>
        <p style="margin:6px 0 0;font-size:14px;color:#888;">${t('result.export.subtitle', {
          start: tp.start_date || '',
          end: tp.end_date || '',
          days: tp.days?.length || 0,
        })}</p>
        ${tp.overall_suggestions ? `<p style="margin:8px auto 0;max-width:600px;font-size:13px;color:#666;line-height:1.6;">${tp.overall_suggestions}</p>` : ''}
      </div>
      ${budgetHTML}
      ${daysHTML}
      ${hotelHTML}
      ${weatherHTML}
      <div style="text-align:center;padding:16px;color:#aaa;font-size:12px;">${t('result.export.footer')}</div>
    </div>`
}

// 导出为图片
const exportAsImage = async () => {
  try {
    message.loading({ content: t('result.messages.generatingImage'), key: 'export', duration: 0 })

    const exportContainer = document.createElement('div')
    exportContainer.innerHTML = buildExportHTML()
    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f0f2f5',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    document.body.removeChild(exportContainer)

    const link = document.createElement('a')
    link.download = `${t('result.export.filePrefix')}_${tripPlan.value?.city}_${new Date().getTime()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()

    message.success({ content: t('result.messages.imageSuccess'), key: 'export' })
  } catch (error: any) {
    console.error('导出图片失败:', error)
    message.error({ content: t('result.messages.imageFailed', { error: error.message }), key: 'export' })
  }
}

// 导出为PDF
const exportAsPDF = async () => {
  try {
    message.loading({ content: t('result.messages.generatingPdf'), key: 'export', duration: 0 })

    const exportContainer = document.createElement('div')
    exportContainer.innerHTML = buildExportHTML()
    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f0f2f5',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    document.body.removeChild(exportContainer)

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    })

    const imgWidth = 210
    const imgHeight = (canvas.height * imgWidth) / canvas.width

    let heightLeft = imgHeight
    let position = 0

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= 297

    while (heightLeft > 0) {
      position = heightLeft - imgHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= 297
    }

    pdf.save(`${t('result.export.filePrefix')}_${tripPlan.value?.city}_${new Date().getTime()}.pdf`)

    message.success({ content: t('result.messages.pdfSuccess'), key: 'export' })
  } catch (error: any) {
    console.error('导出PDF失败:', error)
    message.error({ content: t('result.messages.pdfFailed', { error: error.message }), key: 'export' })
  }
}
// ========== 知识图谱初始化 ==========
const initKnowledgeGraph = () => {
  if (!graphData.value) return

  const container = document.getElementById('kg-chart-container')
  if (!container) return

  // 如果已存在实例则销毁
  if (kgChart) {
    kgChart.dispose()
  }

  kgChart = echarts.init(container, 'dark')

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(12, 23, 32, 0.94)',
      borderColor: 'rgba(215, 110, 66, 0.35)',
      borderWidth: 1,
      padding: [12, 16],
      textStyle: { color: '#fff', fontSize: 13 },
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const catName = graphData.value?.categories[params.data.category]?.name || ''
          const cat = getCategoryLabel(catName)
          let tip = `<b style="color:#ffe3d6;font-size:15px">${params.data.name}</b><br/>`
          tip += `<span style="color:#aaa">${t('result.graph.type')}:</span>${cat}<br/>`
          if (params.data.value) {
            tip += `<span style="color:#aaa">${t('result.graph.detail')}:</span>${params.data.value}`
          }
          return tip
        }
        if (params.dataType === 'edge') {
          return `<span style="color:#ffe3d6">${params.data.label || t('result.graph.relation')}</span>`
        }
        return ''
      }
    },
    legend: {
      show: false  // 使用自定义legend
    },
    animationDuration: 1500,
    animationEasingUpdate: 'quinticInOut',
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: graphData.value.nodes.map(node => ({
          ...node,
          label: {
            show: node.symbolSize >= 35,
            position: 'inside' as const,
            fontSize: node.symbolSize >= 70 ? 14 : node.symbolSize >= 45 ? 12 : 10,
            color: '#fff',
            fontWeight: 'bold' as const,
            formatter: (params: any) => {
              const name = params.data.name as string
              return name.length > 6 ? name.slice(0, 6) + '…' : name
            },
          },
        })),
        links: graphData.value.edges.map(edge => ({
          ...edge,
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.15)',
            width: 1.5,
            curveness: 0.1,
          },
          label: {
            show: true,
            formatter: edge.label || '',
            fontSize: 10,
            color: 'rgba(255, 255, 255, 0.45)',
          },
        })),
        categories: graphData.value.categories,
        roam: true,
        draggable: true,
        force: {
          repulsion: 350,
          gravity: 0.08,
          edgeLength: [80, 200],
          friction: 0.6,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4, color: '#d76e42' },
          itemStyle: { borderColor: '#d76e42', borderWidth: 3 },
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
      },
    ],
  }

  kgChart.setOption(option)

  // 响应窗口变化
  window.addEventListener('resize', () => {
    kgChart?.resize()
  })
}

const escapeHtml = (value: unknown): string => {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const buildMarkerContent = (globalIndex: number, dayIndex: number): string => {
  return `
    <div class="tripstar-map-marker" title="${escapeHtml(t('common.dayNumber', { day: dayIndex + 1 }))}">
      <span class="tripstar-map-marker__pulse"></span>
      <span class="tripstar-map-marker__core">${globalIndex}</span>
      <span class="tripstar-map-marker__tag">D${dayIndex + 1}</span>
    </div>
  `
}

const buildInfoWindowContent = (attraction: any): string => {
  const name = escapeHtml(attraction.name || t('common.noData'))
  const address = escapeHtml(attraction.address || t('common.noData'))
  const visitDuration = Number.isFinite(attraction.visit_duration) ? attraction.visit_duration : '—'
  const description = escapeHtml(attraction.description || t('common.noData')).replace(/\n/g, '<br/>')
  const dayAttractionText = escapeHtml(
    t('result.mapInfo.dayAttraction', { day: attraction.dayIndex + 1, index: attraction.attrIndex + 1 })
  )
  const addressLabel = escapeHtml(t('result.fieldAddress'))
  const durationLabel = escapeHtml(t('result.fieldVisitDuration'))
  const descLabel = escapeHtml(t('result.fieldDescription'))
  const minuteUnit = escapeHtml(t('result.minuteUnit'))

  return `
    <article class="tripstar-map-tooltip">
      <header class="tripstar-map-tooltip__header">
        <h4 class="tripstar-map-tooltip__title">${name}</h4>
        <span class="tripstar-map-tooltip__badge">${dayAttractionText}</span>
      </header>
      <div class="tripstar-map-tooltip__body">
        <p class="tripstar-map-tooltip__line">
          <span class="tripstar-map-tooltip__label">${addressLabel}</span>
          <span>${address}</span>
        </p>
        <p class="tripstar-map-tooltip__line">
          <span class="tripstar-map-tooltip__label">${durationLabel}</span>
          <span>${visitDuration}${minuteUnit}</span>
        </p>
        <p class="tripstar-map-tooltip__line">
          <span class="tripstar-map-tooltip__label">${descLabel}</span>
          <span>${description}</span>
        </p>
      </div>
      <span class="tripstar-map-tooltip__arrow"></span>
    </article>
  `
}

type RouteMode = 'driving' | 'walking' | 'straight'
type RoutePoint = [number, number]

const ROUTE_STYLE_PRESETS: Record<
  RouteMode,
  {
    strokeColor: string
    strokeWeight: number
    strokeOpacity: number
    strokeStyle: 'solid' | 'dashed'
    strokeDasharray?: number[]
    lineJoin?: 'round' | 'miter' | 'bevel'
    lineCap?: 'butt' | 'round' | 'square'
    outlineColor?: string
    borderWeight?: number
  }
> = {
  driving: {
    strokeColor: '#37b4ff',
    strokeWeight: 6,
    strokeOpacity: 0.92,
    strokeStyle: 'solid',
    lineJoin: 'round',
    lineCap: 'round',
    outlineColor: 'rgba(4, 19, 32, 0.7)',
    borderWeight: 2,
  },
  walking: {
    strokeColor: '#6ad38f',
    strokeWeight: 5,
    strokeOpacity: 0.9,
    strokeStyle: 'dashed',
    strokeDasharray: [12, 8],
    lineJoin: 'round',
    lineCap: 'round',
    outlineColor: 'rgba(8, 32, 20, 0.5)',
    borderWeight: 1,
  },
  straight: {
    strokeColor: '#ff9b64',
    strokeWeight: 4,
    strokeOpacity: 0.82,
    strokeStyle: 'dashed',
    strokeDasharray: [10, 10],
    lineJoin: 'round',
    lineCap: 'round',
    outlineColor: 'rgba(33, 17, 8, 0.45)',
    borderWeight: 1,
  },
}

const detectRouteMode = (transportation: string): RouteMode => {
  const normalized = (transportation || '').toLowerCase()
  if (/(步行|徒步|散步|walk|walking)/i.test(normalized)) return 'walking'
  if (/(驾车|开车|自驾|打车|出租车|car|drive|driving|taxi)/i.test(normalized)) return 'driving'
  return 'driving'
}

const toRoutePoint = (raw: any): RoutePoint | null => {
  if (!raw) return null

  if (Array.isArray(raw) && raw.length >= 2) {
    const lng = Number(raw[0])
    const lat = Number(raw[1])
    return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
  }

  if (typeof raw.getLng === 'function' && typeof raw.getLat === 'function') {
    const lng = Number(raw.getLng())
    const lat = Number(raw.getLat())
    return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
  }

  if ('lng' in raw && 'lat' in raw) {
    const lng = Number(raw.lng)
    const lat = Number(raw.lat)
    return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
  }

  if ('longitude' in raw && 'latitude' in raw) {
    const lng = Number(raw.longitude)
    const lat = Number(raw.latitude)
    return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
  }

  return null
}

const parsePolylineString = (polyline: string): RoutePoint[] => {
  if (!polyline) return []

  return polyline
    .split(';')
    .map((pair) => pair.split(','))
    .map((parts) => {
      const lng = Number(parts[0])
      const lat = Number(parts[1])
      return Number.isFinite(lng) && Number.isFinite(lat) ? ([lng, lat] as RoutePoint) : null
    })
    .filter((point): point is RoutePoint => Boolean(point))
}

const dedupeRoutePath = (points: RoutePoint[]): RoutePoint[] => {
  if (points.length <= 1) return points
  return points.filter((point, index, array) => {
    if (index === 0) return true
    const prev = array[index - 1]
    return point[0] !== prev[0] || point[1] !== prev[1]
  })
}

const extractRoutePath = (result: any): RoutePoint[] => {
  const route =
    result?.routes?.[0] ||
    result?.route?.paths?.[0] ||
    result?.route?.routes?.[0] ||
    null

  if (!route) return []

  const steps = route.steps || []
  const points: RoutePoint[] = []

  steps.forEach((step: any) => {
    if (Array.isArray(step?.path)) {
      step.path.forEach((node: any) => {
        const point = toRoutePoint(node)
        if (point) points.push(point)
      })
      return
    }

    if (typeof step?.polyline === 'string') {
      points.push(...parsePolylineString(step.polyline))
    }
  })

  if (points.length > 1) return dedupeRoutePath(points)

  if (typeof route?.polyline === 'string') {
    const fromRoute = dedupeRoutePath(parsePolylineString(route.polyline))
    if (fromRoute.length > 1) return fromRoute
  }

  return []
}

const searchRoutePath = (
  AMap: any,
  mode: Exclude<RouteMode, 'straight'>,
  start: RoutePoint,
  end: RoutePoint
): Promise<RoutePoint[] | null> => {
  return new Promise((resolve) => {
    const ServiceCtor = mode === 'walking' ? AMap.Walking : AMap.Driving
    if (!ServiceCtor) {
      resolve(null)
      return
    }

    const service =
      mode === 'driving'
        ? new ServiceCtor({
            policy: AMap.DrivingPolicy?.LEAST_TIME ?? 0,
          })
        : new ServiceCtor({})

    service.search(start, end, (status: string, result: any) => {
      if (status !== 'complete') {
        resolve(null)
        return
      }
      const path = extractRoutePath(result)
      resolve(path.length > 1 ? path : null)
    })
  })
}

// 初始化地图
const initMap = async () => {
  try {
    const AMap = await AMapLoader.load({
      key: import.meta.env.VITE_AMAP_WEB_JS_KEY,  // 高德地图Web端(JS API) Key
      version: '2.0',
      plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.InfoWindow', 'AMap.Driving', 'AMap.Walking']
    })

    // 创建地图实例
    map = new AMap.Map('amap-container', {
      zoom: 12,
      center: [116.397128, 39.916527], // 默认中心点(北京)
      viewMode: '3D'
    })

    // 添加景点标记
    await addAttractionMarkers(AMap)

    message.success(t('result.messages.mapLoaded'))
  } catch (error) {
    console.error('地图加载失败:', error)
    message.error(t('result.messages.mapLoadFailed'))
  }
}

// 添加景点标记
const addAttractionMarkers = async (AMap: any) => {
  if (!tripPlan.value) return

  const markers: any[] = []
  const allAttractions: any[] = []

  // 收集所有景点（保留全局编号）
  let globalIndex = 0
  tripPlan.value.days.forEach((day, dayIndex) => {
    day.attractions.forEach((attraction, attrIndex) => {
      globalIndex++
      if (attraction.location && attraction.location.longitude && attraction.location.latitude) {
        allAttractions.push({
          ...attraction,
          dayIndex,
          attrIndex,
          globalIndex   // 全局编号（从1开始）
        })
      }
    })
  })

  // 创建标记
  allAttractions.forEach((attraction, index) => {
    const marker = new AMap.Marker({
      position: [attraction.location.longitude, attraction.location.latitude],
      title: attraction.name,
      content: buildMarkerContent(index + 1, attraction.dayIndex),
      anchor: 'bottom-center',
      offset: new AMap.Pixel(0, -8),
      zIndex: 120 + index,
    })

    // 创建信息窗口
    const infoWindow = new AMap.InfoWindow({
      isCustom: true,
      content: buildInfoWindowContent(attraction),
      offset: new AMap.Pixel(0, -52),
      closeWhenClickMap: true,
    })

    // 点击标记显示信息窗口
    marker.on('click', () => {
      infoWindow.open(map, marker.getPosition())
    })

    markers.push(marker)
  })

  // 添加标记到地图
  map.add(markers)

  // 绘制路线（优先真实道路路线，失败时回退直线）
  const routePolylines = await drawRoutes(AMap, allAttractions)

  // 自动调整视野以包含所有标记
  if (allAttractions.length > 0) {
    const overlaysForFit = routePolylines.length > 0 ? [...markers, ...routePolylines] : markers
    map.setFitView(overlaysForFit)
  }
}

// 绘制路线：根据交通方式选择 driving / walking；失败时降级为直线
const drawRoutes = async (AMap: any, attractions: any[]): Promise<any[]> => {
  if (attractions.length < 2 || !tripPlan.value) return []

  // 按天分组绘制路线
  const dayGroups: Record<number, any[]> = {}
  attractions.forEach(attr => {
    if (!dayGroups[attr.dayIndex]) {
      dayGroups[attr.dayIndex] = []
    }
    dayGroups[attr.dayIndex].push(attr)
  })

  const polylines: any[] = []

  // 为每天的景点逐段绘制路线
  for (const dayAttractions of Object.values(dayGroups)) {
    if (dayAttractions.length < 2) continue

    dayAttractions.sort((a: any, b: any) => a.attrIndex - b.attrIndex)
    const dayIndex = dayAttractions[0].dayIndex
    const transportation = tripPlan.value.days?.[dayIndex]?.transportation || ''
    const preferredMode = detectRouteMode(transportation)

    for (let i = 0; i < dayAttractions.length - 1; i++) {
      const start = dayAttractions[i]
      const end = dayAttractions[i + 1]
      const startPoint: RoutePoint = [start.location.longitude, start.location.latitude]
      const endPoint: RoutePoint = [end.location.longitude, end.location.latitude]

      const plannedPath =
        preferredMode === 'straight'
          ? null
          : await searchRoutePath(AMap, preferredMode as Exclude<RouteMode, 'straight'>, startPoint, endPoint)

      const usePlannedRoute = Array.isArray(plannedPath) && plannedPath.length > 1
      const routeModeForStyle: RouteMode = usePlannedRoute ? preferredMode : 'straight'
      const path = usePlannedRoute ? plannedPath : [startPoint, endPoint]
      const style = ROUTE_STYLE_PRESETS[routeModeForStyle]

      const polyline = new AMap.Polyline({
        path,
        ...style,
        showDir: true,
        zIndex: 90,
      })

      polylines.push(polyline)
    }
  }

  if (polylines.length > 0) {
    map.add(polylines)
  }

  return polylines
}
</script>

<style scoped>
@import 'swiper/css';

/* ===== Landing 同款视觉基底 - 结果页 ===== */

.result-container {
  min-height: 100vh;
  background: linear-gradient(180deg, #0d171d 0%, #142430 58%, #0f1a22 100%);
  color: #ecf3fa;
  position: relative;
  isolation: isolate;
  overflow-x: hidden;
}

.lower-shade {
  position: fixed;
  inset: 0% 0 -1px 0;
  z-index: 0;
  pointer-events: none;
  background: rgba(6, 14, 20, 0.72);
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

.result-main {
  position: relative;
  z-index: 2;
  padding: 70px 20px 44px;
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  display: block;
  border: 1.2px solid rgba(236, 243, 250, 0.2);
  border-radius: 22px;
  background: rgba(12, 23, 32, 0.56);
  backdrop-filter: blur(18px);
  box-shadow: 0 24px 80px rgba(4, 11, 18, 0.52);
  padding: 20px;
}

.top-switch-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: space-between;
  margin-bottom: 16px;
}

.top-switch-menu-wrap {
  flex: 1;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: hidden;
}

.top-switch-menu {
  width: 100%;
  min-width: 0;
  border-bottom: 1px solid rgba(236, 243, 250, 0.16) !important;
  background: transparent !important;
}

.top-switch-menu :deep(.ant-menu-item) {
  color: rgba(232, 239, 247, 0.75) !important;
  border-radius: 10px 10px 0 0;
  margin-right: 4px !important;
  transition: all 0.2s ease;
}

.top-switch-menu :deep(.ant-menu-item:hover) {
  color: rgba(236, 243, 250, 0.95) !important;
}

.top-switch-menu :deep(.ant-menu-item-selected) {
  color: #ffe3d6 !important;
}

.top-switch-menu :deep(.ant-menu-item-selected::after),
.top-switch-menu :deep(.ant-menu-item-active::after),
.top-switch-menu :deep(.ant-menu-item:hover::after) {
  border-bottom-color: #d76e42 !important;
}

.top-switch-menu :deep(.ant-menu-overflow) {
  flex-wrap: nowrap;
}

.top-switch-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}

.top-switch-actions :deep(.ant-btn-default) {
  border: 1.2px solid rgba(236, 243, 250, 0.24) !important;
  background: rgba(12, 23, 32, 0.56) !important;
  color: #ecf3fa !important;
  border-radius: 999px !important;
  height: 34px !important;
  padding: 0 12px !important;
  font-size: 12px !important;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.top-switch-actions :deep(.ant-btn-primary) {
  border: 1.2px solid rgba(215, 110, 66, 0.5) !important;
  background: rgba(215, 110, 66, 0.24) !important;
  color: #ffe3d6 !important;
  border-radius: 999px !important;
  height: 34px !important;
  padding: 0 12px !important;
  font-size: 12px !important;
  font-weight: 600;
  letter-spacing: 0.04em;
  box-shadow: none !important;
}

.empty-state-panel {
  max-width: 900px;
  margin: 0 auto;
  border: 1.2px solid rgba(236, 243, 250, 0.2);
  border-radius: 22px;
  background: rgba(12, 23, 32, 0.56);
  backdrop-filter: blur(18px);
  box-shadow: 0 24px 80px rgba(4, 11, 18, 0.52);
  padding: 44px 20px;
  text-align: center;
}

.empty-desc {
  color: rgba(228, 236, 245, 0.72);
}

.empty-back-btn {
  border: 1.2px solid rgba(215, 110, 66, 0.5) !important;
  background: rgba(215, 110, 66, 0.24) !important;
  color: #ffe3d6 !important;
  border-radius: 999px !important;
  min-height: 34px !important;
  padding: 0 14px !important;
  font-size: 12px !important;
  font-weight: 600;
  letter-spacing: 0.04em;
  box-shadow: none !important;
}

/* 景点图片样式 */
.attraction-image-wrapper {
  position: relative;
  margin-bottom: 12px;
  border-radius: 12px;
  overflow: hidden;
}

.attraction-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.attraction-image-wrapper:hover .attraction-image {
  transform: scale(1.08);
}

.attraction-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  background: linear-gradient(135deg, #d76e42 0%, #a14625 100%);
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  box-shadow: 0 4px 12px rgba(215, 110, 66, 0.35);
}

.badge-number {
  font-size: 18px;
}

.price-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(215, 110, 66, 0.9);
  color: white;
  padding: 4px 14px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(215, 110, 66, 0.3);
  backdrop-filter: blur(10px);
}

/* 天气卡片样式 */
.weather-card {
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  backdrop-filter: blur(16px);
  transition: all 0.3s ease;
}

.weather-card:hover {
  transform: translateY(-4px);
  border-color: rgba(215, 110, 66, 0.32) !important;
  box-shadow: 0 8px 24px rgba(215, 110, 66, 0.22);
}

.weather-date {
  font-size: 16px;
  font-weight: bold;
  color: #95c7f5;
  margin-bottom: 12px;
  text-align: center;
}

.weather-info-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.weather-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.weather-value {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
}

.weather-wind {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
}

/* 回到顶部按钮 */
.back-top-button {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #d76e42 0%, #a14625 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.03em;
  box-shadow: 0 4px 20px rgba(215, 110, 66, 0.38);
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-top-button:hover {
  transform: scale(1.15);
  box-shadow: 0 6px 28px rgba(215, 110, 66, 0.48);
}

/* 酒店卡片样式 */
.hotel-card {
  background: rgba(215, 110, 66, 0.1) !important;
  border: 1px solid rgba(215, 110, 66, 0.26) !important;
}

.hotel-card :deep(.ant-card-head) {
  background: linear-gradient(135deg, rgba(215, 110, 66, 0.9) 0%, rgba(161, 70, 37, 0.9) 100%) !important;
}

.hotel-title {
  color: white !important;
  font-weight: 600;
}

.hotel-card :deep(.ant-descriptions-item-label) {
  color: rgba(255, 255, 255, 0.5) !important;
}

.hotel-card :deep(.ant-descriptions-item-content) {
  color: rgba(255, 255, 255, 0.8) !important;
}

/* 顶部信息区布局 */
.top-info-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.left-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-map {
  flex: 1;
}

/* 行程概览卡片 */
.overview-card {
  margin-bottom: 20px;
}

.section-shellless {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.section-shellless:hover {
  box-shadow: none !important;
  border-color: transparent !important;
}

:deep(.section-shellless > .ant-card-head) {
  display: none !important;
}

:deep(.section-shellless > .ant-card-body) {
  padding: 0 !important;
  background: rgba(4, 8, 13, 0.726);
  border-radius: 14px;
}

.overview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 18px;
}

.overview-meta-item {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  /* border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04); */
  color: rgba(236, 243, 250, 0.78);
  font-size: 12px;
  line-height: 1.5;
}

.overview-swiper {
  padding: 8px 2px 14px;
}

.overview-swiper .swiper {
  padding: 1.875rem 0rem;
  overflow: hidden;
  border-radius: 12px;
}

.overview-swiper .swiper-wrapper {
  align-items: flex-end;
}


/* 预算卡片 */
.budget-card {
  height: fit-content;
}

.budget-detail-panel {
  min-height: 100%;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(3, 10, 15, 0.88);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.budget-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.budget-toolbar-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.budget-toolbar-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.budget-select {
  width: 180px;
}

.budget-select :deep(.ant-select-selector) {
  border-radius: 10px !important;
  border-color: rgba(255, 255, 255, 0.24) !important;
  background: rgba(0, 0, 0, 0.2) !important;
  color: rgba(255, 255, 255, 0.86) !important;
}

.budget-select :deep(.ant-select-arrow) {
  color: rgba(255, 255, 255, 0.72) !important;
}

.budget-detail-list {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.18);
}

.budget-detail-row {
  display: grid;
  grid-template-columns: 112px 96px minmax(0, 1fr) 120px 86px;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.01);
}

.budget-detail-row:last-child {
  border-bottom: none;
}

.budget-detail-header {
  background: rgba(255, 255, 255, 0.04);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.64);
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.budget-detail-type,
.budget-detail-day,
.budget-detail-name,
.budget-detail-amount {
  color: rgba(255, 255, 255, 0.86);
  font-size: 13px;
}

.budget-detail-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.budget-detail-amount {
  font-weight: 600;
  color: #ffd5c6;
}

.budget-action-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.budget-icon-btn {
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.budget-icon-btn svg {
  width: 16px;
  height: 16px;
}

.budget-edit-btn {
  color: rgba(255, 255, 255, 0.68);
}

.budget-delete-btn {
  color: rgba(255, 255, 255, 0.68);
}

.budget-edit-btn:hover,
.budget-delete-btn:hover {
  color: #fff;
  transform: scale(1.1);
  /* background: rgba(110, 247, 213, 0.16); */
}

.right-budget-summary {
  flex: 0 0 360px;
}

.budget-summary-panel {
  min-height: 100%;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(3, 10, 15, 0.88);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.budget-summary-title {
  color: rgba(255, 255, 255, 0.92);
  font-size: 34px;
  font-weight: 300;
  letter-spacing: 0.02em;
  line-height: 1;
}

.budget-summary-total-wrap {
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.budget-summary-currency {
  font-size: 42px;
  line-height: 1;
  color: rgba(255, 255, 255, 0.9);
}

.budget-summary-total-value {
  font-size: 78px;
  line-height: 0.88;
  font-weight: 300;
  color: rgba(255, 255, 255, 0.96);
  letter-spacing: 0.01em;
}

.budget-summary-sub-grid {
  margin-top: 6px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 12px;
}

.budget-summary-sub-item {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 8px;
}

.budget-summary-sub-value {
  font-size: 32px;
  line-height: 1;
  color: #ffd4c3;
}

.budget-summary-sub-label {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.4;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.65);
  text-transform: uppercase;
}

.budget-pending-wrap {
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.budget-pending-title {
  font-size: 12px;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.72);
  margin-bottom: 8px;
  text-transform: uppercase;
}

.budget-pending-empty {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  padding: 8px 0;
}

.budget-pending-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.budget-pending-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.09);
}

.budget-pending-name {
  flex: 1;
  min-width: 0;
  color: rgba(255, 255, 255, 0.84);
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.budget-restore-btn {
  padding: 0 !important;
}

/* 地图卡片 */
.map-card {
  height: 100%;
  min-height: 500px;
}

.map-card :deep(.ant-card-body) {
  height: 100%;
  padding: 0;
}

/* 知识图谱卡片 */
.kg-card {
  margin-top: 20px;
}

.kg-card :deep(.ant-card-body) {
  padding: 0 0 16px 0;
}

.kg-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 16px;
  padding: 12px 20px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.kg-legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.kg-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

/* 每日行程卡片 */
.days-card {
  margin-top: 20px;
}

.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.day-title {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
}

.day-date {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.35);
}

.day-info {
  margin-bottom: 20px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.info-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row .label {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.45);
  min-width: 100px;
}

.info-row .value {
  color: rgba(255, 255, 255, 0.8);
  flex: 1;
}

/* 卡片样式 - 玻璃拟态暗色 */
:deep(.ant-card) {
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  margin-bottom: 20px;
  transition: all 0.3s ease;
  animation: fadeInUp 0.6s ease-out;
  color: rgba(255, 255, 255, 0.8);
}

:deep(.ant-card:hover) {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  border-color: rgba(215, 110, 66, 0.26) !important;
}

:deep(.ant-card-head) {
  background: linear-gradient(135deg, rgba(215, 110, 66, 0.2) 0%, rgba(161, 70, 37, 0.14) 100%) !important;
  color: #ffe3d6 !important;
  border-radius: 16px 16px 0 0;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
}

:deep(.ant-card-head-title) {
  color: #ffe3d6 !important;
  font-size: 18px;
}

:deep(.ant-card-head-title span) {
  color: #ffe3d6 !important;
}

:deep(.ant-card-body) {
  color: rgba(255, 255, 255, 0.8);
}

:deep(.ant-card-body p) {
  color: rgba(255, 255, 255, 0.7);
}

:deep(.ant-card-body strong) {
  color: rgba(255, 255, 255, 0.5);
}

/* Collapse 样式 - 暗色 */
:deep(.ant-collapse) {
  border: none;
  background: transparent;
}

:deep(.ant-collapse-item) {
  margin-bottom: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 16px !important;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.02);
}

:deep(.ant-collapse-header) {
  background: rgba(255, 255, 255, 0.04) !important;
  padding: 16px 20px !important;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8) !important;
}

:deep(.ant-collapse-expand-icon) {
  color: rgba(255, 255, 255, 0.4) !important;
}

:deep(.ant-collapse-content) {
  border-top: 1px solid rgba(255, 255, 255, 0.06) !important;
  background: transparent !important;
}

:deep(.ant-collapse-content-box) {
  padding: 20px;
  color: rgba(255, 255, 255, 0.7);
}

/* Descriptions 暗色 */
:deep(.ant-descriptions) {
  background: transparent;
}

:deep(.ant-descriptions-bordered .ant-descriptions-item-label) {
  background: rgba(255, 255, 255, 0.04) !important;
  color: rgba(255, 255, 255, 0.5) !important;
  border-color: rgba(255, 255, 255, 0.06) !important;
}

:deep(.ant-descriptions-bordered .ant-descriptions-item-content) {
  background: transparent !important;
  color: rgba(255, 255, 255, 0.8) !important;
  border-color: rgba(255, 255, 255, 0.06) !important;
}

:deep(.ant-descriptions-item-label) {
  color: rgba(255, 255, 255, 0.5) !important;
}

:deep(.ant-descriptions-item-content) {
  color: rgba(255, 255, 255, 0.8) !important;
}

/* Divider 暗色 */
:deep(.ant-divider) {
  border-color: rgba(255, 255, 255, 0.08) !important;
  color: rgba(255, 255, 255, 0.6) !important;
}

:deep(.ant-divider-inner-text) {
  color: rgba(255, 255, 255, 0.6) !important;
}

/* Empty 暗色 */
:deep(.ant-empty-description) {
  color: rgba(255, 255, 255, 0.4) !important;
}

/* 景点卡片样式 */
:deep(.ant-list-item) {
  transition: all 0.3s ease;
}

:deep(.ant-list-item:hover) {
  transform: scale(1.02);
}

/* 动画 */
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .result-main {
    padding: 60px 10px 24px;
  }

  .content-wrapper {
    padding: 14px;
  }

  .top-switch-nav {
    gap: 8px;
  }

  .top-switch-menu-wrap {
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  .top-switch-menu {
    min-width: max-content;
  }

  .top-switch-menu-wrap::-webkit-scrollbar {
    width: 0;
    height: 0;
    display: none;
  }

  .top-switch-actions {
    max-width: 44%;
  }

  .top-switch-actions :deep(.ant-space) {
    column-gap: 6px !important;
    row-gap: 6px !important;
  }

  .top-switch-actions :deep(.ant-btn-default),
  .top-switch-actions :deep(.ant-btn-primary) {
    height: 32px !important;
    padding: 0 10px !important;
    font-size: 11px !important;
  }

  .top-info-section {
    flex-direction: column;
  }

  .left-info {
    flex: auto;
  }

  .right-budget-summary {
    flex: auto;
    width: 100%;
  }

  .budget-summary-panel {
    min-height: auto;
  }

  .budget-summary-title {
    font-size: 30px;
  }

  .budget-summary-total-value {
    font-size: 56px;
  }

  .budget-summary-sub-value {
    font-size: 24px;
  }

  .overview-meta {
    gap: 8px;
    margin-bottom: 14px;
  }

  .overview-meta-item {
    width: 100%;
    border-radius: 12px;
  }

  .overview-swiper .swiper-wrapper {
    gap: 1rem;
  }

  .budget-toolbar {
    gap: 8px;
  }

  .budget-detail-panel {
    min-height: auto;
    padding: 14px;
  }

  .budget-toolbar-item {
    width: 100%;
    justify-content: space-between;
  }

  .budget-select {
    width: 170px;
  }

  .budget-detail-list {
    overflow-x: auto;
  }

  .budget-detail-row {
    min-width: 620px;
  }

}

</style>

<style>
:root {
  --tripstar-map-accent: #d76e42;
  --tripstar-map-accent-strong: #a14625;
  --tripstar-map-surface: rgba(17, 29, 38, 0.96);
  --tripstar-map-border: rgba(215, 110, 66, 0.35);
  --tripstar-map-text-main: #f6fbff;
  --tripstar-map-text-sub: rgba(240, 246, 252, 0.72);
}

.tripstar-map-marker {
  position: relative;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.tripstar-map-marker__pulse {
  position: absolute;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(215, 110, 66, 0.38) 0%, rgba(215, 110, 66, 0) 72%);
  animation: tripstarMapPulse 2s ease-out infinite;
}

.tripstar-map-marker__core {
  position: relative;
  z-index: 2;
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(140deg, var(--tripstar-map-accent) 0%, var(--tripstar-map-accent-strong) 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow: 0 8px 22px rgba(161, 70, 37, 0.46);
}

.tripstar-map-marker__tag {
  position: absolute;
  right: -8px;
  top: -6px;
  z-index: 3;
  min-width: 24px;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(11, 22, 30, 0.9);
  color: #ffd8c8;
  border: 1px solid rgba(255, 214, 194, 0.34);
  font-size: 10px;
  font-weight: 700;
  text-align: center;
  line-height: 1.2;
}

.tripstar-map-tooltip {
  width: min(330px, calc(100vw - 42px));
  border-radius: 16px;
  border: 1px solid var(--tripstar-map-border);
  background: linear-gradient(160deg, rgba(20, 33, 44, 0.98) 0%, var(--tripstar-map-surface) 100%);
  backdrop-filter: blur(10px);
  box-shadow: 0 18px 36px rgba(4, 10, 15, 0.55);
  color: var(--tripstar-map-text-main);
  overflow: hidden;
  position: relative;
}

.tripstar-map-tooltip__header {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 10px;
  border-bottom: 1px solid rgba(236, 243, 250, 0.12);
  background: linear-gradient(130deg, rgba(215, 110, 66, 0.2) 0%, rgba(215, 110, 66, 0.05) 100%);
}

.tripstar-map-tooltip__title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--tripstar-map-text-main);
  line-height: 1.35;
}

.tripstar-map-tooltip__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 146px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(6, 15, 22, 0.72);
  color: #ffd8c8;
  border: 1px solid rgba(255, 216, 200, 0.34);
  font-size: 10px;
  font-weight: 600;
  text-align: center;
}

.tripstar-map-tooltip__body {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
}

.tripstar-map-tooltip__line {
  margin: 0;
  display: grid;
  gap: 4px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--tripstar-map-text-main);
}

.tripstar-map-tooltip__label {
  font-size: 11px;
  color: var(--tripstar-map-text-sub);
  letter-spacing: 0.02em;
}

.tripstar-map-tooltip__arrow {
  position: absolute;
  left: 50%;
  bottom: -7px;
  width: 14px;
  height: 14px;
  transform: translateX(-50%) rotate(45deg);
  background: rgba(17, 29, 38, 0.98);
  border-right: 1px solid var(--tripstar-map-border);
  border-bottom: 1px solid var(--tripstar-map-border);
}

@keyframes tripstarMapPulse {
  0% {
    transform: scale(0.72);
    opacity: 0.52;
  }
  80% {
    transform: scale(1.18);
    opacity: 0;
  }
  100% {
    transform: scale(1.18);
    opacity: 0;
  }
}
</style>

