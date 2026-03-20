import enUS from 'ant-design-vue/es/locale/en_US'
import jaJP from 'ant-design-vue/es/locale/ja_JP'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import type { AppLocale } from './messages'

type AntdLocale = typeof zhCN

const antdLocales: Record<AppLocale, AntdLocale> = {
  'zh-CN': zhCN,
  'en-US': enUS,
  'ja-JP': jaJP,
}

const dayjsLocaleKeys: Record<AppLocale, string> = {
  'zh-CN': 'zh-cn',
  'en-US': 'en',
  'ja-JP': 'ja',
}

export function getAntdLocale(locale: AppLocale): AntdLocale {
  return antdLocales[locale]
}

export function getDayjsLocaleKey(locale: AppLocale): string {
  return dayjsLocaleKeys[locale]
}
