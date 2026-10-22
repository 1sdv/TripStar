/**
 * TripStar 结果页 UI 断言（浏览器内运行）
 *
 * 用法 1（DevTools 控制台）：打开 /result?plan_id=<id>，整段粘贴回车。
 * 用法 2（PI-Desktop Browser 工具）：把本文件内容作为 evaluate 表达式执行。
 *
 * 返回 { pass, fail, checks: [{name, ok, detail}] }。
 * 仅在"已拿到 TripPlan"时全绿；页面处于空状态会明确报 DATA。
 */
window.__tripstarUiAssert = (async () => {
  const results = [];
  const add = (name, ok, detail = '') => results.push({ name, ok: !!ok, detail: String(detail) });
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const q = (s) => document.querySelector(s);
  const qa = (s) => Array.from(document.querySelectorAll(s));
  const txt = (s) => (q(s) ? q(s).innerText.replace(/\s+/g, ' ').trim() : '');
  const menuByText = (t) => qa('.top-switch-menu .ant-menu-item').find((e) => e.innerText.trim() === t);
  const clickSection = async (t, ms = 900) => {
    const el = menuByText(t);
    if (!el) return false;
    el.click();
    await wait(ms);
    return true;
  };
  const isShown = (sel) => {
    const el = q(sel);
    if (!el) return false;
    const cs = getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden' && el.getBoundingClientRect().height > 0;
  };

  // ---------- 0. 数据装载 ----------
  for (let i = 0; i < 60; i++) {
    if (q('.content-wrapper') || q('.empty-state-panel')) break;
    await wait(250);
  }
  if (!q('.content-wrapper')) {
    const empty = !!q('.empty-state-panel');
    add('DATA 页面已装载 TripPlan', false, empty ? '处于空状态：sessionStorage 无 tripPlan 且后端回补失败（检查 plan_id / CORS / 后端是否在跑）' : '页面未渲染');
    return { pass: 0, fail: results.length, checks: results };
  }
  add('DATA 页面已装载 TripPlan', true, 'city=' + (JSON.parse(sessionStorage.getItem('tripPlan') || '{}').city || '?'));

  // ---------- 1. 骨架与导航 ----------
  add('SKELETON .result-container', !!q('.result-container'));
  const menus = qa('.top-switch-menu .ant-menu-item').map((e) => e.innerText.trim());
  add('SKELETON 分区导航 ≥5 项', menus.length >= 5, menus.join(' | '));

  // ---------- 2. 概览（Swiper） ----------
  await clickSection('行程概览', 1200);
  const slides = qa('.overview-swiper .swiper-slide').length;
  add('OVERVIEW 概览卡片 >0', slides > 0, 'slides=' + slides);
  add('OVERVIEW Swiper 已实例化', !!q('.overview-swiper .swiper-initialized'));
  add('OVERVIEW 日期/建议 meta', /至|~|Plan ID/.test(txt('.overview-meta')), txt('.overview-meta').slice(0, 60));

  // ---------- 3. 预算 ----------
  if (menuByText('预算明细')) {
    await clickSection('预算明细');
    add('BUDGET 分区可见', isShown('#budget'));
    const total = txt('.budget-summary-total-value');
    add('BUDGET 总额为数字', /^\d+(\.\d+)?$/.test(total), 'total=' + total);
    add('BUDGET 子项 ≥4', qa('.budget-summary-sub-item').length >= 4, qa('.budget-summary-sub-item').length + ' 项');
    add('BUDGET 明细行 >0', qa('.budget-detail-row:not(.budget-detail-header)').length > 0, qa('.budget-detail-row:not(.budget-detail-header)').length + ' 行');
  } else {
    add('BUDGET 分区存在', false, '无「预算明细」菜单项（tripPlan.budget 为空）');
  }

  // ---------- 4. 每日行程 ----------
  await clickSection('每日行程', 1000);
  add('DAYS 卡片可见', isShown('.days-card'));
  const panels = qa('.days-card .ant-collapse-item').length;
  add('DAYS 天数面板 >0', panels > 0, panels + ' 天');
  add('DAYS 首日景点 >0', qa('#day-0 .attraction-card').length > 0, qa('#day-0 .attraction-card').length + ' 个');
  add('DAYS 首日餐饮 >0', qa('#day-0 .ant-descriptions-row').length > 0);

  // ---------- 5. 天气 ----------
  if (menuByText('天气信息')) {
    await clickSection('天气信息');
    add('WEATHER 分区可见', isShown('#weather'));
    add('WEATHER 温度形如 N°C', /^\d+°C$/.test(txt('.weather-temp')), txt('.weather-temp'));
    add('WEATHER 天气文字非空', txt('.weather-desc').length > 0, txt('.weather-desc'));
    const icon = (q('.weather-hero-icon') || {}).classList;
    const kinds = ['sunny', 'rainy', 'cloudy', 'sun-shower', 'thunder-storm', 'flurries'];
    add('WEATHER CSS 图标已选中', !!icon && kinds.some((k) => icon.contains(k)), icon ? kinds.find((k) => icon.contains(k)) : 'none');
    add('WEATHER 未来几天列表 >0', qa('.week-list > li').length > 0, qa('.week-list > li').length + ' 天');
    add('WEATHER 明细 5 行', qa('.today-info-item').length === 5, qa('.today-info-item').length + ' 行');
  } else {
    add('WEATHER 分区存在', false, '无「天气信息」菜单项（tripPlan.weather_info 为空）');
  }

  // ---------- 6. 知识图谱（ECharts 真的画了像素） ----------
  await clickSection('知识图谱', 2400);
  add('KG 分区可见', isShown('#knowledge-graph'));
  add('KG 图例 8 类', qa('.kg-legend-item').length === 8, qa('.kg-legend-item').length + ' 类');
  const cv = q('#kg-chart-container canvas');
  add('KG canvas 已创建', !!cv, cv ? cv.width + 'x' + cv.height : 'none');
  let painted = -1;
  if (cv) {
    try {
      const ctx = cv.getContext('2d');
      const d = ctx.getImageData(0, 0, cv.width, Math.min(cv.height, 400)).data;
      painted = 0;
      for (let i = 3; i < d.length; i += 4) if (d[i] > 8) painted++;
    } catch (e) {
      painted = -2;
    }
  }
  add('KG 画布已绘制像素', painted > 1000, 'painted=' + painted);

  // ---------- 7. 地图（高德；Google 失败会降级） ----------
  await clickSection('景点地图', 800);
  for (let i = 0; i < 40; i++) {
    const a = q('#amap-container');
    if (a && a.querySelectorAll('canvas,img').length > 0) break;
    await wait(500);
  }
  await wait(1200);
  add('MAP 分区可见', isShown('.right-map'));
  const amap = q('#amap-container');
  add('MAP 高德容器有内容', !!amap && amap.children.length > 0, amap ? amap.children.length + ' 个子节点' : 'none');
  add('MAP 瓦片/画布已渲染', !!amap && amap.querySelectorAll('canvas,img').length > 0, amap ? amap.querySelectorAll('canvas,img').length + ' 个' : 0);
  add('MAP 景点标记 >0', !!amap && amap.querySelectorAll('.tripstar-map-marker, .amap-marker').length > 0,
    amap ? amap.querySelectorAll('.tripstar-map-marker, .amap-marker').length + ' 个' : 0);

  await clickSection('行程概览', 600);

  const fail = results.filter((r) => !r.ok);
  return {
    pass: results.length - fail.length,
    fail: fail.length,
    checks: results,
    failed: fail.map((f) => f.name + ' — ' + f.detail),
  };
})()
  .then((r) => {
    try {
      console.table(r.checks.map((c) => ({ check: c.name, ok: c.ok, detail: c.detail })));
    } catch (e) { /* ignore */ }
    appendSummary(r);
    return r;
  });

function appendSummary(r) {
  const line =
    'TripStar UI: ' + r.pass + ' pass / ' + r.fail + ' fail' +
    (r.failed && r.failed.length ? ' | failed: ' + r.failed.join('; ') : '');
  console.log(line);
}