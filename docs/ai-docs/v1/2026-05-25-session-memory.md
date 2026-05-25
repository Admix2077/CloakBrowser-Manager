# Codex Session 记忆文档

日期：2026-05-25

用途：为后续新开的 Codex session 保留当前上下文，避免丢失关键事实、设计决策和验证状态。

## 1. 仓库与运行状态

仓库路径：

```text
/home/jeff/code/cloakbrowser-invisible-manager
```

当前分支：

```text
feature/invisible-playwright-engine
```

当前最新关键提交：

```text
aa84726 fix: sync geoip language timezone fingerprints
```

当前本地服务曾部署到：

```text
http://100.104.13.11:8080/
```

Docker 容器名：

```text
invisible-browser-manager-live
```

Docker 镜像：

```text
invisible-browser-manager:latest
```

最近验证时服务状态：

- `/api/status` 可访问。
- 当前 profile 总数为 1。
- profile 名称/标识为 `1`。
- profile 运行中。

## 2. 已完成的重要改造

本轮之前已经完成并验证的核心能力：

- 将 CloakBrowser Manager 后端浏览器内核替换为 `invisible_playwright` / Firefox。
- 保留 manager 面板、profile 管理和 VNC Viewer。
- 增加自有 Automation REST API，用于替代原 CDP 思路。
- 修复强杀容器后 Firefox session restore 导致 profile 启动超时的问题。
- 修复 BrowserScan 出现的：
  - `Different time zones`
  - `Language mismatch`
- 增加 GeoIP 多 provider fallback：
  - `ip-api.com`
  - `ipapi.co`
  - `ipwho.is`
- 增加 `last_geoip_*` 字段，保存最近自动解析结果：
  - `last_geoip_ip`
  - `last_geoip_country_code`
  - `last_geoip_timezone`
  - `last_geoip_locale`
  - `last_geoip_source`
  - `last_geoip_resolved_at`
- 明确字段语义：
  - `timezone` / `locale` 是手动覆盖字段。
  - `last_geoip_*` 是自动检测结果。
  - 自动检测不覆盖手动字段，避免换代理/换国家后被旧值锁死。

## 3. BrowserScan 验证结论

曾使用 profile `1` 打开 BrowserScan 验证。

修复前异常：

- `Different time zones`
- `Language mismatch`
- 页面中 `Languages` 和 `Accept-Language header` 不一致。

修复后结果：

- `Browser fingerprint authenticity: 100%`
- BrowserScan 文本里未找到：
  - `Language mismatch`
  - `Different time`
- 当时落库结果：
  - IP: `23.144.4.92`
  - Country: `US`
  - Timezone: `America/Los_Angeles`
  - Locale: `en-US`
  - Source: `ip-api`

关键技术处理：

- Firefox / invisible_playwright 场景下，直接覆盖请求 header 不一定可靠。
- 最终采用“让 JS 暴露语言和 Firefox 实际 Accept-Language 对齐”的方案。
- `_browser_init_script("en-US")` 会将：
  - `navigator.language`
  - `navigator.languages`
  - `Intl` 相关 locale 表现
  与启动 locale 对齐。

## 4. 当前内核和自动化边界

当前内核是：

```text
Firefox through invisible_playwright
```

当前不是 Chromium CDP 产品形态。

不能把后续功能设计成必须依赖 Chromium CDP。自动化入口应继续基于项目已有 Automation REST API。

现有 Automation API 已覆盖：

- 获取运行中 profile 自动化信息。
- 页面列表。
- 页面跳转。
- 页面 evaluate。
- screenshot。
- clipboard get/set。

后续如果设计脚本/RPA，应优先封装现有 REST API，而不是假设 CDP 可用。

## 5. 当前后端关键文件

```text
backend/browser_manager.py
backend/geoip.py
backend/database.py
backend/main.py
backend/models.py
backend/tests/test_browser_manager.py
backend/tests/test_geoip.py
backend/tests/test_api.py
backend/tests/test_database.py
```

重点事实：

- `backend/browser_manager.py`
  - `_build_invisible_kwargs()` 映射 manager profile 到 `InvisiblePlaywright` 参数。
  - `_build_invisible_pin()` 映射 screen、GPU、hardware concurrency、color scheme。
  - `_filter_firefox_launch_args()` 会过滤不适合 Firefox/invisible_playwright 的危险参数。
  - `_browser_init_script()` 注入语言和剪贴板辅助脚本。
  - `BrowserManager.launch()` 会先校验 proxy，再分配 VNC，再解析 GeoIP，再启动 Firefox。
- `backend/geoip.py`
  - `resolve_network_geo()` 做多 provider fallback。
  - `resolve_profile_network_fingerprint()` 基于 `geoip=true` 自动补 timezone/locale。
  - 自动结果通过 `_geoip_result` 传回 launch 流程。
- `backend/database.py`
  - `update_profile_geoip_result()` 写入 `last_geoip_*`。
- `backend/main.py`
  - launch 成功后调用 `db.update_profile_geoip_result()`。

## 6. 当前前端关键文件

```text
frontend/src/App.tsx
frontend/src/components/ProfileList.tsx
frontend/src/components/ProfileForm.tsx
frontend/src/components/ProfileViewer.tsx
frontend/src/components/LaunchButton.tsx
frontend/src/components/StatusIndicator.tsx
frontend/src/hooks/useProfiles.ts
frontend/src/lib/api.ts
frontend/src/styles/globals.css
```

当前 UI 判断：

- `App.tsx` 是左侧 sidebar + 顶部 bar + 右侧内容的三段式结构。
- `ProfileList.tsx` 只做名称搜索和简单状态显示。
- `ProfileForm.tsx` 是长表单，分组包括 Basic、Network、Hardware、Behavior、Tags、Launch Args、Notes。
- `ProfileViewer.tsx` 是 VNC 画面加简单工具条。
- 当前体验更像开发者配置面板，不像多账号运营台。

## 7. 用户最新产品偏好

用户明确希望：

- 参考市面成熟指纹浏览器产品能力。
- 不只是修当前美国 IP / en-US 的问题，要考虑未来不同国家、不同代理、不同语言场景。
- 当前前端 UI 有点 low，需要用 frontend design skill / UI Pro Max 的思路升级。
- 优先方向是“健康 + 运营台”。
- 第一版深度是“可视化 + 轻检测”。
- 需要落盘计划和上下文记忆，便于开启新的 Codex session。

## 8. 已做过的头脑风暴结论

六顶帽子简要结论：

- 白帽：当前已有 profile、proxy、timezone、locale、geoip、screen、GPU、humanize、launch_args、VNC、Automation API、tags、last_geoip_*。
- 红帽：用户真正想看的是“这个账号现在能不能安全继续操作”，不是一堆底层字段。
- 黑帽：批量启动容易打满资源；自动同步不能只适配美国；Firefox 参数不能照搬 Chromium；VNC 手工操作和自动化操作可能冲突。
- 黄帽：现有架构已经有 profile 数据、持久目录、VNC、Automation API 和 GeoIP 基础，适合做运营台。
- 绿帽：可做健康状态、轻检测、环境条、批量动作、profile summary、模板、代理管理、检测历史、自动化控制台。
- 蓝帽：V1 先做健康运营台和轻检测，V1.5 做模板/代理管理/检测历史，V2 做团队/RPA/同步器。

## 9. 竞品调研摘要

成熟产品共性：

- AdsPower：
  - 批量创建。
  - Proxy List 检测和筛选。
  - 动态 IP 自动匹配 timezone/location。
  - Synchronizer。
  - RPA。
  - Team / Members。
  - Action Logs。
- GoLogin：
  - folders。
  - bulk actions。
  - cookie import/export。
  - team sharing。
  - cloud launch、API、automation。
- Multilogin：
  - profile template。
  - proxy template。
  - team roles。
  - CLI/API/script runner。
  - profile import/export。
- Dolphin Anty：
  - profile sorting/search。
  - mass actions。
  - tags/status/notes/folders。
  - synchronizer。
  - scenarios。
  - teamwork。
  - API。
- Octo Browser：
  - bulk profile creation。
  - profile/proxy/tag/cookie/startup switches。
  - API。
  - team settings。
  - action log。
- MoreLogin：
  - profile list。
  - quick edit。
  - bulk operations。
  - proxy detection。
  - Local API。

内化结论：

- V1 做 profile 健康运营台、轻检测、批量动作、筛选、视觉升级。
- V1.5 做 proxy manager、profile template、检测历史、批量导入导出、API 控制台。
- V2 做 RPA、同步器、团队权限、审计中心、cookie robot、短生命周期 automation profile。

## 10. 2026-05-25 至 2026-05-26 推进记录

### 10.1 01 契约边界与事实源

