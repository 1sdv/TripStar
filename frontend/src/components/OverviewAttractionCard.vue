<template>
  <div class="swiper-slide" :class="{ 'swiper-slide-active': active }" @mouseenter="emit('hover')" @focusin="emit('hover')">
    <div class="swiper-slide-img">
      <img :src="imageSrc" :alt="item.name" loading="lazy" @error="emit('image-error', $event)" />
      <svg data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 120" preserveAspectRatio="none">
        <path d="M0,0V46.29c47.79,22.2,103.59,32.17,158,28,70.36-5.37,136.33-33.31,206.8-37.5C438.64,32.43,512.34,53.67,583,72.05c69.27,18,138.3,24.88,209.4,13.08,36.15-6,69.85-17.84,104.45-29.34C989.49,25,1113-14.29,1200,52.47V0Z" opacity=".25" class="shape-fill"></path>
        <path d="M0,0V15.81C13,36.92,27.64,56.86,47.69,72.05,99.41,111.27,165,111,224.58,91.58c31.15-10.15,60.09-26.07,89.67-39.8,40.92-19,84.73-46,130.83-49.67,36.26-2.85,70.9,9.42,98.6,31.56,31.77,25.39,62.32,62,103.63,73,40.44,10.79,81.35-6.69,119.13-24.28s75.16-39,116.92-43.05c59.73-5.85,113.28,22.88,168.9,38.84,30.2,8.66,59,6.17,87.09-7.5,22.43-10.89,48-26.93,60.65-49.24V0Z" opacity=".5" class="shape-fill"></path>
        <path d="M0,0V5.63C149.93,59,314.09,71.32,475.83,42.57c43-7.64,84.23-20.12,127.61-26.46,59-8.63,112.48,12.24,165.56,35.4C827.93,77.22,886,95.24,951.2,90c86.53-7,172.46-45.71,248.8-84.81V0Z" class="shape-fill"></path>
      </svg>
    </div>
    <div class="swiper-slide-content">
      <div>
        <h2>{{ item.name }}</h2>
        <p>{{ item.description || item.address || t('common.noData') }}</p>
        <a class="show-more" href="#" target="_self" @click.prevent="emit('select-day', item.dayArrayIndex)">
          <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 8.25L21 12m0 0l-3.75 3.75M21 12H3"></path>
          </svg>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

type OverviewAttractionItem = {
  name: string
  address: string
  visit_duration: number
  description: string
  dayArrayIndex: number
}

defineProps<{
  item: OverviewAttractionItem
  imageSrc: string
  active: boolean
}>()

const emit = defineEmits<{
  (e: 'hover'): void
  (e: 'select-day', dayArrayIndex: number): void
  (e: 'image-error', event: Event): void
}>()

const { t } = useI18n()
</script>

<style scoped lang="scss">
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: "Nunito Sans", sans-serif;
}
.swiper {
  width: 100%;
  padding: 1.875rem 0;
}
.swiper-slide {
  width: 10.75rem;
  height: 25rem;
  display: flex;
  flex-direction: column;
  justify-content: end;
  align-items: self-start;
  box-shadow: 0.063rem 0.5rem 1.25rem hsl(0deg 0% 0% / 12.16%);
  border-bottom-left-radius: 0.5rem;
  border-bottom-right-radius: 0.5rem;
  background-color: #fff;
  overflow: hidden;
  position: relative;

  &-img {
    position: relative;
    width: 100%;
    height: 18rem;
    flex-shrink: 0;
    overflow: hidden;
    line-height: 0;
    background-color: #1a262f;

    img {
      width: 100%;
      height: 100%;
      position: absolute;
      inset: 0;
      object-fit: cover;
      z-index: 0;
      transition: transform 0.3s ease-in-out;
    }

    svg {
      position: absolute;
      bottom: -1px;
      left: 0;
      display: block;
      width: calc(300% + 1.3px);
      height: 5rem;
      transform: scaleY(-1);
      z-index: 1;
    }
    .shape-fill {
      fill: #ffffff;
    }
  }

  &-content {
    position: relative;
    z-index: 2;
    background: #fff;
    border-bottom-left-radius: 0.5rem;
    border-bottom-right-radius: 0.5rem;
    padding: 0 1.65rem;
    flex: 1;
    display: flex;
    flex-direction: column;
    width: 100%;

    > div {
      // transform: translateY(-0.75rem);
    }

    h2 {
      color: #000;
      font-family: "Raleway", sans-serif;
      font-weight: 700;
      font-size: 1.4rem;
      line-height: 1.4;
      margin-bottom: 0.425rem;
      text-transform: capitalize;
      letter-spacing: 0.02rem;
      white-space: nowrap;
      text-overflow: ellipsis;
    }

    p {
      color: #000 !important;
      line-height: 1.6;
      font-size: 0.9rem;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .show-more {
      width: 3.125rem;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f5593d;
      border-radius: 50%;
      box-shadow: 0px 0.125rem 0.875rem #e7882f6b;
      margin-top: 1em;
      margin-bottom: 0.8em;
      height: 0;
      opacity: 0;
      transition: opacity 0.3s ease-in;
      margin-left: auto;

      &:hover {
        background: #cc462f;
      }

      svg {
        width: 1.75rem;
        color: #fff;
      }
    }
  }
}

.swiper-slide-active:hover img {
  transform: scale(1.2) rotate(-5deg);
}

.swiper-slide-active:hover .show-more {
  opacity: 1;
  height: 3.125rem;
}

.swiper-slide-active:hover p {
  display: block;
  overflow: visible;
}

.swiper-3d .swiper-slide-shadow-left,
.swiper-3d .swiper-slide-shadow-right {
  background-image: none;
}

@media screen and (min-width: 93.75rem) {
  .swiper {
    width: 85%;
  }
}
</style>
