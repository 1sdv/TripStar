<template>
  <div class="ai-chat-floating">
    <div class="container-ai-input">
      <div v-for="index in 15" :key="`chat-area-${index}`" class="area"></div>
      <div class="container-wrap" :class="{ open: chatOpen }">
        <div class="card">
          <div class="background-blur-balls">
            <div class="balls">
              <span class="ball rosa"></span>
              <span class="ball violet"></span>
              <span class="ball green"></span>
              <span class="ball cyan"></span>
            </div>
          </div>
          <div class="content-card" :class="{ clickable: !chatOpen }" @click="openChatPanel">
            <div class="background-blur-card">
              <div class="eyes">
                <span class="eye"></span>
                <span class="eye"></span>
              </div>
              <div class="eyes happy">
                <svg fill="none" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M8.28386 16.2843C8.9917 15.7665 9.8765 14.731 12 14.731C14.1235 14.731 15.0083 15.7665 15.7161 16.2843C17.8397 17.8376 18.7542 16.4845 18.9014 15.7665C19.4323 13.1777 17.6627 11.1066 17.3088 10.5888C16.3844 9.23666 14.1235 8 12 8C9.87648 8 7.61556 9.23666 6.69122 10.5888C6.33728 11.1066 4.56771 13.1777 5.09858 15.7665C5.24582 16.4845 6.16034 17.8376 8.28386 16.2843Z"
                  ></path>
                </svg>
                <svg fill="none" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M8.28386 16.2843C8.9917 15.7665 9.8765 14.731 12 14.731C14.1235 14.731 15.0083 15.7665 15.7161 16.2843C17.8397 17.8376 18.7542 16.4845 18.9014 15.7665C19.4323 13.1777 17.6627 11.1066 17.3088 10.5888C16.3844 9.23666 14.1235 8 12 8C9.87648 8 7.61556 9.23666 6.69122 10.5888C6.33728 11.1066 4.56771 13.1777 5.09858 15.7665C5.24582 16.4845 6.16034 17.8376 8.28386 16.2843Z"
                  ></path>
                </svg>
              </div>
            </div>
          </div>
          <div class="container-ai-chat" @click.stop>
            <button type="button" class="chat-close-btn btn-round btn-danger" @click.stop="closeChatPanel">×</button>
            <div class="chat">
              <div class="chat-bot">
                <div class="chat-history" ref="chatMessagesRef">
                  <div v-if="chatHistory.length === 0" class="chat-empty">
                    <p>{{ t('result.chat.welcome') }}</p>
                    <div class="chat-suggestions">
                      <button
                        v-for="question in quickQuestions"
                        :key="question.labelKey"
                        type="button"
                        class="chat-suggestion"
                        :disabled="chatLoading || !tripPlan"
                        @click="sendQuickQuestion(t(question.questionKey))"
                      >
                        {{ t(question.labelKey) }}
                      </button>
                    </div>
                  </div>
                  <div
                    v-for="(msg, idx) in chatHistory"
                    :key="`chat-${idx}`"
                    class="chat-msg"
                    :class="msg.role"
                  >
                    {{ msg.content }}
                  </div>
                  <div v-if="chatLoading" class="chat-msg assistant typing">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                  </div>
                </div>
                <textarea
                  v-model="chatInput"
                  :placeholder="chatPlaceholder"
                  name="chat_bot"
                  id="chat_bot"
                  :disabled="chatLoading || !tripPlan"
                  @keydown.enter.exact.prevent="sendChatMessage"
                ></textarea>
              </div>
              <div class="options">
                <div class="btns-add">
                  <button type="button" disabled>
                    <svg
                      viewBox="0 0 24 24"
                      height="20"
                      width="20"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M7 8v8a5 5 0 1 0 10 0V6.5a3.5 3.5 0 1 0-7 0V15a2 2 0 0 0 4 0V8"
                        stroke-width="2"
                        stroke-linejoin="round"
                        stroke-linecap="round"
                        stroke="currentColor"
                        fill="none"
                      ></path>
                    </svg>
                  </button>
                  <button type="button" disabled>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                    >
                      <path
                        fill="none"
                        stroke="currentColor"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1zm0 10a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1zm10 0a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1zm0-8h6m-3-3v6"
                      ></path>
                    </svg>
                  </button>
                  <button type="button" disabled>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                    >
                      <path
                        fill="currentColor"
                        d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10s-4.477 10-10 10m-2.29-2.333A17.9 17.9 0 0 1 8.027 13H4.062a8.01 8.01 0 0 0 5.648 6.667M10.03 13c.151 2.439.848 4.73 1.97 6.752A15.9 15.9 0 0 0 13.97 13zm9.908 0h-3.965a17.9 17.9 0 0 1-1.683 6.667A8.01 8.01 0 0 0 19.938 13M4.062 11h3.965A17.9 17.9 0 0 1 9.71 4.333A8.01 8.01 0 0 0 4.062 11m5.969 0h3.938A15.9 15.9 0 0 0 12 4.248A15.9 15.9 0 0 0 10.03 11m4.259-6.667A17.9 17.9 0 0 1 15.973 11h3.965a8.01 8.01 0 0 0-5.648-6.667"
                      ></path>
                    </svg>
                  </button>
                </div>
                <button
                  type="button"
                  class="btn-submit"
                  :disabled="chatLoading || !chatInput.trim() || !tripPlan"
                  @click="sendChatMessage"
                >
                  <i>
                    <svg viewBox="0 0 512 512">
                      <path
                        d="M473 39.05a24 24 0 0 0-25.5-5.46L47.47 185h-.08a24 24 0 0 0 1 45.16l.41.13l137.3 58.63a16 16 0 0 0 15.54-3.59L422 80a7.07 7.07 0 0 1 10 10L226.66 310.26a16 16 0 0 0-3.59 15.54l58.65 137.38c.06.2.12.38.19.57c3.2 9.27 11.3 15.81 21.09 16.25h1a24.63 24.63 0 0 0 23-15.46L478.39 64.62A24 24 0 0 0 473 39.05"
                        fill="currentColor"
                      ></path>
                    </svg>
                  </i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import type { ChatMessage, TripPlan } from '@/types'