已提交：

```text
a1a1fb0 docs: define cloakbrowser runtime boundaries
```

完成内容：

- 新增 `docs/ai-docs/v1` 文档树。
- 明确 CloakBrowser、Project Mileage App、Project Mileage Payload 的职责边界。
- `tasks/progress.md` 中 01 已勾选。

### 10.2 02 指纹健康引擎后端

已提交：

```text
e7a5c69 feat: add profile health engine api
```

完成内容：

- 新增 `backend/health.py`。
- 新增 `GET /api/profiles/{id}/health`。
- 新增 `POST /api/profiles/{id}/health/check`。
- 成功 GeoIP 检测只写 `last_geoip_*`，不覆盖手动 `timezone` / `locale`。
- lookup 失败不清空旧检测结果。
- 无效 proxy 返回稳定 health response，不发起 GeoIP lookup。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q
# 11 passed

. .venv/bin/activate && python -m pytest backend/tests/test_health.py backend/tests/test_geoip.py backend/tests/test_api.py -q
# 77 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 216 passed
```

### 10.3 02 指纹健康引擎前端

完成内容：

- 新增前端 health 类型和 API client。
- 新增 `frontend/src/lib/health.ts`。
- 新增 `frontend/src/components/HealthBadge.tsx`。
- `useProfiles()` 增加 `healthByProfileId`，首屏按 profile id 集合拉取 cached health。
- `ProfileList` 在 profile 名称同行右侧显示 HealthBadge，第二行显示 warning summary 与 GeoIP 摘要。
- 搜索仍只按 profile 名称，不被 health 文案污染。

验证：

```bash
cd frontend && npm test -- --run
# 6 passed, 33 passed

cd frontend && npm run build
# built successfully

. .venv/bin/activate && python -m pytest backend/tests/test_health.py backend/tests/test_geoip.py backend/tests/test_api.py -q
# 77 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 216 passed
```

浏览器走查：

- 使用临时后端数据目录 `/tmp/cloakbrowser-manager-qa-data`，因为本机无 `/data` 写权限。
- 使用 `agent-browser` 打开 `http://127.0.0.1:5173/`。
- 桌面 `1440x900` 与移动 `390x844` 视口已检查。
- `可继续`、`需关注`、`不可用`、`未检测` 四种状态可见。
- warning / error / GeoIP 摘要没有明显重叠。
- 搜索 `需关注` 返回 `No matches`。
- 搜索 `Warning` 后选择 profile，编辑表单和 `Launch` 按钮仍可用。
- 控制台无相关应用错误。

02 模块已完成，`tasks/progress.md` 中 02 已勾选。

### 10.4 GitHub 远端事实

用户明确要求：

- 只能维护用户自己的 GitHub 账号下仓库。
- 不向上游 `CloakHQ/CloakBrowser-Manager.git` 推送。
- 如果需要远端，必须新建用户账号下的私有仓库。

当前事实：

- 本地分支为 `feature/invisible-playwright-engine`。
- `origin` fetch 仍指向上游：

```text
https://github.com/CloakHQ/CloakBrowser-Manager.git
```

- 已将 `origin` push URL 禁用：

```text
DISABLED_DO_NOT_PUSH_TO_UPSTREAM
```

- 此前尝试推送上游失败，GitHub 返回 401，没有成功在上游创建分支或提交。
- `gh auth status` 显示 active account 为 `Admix2077`，但 token/API 当前不可用或超时，不能用 CLI 创建私有仓库。
- 后续需要用户重新完成 `gh auth login`，或在 `Admix2077` 账号下手动创建私有仓库并提供 remote URL，再新增独立 remote 推送。

### 10.5 03 Profile 运营台：列表筛选与排序

完成内容：

- 新增 `frontend/src/lib/filters.ts`，集中实现 profile 过滤和排序。
- 新增 `frontend/src/components/ProfileFilters.tsx`。
- 现有 `ProfileList` 接入紧凑筛选区，仍保持 sidebar 单选 profile -> 右侧编辑/VNC 的原有路径。
- 支持：
  - search。
  - runtime status。
  - health status。
  - proxy exists。
  - country。
  - tag。
  - sort by risk / last checked / name / runtime / country。
- 默认按风险排序：`error -> warning -> unknown -> good`。
- `last checked` 优先使用 `health.checked_at`，fallback 到 `profile.last_geoip_resolved_at`。
- 搜索仍只匹配 profile name，不把 health 中文状态、tag 或 GeoIP 文案纳入搜索。

验证：

```bash
cd frontend && npm test -- --run src/lib/filters.test.ts src/components/ProfileFilters.test.tsx src/components/ProfileList.test.tsx
# 3 passed, 11 passed

cd frontend && npm test -- --run
# 8 passed, 41 passed

cd frontend && npm run build
# built successfully
```

浏览器走查：

- 使用 `agent-browser` 打开 `http://127.0.0.1:5173/`。
- 桌面 `1440x900` 与移动 `390x844` 视口已检查。
- 默认风险排序、health/proxy/country/search 过滤、点击筛选结果进入编辑页、点击 `New Profile` 进入创建页均已验证。
- 控制台无相关应用错误。

### 10.6 03 Profile 运营台：只读 ProfileTable 主区

完成内容：

- 新增 `frontend/src/components/ProfileTable.tsx`。
- 新增 `frontend/src/components/ProfileTable.test.tsx`。
- 新增 `frontend/src/App.test.tsx`，覆盖 sidebar 筛选/排序同步主表格，以及窄屏默认收起 sidebar。
- `AppContent` 将 `ProfileFilterState` 上提，`ProfileList` 和 `ProfileTable` 共享同一组筛选、排序结果。
- `ProfileTable` 作为 `view === "empty"` 的主区 dense table，展示：
  - profile。
  - runtime。
  - health。
  - proxy。
  - IP。
  - country。
  - timezone。
  - locale。
  - tags。
  - last checked。
  - actions。
- `ProfileTable` 不再组件内二次排序，只消费 `AppContent` 传入的 filtered rows，避免覆盖用户选择的 `Name` / `Runtime` / `Country` / `Last checked` 排序。
- `Open` action 复用现有 `onSelect(profile.id)`，进入原有 edit / VNC viewer 流程。
- proxy 列显示可诊断但不暴露账号密码的标签：
  - 有效 URL 显示 `protocol//host`。
  - 无效 URL 显示 `Invalid proxy`。
  - 无 proxy 显示 `-`。
  - 可见文本和 `title` 均不保留 proxy 用户名密码。
- 窄屏初始收起 sidebar，让 390px 视口优先显示主表格；用户仍可通过 top bar 按钮打开筛选 sidebar。

已跑验证：

```bash
cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileTable.test.tsx src/components/ProfileList.test.tsx
# 3 passed, 13 passed

cd frontend && npm test -- --run
# 10 passed, 49 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 使用临时 QA 数据目录 `/tmp/cloakbrowser-manager-qa-data`。
- Vite dev server：`http://127.0.0.1:5173/`。
- `agent-browser` 在当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 截图保存到：
  - `/tmp/cloak-profile-table-desktop-v2.png`
  - `/tmp/cloak-profile-table-768-v2.png`
  - `/tmp/cloak-profile-table-mobile-v2.png`
  - `/tmp/cloak-profile-table-mobile-sidebar-v2.png`
- 桌面 `1440x900` 显示 dense table。
- `768x900` body 未横向撑破，table 在主区内横向滚动。
- `390x844` 默认 sidebar 收起，主表格占满首屏；打开 sidebar 后筛选区可用。
- 已验证 `Sort profiles = Name` 会同步主表格排序。
- 已验证 `Health status = 不可用` 会同步主表格筛选。
- 已验证点击 `Open QA Invalid Proxy` 进入原有编辑表单，`Launch`、`Delete`、`Cancel`、`Save` 仍可见。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。

范围说明：

- 03 模块仍未完成。
- 本小闭环不包含多选 checkbox、`BulkActionBar`、批量 launch/stop/health check/set tags/delete、右侧 summary panel 或移动 card list。
- `frontend/tsconfig.tsbuildinfo` 是当前仓库已跟踪的 TypeScript build metadata，历史前端提交也会更新；本轮作为显式已跟踪编译元数据处理，不做单独清理。

### 10.7 03 Profile 运营台：ProfileTable 多选状态

完成内容：

- `ProfileTable` 新增 `Select` 列。
- 每行新增 profile checkbox，点击只切换多选状态，不触发 `Open`。
- 表头新增 `Select all visible profiles` checkbox，只作用当前筛选后的可见 rows。
- 表头 checkbox 支持半选态。
- `AppContent` 新增独立 `selectedProfileIds`，和现有 `selectedId` / `view` 详情流分离。
- 筛选后隐藏的已选 profile 会自动清理，避免后续批量动作误作用到不可见 rows。
- 选择后显示轻量选择条：`N selected` + `Clear`。
- 空表格 `colSpan` 已随 Select 列更新。
- `tasks/03-profile-operations-console.md` 已勾选：
  - `新增 ProfileTable`。
  - `新增多选状态`。

