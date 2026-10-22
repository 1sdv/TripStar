/**
 * TripStar 复刻指南 — PI-Desktop 插件入口。
 *
 * 这个插件只贡献一个 skill 文档（skills/tripstar-trip-planner.md），
 * 没有运行时 UI、没有命令、没有面板，所以 onLoad/onUnload 保持空实现即可。
 */

async function onLoad() {
  // 无需初始化动作：skill 文档由宿主在插件启用时注入系统提示。
}

async function onUnload() {
  // 无需清理。
}

module.exports = { onLoad, onUnload };