const props = defineProps<{
  tripPlan: TripPlan | null
}>()

const { t } = useI18n()
const chatOpen = ref(false)
const chatInput = ref('')
const chatHistory = ref<ChatMessage[]>([])
const chatLoading = ref(false)
const chatMessagesRef = ref<HTMLElement | null>(null)

const quickQuestions = [
  {
    labelKey: 'result.chat.quickPriceLabel',
    questionKey: 'result.chat.quickPriceQuestion',
  },
  {
    labelKey: 'result.chat.quickSuitabilityLabel',
    questionKey: 'result.chat.quickSuitabilityQuestion',
  },
  {
    labelKey: 'result.chat.quickMealLabel',
    questionKey: 'result.chat.quickMealQuestion',
  },
]

const chatPlaceholder = computed(() => {
  if (!props.tripPlan) return t('result.noTripPlanDesc')
  return t('result.chat.placeholder')
})

const scrollChatToBottom = () => {
  nextTick(() => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    }
  })
}

watch(chatOpen, (open) => {
  if (open) scrollChatToBottom()
})

const openChatPanel = () => {
  if (!chatOpen.value) {
    chatOpen.value = true
  }
}

const closeChatPanel = () => {
  chatOpen.value = false
}

const sendQuickQuestion = (q: string) => {
  chatInput.value = q
  void sendChatMessage()
}

const sendChatMessage = async () => {
  const text = chatInput.value.trim()
  if (!text || chatLoading.value || !props.tripPlan) return

  chatHistory.value.push({ role: 'user', content: text })
  chatInput.value = ''
  chatLoading.value = true
  scrollChatToBottom()

  try {
    const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''
    const res = await axios.post(`${apiBase}/api/chat/ask`, {
      message: text,
      trip_plan: props.tripPlan,
      history: chatHistory.value.slice(0, -1),
    })

    if (res.data.success) {
      chatHistory.value.push({ role: 'assistant', content: res.data.reply })
    } else {
      chatHistory.value.push({ role: 'assistant', content: t('result.chat.replyFallback') })
    }
  } catch (err) {
    console.error('Chat error:', err)
    chatHistory.value.push({ role: 'assistant', content: t('result.chat.networkError') })
  } finally {
    chatLoading.value = false
    scrollChatToBottom()
  }
}
</script>

<style scoped lang="scss">
.ai-chat-floating {
  position: fixed;
  left: 38px;
  bottom: 58px;
//   width: 260px;
//   height: 260px;
  z-index: 1000;
  transform: scale(0.39);
}