已跑验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/App.test.tsx
# 2 passed, 10 passed

cd frontend && npm test -- --run
# 10 passed, 52 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- Vite dev server：`http://127.0.0.1:5173/`。
- QA 数据目录：`/tmp/cloakbrowser-manager-qa-data`。
- `agent-browser` 在当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 截图保存到：
  - `/tmp/cloak-profile-multiselect-desktop.png`
  - `/tmp/cloak-profile-multiselect-mobile.png`
- 桌面 `1440x900`：
  - 点击 `Select QA Invalid Proxy` 后出现 `1 selected` 和 `Clear`。
  - 表头 checkbox 呈半选态。
  - `Open` 按钮仍可见，未被选择条遮挡。
- 筛选：
  - 选择 invalid proxy 后切换 `Health status = 可继续`，隐藏选择被清理，不再显示 `1 selected`。
  - `Health status = 不可用` 后点击表头 checkbox，只选中当前可见的 invalid proxy。
- 移动 `390x844`：
  - 默认 sidebar 收起。
  - Select 列、选择条和横向滚动可用。
  - 选择条不遮挡 profile rows。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。

范围说明：

- 本小闭环不新增 `BulkActionBar` 文件。
- 不接入批量 launch / stop / health check / set tags / delete。
- 不新增后端 API 或 mutation。
- 后续应基于 `selectedProfileIds` 接 `BulkActionBar`，先做安全动作和清晰确认，再做危险动作。

### 10.8 03 Profile 运营台：左侧 ProfileList 虚拟滚动

背景：

- Jeff 反馈：几百个 profile 时，左侧列表全量渲染会卡顿。
- 本小闭环只优化左侧 `ProfileList` 渲染数量，不改 API，不做服务端分页，不改筛选/排序语义。

完成内容：

- `ProfileList` 在过滤结果超过 80 条时启用无依赖固定高度虚拟窗口。
- 列表项高度收敛为 112px，左侧列表继续定位为导航/扫视区；长 warning、GeoIP、tag 仍截断，完整信息继续在主表格或详情里查看。
- 虚拟窗口包含 overscan，减少滚动时的空白感。
- 筛选条件变化后重置左侧列表滚动位置，避免筛选后停留在旧滚动区导致空白窗口。
- 虚拟窗口起点做边界 clamp，列表数量从多变少时不会越界。
- `New Profile` 按钮仍固定在左侧底部，不受虚拟滚动影响。
- 选择 profile 仍按 `profile.id` 调用 `onSelect`。

已跑验证：

```bash
cd frontend && npm test -- --run src/components/ProfileList.test.tsx
# 1 passed, 8 passed

cd frontend && npm test -- --run
# 10 passed, 53 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-qa-data` 写入 180 个 `Perf Profile`，总计 184 个 profiles。
- Vite dev server：`http://127.0.0.1:5173/`。
- `agent-browser` 在当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 截图保存到：
  - `/tmp/cloak-profile-list-virtualized-desktop.png`
  - `/tmp/cloak-profile-list-virtualized-mobile.png`
- 桌面 `1440x900`：
  - 左侧 `Profiles list` 区域约渲染 18 个 profile button，而不是 184 个。
  - 左侧列表 `scrollHeight` 正常增大，滚动条可用。
  - 滚动到 `112 * 120` 后，`Perf Profile 120` 出现在左侧窗口内，`Perf Profile 000` 不在左侧 DOM 内。
  - `New Profile` 按钮仍固定在底部。
- 移动 `390x844`：
  - 打开 sidebar 后，左侧列表仍只渲染窗口内约 18 个 profile button。
  - 选择区、滚动条和底部 `New Profile` 可用。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。

范围说明：

- 主区 `ProfileTable` 当前仍会全量渲染过滤结果；几百行时短期可接受，但上千 profile 时应继续做主表格虚拟滚动。
- 本小闭环不引入 `react-window` 或 `@tanstack/react-virtual`；如果后续要求左侧 item 保持完全可变高度、多行 warning/tag 完整展示，再考虑引入支持测量动态高度的虚拟滚动库。
- 本小闭环不做服务端分页。服务端分页需要重新定义筛选、排序、select filtered 和批量操作契约，建议等 API/批量动作语义稳定后再进入。

### 10.9 03 Profile 运营台：主区 ProfileTable 虚拟滚动

背景：

- Jeff 追问确认：几百个 profile 不应主要靠左侧导航滚动管理。
- 产品信息架构判断：运营台应以主区 table、搜索筛选和批量操作为核心；左侧后续应逐步降级为最近、分组、收藏、状态快捷过滤和导航兜底。
- 因此左侧虚拟滚动保留为性能兜底，同时优先补齐主区 `ProfileTable` 大列表虚拟滚动。

完成内容：

- `ProfileTable` 在过滤结果超过 120 条时启用固定行高虚拟窗口。
- 保留原生 `table` / `thead` / `tbody` / `tr` 语义，用顶部和底部 spacer row 撑出总高度。
- 表格 row 高度收敛为 64px；tag 区域限制最大高度，避免长 tag 撑破虚拟滚动估算。
- `Profile operations table` 成为主表滚动根，sticky 选择条和 sticky 表头仍在同一容器内工作。
- 筛选结果变化后重置主表滚动位置，避免从大列表中段切到少量结果时出现空白窗口。
- 表头 `Select all visible profiles` 继续作用于当前筛选后的全部 rows，而不是当前虚拟窗口 rows。
- 滚动后可见行的 checkbox 和 `Open` action 仍按正确 profile id 工作。
- proxy 列继续只显示脱敏后的 `protocol//host` 或 `Invalid proxy`，不暴露 proxy 凭据。
- `tasks/03-profile-operations-console.md` 已勾选 `主区 ProfileTable 大列表虚拟滚动`。

已跑验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 1 passed, 10 passed

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/App.test.tsx src/components/ProfileList.test.tsx
# 3 passed, 22 passed

cd frontend && npm test -- --run
# 10 passed, 57 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-qa-data` 写入 240 个 `Perf Table Profile`。
- Vite dev server：`http://127.0.0.1:5173/`。
- 使用 `agent-browser`，当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 主区 `Profile operations table` 只渲染约 30 个 `Open Perf Table Profile` 按钮，而不是 240 个。
  - 滚动到中段后 `Perf Table Profile 120` 出现在主表窗口内，`Perf Table Profile 000` 不在主表 DOM 内。
  - 点击 `Select Perf Table Profile 120` 后显示 `1 selected`。
  - 点击表头 `Select all visible profiles` 后显示 `240 selected`，证明全选语义仍是当前筛选结果全集。
  - 搜索 `239` 后主表回到顶部，只显示 `Perf Table Profile 239`，没有旧虚拟窗口残留。
- 移动 `390x844`：
  - 刷新后 sidebar 默认收起。
  - 主表仍只渲染窗口内行。
  - 页面本体没有横向撑破，主表自身保留横向滚动。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。
- 截图保存到：
  - `/tmp/cloak-profile-table-virtualized-desktop.png`
  - `/tmp/cloak-profile-table-virtualized-mobile.png`
  - `/tmp/cloak-profile-table-virtualized-mobile-initial.png`

### 10.10 03 Profile 运营台：BulkActionBar 安全壳

背景：

- `ProfileTable` 已有多选状态和轻量 `N selected + Clear` 选择条。
- 本小闭环只把选择条升级为独立 `BulkActionBar` 组件，为后续真实批量动作提供稳定 UI 容器。
- 当前不接入任何批量 mutation，不伪造批量 launch / stop / health check / tag / delete 成功态。

完成内容：

- 新增 `frontend/src/components/BulkActionBar.tsx`。
- `ProfileTable` 用 `BulkActionBar` 替换原 inline 选择条，保留 `sticky top-0` 和 40px 高度，避免破坏 sticky table header 的 `top-10` 偏移。
- `BulkActionBar` 只消费受控 `selectedProfileIds` 派生出的 `selectedProfiles`，不持有选择状态。
- 展示 selected count、running count、stopped count、issue count 和 `Clear`。
- 预留 `Check health`、`Launch selected`、`Stop selected`、`Tag selected`、`Delete selected` 按钮，但全部 disabled，不调用 API。
- 不展示 proxy、cookie、token 等敏感字段。
- `tasks/03-profile-operations-console.md` 已勾选 `新增 BulkActionBar` 和浏览器验收 `批量选择后 action bar 不遮挡主要操作`。