.container-ai-input {
  --perspective: 1000px;
  --translateY: 45px;
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  transform-style: preserve-3d;
}

.container-wrap {
  display: flex;
  align-items: center;
  justify-items: center;
  position: absolute;
  left: 0;
  bottom: 0;
  z-index: 9;
  transform-style: preserve-3d;
  cursor: default;
  padding: 4px;
  transition: all 0.3s ease;
}

.container-wrap:hover {
  padding: 0;
}

.container-wrap:active {
  transform: scale(0.95);
}

.container-wrap:after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translateX(-50%) translateY(-55%);
  width: 12rem;
  height: 11rem;
  background-color: #dedfe0;
  border-radius: 2rem;
  transition: all 0.3s ease;
}

.container-wrap:hover:after {
  transform: translateX(-50%) translateY(-50%);
  height: 10rem;
}

.container-wrap.open .eyes {
  opacity: 0;
}

.container-wrap.open .content-card {
  width: 1260px;
  height: 1100px;
}

.container-wrap.open .background-blur-balls {
  border-radius: 24px;
}

.container-wrap.open .container-ai-chat {
  opacity: 1;
  visibility: visible;
  z-index: 99999;
  pointer-events: auto;
}

.card {
  width: 100%;
  height: 100%;
  /* background-color: #fff; */
  position: relative;
  transform-style: preserve-3d;
  will-change: transform;
  transition: all 0.6s ease;
  border-radius: 3rem;
  display: flex;
  align-items: flex-end;
  transform: translateZ(50px);
  justify-content: flex-start;
}

.card:hover {
  box-shadow:
    0 10px 40px rgba(0, 0, 60, 0.25),
    inset 0 0 10px rgba(255, 255, 255, 0.5);
}

.background-blur-balls {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  z-index: -10;
  border-radius: 3rem;
  transition: all 0.3s ease;
  background-color: rgba(255, 255, 255, 0.8);
  overflow: hidden;
}
.balls {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translateX(-50%) translateY(-50%);
  animation: rotate-background-balls 10s linear infinite;
}

.container-wrap:hover .balls {
  animation-play-state: paused;
}

.background-blur-balls .ball {
  width: 6rem;
  height: 6rem;
  position: absolute;
  border-radius: 50%;
  filter: blur(30px);
}

.background-blur-balls .ball.violet {
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  background-color: #9147ff;
}

.background-blur-balls .ball.green {
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  background-color: #34d399;
}

.background-blur-balls .ball.rosa {
  top: 50%;
  left: 0;
  transform: translateY(-50%);
  background-color: #ec4899;
}

.background-blur-balls .ball.cyan {
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  background-color: #05e0f5;
}

.content-card {
  width: 12rem;
  height: 12rem;
  display: flex;
  border-radius: 3rem;
  transition: all 0.3s ease;
  overflow: hidden;
}

.content-card.clickable {
  cursor: pointer;
}

.background-blur-card {
  width: 100%;
  height: 100%;
  backdrop-filter: blur(50px);
}

.eyes {
  position: absolute;
  left: 50%;
  bottom: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  height: 52px;
  gap: 2rem;
  transition: all 0.3s ease;

  & .eye {
    width: 26px;
    height: 52px;
    background-color: #fff;
    border-radius: 16px;
    animation: animate-eyes 10s infinite linear;
    transition: all 0.3s ease;
  }
}

.eyes.happy {
  display: none;
  color: #fff;
  gap: 0;

  & svg {
    width: 60px;
  }
}

.container-wrap:hover .eyes .eye {
  display: none;
}

.container-wrap:hover .eyes.happy {
  display: flex;
}

.container-ai-chat {
  position: absolute;
  width: 100%;
  height: 100%;
  padding: 36px;
  opacity: 0;
  pointer-events: none;
}

.container-ai-chat .chat-close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 3;
  width: 62px;
  height: 62px;
  border: none;
  border-radius: 50%;
//   background: rgba(0, 0, 0, 0.12);
//   color: rgba(255, 255, 255, 0.92);
  font-size: 50px;
  line-height: 1;
  cursor: pointer;
}

.container-wrap .card .chat {
  display: flex;
  justify-content: space-between;
  flex-direction: column;
  border-radius: 15px;
  width: 100%;
  height: 100%;
  padding: 90px 20px 20px;
  overflow: hidden;
  background-color: #ffffff;
}

.container-wrap .card .chat .chat-bot {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  transition: all 0.3s ease;
}

.card .chat .chat-bot .chat-history {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border-radius: 12px;
  padding: 26px 26px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: rgba(0, 0, 0, 0.03);

  &::-webkit-scrollbar {
    width: 12px;
  }

  &::-webkit-scrollbar-thumb {
    background: #dedfe0;
    border-radius: 5px;
  }
}

.card .chat .chat-bot .chat-empty {
  color: #8b8b8b;
  line-height: 1.5;

  p {
    margin: 0;
    font-size: 32px;
  }
}

.card .chat .chat-bot .chat-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}

.card .chat .chat-bot .chat-suggestion {
  border: none;
  border-radius: 20px;
  padding: 8px 16px;
  font-size: 30px;
  background-color: #f5593d;
  border-color: #f5593d;
  color: #ffffff;
  opacity: 1;
  filter: alpha(opacity=100);
//   background: linear-gradient(135deg, #ff4141, #9147ff, #3b82f6);
  cursor: pointer;
  transition: all 0.2s ease;
}

.card .chat .chat-bot .chat-suggestion:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.card .chat .chat-bot .chat-msg {
  max-width: 92%;
  font-size: 29px;
  line-height: 1.5;
  border-radius: 20px;
  padding: 8px 16px;
  color: #3f3f3f;
  background: #f3f6fd;
  white-space: pre-wrap;
  word-break: break-word;
}

.card .chat .chat-bot .chat-msg.user {
  margin-left: auto;
  background-color: #f5593d;
  border-color: #f5593d;
  color: #ffffff;
  opacity: 1;
  filter: alpha(opacity=100);

//   background: linear-gradient(135deg, #ff4141, #9147ff);
}

.card .chat .chat-bot .chat-msg.assistant {
  margin-right: auto;
}

.card .chat .chat-bot .chat-msg.typing {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
}

.card .chat .chat-bot .chat-msg.typing .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
//   background: #9147ff;
  background-color: #f5593d;
  border-color: #f5593d;
  color: #ffffff;
  opacity: 1;
  filter: alpha(opacity=100);
  animation: aiChatDotPulse 1.4s infinite ease-in-out both;
}

.card .chat .chat-bot .chat-msg.typing .dot:nth-child(2) {
  animation-delay: 0.16s;
}

.card .chat .chat-bot .chat-msg.typing .dot:nth-child(3) {
  animation-delay: 0.32s;
}

.card .chat .chat-bot textarea {
  background-color: transparent;
  border-radius: 16px;
  border: none;
  width: 100%;
  min-height: 156px;
  max-height: 178px;
  color: #8b8b8b;
  font-family: sans-serif;
  font-size: 36px;
  font-weight: 400;
  padding: 10px;
  resize: none;
  outline: none;

  &::-webkit-scrollbar {
    width: 6px;
    height: 10px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: #dedfe0;
    border-radius: 5px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: #8b8b8b;
    cursor: pointer;
  }

  &::placeholder {
    color: #dedfe0;
    transition: all 0.3s ease;
  }
  &:focus::placeholder {
    color: #8b8b8b;
  }
}

.card .chat .options {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 20px;

  & button {
    transition: all 0.3s ease;
  }
}

.card .chat .options .btns-add {
  display: flex;
  gap: 16px;

  & button {
    display: flex;
    color: rgba(0, 0, 0, 0.1);
    background-color: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-10px);
      color: #8b8b8b;
    }
  }
}