已跑验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 1 passed, 11 passed

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/App.test.tsx src/components/ProfileList.test.tsx
# 3 passed, 23 passed

cd frontend && npm test -- --run
# 10 passed, 58 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-qa-data` 使用 240 个 profile。
- Vite dev server：`http://127.0.0.1:5173/`。
- 使用 `agent-browser`，当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 选择首行后显示 `Bulk profile actions` toolbar。
  - toolbar 显示 `1 selected`、running/stopped/issue 摘要。
  - `Check health`、`Launch selected`、`Stop selected`、`Tag selected`、`Delete selected` 均为 disabled。
  - `Clear` 可点击且不是 disabled。
  - 主表滚动到中段后 toolbar 仍 sticky 可见，表头仍可见，主表仍只渲染窗口内行。
- 移动 `390x844`：
  - 刷新后 sidebar 默认收起。
  - 选择首行后 toolbar 可见。
  - 页面本体没有横向撑破，主表自身保留横向滚动。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。
- 截图保存到：
  - `/tmp/cloak-bulk-action-bar-desktop.png`
  - `/tmp/cloak-bulk-action-bar-mobile.png`

## 11. 推荐下一步执行计划

下一次 session 可以从这个顺序开始：

1. 阅读本文档和同目录计划文档：
   - `docs/ai-docs/v1/2026-05-25-session-memory.md`
   - `docs/ai-docs/v1/2026-05-25-fingerprint-health-ops-plan.md`
   - `docs/ai-docs/v1/tasks/progress.md`
   - `docs/ai-docs/v1/tasks/03-profile-operations-console.md`
2. 检查工作区：
   - `git status --short`
3. 跑现有测试作为基线：
   - `. .venv/bin/activate && python -m pytest backend/tests -q`
   - `cd frontend && npm test -- --run`
   - `cd frontend && npm run build`
4. 从 03 Profile 运营台开始推进第一个可验证小闭环：
   - 第一批真实批量动作建议从 `health check` 开始，`delete` 必须单独确认闭环。
   - 后续再接批量 launch / stop / set tags。
5. 每个前端小闭环必须跑前端测试、build 和浏览器 UI/UE 走查。

## 12. 验证命令记录

之前已通过的验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests -q
```

结果：

```text
205 passed
```

```bash
cd frontend && npm test -- --run
```

结果：

```text
22 passed
```

```bash
cd frontend && npm run build
```

结果：

```text
build passed
```

Docker 构建和部署之前已通过：

```bash
docker build --network=host --platform linux/amd64 -t invisible-browser-manager:latest .
docker rm -f invisible-browser-manager-live
docker run -d --name invisible-browser-manager-live -p 100.104.13.11:8080:8080 -v invisible-browser-profiles:/data invisible-browser-manager:latest
```

## 13. GitHub 状态

用户之前希望创建 GitHub private repo 并 push。

阻塞点：

```text
gh auth token invalid
```

当时 `gh auth status` 显示账号 `Admix2077` 的 token 无效，需要用户重新执行：

```bash
gh auth login -h github.com
```

认证恢复后，可以继续创建 private repo 并 push。

## 14. 注意事项

- 不要把 `timezone` / `locale` 自动改写为 GeoIP 结果。
- 不要把当前项目重新设计成 Chromium CDP 架构。
- 不要在 V1 承诺“完整反检测评分”。
- 不要把第三方检测站抓取作为 V1 必需能力。
- UI 不要做营销页、hero、夸张渐变或游戏 HUD。
- 批量启动必须限制并发。
- 敏感 proxy 认证信息在 UI 中要遮蔽。
- 删除 profile 必须有确认。
- 后续涉及健康/代理/启动失败的改动应优先补测试。

## 14. 2026-05-25 新增文档树

用户补充要求：文档组织方式参考“需求文档 -> 概要设计 -> 详细设计 -> 模块任务 -> 总进度”的结构，但所有文件必须留在：

```text
/home/jeff/code/cloakbrowser-invisible-manager/docs/ai-docs/v1
```

已新增或更新：

- `2026-05-25-fingerprint-health-ops-plan.md`：主控总文档，作为后续 `/goal` 入口。
- `proposal.md`：需求文档。
- `high-level-design.md`：概要设计。
- `detailed-design.md`：详细设计。
- `goal-prompt.md`：新 session 可直接使用的 goal 说明。
- `tasks/progress.md`：模块总进度。
- `tasks/01-contract-and-boundaries.md`
- `tasks/02-health-engine.md`
- `tasks/03-profile-operations-console.md`
- `tasks/04-proxy-manager.md`
- `tasks/05-session-broker-project-mileage.md`
- `tasks/06-vnc-remote-workspace.md`
- `tasks/07-automation-api-script-runner.md`
- `tasks/08-cookie-profile-import-export.md`
- `tasks/09-templates-bulk-ops.md`
- `tasks/10-audit-security-rbac.md`
- `tasks/11-ui-visual-system.md`
- `tasks/12-deployment-observability.md`
- `tasks/13-regression-release.md`

核心新增方向：

- 终极目标不是只做第一版健康台，而是把 CloakBrowser 做成成熟指纹浏览器运行时平台。
- Project Mileage 的 `/app/remote-workspace`、`/app/remote-workspace/[id]/vnc`、`/ops/remote-monitor` 是未来集成入口。
- 当前 Project Mileage 远程相关页面仍是安全占位；必须等 Payload contract 确认会话、VNC token、钱包扣费、权限和审计后再解除占位。
- CloakBrowser 负责 runtime，Payload 负责授权/扣费/审计，App 负责用户和运营界面。

## 15. 2026-05-25 01 契约边界闭环

已完成 `tasks/01-contract-and-boundaries.md` 的契约边界与事实源闭环，并在 `tasks/progress.md` 勾选 01。

本轮结论：

- 01 只冻结契约边界和 `/api/runtime/*` 草案，不进入 Project Mileage 跨仓实现。
- Project Mileage 远程工作台、VNC 页面和运营远程监控仍保持安全占位。
- Payload 仍是用户身份、角色权限、账号/订单、钱包扣费、remote session 业务状态和业务审计事实源。
- CloakBrowser 仍是 profile、browser runtime、VNC runtime、Automation REST API、GeoIP、proxy 和 health 事实源。
- App 只能通过 Payload 安全 DTO 展示远程工作台和运营监控，不能直接调用 CloakBrowser runtime service API。
- CloakBrowser 当前已有单机 runtime 底座：profile CRUD、launch/stop/status、KasmVNC/noVNC WebSocket、Automation REST API 和 launch 时 GeoIP `last_geoip_*` 记录。
- CloakBrowser 当前没有 CDP 产品 API，没有多用户 RBAC，没有 runtime session broker，runtime 状态仍主要在内存 `BrowserManager.running` 中。

后续推荐：

1. 继续 02 指纹健康引擎，优先后端测试驱动。
2. 05 Session Broker 之前不要解除 Project Mileage 远程占位。
3. `/api/runtime/*`、viewer token、runtime session 表、service token 和审计落库必须在 05/10 模块按测试实现，不要把 01 草案当作已实现能力。

## 16. 2026-05-25 02 指纹健康引擎后端小闭环

已完成 02 的后端最小闭环，02 整体未完成，前端 HealthBadge 和 profile 列表展示留下一轮。

实现：

- 新增 `backend/health.py`。
- 新增健康状态：`unknown`、`good`、`warning`、`error`。
- 新增 `HEALTH_WARNING_CODES`，覆盖 `geoip_missing`、`geoip_stale`、`proxy_invalid`、`geoip_lookup_failed`、`manual_timezone_mismatch`、`manual_locale_mismatch`、`runtime_vnc_missing`、`runtime_automation_missing`、`launch_failed`。
- 新增 `GET /api/profiles/{id}/health`：不访问网络，只用 DB profile、`last_geoip_*` 和 `browser_mgr.get_status()` 计算。
- 新增 `POST /api/profiles/{id}/health/check`：校验 proxy、调用 GeoIP、成功时写入 `last_geoip_*`，失败时返回稳定 health response 且保留旧检测结果。
- 手动 `timezone` / `locale` 继续是手动覆盖字段，health/check 不覆盖它们，只通过 warning 提示与 GeoIP 建议不一致。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q
# 11 passed

. .venv/bin/activate && python -m pytest backend/tests/test_health.py backend/tests/test_geoip.py backend/tests/test_api.py -q
# 77 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 216 passed
```

UI/UE 预审：

- 后续 `HealthBadge` 建议放在 profile 列表第一行右侧，成为运营扫列表时的快速决策信号。
- 状态短文案建议：`good = 可继续`、`warning = 需关注`、`error = 不可用`、`unknown = 未检测`。
- 色彩应低饱和，避免和运行态绿点、tag 多色冲突；warning 用 amber，error 沿用 red，unknown 用中性灰，good 用弱绿色或灰底小绿点。
- `HealthBadge` 必须有可访问名称或 tooltip，不能只靠颜色表达状态。

## 17. 2026-05-26 Profile 运营台 UI/UE 质感小闭环

Jeff 反馈当前前端整体偏 low、运营台 UE 不够专业，本轮暂停继续堆功能，优先优化 Profile 运营台体验。

设计判断：

- 数百 profile 不应主要靠左侧长列表滚动管理。
- 左侧应定位为 quick views、分组、最近、快捷入口和导航兜底。
- 主区应承担核心运营：搜索、筛选、表格、多选、批量操作和状态扫视。
- 默认视觉从深色开发面板改为浅色 B2B / data-dense dashboard，更适合长时间运营管理。

实现范围：

- `App.tsx`：
  - 顶部变为 `Profile Operations`。
  - 主区新增 summary tiles 和 toolbar。
  - 移动端 sidebar 改成 overlay 抽屉，打开后不再撑宽 body。
- `ProfileList.tsx`：
  - 左侧新增 quick views：`All profiles`、`Running profiles`、`Stopped profiles`、`Unavailable profiles`、`Needs attention`、`No proxy`。
  - quick views 直接写入现有 `ProfileFilterState`。
  - 保留左侧虚拟滚动，只作为 matching profiles 扫视区。
- `ProfileFilters.tsx`：
  - 支持 `rail` / `toolbar` 两种布局。
  - 主区使用 toolbar 布局。
- `ProfileTable.tsx`：
  - 改为 `table-fixed` 和固定列宽。
  - 长字段截断，不撑破布局。
  - 1440px 桌面可直接看到 `Actions` 列。
- `BulkActionBar.tsx`：
  - 改为浅色 sticky command bar。
  - 仍然只做 disabled 安全壳，不调用批量 API。
- `tailwind.config.ts` / `globals.css`：
  - `surface`、`border`、`accent` 改为浅色 B2B token。
  - 更新按钮、输入、select、textarea、focus、scrollbar。
- `LoginPage`、`ProfileForm`、`ProfileViewer`、`LaunchButton` 做浅色 token 兼容，避免默认浅色主题下不可读。

测试与验证：

```bash
cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileList.test.tsx src/components/ProfileFilters.test.tsx src/components/ProfileTable.test.tsx
# 4 passed, 25 passed

cd frontend && npm test -- --run
# 10 passed, 59 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器验证：

- 使用临时 QA 数据库 `/tmp/cloakbrowser-manager-qa-data`，共 240 个 profiles。
- 使用 `agent-browser`，环境变量 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 主区 summary / toolbar / dense table 可见。
  - quick view `Needs attention` 可驱动 `Health status=warning`，主表显示 26 行。
  - 选择首行后 `Bulk profile actions` 和 `1 selected` 可见。
  - 控制台无相关应用错误。
- 移动 `390x844`：
  - 初始 sidebar 收起，主区搜索筛选可用。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身横向滚动，body 不横向撑破。
  - 打开 sidebar 后为 overlay 抽屉，body 仍不横向撑破。

截图：

- `/tmp/cloak-ui-refresh-desktop.png`
- `/tmp/cloak-ui-refresh-quick-view.png`
- `/tmp/cloak-ui-refresh-bulk.png`
- `/tmp/cloak-ui-refresh-mobile.png`
- `/tmp/cloak-ui-refresh-mobile-sidebar.png`

仍未做：

- 批量 launch / stop / health check / tag / delete 仍未接入。
- `Open` 仍然切换到原详情页，后续可改为“表格 + 详情抽屉/右栏”的连续运营形态。

## 18. 2026-05-26 ProfileSummaryPanel 右侧摘要小闭环

本轮继续推进 03 Profile 运营台，补齐右侧 summary panel。

核心决策：

- `previewProfileId` 独立于 `selectedId` / `view` / `selectedProfileIds`。
- 表格 profile name 是预览动作，只更新右侧摘要，不触发编辑页、VNC viewer 或顶部 `LaunchButton` 语义。
- 表格 `Open` 和右侧 `Open profile` 继续走现有 `handleSelect()`，保留原 edit / VNC 流。
- 右侧 summary 是主表格的 drill-down，不替代主表格；移动端放到表格下方，不遮挡主操作。

实现范围：

- 新增 `frontend/src/components/ProfileSummaryPanel.tsx`：
  - health。
  - runtime。
  - GeoIP。
  - manual override。
  - proxy。
  - device。
  - `Open profile` quick action。
- 新增 `frontend/src/lib/profileDisplay.ts`：
  - `formatProxyLabel()`。
  - `formatTimestamp()`。
  - `redactUrlCredentials()`，用于 health warning 文本/title 的防御性脱敏。
- 更新 `backend/browser_manager.py`：
  - `_validate_proxy()` 的 missing hostname / missing port / invalid port 错误不再返回 proxy 用户名密码。
- 更新 `frontend/src/components/ProfileTable.tsx`：
  - profile name 变为 `Preview <name>` button。
  - 增加 `previewProfileId` / `onPreviewProfile` props。
  - 预览行有轻量背景。
- 更新 `frontend/src/App.tsx`：
  - 在 `view === "empty"` 下使用桌面 `main table + 320px summary panel` grid。
  - 当前预览被筛选隐藏后回到当前可见第一项；无结果时显示空摘要。

测试与验证：

```bash
cd frontend && npm test -- --run src/components/ProfileSummaryPanel.test.tsx src/components/ProfileTable.test.tsx src/App.test.tsx
# 3 passed, 19 passed

cd frontend && npm test -- --run src/components/ProfileSummaryPanel.test.tsx src/components/ProfileTable.test.tsx
# 2 passed, 13 passed

cd frontend && npm test -- --run
# 11 passed, 62 passed

.venv/bin/python -m pytest backend/tests -q
# 217 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-qa-data`，共 243 个 profiles。
- 使用 `agent-browser`，环境变量 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 主表格和右侧 `Profile summary` 同屏可见。
  - 搜索 `QA Summary` 后主表显示 3 行。
  - 点击 `Preview QA Summary Good` 后右侧 summary 更新，主表格仍存在，未进入编辑页。
  - 右侧 `Open profile` 可进入原编辑流，`Edit Profile`、`Launch`、`Delete`、`Cancel`、`Save` 可见。
  - DOM 未出现 `hiddenpass`。
- 脱敏补验：
  - QA 数据库增加 `QA Summary Secret Missing Port`，总计 244 个 profiles。
  - API health warning 为 `Proxy URL missing port: http://proxy-secret.example`。
  - 表格、左侧列表和右侧 summary 的 DOM 未出现 `hiddenpass` 或 `user:hiddenpass`。
- 移动 `390x844`：
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表横向滚动保留。
  - summary panel 位于表格下方，可通过主内容滚动查看。

截图：

- `/tmp/cloak-summary-panel-desktop.png`
- `/tmp/cloak-summary-panel-preview.png`
- `/tmp/cloak-summary-panel-mobile.png`
- `/tmp/cloak-summary-panel-mobile-summary.png`
- `/tmp/cloak-summary-panel-secret-redaction.png`

仍未做：

- 批量 launch / stop / health check / tag / delete 仍未接入。
- 空态细分、窄屏 card list、VNC viewer 连续运营形态仍未进入本闭环。

## 19. 2026-05-26 Profile 运营台 IA/视觉二次收口与批量 health check 小闭环

本轮根据 Jeff 反馈暂停继续堆功能，优先处理 Profile 运营台 UI/UE 质感。

设计判断：

- 当前体验的主要问题不是单一配色，而是信息架构和层级不稳：左侧全量列表、主区表格、右侧自动预览同时争夺主工作区。
- 数百 profile 的管理核心应是主区表格、搜索筛选、批量操作和右侧 inspector；左侧只做 saved views / shortcuts / 分组或最近入口。
- `/home/jeff/code/repo/sasskit` 在本机不存在，实际参考目录为 `/home/jeff/code/reference-repos/saas_kit`。
- 视觉方向采用浅色、低噪声、data-dense B2B 运营台，借鉴 `ai-mksaas-template` 的数据表格/toolbar 和 `ai-supastarter-template` 的 app shell，不采用营销 hero、大面积渐变或紫色官网风格。

实现范围：

- `frontend/src/App.tsx`
  - 顶部标题收敛为 `Profiles`，增加主操作 `New Profile`。
  - 主区拆成标题/指标 strip、筛选 toolbar、表格 + inspector。
  - 左 rail 宽度从 280px 收敛到 264px，右 inspector 从 320px 收敛到 280px。
  - 接入 `handleCheckSelectedHealth()`，批量检测期间传递 loading 状态。
- `frontend/src/components/ProfileList.tsx`
  - `Quick views` -> `Saved views`。
  - `Matching profiles / virtualized` -> `Profile shortcuts / filtered`。
  - 保留左侧虚拟滚动和选择能力，但产品定位降级为快捷入口。
- `frontend/src/components/ProfileFilters.tsx`
  - toolbar 模式增加可见短标签：`Search / Runtime / Health / Proxy / Country / Tag / Sort`。
  - rail 模式继续使用 sr-only 完整 label，避免和 profile 行文本冲突。
- `frontend/src/components/ProfileTable.tsx`
  - 主表最小宽度从 1068px 收敛到 840px，列宽压实，1440px 桌面可看到 `Actions`。
  - hover/focus/selected/preview 样式收口。
  - `onCheckSelectedHealth` / `checkingSelectedHealth` props 接入 `BulkActionBar`。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - header 使用轻背景，`Open profile` 变为主按钮。
  - 分区使用 divider，减少卡片套卡片。
- `frontend/src/components/BulkActionBar.tsx`
  - `Check health` 变成真实可点击动作。
  - `Checking...` loading state。
  - `Launch selected` / `Stop selected` / `Tag selected` / `Delete selected` 继续 disabled。
- `frontend/src/hooks/useProfiles.ts`
  - 新增 `checkHealth(ids)`。
  - 去重、过滤空 id、最多 6 并发。
  - 成功项写入 `healthByProfileId`，失败项不清空旧 health。
  - 部分失败设置 `Failed to check health for N profile(s)`。

测试与验证：

```bash
cd frontend && npm test -- --run src/hooks/useProfiles.test.ts src/components/ProfileTable.test.tsx src/App.test.tsx src/components/ProfileList.test.tsx src/components/ProfileFilters.test.tsx src/components/ProfileSummaryPanel.test.tsx
# 6 passed, 40 passed

cd frontend && npm test -- --run
# 11 passed, 66 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed
```

浏览器验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-ui-qa-data`，共 180 个 profiles。
- 后端 `http://127.0.0.1:8080`，Vite `http://127.0.0.1:5173/`。
- 使用 `agent-browser`，环境变量 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 主区显示标题/指标 strip、可见标签筛选 toolbar、dense table 和右侧 inspector。
  - 左侧显示 `Saved views` / `Profile shortcuts`，不再出现 `virtualized`。
  - `Actions` 列直接可见。
  - 选择首行后 `Bulk profile actions` 可见，`Check health` 可点击，其他批量动作 disabled。
  - 点击 `Check health` 后 summary `Last checked` 更新时间。
- 移动 `390x844`：
  - 初始 sidebar 收起。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身横向滚动，`tableScrollWidth=840`、`tableClientWidth=352`。
  - 打开 sidebar 后为 overlay，body 不横向撑破。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。

截图：

- `/tmp/cloak-ui-ue-refresh-desktop-compact.png`
- `/tmp/cloak-ui-ue-refresh-bulk-selected.png`
- `/tmp/cloak-ui-ue-refresh-bulk-checked.png`
- `/tmp/cloak-ui-ue-refresh-mobile.png`
- `/tmp/cloak-ui-ue-refresh-mobile-sidebar.png`

仍未做：

- 批量 launch / stop / set tags / delete 仍未接入。
- 服务端分页未做；当前仍采用固定行高虚拟滚动覆盖数百 profile。
- 空态细分、窄屏 card list、VNC viewer 连续运营形态仍未进入本闭环。

## 20. 2026-05-26 批量 launch 小闭环

本轮继续推进 03 Profile 运营台，完成 `接入批量 launch`。

实现范围：

- `frontend/src/hooks/useProfiles.ts`
  - 新增 `launchProfiles(ids)`。
  - 去重、过滤空 id。
  - 只启动当前 profile 列表中 `status === "stopped"` 的 profiles，running profiles 跳过。
  - 最多 2 并发，复用现有 `api.launchProfile(id)`，不新增后端 bulk API。
  - 批量完成后统一 `refresh()` 一次，成功项再 `refreshHealth(successfulIds)`。
  - 部分失败不阻断其他 profile。
  - 失败提示带后端错误摘要，并通过 `redactUrlCredentials()` 防御性脱敏。
  - 将 fetch error 和 operation error 分开维护，后台轮询 refresh 成功不会清掉操作失败 banner。
- `frontend/src/components/BulkActionBar.tsx`
  - `Launch selected` 从 disabled shell 改为真实按钮。
  - 仅在存在 stopped 选中项时启用。
  - loading 状态显示 `Launching...`。
- `frontend/src/components/ProfileTable.tsx`
  - bulk launch 只传 selected stopped profile ids。
- `frontend/src/App.tsx`
  - 接入 `bulkLaunching` 状态和 `handleLaunchSelectedProfiles()`。
  - 不改变单 profile launch / stop / VNC viewer 流。

子 agent 审计结论：

- 当前可见 stopped selection 主路径没有发现传空 ids 或完全未调用 API 的问题。
- 审计指出批量失败只显示聚合计数会降低可诊断性；已改为显示去重后的后端错误摘要。
- 审计提到隐藏选中项风险；主 App 已有筛选后清理不可见 selection 的 effect，并有现有测试覆盖，本轮未改该语义。

测试与验证：

```bash
cd frontend && npm test -- --run src/hooks/useProfiles.test.ts
# 1 passed, 14 passed

cd frontend && npm test -- --run src/hooks/useProfiles.test.ts src/components/ProfileTable.test.tsx src/App.test.tsx
# 3 passed, 36 passed

cd frontend && npm test -- --run
# 11 passed, 71 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed

git diff --check
# passed
```

浏览器验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-bulk-launch-qa-data`，2 个 stopped/headless/no-proxy profiles。
- 后端 `http://127.0.0.1:8080`，Vite `http://127.0.0.1:5173/`。
- 使用 `agent-browser`。
- 桌面 `1440x900`：
  - 选择两个 stopped profiles 后显示 `2 selected`、`0 running`、`2 stopped`。
  - `Launch selected` 可点击。
  - 点击后后端日志显示两个 profile 都尝试启动。
  - 当前本机环境缺 `Xvnc`，后端返回 `500 {"detail":"Failed to launch browser"}`，profile 保持 stopped。
  - 前端显示 `Failed to launch 2 profile(s): Failed to launch browser`。
  - 等待 3.5 秒后台轮询后，失败 banner 仍保持可见。
  - 清空 console 后重跑当前流程，无相关前端 console error。
- 移动 `390x844`：
  - 失败 banner 可见。
  - `body.scrollWidth === window.innerWidth === 390`。

截图：

- `/tmp/cloak-bulk-launch-error-persist-desktop.png`
- `/tmp/cloak-bulk-launch-error-persist-mobile.png`
- `/tmp/cloak-bulk-launch-before.png`
- `/tmp/cloak-bulk-launch-selected.png`
- `/tmp/cloak-bulk-launch-after-click.png`

运行时限制：

- 本机 `command -v Xvnc` 为空，仅有 `/usr/bin/firefox`。
- 因此本轮无法直接验证 profile 进入 `running` / VNC 可连状态。
- Dockerfile 生产镜像安装 KasmVNC；真实 running 状态需要在容器环境或安装 `Xvnc` 的运行时环境补验。

仍未做：

- 批量 stop / set tags / delete 未接入。
- 批量 delete 仍需单独确认闭环。
- `保留创建/编辑 profile 能力`、`保留 VNC viewer 能力`、空态拆分、窄屏 card list 仍待 03 后续小闭环复核。

## 21. 2026-05-26 批量 stop 小闭环

本轮继续推进 03 Profile 运营台，完成 `接入批量 stop`。

实现范围：

- `frontend/src/hooks/useProfiles.ts`
  - 新增 `stopProfiles(ids)`。
  - 去重、过滤空 id。
  - 只停止当前 profile 列表中 `status === "running"` 的 profiles。
  - stopped profiles 跳过，计入 `skippedStoppedCount`，不作为错误。
  - 最多 2 并发，复用现有 `api.stopProfile(id)`，不新增后端 bulk API。
  - 批量完成后统一 `refresh()` 一次，成功项再 `refreshHealth(successfulIds)`。
  - 部分失败不阻断其他 profile。
  - 失败提示带后端错误摘要，并通过 `redactUrlCredentials()` 统一防御性脱敏。
- `frontend/src/components/BulkActionBar.tsx`
  - `Stop selected` 从 disabled shell 改为真实按钮。
  - 仅在存在 running 选中项时启用。
  - loading 状态显示 `Stopping...`。
  - `Tag selected`、`Delete selected` 继续 disabled。
- `frontend/src/components/ProfileTable.tsx`
  - bulk stop 只传 selected running profile ids。
- `frontend/src/App.tsx`
  - 接入 `bulkStopping` 状态和 `handleStopSelectedProfiles()`。
  - 不改变单 profile launch / stop / VNC viewer 流。

子 agent 审计结论：

- bulk stop 必须 running-only，因为后端 stop API 对非 running profile 返回 404。
- stopped profile 应跳过，不应作为失败。
- stop 后应刷新列表，并刷新成功 stopped profile 的 health，避免 runtime health 残留。
- 选择不应主动清空；All 视图保留选择，过滤视图由既有 effect 自动剪掉不可见项。
- 本机缺 `Xvnc` 时不能声称完成真实 VNC teardown 浏览器联调，只能用模拟 running 环境验证前端流。

测试与验证：

```bash
cd frontend && npm test -- --run src/hooks/useProfiles.test.ts src/components/ProfileTable.test.tsx src/App.test.tsx
# 3 passed, 40 passed

cd frontend && npm test -- --run
# 11 passed, 75 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed

git diff --check
# passed
```

浏览器验证：

- 当前本机缺 `Xvnc`，不能通过真实 launch 构造 running profile。
- 使用临时 QA 后端 8081 monkeypatch `browser_mgr.running` 和 `browser_mgr.stop()`，只验证前端 running-only stop 流和 API 成功路径。
- 5174 静态代理服务用于访问当前 build 的前端并代理 `/api` 到 8081。
- 临时 QA 数据库 `/tmp/cloakbrowser-manager-bulk-stop-qa-data`，2 个 profiles：
  - `Bulk Stop QA Running` 初始 `running`。
  - `Bulk Stop QA Stopped` 初始 `stopped`。
- 桌面 `1440x900`：
  - 选中 running + stopped 后显示 `2 selected`、`1 running`、`1 stopped`。
  - `Stop selected` 可点击。
  - 点击后 `/api/status` 返回 `running_count: 0`。
  - 表格中 running profile 变为 `stopped`。
  - toolbar 保留 `2 selected`，显示 `0 running`、`2 stopped`，`Stop selected` 变 disabled。
  - 清空 console 后当前流程无相关前端 console error。
- 移动 `390x844`：
  - 停止后 `2 selected`、`0 running` 可见。
  - `body.scrollWidth === window.innerWidth === 390`。

截图：

- `/tmp/cloak-bulk-stop-selected-desktop.png`
- `/tmp/cloak-bulk-stop-after-desktop.png`
- `/tmp/cloak-bulk-stop-after-mobile.png`

运行时限制：

- 未覆盖真实 XvNC / KasmVNC teardown、真实 noVNC websocket 断开、真实 VNC 进程退出。
- 完整运行时联调需要在安装 `Xvnc` 或 Docker/KasmVNC 环境补验。

仍未做：

- 批量 set tags / delete 未接入。
- 批量 delete 仍需单独确认闭环。
- `保留创建/编辑 profile 能力`、`保留 VNC viewer 能力`、空态拆分、窄屏 card list 仍待 03 后续小闭环复核。

## 22. 2026-05-26 Profile 运营台控件质感 UI polish 小闭环

本轮按 Jeff 最新反馈暂停继续堆功能，聚焦 Profile 运营台 UI polish，重点修复 checkbox、bulk action、table row、toolbar、inspector 的低质感问题。

设计判断：

- 当前运营台信息架构方向正确：左侧 rail 做 quick views / shortcuts，主区表格承担数百 profile 的核心管理，右侧 inspector 做快速判断。
- 当前 low 的主要原因是控件细节：
  - checkbox 依赖浏览器默认视觉，半选态和 focus 不够精致。
  - bulk toolbar 过蓝且按钮同权，容易像半成品提示条。
  - row selected / previewed 只靠背景色，不够清晰。
  - toolbar filter / inspector 的边框、ring、shadow、section hierarchy 偏普通。
- 参考 `/home/jeff/code/reference-repos/saas_kit` 时只吸收 B2B SaaS data table 的视觉规律，没有迁入 auth/db/payment/schema。

实现范围：

- `frontend/src/components/ProfileTable.tsx`
  - `SelectionCheckbox` 改为真实 input + 自定义视觉层。
  - 增加 checked / indeterminate 图标态，半选使用 `aria-checked="mixed"`。
  - row selected / previewed 增加左侧状态线，降低背景色噪声。
  - table header 继续 sticky，保留 `selectedCount > 0 ? top-11 : top-0`。
- `frontend/src/components/BulkActionBar.tsx`
  - toolbar 改为 neutral white contextual surface。
  - `Check health` 保持主按钮和真实可用。
  - `Launch selected` / `Stop selected` 保留已完成真实动作。
  - `Tag selected` / `Delete selected` 继续 disabled。
  - 所有 bulk 按钮 `whitespace-nowrap`，避免窄表格中折行。
- `frontend/src/components/ProfileFilters.tsx`
  - 搜索框和 filter select 增加 compact ring / hover / focus polish。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector header、section icon、row hierarchy、Open profile action 降噪。
- `frontend/src/App.tsx`
  - filter section、table shell、summary tiles 使用更细的 ring / hairline shadow。
- `frontend/src/components/ProfileTable.test.tsx`
  - 补 header checkbox 半选态断言。
  - 补 checkbox input focusable / disabled 语义断言。

保持不变：

- 主表 `min-w-[840px]` 和 table 自身横向滚动。
- 桌面 `Actions` 列可见。
- 移动端 body 不横向撑破。
- 主表超过 120 条固定 64px 行高虚拟滚动。
- 左侧超过 80 条固定 112px item 虚拟滚动。
- `Check health` / bulk launch / bulk stop 真实动作语义。
- `Tag selected` / `Delete selected` disabled。
- proxy 脱敏。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 1 passed, 17 passed

cd frontend && npm test -- --run
# 11 passed, 77 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed

git diff --check
# passed
```

浏览器验证：

- QA 数据目录：`/tmp/cloakbrowser-manager-ui-polish-data`，240 个 profiles。
- 后端 QA：`http://127.0.0.1:8082`。
- 静态前端代理：`http://127.0.0.1:5175/`。
- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 首屏可见 operations rail、summary tiles、toolbar、dense table、inspector。
  - `Actions` 列可见。
  - bulk selected 状态下 checkbox、toolbar、Tag/Delete disabled、Check health enabled 正常。
  - 点击 `Check health` 后 `Last checked` 更新时间。
  - 主表滚动到中段后表格区域不再包含顶部 profile，窗口内约 26 个 Open 按钮，虚拟滚动保持。
- 移动 `390x844`：
  - 初始 sidebar 收起。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表 `scrollWidth=840`、`clientWidth=352`，自身横向滚动可用。
  - 横向滚到右侧后 `Actions` / `Open` 可见。
  - sidebar overlay 打开后 body 仍不横向撑破。
- console 清空后无相关前端错误。

截图：

- `/tmp/cloak-profile-polish-desktop.png`
- `/tmp/cloak-profile-polish-bulk-selected.png`
- `/tmp/cloak-profile-polish-bulk-checked.png`
- `/tmp/cloak-profile-polish-mobile.png`
- `/tmp/cloak-profile-polish-mobile-table-actions.png`
- `/tmp/cloak-profile-polish-mobile-sidebar.png`
- `/tmp/cloak-profile-polish-virtual-scroll.png`

仍未做：

- 批量 set tags / delete 未接入。
- 服务端分页未做；当前仍用固定行高虚拟滚动覆盖数百 profile。
- 窄屏 card list、空态细分、Profile/VNC 连续运营抽屉形态未进入本闭环。

## 23. 2026-05-26 批量 set tags 与控件 polish 收口小闭环

本轮继续按 Jeff 最新反馈处理 Profile 运营台的高质感 UI polish，同时把上一轮预留的 `Tag selected` 接成真实批量 set tags。

设计判断：

- 当前信息架构继续保持：左侧 rail 是 quick views / shortcuts，主区 table 是数百 profile 的核心运营面，右侧 inspector 做快速预览。
- 真正需要收口的是控件细节和真实动作：
  - checkbox 需要更像专业 data table control。
  - bulk action 需要短文案、清晰主次和弱态 danger。
  - `Tag selected` 不应继续作为 disabled 占位。
  - 高风险 `Delete selected` 必须继续 disabled，且视觉上不能像可点击危险主按钮。

实现范围：

- `frontend/src/hooks/useProfiles.ts`
  - 新增 `addTagsToProfiles(profileIds, tags)`。
  - ids 去重，tag trim / 去空 / 去重。
  - 基于当前 `profiles` 中的 `profile.tags` 合并，只传 `{ tags }` 给 `api.updateProfile`。
  - 已有同名 tag 保留原 color，不覆盖运营已有标签。
  - 未变化 profile 跳过，不触发 update / refresh。
  - 选中态与列表刷新发生竞态时，已消失的 profile id 明确计入 failedCount，不静默丢失。
  - 并发上限 4；成功后 refresh profiles 和成功 ids 的 health cache。
  - 部分失败写入脱敏后的 operation error。
- `frontend/src/App.tsx`
  - 接入 `addTagsToProfiles`。
  - 新增 `bulkTagging` 状态，并传入 `ProfileTable`。
- `frontend/src/components/BulkActionBar.tsx`
  - `Tag selected` 打开内联 tag form。
  - 输入框自动 focus，Escape 取消。
  - 可见文案压缩为 `Health / Launch / Stop / Tag / Delete`，保留原 aria-label 语义。
  - `Delete selected` 继续 disabled，弱化 danger disabled 样式。
- `frontend/src/components/ProfileTable.tsx`
  - checkbox 视觉升级为 18px custom control，保留真实 input、focus-visible、mixed state。
  - selected / previewed row 使用更克制的渐变与左侧状态线。
  - tag chip 增加轻微 inset polish。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector header 增加 `Previewing / Inspector` 上下文。
- 测试：
  - hook 覆盖追加 tag、不移除已有 tag、不覆盖同名 tag color、无变化跳过。
  - table 覆盖 tag form、自动 focus、tagging disabled/loading。
  - App 覆盖当前 selected profiles 的批量 tag 调用，且 delete 仍 disabled。

验证：

```bash
cd frontend && npm test -- --run src/hooks/useProfiles.test.ts
# 1 passed, 21 passed

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 1 passed, 19 passed

cd frontend && npm test -- --run src/App.test.tsx
# 1 passed, 10 passed

cd frontend && npm test -- --run
# 11 passed, 85 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed

git diff --check
# passed
```

浏览器验证：

- 临时 QA 数据目录：`/tmp/cloakbrowser-manager-qa-data-polish`。
- QA 后端：`http://127.0.0.1:8092/`。
- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 选择 `QA Existing Tag` 与 `QA Plain Profile` 后，bulk toolbar 显示 `2 selected`。
  - `Check health` 可用，`Launch` 可用，`Stop` disabled，`Tag` 可用，`Delete` disabled 且弱态。
  - tag form 自动 focus，输入后 action bar 不折行。
  - 提交 `ops` 后：已有 `existing` 保留，两个选中 profile 都追加 `ops`，tag filter 出现 `ops`。
  - 点击 `Check health` 后 health / GeoIP / Last checked 更新，证明批量健康检测仍真实可用。
- 移动 `390x844`：
  - 初始 sidebar 收起。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身横向滚动，`table.scrollWidth=840`、`table.clientWidth=358`。
- console / errors 无相关前端错误。

截图：

- `/tmp/cloak-polish-selected-desktop.png`
- `/tmp/cloak-polish-bulk-tag-form-desktop.png`
- `/tmp/cloak-polish-bulk-tag-applied-desktop.png`
- `/tmp/cloak-polish-health-check-desktop.png`
- `/tmp/cloak-polish-mobile.png`

仍未做：

- 批量 delete 未接入，仍需确认弹窗和测试。
- 服务端分页未做；当前继续以固定行高虚拟滚动覆盖数百 profile。
- 窄屏 card list、空态细分、Profile/VNC 连续运营抽屉形态仍待后续。

## 24. 2026-05-26 Profile 运营台控件质感 polish 小闭环

背景：

- Jeff 反馈当前界面质感和细节仍不够，尤其 checkbox 等控件显得 low。
- 本轮暂停继续堆功能，使用 `ui-ux-pro-max` / frontend design 方向做 UI polish。
- 参考 `/home/jeff/code/reference-repos/saas_kit` 的 B2B SaaS app shell / data table 质感，只借鉴视觉与交互模式；没有迁入 auth、db、payment、schema 或业务逻辑。

设计判断：

- 当前 UI low 的主要原因不是信息架构，而是边框、阴影、渐变、圆角和卡片层级过多。
- checkbox 在密表内需要更扁平、更像 data-table control。
- bulk action bar 需要从“浮动按钮组”收敛成 compact command bar。
- table row 的 selected / previewed 状态需要降低渐变噪声，保留轻背景和左侧状态线。
- inspector 需要更像只读审计面板，降低 header 渐变和 icon 方块装饰。

实现：

- `frontend/src/components/ProfileTable.tsx`
  - checkbox 改为更扁平的 16px 控件，并将选择列扩到 42px 以匹配 28px 命中区，保留真实 input、focus ring、半选态、`aria-checked="mixed"`。
  - selected / previewed row 从横向渐变降噪为轻背景 + 左侧状态线。
  - 表格行分隔改为 `slate-100`，保留固定 64px 行高、120 阈值虚拟滚动、`min-w-[840px]` 和 table region 自身横向滚动。
- `frontend/src/components/BulkActionBar.tsx`
  - bulk toolbar 改为 compact command bar。
  - `Check health` 改为可见主动作文案。
  - `Delete selected` 继续 disabled，并以弱 danger 样式表达高风险未接入。
  - tag form 自动 focus / Escape 取消 / 真实批量 set tags 语义保持。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - 降低 header 渐变、section icon 方块、divide line 装饰密度。
  - proxy 凭据脱敏语义保持。
- `frontend/src/App.tsx`
  - app shell 背景、top bar、summary tiles、table panel 阴影和边框细化。
  - 信息架构保持：左侧 rail 做 shortcuts / quick views，主区 table 承担核心运营。

测试更新：

- `ProfileTable.test.tsx`
  - 新增 table 横滚只在 `Profile operations table` region 内的结构断言。
  - 新增 selected / previewed row `data-state` 断言，确认不隐藏 `Open` actions。
  - 新增 `Check health` 可见文案断言。
- `App.test.tsx`
  - 窄屏用例补充 table region `overflow-auto` 断言。
- `ProfileSummaryPanel.test.tsx`
  - 补充 inspector header 仍可见断言。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/App.test.tsx src/components/ProfileSummaryPanel.test.tsx
# 3 passed, 32 passed

cd frontend && npm test -- --run
# 11 passed, 87 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed

git diff --check
# passed
```

浏览器验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- 前端：`http://127.0.0.1:5173/`。
- QA 后端：`http://127.0.0.1:8080/`。
- QA 数据：现有 2 个 profile + 本轮追加 160 个 `Polish QA Profile`，总计 162 个 profiles。
- 桌面 `1440x900`：
  - 首屏可见 operations rail、summary tiles、filter toolbar、dense table、inspector。
  - `Actions` 列和 `Open ...` 按钮可访问。
  - 选择两个 profile 后 bulk bar 显示 `2 selected`，`Check health / Launch / Tag` 可用，`Stop / Delete` disabled。
  - `Tag selected` 输入 `polish` 后真实更新选中 profiles，tag filter 出现 `polish`。
  - 点击 `Check health` 后真实调用健康检测，country filter 出现 `US`。
  - 主表滚动到约第 120 行后首屏早期 profile 离开 DOM，可见 `Polish QA Profile 113` 至 `120`，虚拟滚动仍生效。
- 移动 `390x844`：
  - 初始 sidebar 收起。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身横向滚动，`table.scrollWidth=846`、`table.clientWidth=352`。
  - 横向滚动到右侧后 `Actions` / `Open` 仍可访问。
  - 打开 sidebar overlay 后 body 仍不横向撑破。
- console / errors 无相关前端错误，仅有 Vite debug 和 React DevTools info。

截图：

- `/tmp/cloak-ui-polish-desktop.png`
- `/tmp/cloak-ui-polish-bulk-selected.png`
- `/tmp/cloak-ui-polish-bulk-tag-form.png`
- `/tmp/cloak-ui-polish-bulk-tag-applied.png`
- `/tmp/cloak-ui-polish-health-check.png`
- `/tmp/cloak-ui-polish-virtual-scroll.png`
- `/tmp/cloak-ui-polish-mobile.png`
- `/tmp/cloak-ui-polish-mobile-actions.png`
- `/tmp/cloak-ui-polish-mobile-sidebar.png`

仍未做：

- 批量 delete 未接入，仍需确认弹窗和测试。
- 服务端分页未做；当前继续以固定行高虚拟滚动覆盖数百 profile。
- 窄屏 card list、空态细分、Profile/VNC 连续运营抽屉形态仍待后续。