.card .chat .options .btn-submit {
  display: flex;
  padding: 15px;
  background-color: #f5593d;
  border-color: #f5593d;
  color: #ffffff;
  opacity: 1;
  filter: alpha(opacity=100);
//   background-image: linear-gradient(to top, #ff4141, #9147ff, #3b82f6);
  border-radius: 10px;
  box-shadow: inset 0 6px 2px -4px rgba(255, 255, 255, 0.5);
  cursor: pointer;
  border: none;
  outline: none;
  opacity: 0.7;
//   transform: translateY(-100%);
  transition: all 0.15s ease;

  & i {
    width: 60px;
    height: 60px;
    padding: 6px;
    background: rgba(0, 0, 0, 0.1);
    border-radius: 10px;
    backdrop-filter: blur(3px);
    color: #cfcfcf;
  }
  & svg {
    transition: all 0.3s ease;
  }
  &:hover {
    opacity: 1;
    & svg {
      color: #f3f6fd;
      filter: drop-shadow(0 0 5px #ffffff);
    }
  }

  &:focus svg {
    color: #f3f6fd;
    filter: drop-shadow(0 0 5px #ffffff);
    transform: scale(1.2) rotate(45deg) translateX(-2px) translateY(1px);
  }

  &:active {
    transform: scale(0.92);
  }
}

.card .chat .options .btn-submit:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

@keyframes aiChatDotPulse {
  0%, 80%, 100% {
    transform: scale(0.4);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.area:nth-child(15):hover ~ .container-wrap .card,
.area:nth-child(15):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(-15deg) rotateY(15deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(14):hover ~ .container-wrap .card,
.area:nth-child(14):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(-15deg) rotateY(7deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(13):hover ~ .container-wrap .card,
.area:nth-child(13):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(-15deg) rotateY(0)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(12):hover ~ .container-wrap .card,
.area:nth-child(12):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(-15deg) rotateY(-7deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(11):hover ~ .container-wrap .card,
.area:nth-child(11):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(-15deg) rotateY(-15deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(10):hover ~ .container-wrap .card,
.area:nth-child(10):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(0) rotateY(15deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(9):hover ~ .container-wrap .card,
.area:nth-child(9):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(0) rotateY(7deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(8):hover ~ .container-wrap .card,
.area:nth-child(8):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(0) rotateY(0)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(7):hover ~ .container-wrap .card,
.area:nth-child(7):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(0) rotateY(-7deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(6):hover ~ .container-wrap .card,
.area:nth-child(6):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(0) rotateY(-15deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(5):hover ~ .container-wrap .card,
.area:nth-child(5):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(15deg) rotateY(15deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(4):hover ~ .container-wrap .card,
.area:nth-child(4):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(15deg) rotateY(7deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(3):hover ~ .container-wrap .card,
.area:nth-child(3):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(15deg) rotateY(0)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(2):hover ~ .container-wrap .card,
.area:nth-child(2):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(15deg) rotateY(-7deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}
.area:nth-child(1):hover ~ .container-wrap .card,
.area:nth-child(1):hover ~ .container-wrap .eyes .eye {
  transform: perspective(var(--perspective)) rotateX(15deg) rotateY(-15deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(15):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(15):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(-10deg) rotateY(8deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(14):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(14):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(-10deg) rotateY(4deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(13):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(13):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(-10deg) rotateY(0deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(12):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(12):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(-10deg) rotateY(-4deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(11):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(11):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(-10deg) rotateY(-8deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(10):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(10):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(0deg) rotateY(8deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(9):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(9):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(0deg) rotateY(4deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(8):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(8):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(0deg) rotateY(0deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(7):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(7):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(0deg) rotateY(-4deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(6):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(6):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(0deg) rotateY(-8deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(5):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(5):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(10deg) rotateY(8deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(4):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(4):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(10deg) rotateY(4deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(3):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(3):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(10deg) rotateY(0deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(2):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(2):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(10deg) rotateY(-4deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

.area:nth-child(1):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .options
  button,
.area:nth-child(1):hover
  ~ .container-wrap
  .card
  .container-ai-chat
  .chat
  .chat-bot {
  transform: perspective(var(--perspective)) rotateX(10deg) rotateY(-8deg)
    translateZ(var(--translateY)) scale3d(1, 1, 1);
}

@keyframes rotate-background-balls {
  from {
    transform: translateX(-50%) translateY(-50%) rotate(360deg);
  }
  to {
    transform: translateX(-50%) translateY(-50%) rotate(0);
  }
}

@keyframes animate-eyes {
  46% {
    height: 52px;
  }
  48% {
    height: 20px;
  }
  50% {
    height: 52px;
  }
  96% {
    height: 52px;
  }
  98% {
    height: 20px;
  }
  100% {
    height: 52px;
  }
}

@media (max-width: 768px) {
  .ai-chat-floating {
    left: 12px;
    bottom: 12px;
    width: 220px;
    height: 220px;
  }

  .container-wrap.open .content-card {
    width: 300px;
    height: 220px;
  }

  .container-wrap:after {
    width: 6.5rem;
    height: 6rem;
  }

  .container-wrap:hover:after {
    height: 6.5rem;
  }

  .content-card {
    width: 6.5rem;
    height: 6.5rem;
  }
}
</style>
