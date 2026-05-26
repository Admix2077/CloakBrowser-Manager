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
087097a add proxy provider preset manager
```

当前本地 QA 服务：

```text
http://127.0.0.1:8095/
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
- `running_count=0`。
- `binary_version=invisible-playwright`。
- `profiles_total=6`。
- 05 已完成 CloakBrowser 侧最小 runtime session API，详见文末最新接力记录。

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

- 服务端分页未做；当前继续以固定行高虚拟滚动覆盖数百 profile。
- 窄屏 card list、空态细分、Profile/VNC 连续运营抽屉形态仍待后续。

## 25. 2026-05-26 批量 delete 确认小闭环（最新状态）

说明：

- 上方 UI polish 小闭环记录的是当时状态；本节是后续最新状态，已覆盖“Delete selected 继续 disabled / 批量 delete 未接入”的历史备注。
- 03 Profile 运营台的 `接入批量 delete，必须有确认` 已完成并勾选。
- `tasks/progress.md` 中 03 模块仍不标完成，因为创建/编辑能力复核、VNC viewer 能力复核、空态拆分、窄屏 card list 还未完成。

关键实现：

- `frontend/src/hooks/useProfiles.ts`
  - 新增 `deleteProfiles(profileIds)`。
  - 复用真实 `DELETE /api/profiles/{id}`，不新增 mock route。
  - 前端批量层只删除 stopped profiles，跳过 running profiles。
  - 删除并发限制为 2。
  - 成功后本地移除 `profiles` 和 `healthByProfileId`，返回 `deletedIds`。
  - 部分失败继续执行，失败原因经过 proxy 凭据脱敏。
- `frontend/src/components/BulkActionBar.tsx`
  - `Delete selected` 接入真实 danger action。
  - running-only selection 下 disabled，并提示先 stop running profiles。
  - 确认面板要求输入大写 `DELETE`；确认文案明确浏览器数据会永久删除。
- `frontend/src/components/ProfileTable.tsx`
  - bulk delete 只向 App 传 stopped ids。
  - 保持 `min-w-[840px]`、表格自身横向滚动和大列表虚拟滚动语义。
- `frontend/src/App.tsx`
  - 新增 `bulkDeleting` 状态。
  - 删除成功后清理成功删除 profile 的 selection。
  - 当前 preview / detail 命中已删除 profile 时回到可用状态，避免 stale view。

验证：

```bash
cd frontend && npm test -- --run src/hooks/useProfiles.test.ts src/components/ProfileTable.test.tsx src/App.test.tsx
# 3 passed, 61 passed

cd frontend && npm test -- --run
# 11 passed, 96 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed

git diff --check
# passed
```

浏览器验证：

- `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8092/`。
- QA 数据目录：`/tmp/cloakbrowser-bulk-delete-qa-data`。
- 150 个 `QA Bulk Profile` 用于验证批量删除和数百 profile 虚拟滚动。
- 桌面 `1440x900`：
  - 选择 2 个 stopped profiles 后 `Delete` 可用。
  - 点击 `Delete` 后确认面板出现，未输入 `DELETE` 时确认按钮 disabled。
  - 输入 `DELETE` 后真实删除 2 个 profile，列表 150 -> 148，selection 清理。
  - 主表滚动到约第 120 行后可见 `QA Bulk Profile 122` 至 `130`，虚拟滚动仍生效。
  - `Check health` 对选中 profile 真实调用，未破坏既有批量健康检测。
- 移动 `390x844`：
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身横向滚动，`Actions` / `Open` 可访问。
- console / errors 无相关前端错误。

截图：

- `/tmp/cloak-bulk-delete-desktop.png`
- `/tmp/cloak-bulk-delete-confirm.png`
- `/tmp/cloak-bulk-delete-after.png`
- `/tmp/cloak-bulk-delete-health-check.png`
- `/tmp/cloak-bulk-delete-virtual-scroll.png`
- `/tmp/cloak-bulk-delete-mobile.png`
- `/tmp/cloak-bulk-delete-mobile-actions.png`

## 26. 2026-05-26 Profile 运营台高质感控件 polish 小闭环

背景：

- Jeff 继续反馈当前 UI 质感和细节不足，尤其 checkbox 等控件显得 low。
- 本轮继续暂停堆功能，使用 `ui-ux-pro-max` / frontend design 方向做 Profile 运营台最小 UI polish。
- 参考 `/home/jeff/code/reference-repos/saas_kit` 的 B2B SaaS app shell / data table 质感，只借鉴低噪声控件、command bar、table row 和 inspector 层级；未复制整仓，未迁入 auth/db/payment/schema。

本轮实现：

- `frontend/src/styles/globals.css`
  - 收敛 `.btn`、`.input`、`.label` 的圆角、边框、阴影、hover/focus 和 disabled 状态。
  - 新增 `.form-section`、`.section-title`、`.choice-card`、`.choice-checkbox`、`.token-chip`、`.icon-action`。
- `frontend/src/components/ProfileForm.tsx`
  - 创建/编辑页升级为更专业的配置表单 section。
  - 核心字段补 `id/htmlFor`，行为 checkbox 改为 choice card，tag swatch / removable chip / launch arg action 补可访问名称。
  - 保留真实 create/update/delete/cancel 语义。
- `frontend/src/components/BulkActionBar.tsx`
  - bulk toolbar 继续降噪为 compact command bar。
  - 保留 `Check health` 主动作、tag form、delete confirm、running/stopped 过滤语义。
- `frontend/src/components/ProfileTable.tsx`
  - checkbox、selected row、preview row、hover、Open action 视觉细节 polish。
  - 保留 `min-w-[840px]`、table region 横向滚动、固定 64px 行高和 120 条阈值虚拟滚动。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector header、section icon 和字段 hover 降噪。
- `frontend/src/App.tsx`
  - 移动端顶部 `New Profile` 主按钮保持单行和稳定高度。
- 任务文档：
  - `docs/ai-docs/v1/tasks/03-profile-operations-console.md` 追加本轮记录。
  - `保留创建/编辑 profile 能力` 已按测试和浏览器证据标为完成。

验证：

```bash
cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileForm.test.tsx
# 2 passed, 20 passed

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileForm.test.tsx src/App.test.tsx
# 4 passed, 45 passed

cd frontend && npm test -- --run
# 11 passed, 101 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed

git diff --check
# passed
```

浏览器证据：

- QA 地址：`http://127.0.0.1:8092/`。
- QA 数据目录：`/tmp/cloakbrowser-ui-polish-qa-data`。
- 数据规模约 184 profiles，用于验证数百 profile 虚拟滚动。
- 桌面 `1440x900`：
  - table Actions 可见。
  - bulk `Check health` 真实调用。
  - bulk tag `polish-v2` 真实写入并出现在 filter / row tags。
  - 主表滚动到 `Polish QA Profile 139+`，早期 rows 离开 DOM，虚拟滚动仍生效。
  - create -> edit -> rename 流程可用。
- 移动 `390x844`：
  - `body.scrollWidth === window.innerWidth === 390`。
  - table region `clientWidth=352`、`scrollWidth=846`，横向滚动到右侧后 Actions / Open 可见。
  - sidebar overlay 不撑破 body。
  - 顶部 `New Profile` 主按钮保持单行。
- `agent-browser errors --clear` 无相关应用错误。

截图：

- `/tmp/cloak-ui-polish-v2-desktop.png`
- `/tmp/cloak-ui-polish-v2-bulk-selected.png`
- `/tmp/cloak-ui-polish-v2-bulk-tag-form.png`
- `/tmp/cloak-ui-polish-v2-bulk-tag-applied.png`
- `/tmp/cloak-ui-polish-v2-health-check.png`
- `/tmp/cloak-ui-polish-v2-virtual-scroll.png`
- `/tmp/cloak-ui-polish-v2-create-form.png`
- `/tmp/cloak-ui-polish-v2-edit-form-after-create.png`
- `/tmp/cloak-ui-polish-v2-create-submit-edit.png`
- `/tmp/cloak-ui-polish-v2-mobile-nowrap.png`
- `/tmp/cloak-ui-polish-v2-mobile-actions-nowrap.png`
- `/tmp/cloak-ui-polish-v2-mobile-sidebar-nowrap.png`

仍未做：

- VNC viewer 能力复核。
- 空态拆分。
- 窄屏 card list。
- 服务端分页。

03 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 27. 2026-05-26 VNC viewer 能力保留小闭环

背景：

- 03 Profile 运营台经过 dense table / summary inspector / bulk actions / UI polish 后，需要复核原有 running profile 的 VNC viewer 入口没有被破坏。
- 本轮只保留和验证 VNC viewer 入口、前端 noVNC 连接和断开返回路径，不改 VNC proxy、KasmVNC 或 noVNC 生产逻辑。

实现与测试：

- `frontend/src/App.test.tsx`
  - mock `ProfileViewer`，覆盖 running profile 从 operations table 点击 `Open` 后进入 VNC viewer。
  - 覆盖 viewer `onDisconnect` 后返回 `Edit Profile`。
- `frontend/src/components/ProfileViewer.test.tsx`
  - mock 可构造的 noVNC `RFB`，断言连接 `ws://<host>/api/profiles/<profile_id>/vnc`。
  - 断言 `wsProtocols: ["binary"]`、`scaleViewport=true`、`resizeSession=false`、`showDotCursor=true`。
  - 触发 noVNC `disconnect`，断言上层 `onDisconnect` 被调用。
- `docs/ai-docs/v1/tasks/03-profile-operations-console.md`
  - `保留 VNC viewer 能力` 已按本轮证据勾选。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileViewer.test.tsx src/App.test.tsx
# 2 passed, 20 passed

cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileViewer.test.tsx src/components/ProfileTable.test.tsx
# 3 passed, 44 passed

cd frontend && npm test -- --run
# 11 passed, 105 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed

git diff --check
# passed
```

浏览器证据：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8093/`。
- QA 数据目录：`/tmp/cloakbrowser-vnc-retain-qa-data`。
- host 环境 `command -v Xvnc` 无输出，无法直接启动真实 KasmVNC；本轮用临时 fake RFB WebSocket 服务模拟最小 RFB handshake，以验证前端 noVNC viewer 和后端 VNC proxy 路径。
- 桌面 `1440x900`：
  - table 显示 `QA Running VNC Profile` 为 running，inspector 显示 `VNC :6119`。
  - 点击 table `Open` 后进入 viewer。
  - viewer 显示 `Connected`，存在 canvas，Automation API copy action 可见。
  - 点击 `Stop` 后回到 `Edit Profile`，运行数归零，`Launch` 按钮恢复。
- `agent-browser errors --clear` 无相关应用错误。

截图：

- `/tmp/cloak-vnc-retain-viewer-connected.png`
- `/tmp/cloak-vnc-retain-stop-edit.png`

仍未做：

- 真实 KasmVNC / `Xvnc` 二进制启动端到端复验，需在 Docker/运行时回归补验。
- 当时 03 剩余：空态拆分、窄屏 card list；本轮后空态拆分已完成。

03 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 28. 2026-05-26 Profile 运营台空态拆分小闭环

背景：

- 03 模块剩余空态拆分：无 profile、筛选无结果、health 未检测。
- 本轮在已完成 UI polish、bulk action 和虚拟滚动基础上补齐空态体验，不重构运营台主结构。
- `ui-ux-pro-max` 本轮设计系统仍采用 Data-Dense Dashboard：浅色、专业 B2B、低噪声、明确 CTA 和稳定 focus。

本轮实现：

- `frontend/src/components/ProfileTable.tsx`
  - 新增 `totalProfileCount`、`hasActiveFilters`、`onCreateProfile`、`onClearFilters`。
  - 空库显示 `No profiles yet` 和 `Create profile`。
  - 筛选无结果显示 `No profiles match these filters` 和 `Clear filters`。
  - 可见 rows 全部 health 缺失或 `unknown` 时显示 `Health not checked yet` 提示，不遮挡 rows 和 `Open` action。
  - 保留 `min-w-[840px]`、table 自身横向滚动、固定 64px 行高和主表虚拟滚动。
- `frontend/src/App.tsx`
  - 增加 `profileFiltersEqual()` 和 `hasActiveFilters`。
  - 将 profile 总数、清空筛选和创建 profile 动作传给 `ProfileTable`。
- `frontend/src/components/ProfileTable.test.tsx`
  - 覆盖首次空态、筛选空态、health 未检测提示和虚拟滚动 reset。
- `frontend/src/App.test.tsx`
  - 覆盖空态创建、筛选空态清空、health 未检测不阻塞 table 操作。
- `docs/ai-docs/v1/tasks/03-profile-operations-console.md`
  - `空态拆分` 已勾选，并追加本轮记录。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/App.test.tsx
# 2 passed, 45 passed

cd frontend && npm test -- --run
# 11 passed, 110 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed
```

浏览器证据：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:18181/`。
- QA 数据目录：`/tmp/cloakbrowser-empty-qa-data`。
- 桌面 `1440x900`：
  - 空库 `No profiles yet` 可见。
  - 2 个 profile 下 `Health not checked yet` 可见，table rows / Actions 仍可见。
  - select all 后 bulk bar 可见，`Check health` 真实调用后端并更新 risk-first 状态。
  - 搜索无结果显示 `No profiles match these filters`，`Clear filters` 恢复 rows。
- 移动 `390x844`：
  - `body.scrollWidth === window.innerWidth === 390`。
  - table region `overflow === "auto"`，横向滚动不撑破 body。
- `agent-browser console --clear` / `agent-browser errors --clear` 无相关应用错误。

截图：

- `/tmp/cloakbrowser-polish-screens/no-profiles-desktop.png`
- `/tmp/cloakbrowser-polish-screens/health-unknown-desktop.png`
- `/tmp/cloakbrowser-polish-screens/bulk-selected-desktop.png`
- `/tmp/cloakbrowser-polish-screens/bulk-check-health-after.png`
- `/tmp/cloakbrowser-polish-screens/filtered-empty-desktop.png`
- `/tmp/cloakbrowser-polish-screens/mobile-table.png`

仍未做：

- 当时 03 剩余：窄屏 card list；后续已在第 29 节完成。

## 29. 2026-05-26 窄屏 card list 与高质感控件 polish 收口

背景：

- Jeff 继续反馈 Profile 运营台控件质感仍不够，尤其 checkbox / bulk action / table row / toolbar / inspector。
- 本轮继续使用 `ui-ux-pro-max` 和 frontend design 方向，参考 `/home/jeff/code/reference-repos/saas_kit` 的 B2B SaaS app shell / data table 规律，但没有复制其 auth/db/payment/schema。
- 本轮只改 CloakBrowser Profile 运营台，不触碰 Project Mileage 钱包、订单、权限逻辑，不 push 远端。

本轮实现：

- `frontend/src/components/ProfileTable.tsx`
  - `<768px` 下从 desktop table 降级为 `ProfileCardList`，桌面仍使用 `ProfileDesktopTable`，避免 table/card 双渲染。
  - mobile card 保留 checkbox、select all、bulk action、preview、Open、health、proxy 脱敏、GeoIP fallback、tags、last checked。
  - card list 使用固定高度虚拟滚动，`PROFILE_CARD_ROW_HEIGHT = 188`；全选仍作用完整 filtered ids。
  - mobile card selection toolbar 在有 bulk bar 时使用 `top-11`，避免 sticky 重叠。
  - table row / card selected / previewed 状态改为低噪声左侧状态线和渐变。
- `frontend/src/components/BulkActionBar.tsx`
  - bulk toolbar 降噪，`Check health` 保持唯一主动作；launch / stop / tag / delete 的真实动作和高风险确认语义不变。
- `frontend/src/components/ProfileFilters.tsx`
  - main filter strip 增加 `role="toolbar"` / `aria-label="Profile filters"`。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector header 和 section icon 降噪。
- `frontend/src/App.tsx`
  - 主区 surface 降低 shadow / ring 噪声。
  - 修复移动端从 card `Open` 进入 edit 后 top bar 造成的 2px body 横向 overflow。
- `frontend/src/styles/globals.css`
  - 统一 enabled / disabled button cursor。
- `docs/ai-docs/v1/tasks/03-profile-operations-console.md`
  - `窄屏降级为 card list` 已勾选，并追加本轮证据。
- `docs/ai-docs/v1/tasks/progress.md`
  - 03 Profile 运营台已标为完成。

验证：

```bash
cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileTable.test.tsx src/components/ProfileFilters.test.tsx
# 3 passed, 51 passed

cd frontend && npm test -- --run
# 11 passed, 115 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 217 passed

git diff --check
# passed
```

浏览器证据：

- QA 地址：`http://127.0.0.1:18183/`。
- QA 数据目录：`/tmp/cloakbrowser-ui-card-polish-data`，共 180 个 profile。
- 桌面 `1440x900`：
  - dense table 可见、card list 不渲染，`Actions` / `Open` 首屏可见。
  - `body.scrollWidth === window.innerWidth === 1440`。
  - bulk `Check health` 真实可点击并完成，无前端 alert。
- 移动 `390x844`：
  - card list 可见、desktop table 不渲染。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 首屏约 20 张 card，180 条没有全量渲染。
  - card selection toolbar 在 bulk bar 下方，class 包含 `top-11`。
  - card 虚拟滚动到中段后早期 card 离开 region DOM。
  - card `Open` 进入 `Edit Profile` 后 `body.scrollWidth` 小于 `window.innerWidth`。
- `agent-browser console --clear` / `agent-browser errors --clear` 无相关应用错误。

截图：

- `/tmp/cloakbrowser-ui-card-polish-screens/desktop-table-polish.png`
- `/tmp/cloakbrowser-ui-card-polish-screens/desktop-bulk-selected-polish.png`
- `/tmp/cloakbrowser-ui-card-polish-screens/desktop-bulk-health-polish.png`
- `/tmp/cloakbrowser-ui-card-polish-screens/desktop-virtual-scroll-polish.png`
- `/tmp/cloakbrowser-ui-card-polish-screens/mobile-card-polish.png`
- `/tmp/cloakbrowser-ui-card-polish-screens/mobile-card-bulk-selected-polish.png`
- `/tmp/cloakbrowser-ui-card-polish-screens/mobile-card-health-polish.png`
- `/tmp/cloakbrowser-ui-card-polish-screens/mobile-card-virtual-scroll-polish.png`
- `/tmp/cloakbrowser-ui-card-polish-screens/mobile-card-open-edit-polish.png`

仍未做：

- 服务端分页未做；当前继续用固定高度虚拟滚动覆盖数百 profile。
- Profile 详情 / VNC viewer 还未改为抽屉式连续运营形态。
- 04 Proxy Manager 尚未开始。

## 30. 2026-05-26 Proxy asset 表与 CRUD API 小闭环

背景：

- 03 Profile 运营台已完成，按 `tasks/progress.md` 进入 04 Proxy Manager。
- 本轮遵循 TDD：先写 `backend/tests/test_proxies.py` 并确认失败，再实现后端最小 CRUD。
- 本小闭环只做 proxy asset 后端存储和 CRUD API，不做检测、批量检测、前端页面、CSV 导入或 profile 分配。

本轮实现：

- `backend/database.py`
  - 新增 `proxies` 表。
  - 新增 `create_proxy()`、`list_proxies()`、`get_proxy()`、`update_proxy()`、`delete_proxy()`。
  - 字段覆盖 name、url、country_code、city、asn、provider、tags、notes、last_check_*、created_at、updated_at。
  - 入库前 normalize + validate，`host:port` 会保存为 `http://host:port`；无效 proxy 不保存。
- `backend/proxies.py`
  - 新增 proxy asset helper。
  - 复用 `backend/browser_manager.py` 里的 `_normalize_proxy()`、`_validate_proxy()`、`_redact_proxy_url()`。
- `backend/models.py`
  - 新增 `ProxyCreate`、`ProxyUpdate`、`ProxyResponse`。
- `backend/main.py`
  - 新增 `GET /api/proxies`。
  - 新增 `POST /api/proxies`。
  - 新增 `GET /api/proxies/{proxy_id}`。
  - 新增 `PUT /api/proxies/{proxy_id}`。
  - 新增 `DELETE /api/proxies/{proxy_id}`。
  - API 响应默认脱敏 `url`，例如 `socks5://user:hiddenpass@jp.proxy.example:1080` 返回 `socks5://jp.proxy.example:1080`。
  - 创建/更新无效 proxy 返回 400，错误响应不泄露密码。
- `backend/tests/test_proxies.py`
  - 覆盖表创建、数据库 CRUD、tags 往返、URL 规范化、无效 URL 拒绝、API CRUD、API 脱敏、404。
  - 覆盖删除 proxy asset 不删除仍使用同一 proxy 字符串的 profile。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 勾选 `proxies` 表、proxy CRUD、URL 保存/脱敏、无效 proxy 不保存、列表不明文展示密码、删除 proxy 不删除 profile。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 7 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 15 passed

.venv/bin/python -m pytest backend/tests -q
# 224 passed

git diff --check
# passed
```

仍未做：

- `POST /api/proxies/{id}/check`。
- `POST /api/proxies/bulk/check`。
- 前端 Proxy Manager 页面、搜索筛选、批量检测、CSV 粘贴导入。
- 将 proxy 分配到 profile、从 profile 当前 proxy 保存为 proxy asset。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 31. 2026-05-26 Profile 运营台控件质感二次 polish 小闭环

背景：

- Jeff 继续反馈 Profile 运营台质感和细节还不够，尤其是 checkbox、bulk action、table row、toolbar、inspector。
- 本轮暂停继续堆功能，只做 UI/UE polish；不触碰 Project Mileage 业务逻辑，不复制 `/home/jeff/code/reference-repos/saas_kit` 的 auth、db、payment、schema。
- 当前仓库仍有 04 Proxy Manager 的未完成红灯测试在 `backend/tests/test_proxies.py`，本轮没有接管该后端小闭环。

本轮实现：

- `frontend/src/components/ProfileTable.tsx`
  - `SelectionCheckbox` 增加 `data-state="checked|unchecked|indeterminate"`。
  - checkbox 保留真实 input、半选态、`aria-checked="mixed"`、键盘 focus。
  - table header / row / card selected-preview 状态降噪，保留 `min-w-[840px]`、64px table 行高、188px card 行高和虚拟滚动阈值。
- `frontend/src/components/BulkActionBar.tsx`
  - 增加 `Selected profile summary` / `Bulk action commands` 两个 `role="group"`。
  - secondary actions 改成图标按钮，保留 `aria-label` / `title` / loading 文案。
  - `Check health` 仍为主动作且真实调用后端；launch / stop / tag / delete 既有语义不变。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - Health / Runtime / GeoIP / Proxy / Device section 增加可访问 region。
  - inspector header / section surface / field row 做低噪声 polish。
- `frontend/src/components/ProfileTable.test.tsx`
  - 补充 checkbox 状态、bulk toolbar 分组断言。
- `frontend/src/components/ProfileSummaryPanel.test.tsx`
  - 补充 inspector section region 断言。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx
# 2 passed, 31 passed

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 1 passed, 30 passed

cd frontend && npm test -- --run
# 11 passed, 115 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8080/`，当前 QA 数据约 162 个 profiles。
- 桌面 `1440x900`：
  - 选择 2 个 profile 后 bulk toolbar 分组存在，`Check health` 可点击，`Actions` / `Open` 和 `Clear` 可见。
  - `body.scrollWidth === window.innerWidth === 1440`，table region `overflow: auto`。
- 移动 `390x844`：
  - card list 可见，desktop table 不渲染，sidebar 初始收起。
  - 选择 1 个 profile 后 bulk toolbar 分组存在。
  - `body.scrollWidth === window.innerWidth === 390`，约 21 张 card 在 DOM 中，数百 profile 没有全量渲染。
- `agent-browser errors` / `agent-browser console` 无输出。

截图：

- `/tmp/cloakbrowser-ui-polish-v3-screens/desktop-table-bulk-inspector.png`
- `/tmp/cloakbrowser-ui-polish-v3-screens/mobile-card-selected.png`

仍未做：

- 服务端分页未做；当前继续以固定高度虚拟滚动覆盖数百 profile。
- ProfileForm 页签、Viewer EnvironmentStrip、Proxy Manager 页面未在本轮处理。
- 04 Proxy Manager 的 `POST /api/proxies/{id}/check` 仍是下一后端小闭环。

## 32. 2026-05-26 Proxy 单个检测 API 小闭环

背景：

- 继续 04 Proxy Manager，基于 proxy asset CRUD API 增加 `POST /api/proxies/{id}/check`。
- 本小闭环只做单个 proxy 检测 API；不做 bulk check、前端 Proxy Manager、CSV 导入或 profile 分配。
- 使用 TDD：先补充 `backend/tests/test_proxies.py`，确认 405 红灯后实现。

本轮实现：

- `backend/database.py`
  - `proxies` 表新增 `last_check_error`。
  - 对旧库做兼容迁移，缺列时执行 `ALTER TABLE proxies ADD COLUMN last_check_error TEXT`。
  - `create_proxy()` / `update_proxy()` 支持写入检测错误原因。
- `backend/models.py`
  - `ProxyResponse` 新增 `last_check_error`。
- `backend/main.py`
  - 新增 `POST /api/proxies/{proxy_id}/check`。
  - 成功检测时调用 `resolve_network_geo(raw_proxy_url)`，使用包含凭据的原始 proxy URL 做真实网络检测。
  - 成功后写入 `last_check_status="good"`、IP、country、timezone、locale、source、checked_at，并清空错误。
  - 检测失败时返回 200，不抛 500；写入 `last_check_status="error"`、`last_check_at` 和脱敏后的 `last_check_error`。
  - API 响应继续通过 `_proxy_response()`，`url` 默认脱敏。
- `backend/tests/test_proxies.py`
  - 覆盖 missing proxy 返回 404。
  - 覆盖成功检测写入 `last_check_*`。
  - 覆盖失败检测不会泄露 proxy 密码，DB 和 API 响应都脱敏。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 勾选 `POST /api/proxies/{id}/check`、`支持字段`、`检测时复用 GeoIP resolver`、`检测失败保留错误原因`。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 9 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 17 passed

.venv/bin/python -m pytest backend/tests/test_health.py backend/tests/test_api.py -q
# 70 passed

.venv/bin/python -m pytest backend/tests -q
# 226 passed

git diff --check
# passed
```

接管后新鲜复验：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 17 passed

git diff --check
# passed
```

仍未做：

- `POST /api/proxies/bulk/check`。
- 前端 Proxy Manager 页面、搜索筛选、批量检测、CSV 粘贴导入。
- 将 proxy 分配到 profile、从 profile 当前 proxy 保存为 proxy asset。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 33. 2026-05-26 Proxy 批量检测 API 小闭环

背景：

- 继续 04 Proxy Manager，基于单个 proxy check 增加 `POST /api/proxies/bulk/check`。
- 本小闭环只做后端批量检测 API，不做前端 Proxy Manager 页面、CSV 导入、搜索筛选或 profile 分配。
- 使用 TDD：先补充 `backend/tests/test_proxies.py`，确认 `/api/proxies/bulk/check` 返回 404 红灯后实现。

本轮实现：

- `backend/tests/test_proxies.py`
  - 新增 bulk check 部分成功测试：成功 proxy、检测失败 proxy、missing id 同批返回。
  - 断言 HTTP 200、`total/succeeded/failed/results` 汇总正确，部分失败不影响整批。
  - 断言 GeoIP resolver 接收包含凭据的原始 proxy URL。
  - 断言响应、错误原因和 DB `last_check_error` 不泄露 `hiddenpass`。
  - 新增 `proxy_ids=[]` 返回 422 测试。
- `backend/models.py`
  - 新增 `ProxyBulkCheckRequest`、`ProxyBulkCheckResult`、`ProxyBulkCheckResponse`。
- `backend/main.py`
  - 新增 `POST /api/proxies/bulk/check`。
  - 路由放在 `POST /api/proxies/{proxy_id}/check` 前，避免 `bulk` 被动态路由当成 proxy id。
  - 抽出 `_run_proxy_check()`，单个检测和批量检测共用 GeoIP、写库和失败状态逻辑。
  - 抽出 `_safe_proxy_check_error()`，异常中的原始 proxy URL 会被替换成脱敏 URL，独立出现的 proxy password 也会被替换。
  - missing proxy id 只作为单项失败返回 `Proxy not found`。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 勾选 `新增 POST /api/proxies/bulk/check`。
  - 追加本轮小闭环记录。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 11 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 19 passed

.venv/bin/python -m pytest backend/tests/test_health.py backend/tests/test_api.py -q
# 70 passed

.venv/bin/python -m pytest backend/tests -q
# 228 passed
```

仍未做：

- 前端 Proxy Manager 页面、搜索筛选、批量检测交互。
- 按国家、provider、tag 筛选。
- CSV 粘贴导入。
- 将 proxy 分配到 profile。
- 从 profile 当前 proxy 保存为 proxy asset。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 34. 2026-05-26 Proxy 分配到 Profile 后端 API 小闭环

背景：

- 继续 04 Proxy Manager，补齐后端层面的 proxy asset 分配到 profile 能力。
- 本小闭环只做 `POST /api/proxies/{id}/assign`，不做前端 Proxy Manager 分配入口，不迁移 `profiles.proxy` 为 `proxy_id`。
- 关键边界：assignment API 不返回完整 `ProfileResponse`，避免把 profile 中保存的 raw proxy URL 暴露给前端。

本轮实现：

- `backend/tests/test_proxies.py`
  - 新增带凭据 proxy asset 分配给多个 profile 的测试。
  - 断言响应中不包含 `hiddenpass`。
  - 断言 DB 中 `profiles.proxy` 写入 raw proxy URL，保持 launch / health 继续可用。
  - 覆盖同批 missing profile 部分失败，HTTP 仍返回 200。
  - 覆盖 missing proxy 返回 404。
  - 覆盖 `profile_ids=[]` 返回 422。
- `backend/models.py`
  - 新增 `ProxyAssignRequest`、`ProxyAssignResult`、`ProxyAssignResponse`。
- `backend/main.py`
  - 新增 `POST /api/proxies/{proxy_id}/assign`。
  - 后端内部读取 proxy asset 原始 `url` 并调用 `db.update_profile(profile_id, proxy=raw_url)`。
  - 响应只返回脱敏后的 `ProxyResponse` 和逐项 assignment result。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 在 `支持将 proxy 分配到 profile` 下新增并勾选后端 assignment API 子项。
  - 顶层 `支持将 proxy 分配到 profile` 暂不勾选，因为前端分配入口未做。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 13 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 21 passed

.venv/bin/python -m pytest backend/tests/test_health.py backend/tests/test_api.py -q
# 70 passed

.venv/bin/python -m pytest backend/tests -q
# 230 passed
```

仍未做：

- 前端 Proxy Manager 分配入口。
- 从 profile 当前 proxy 保存为 proxy asset。
- 前端 Proxy Manager 页面、搜索筛选、批量检测交互。
- 按国家、provider、tag 筛选。
- CSV 粘贴导入。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 35. 2026-05-26 Profile 当前 Proxy 保存为 Proxy Asset 后端 API 小闭环

背景：

- 继续 04 Proxy Manager，补齐从 profile 当前 proxy 字符串保存为 proxy asset 的后端入口。
- 本小闭环只做 `POST /api/profiles/{id}/proxy-asset`，不做前端 Proxy Manager 页面或按钮，不迁移 `profiles.proxy` 为 `proxy_id`。
- 关键边界：请求体不允许前端提交 `url`；后端只从 profile 当前 `proxy` 字段读取原始 URL，保存时复用 proxy asset normalize / validate，响应继续脱敏。

本轮实现：

- `backend/tests/test_proxies.py`
  - 新增 profile 当前 proxy 含凭据时保存为 proxy asset 的测试。
  - 断言 API 响应不包含 `hiddenpass`。
  - 断言 DB 中 proxy asset 保留 raw proxy URL，后续真实连接仍可用。
  - 覆盖 profile 没有 proxy 返回 400。
  - 覆盖 profile proxy 无效时返回 400，错误响应不泄露密码。
  - 覆盖 missing profile 返回 404。
- `backend/models.py`
  - 新增 `ProxyFromProfileCreate`，字段为 `ProxyCreate` 去掉 `url` 后的元信息子集。
- `backend/main.py`
  - 新增 `POST /api/profiles/{profile_id}/proxy-asset`。
  - 查不到 profile 时返回 404。
  - profile 没有 proxy 时返回 `Profile has no proxy`。
  - 调用 `db.create_proxy(**data)` 保存，复用现有 proxy normalize / validate。
  - 响应通过 `_proxy_response(proxy)` 返回脱敏后的 `ProxyResponse`。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 勾选 `支持从 profile 当前 proxy 保存为 proxy asset`。
  - 追加本轮小闭环记录。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 15 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 23 passed

.venv/bin/python -m pytest backend/tests/test_health.py backend/tests/test_api.py -q
# 70 passed

.venv/bin/python -m pytest backend/tests -q
# 232 passed
```

仍未做：

- 前端 Proxy Manager 页面和按钮。
- 前端 Proxy Manager 分配入口，因此顶层 `支持将 proxy 分配到 profile` 暂不勾选完成。
- 前端搜索、筛选、批量检测交互。
- 按国家、provider、tag 筛选。
- CSV 粘贴导入。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 36. 2026-05-26 Profile 运营台控件质感三次 polish 小闭环

背景：

- Jeff 继续反馈 Profile 运营台界面质感和控件细节还不够，尤其是 checkbox / bulk action / table row / toolbar / inspector。
- 本轮暂停 04 Proxy Manager 功能推进，继续在 03 Profile 运营台已完成模块上做 UI polish 小闭环。
- 使用 `ui-ux-pro-max` 生成 Data-Dense Dashboard 方向，并派发两个只读子 agent：
  - 一个审计当前 Profile 运营台实现、测试边界和不能破坏的行为。
  - 一个只读提炼 `/home/jeff/code/reference-repos/saas_kit` 的 B2B SaaS app shell / data table 视觉原则。
- 结论：只吸收密度、低噪声状态、ring / shadow、控件分组和 inspector 层级；禁止复制参考仓库代码，禁止迁入 auth / db / payment / schema。

本轮实现：

- `frontend/src/components/ProfileTable.tsx`
  - `SelectionCheckbox` 保留真实 checkbox input、`data-state`、`aria-checked="mixed"`、键盘 focus 和 disabled 语义。
  - checkbox 命中区增加低噪声 hover border / surface / inset highlight。
  - checkbox 视觉层改为 white-to-slate / blue gradient，checked / mixed 状态更稳定。
- `frontend/src/components/BulkActionBar.tsx`
  - 保持 `sticky top-0 h-11` 不变，不破坏 table header 和 card selection toolbar 的 `top-11` 偏移。
  - summary group / command group 改为更克制的 gradient surface 和更轻 shadow。
  - `Check health` 与 inline `Apply tag` 主按钮增加低噪声 blue gradient 和 inset highlight；真实动作、loading、disabled 语义不变。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - 空 inspector 改为带 `Inspector` header、icon container 和内层空态 surface 的审计面板空态。
- `frontend/src/components/ProfileTable.test.tsx`
  - 补充桌面 selected 后 `thead` 保留 `top-11`。
  - 补充桌面和窄屏 selected + previewed 同时存在时 `selected` 状态优先。
  - 补充窄屏 card checkbox 的 checked / unchecked / indeterminate `data-state`。
  - 补充 bulk tag form 和 delete confirm 通过 Escape 关闭且不触发 mutation。
- `frontend/src/components/ProfileSummaryPanel.test.tsx`
  - 补充空 inspector 状态测试。

保持不变：

- 桌面 table `Actions` / `Open` 仍可见。
- 移动端 body 不横向撑破；窄屏继续只渲染 card list，不重复 desktop table。
- `Check health` 批量动作仍真实调用后端。
- 批量 launch / stop / tag / delete 保留既有真实动作、运行态过滤、disabled 和 typed delete 确认语义。
- 主表超过 120 条、左侧超过 80 条的固定行高虚拟滚动语义不变。
- proxy 可见文本和 `title` 继续不暴露用户名/密码。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx
# 2 passed, 37 passed

cd frontend && npm test -- --run
# 11 passed, 121 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8080/`，当前 QA 数据 162 个 profiles。
- 桌面 `1440x900`：
  - dense table 可见，card list 不渲染。
  - `body.scrollWidth === window.innerWidth === 1440`。
  - `Actions` / `Open` 首屏可见。
  - 当前主表只渲染 26 个 `Open Polish QA Profile` 按钮，不是 162 条全量渲染。
  - 选择首行后 bulk toolbar 显示 `1 selected`，summary / commands 分组存在。
  - 表头 `Select all visible profiles` 为 mixed，`thead` 保留 `top-11`。
  - 点击 `Check health` 后 selection 保留，无前端 alert。
  - 主表滚动到中段后 early rows 离开 table region，窗口内显示 `Polish QA Profile 115+`。
- 移动 `390x844`：
  - card list 可见，desktop table 不渲染。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 首屏渲染约 20 张 card，不是全量渲染。
  - 选择首张 card 后 bulk toolbar 可见，card selection toolbar 保留 `top-11`。
  - 滚动到中段后 early card 离开 table region，仍只渲染约 20 张 card。
  - 打开 sidebar 后为 overlay，body 仍不横向撑破。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 仅执行清理，无相关前端错误。

截图：

- `/tmp/cloakbrowser-ui-polish-v4-screens/desktop-table.png`
- `/tmp/cloakbrowser-ui-polish-v4-screens/desktop-bulk-selected.png`
- `/tmp/cloakbrowser-ui-polish-v4-screens/desktop-check-health.png`
- `/tmp/cloakbrowser-ui-polish-v4-screens/desktop-virtual-scroll.png`
- `/tmp/cloakbrowser-ui-polish-v4-screens/mobile-card.png`
- `/tmp/cloakbrowser-ui-polish-v4-screens/mobile-card-selected.png`
- `/tmp/cloakbrowser-ui-polish-v4-screens/mobile-card-virtual-scroll.png`
- `/tmp/cloakbrowser-ui-polish-v4-screens/mobile-sidebar.png`

仍未做：

- 服务端分页未做。
- bulk toolbar 未改成底部浮动形态，避免破坏当前 sticky header / virtualized table 成熟语义。
- ProfileForm 页签、Viewer EnvironmentStrip、Proxy Manager 页面未改。
- 04 Proxy Manager 前端页面和剩余能力仍未完成。

## 37. 2026-05-26 Profile 运营台控件质感四次 polish 小闭环

背景：

- Jeff 继续反馈当前界面质感和细节还不够，复选框等控件显 low。
- 本轮继续暂停 04 Proxy Manager 功能推进，只做 Profile 运营台 UI polish。
- 使用 `ui-ux-pro-max` 确认 B2B SaaS / data-dense operations console 方向。
- 只读参考 `/home/jeff/code/reference-repos/saas_kit/ai-mksaas-template` 的 data table / action bar / checkbox / inspector 视觉原则，未复制业务逻辑，未迁入 auth / db / payment / schema。
- 派发只读子 agent 审计当前 Profile 运营台实现和不能破坏的测试语义。

本轮实现：

- `frontend/src/components/ProfileTable.tsx`
  - 保留真实 checkbox input、`data-state`、`aria-checked="mixed"`、键盘 focus、disabled 和虚拟滚动。
  - checkbox 改为更克制的 white / blue solid state、18px 控件、7px hit target、低噪声 hover / focus ring。
  - table header 改为 slate toolbar 质感，行状态收敛为左侧状态条 + 轻背景。
  - 移动 card list 继续独立渲染，`Open` action 常显。
- `frontend/src/components/BulkActionBar.tsx`
  - 保留 `sticky top-0 h-11` 和 `top-11` offset 契约。
  - summary / commands 改为单层浅色工具条，`1 selected` 使用深色明确选中状态。
  - `Check health` 保持主动作突出且真实可用；Launch / Stop / Tag / Delete 保持既有 disabled / confirmation 语义。
  - 新增 `Escape` 清空 selection；tag form / delete confirm 打开时不误触清空。
- `frontend/src/components/ProfileFilters.tsx`
  - search / select 控件统一 6px 半径、轻 shadow 和 focus ring。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector header、section icon、warning block、property row 做更精细的属性面板视觉。
- `frontend/src/App.tsx`
  - top bar pill、filter band、table panel 轻量 polish，减少卡片堆叠感。
- `frontend/src/styles/globals.css`
  - font fallback 优先 `Plus Jakarta Sans`，form controls 继承字体。
  - 增加 `prefers-reduced-motion: reduce`。
- `frontend/src/components/ProfileTable.test.tsx`
  - TDD 新增 `Escape` 清空 bulk selection 测试，已先确认红灯。

保持不变：

- 桌面 `Actions` / `Open` 首屏仍可见。
- 移动端 body 不横向撑破；窄屏继续 card list。
- 表格自身保持横向滚动边界。
- 批量 `Check health`、launch、stop、tag、delete 的真实业务语义不变。
- 高风险 delete 仍只作用 stopped profiles，并要求输入 `DELETE`。
- 主表超过 120 条、左侧超过 80 条的固定行高虚拟滚动语义不变。
- proxy 可见文本和 `title` 继续不暴露用户名/密码。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 1 failed, 35 passed
# 红灯：Escape 尚未清空 bulk selection

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 1 passed, 36 passed

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileFilters.test.tsx src/App.test.tsx
# 4 passed, 59 passed

cd frontend && npm test -- --run
# 11 passed, 122 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8080/`，当前 QA 数据 162 个 profiles。
- 桌面 `1440x900`：
  - dense table 可见，`Actions` / `Open` 首屏可见。
  - 选择首行后 bulk toolbar 显示 `1 selected`，`Check health` 主动作可见。
  - 按 `Escape` 后 selection 清空，bulk toolbar 消失。
  - `agent-browser errors --clear` 无输出。
- 移动 `390x844`：
  - card list 可见，desktop table 不渲染。
  - `document.documentElement.scrollWidth === window.innerWidth === 390`，body 未横向撑破。
  - filter toolbar、card selection toolbar、Open action 和 inspector 在窄屏下未重叠。

截图：

- `/tmp/cloakbrowser-ui-polish-v5-screens/desktop-profile-ops.png`
- `/tmp/cloakbrowser-ui-polish-v5-screens/desktop-bulk-selected.png`
- `/tmp/cloakbrowser-ui-polish-v5-screens/mobile-profile-ops.png`

仍未做：

- 服务端分页、无限滚动或 Profile 数据架构变更。
- 04 Proxy Manager 前端页面。
- ProfileForm 页签、Viewer EnvironmentStrip。

## 38. 2026-05-26 Profile 运营台控件质感五次降噪 polish 小闭环

背景：

- Jeff 继续反馈当前界面质感和细节还不够，尤其是 checkbox、bulk action、table row、toolbar、inspector。
- 本轮暂停 04 Proxy Manager 前端功能推进，只做 Profile 运营台最小 UI polish。
- 使用 `ui-ux-pro-max` 确认 data-dense operations console 方向，并派发只读子 agent 审计当前 Profile 运营台和 `/home/jeff/code/reference-repos/saas_kit`。结论：当前功能语义已满足，值得追加一个视觉层降噪小闭环。

已完成：

- `frontend/src/components/BulkActionBar.tsx`
  - 降低 summary / commands 外层阴影和 ring，保留 sticky `top-0 h-11`。
  - 新增 `Primary bulk action` / `Secondary bulk actions` 可访问分组，保持 `Check health` 作为一级文字动作。
  - Launch / Stop / Tag / Delete / Clear 保持次级图标/文字命令；typed delete 和运行态过滤语义不变。
- `frontend/src/components/ProfileTable.tsx`
  - table header 改为更平的 white sticky header。
  - row / card / checkbox / tag chip / Open button 去掉过重 shadow，保留 selected / previewed 状态线。
  - 未改 `PROFILE_TABLE_ROW_HEIGHT = 64`、`PROFILE_CARD_ROW_HEIGHT = 188`、120 条虚拟滚动阈值、`min-w-[840px]` 桌面表格契约。
- `frontend/src/components/ProfileFilters.tsx`
  - search / select 控件减少 shadow / ring 堆叠，保留 `role="toolbar"`。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector header、section icon、warning block、空态面板降噪，减少卡片套卡片感。
- `frontend/src/App.tsx`
  - top pill、filter band、table panel 降噪，保持主区表格 + 右侧 inspector。
- `frontend/src/components/ProfileTable.test.tsx`
  - TDD 新增 bulk toolbar primary/secondary 分组测试；先确认红灯后实现。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 1 failed, 35 passed
# 红灯：缺少 Primary bulk action / Secondary bulk actions 分组

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileFilters.test.tsx src/App.test.tsx
# 4 passed, 59 passed

cd frontend && npm test -- --run
# 11 passed, 122 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器验证：

- `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8080/`，QA 数据 162 个 profiles。
- 桌面 `1440x900`：
  - dense table 可见，`Actions` / `Open` 首屏可见。
  - bulk toolbar 显示 `Check health` 一级动作；Escape 可清空 selection。
  - 主表滚动到中段后 table region 内早期 row 离开 DOM，可见 `Polish QA Profile 120`，窗口内 `Open` 按钮约 26 个。
- 移动 `390x844`：
  - card list 可见，desktop table 不渲染。
  - `document.documentElement.scrollWidth === window.innerWidth === 390`。
  - 首屏约 20 张 card，选择首张后 bulk toolbar 和 card selection toolbar 可见。
  - 点击 `Check health` 后 `Last checked` 更新时间，selection 保留。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-ui-polish-v6-screens/desktop-profile-ops.png`
- `/tmp/cloakbrowser-ui-polish-v6-screens/desktop-bulk-selected.png`
- `/tmp/cloakbrowser-ui-polish-v6-screens/desktop-virtual-scroll.png`
- `/tmp/cloakbrowser-ui-polish-v6-screens/mobile-profile-ops.png`
- `/tmp/cloakbrowser-ui-polish-v6-screens/mobile-card-selected.png`
- `/tmp/cloakbrowser-ui-polish-v6-screens/mobile-check-health.png`

仍未做：

- 04 Proxy Manager 前端页面未推进。
- 服务端分页 / 无限滚动未做；当前继续以固定行高虚拟滚动覆盖数百 profile。
- ProfileForm 页签和 Viewer EnvironmentStrip 未改。

注意：

- 本轮开始前曾将无关的 Proxy Manager API client 红灯测试暂存到 stash：

```bash
stash@{0}: wip proxy manager api tests before profile ui polish
```

后续继续 04 Proxy Manager 前端小闭环时，需要先恢复该 stash 或重新写对应测试。

## 39. 2026-05-26 Profile 运营台控件质感六次精修 polish 小闭环

背景：

- Jeff 继续反馈当前界面质感和细节还不够，复选框等控件仍显 low。
- 本轮仍暂停 04 Proxy Manager 功能推进，只做 Profile 运营台最小 UI polish。
- 使用 `ui-ux-pro-max` 确认 B2B data-dense operations dashboard 方向。
- 派发两个只读子 agent：
  - 一个审计当前 Profile 运营台 UI 风险，结论是局部改 checkbox / bulk action / table row / toolbar / inspector，不能动虚拟滚动、行高、批量动作数据流。
  - 一个审计 `/home/jeff/code/reference-repos/saas_kit/ai-mksaas-template`，结论是只借鉴 data table、action bar、checkbox、inspector 的视觉原则，禁止复制 auth / db / payment / schema。

已完成：

- `frontend/src/components/ProfileFilters.tsx`
  - toolbar search / select 增加 `data-filter-control` 和 `data-active`。
  - active search、runtime、tag 等筛选有更明确的边框 / 左侧 accent / soft background。
- `frontend/src/components/ProfileTable.tsx`
  - selection checkbox 增加 `data-control="selection-checkbox"`。
  - checkbox 视觉强化为 18px 控件、solid checked state、低噪声 hover / focus / disabled。
  - desktop row 的 selected / previewed 状态改为 inset 状态线和低噪声背景。
  - `Open` action 常显，hover / focus 更清楚。
- `frontend/src/components/BulkActionBar.tsx`
  - 保持 `sticky top-0 h-11`。
  - summary / commands 分组变成更稳定的白色 data-table surface。
  - `Check health` 仍是一级真实动作。
  - Launch / Stop / Tag / Delete 在 Profile 运营台 UI 中锁定为 disabled，不触发 mutation，不打开 tag form 或 delete confirm。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector header、Open profile 按钮、section icon 精修。
  - Health / Runtime 增加 `data-priority="primary"`，GeoIP / Proxy / Device 为 secondary。
- `frontend/src/App.tsx`
  - 页面背景、filter band、table panel、summary tile 做轻量 token 收口。
- 测试：
  - `ProfileFilters.test.tsx` 新增 active toolbar control 断言。
  - `ProfileSummaryPanel.test.tsx` 新增 section priority 断言。
  - `ProfileTable.test.tsx` 和 `App.test.tsx` 新增 checkbox `data-control` 与高风险批量动作 disabled 断言。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileFilters.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileTable.test.tsx
# 4 failed, 37 passed
# 红灯：缺少 active filter data attribute、inspector priority、selection checkbox data-control、高风险批量动作 disabled 锁定

cd frontend && npm test -- --run src/components/ProfileFilters.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileTable.test.tsx
# 3 passed, 41 passed

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/App.test.tsx
# 2 passed, 50 passed

cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileList.test.tsx src/components/ProfileForm.test.tsx
# 3 passed, 33 passed

cd frontend && npm test -- --run
# 11 passed, 127 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:5173/`。
- 桌面 `1440x900`：
  - dense table 可见，`Actions` / `Open` 首屏可见。
  - 选择首行后 bulk toolbar 显示 `1 selected`。
  - Launch / Stop / Tag / Delete 可见但 disabled，不触发高风险 mutation。
  - 点击 `Check health` 后所选行 `Last checked` 更新时间，问题计数同步变化。
  - 主表滚动到中段后 table region 内早期 row 离开 DOM，可见 `Polish QA Profile 120`，窗口内 `Open` 按钮约 26 个。
  - `document.documentElement.scrollWidth === window.innerWidth === 1440`。
- 移动 `390x844`：
  - card list 可见，desktop table 不渲染。
  - `document.documentElement.scrollWidth === window.innerWidth === 390`。
  - 首屏约 22 张 card，不全量渲染 162 个 profiles。
  - 选择首张 card 后 bulk toolbar 和 card selection toolbar 可见。
  - 高风险批量动作保持 disabled。
  - 点击 `Check health` 后 `Last checked` 更新时间，selection 保留。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-ui-polish-v7-screens/desktop-profile-ops.png`
- `/tmp/cloakbrowser-ui-polish-v7-screens/desktop-bulk-selected.png`
- `/tmp/cloakbrowser-ui-polish-v7-screens/desktop-check-health.png`
- `/tmp/cloakbrowser-ui-polish-v7-screens/desktop-virtual-scroll.png`
- `/tmp/cloakbrowser-ui-polish-v7-screens/mobile-profile-ops.png`
- `/tmp/cloakbrowser-ui-polish-v7-screens/mobile-card-selected.png`
- `/tmp/cloakbrowser-ui-polish-v7-screens/mobile-check-health.png`

仍未做：

- 04 Proxy Manager 前端页面未推进。
- 服务端分页 / 无限滚动未做；当前继续以固定行高虚拟滚动覆盖数百 profile。
- ProfileForm 页签和 Viewer EnvironmentStrip 未改。

注意：

- 工作树仍保留无关的 Proxy Manager API client 未提交改动：
  - `frontend/src/lib/api.ts`
  - `frontend/src/lib/api.test.ts`
- 本轮 commit 时不要把这两个文件混入 UI polish commit。

## 40. 2026-05-26 Proxy Manager 前端 API Client 小闭环

背景：

- 继续 04 Proxy Manager，接管上一轮 UI polish 期间刻意未提交的 Proxy API client diff。
- 后端 proxy asset CRUD、单个检测、批量检测、分配到 profile、从 profile 当前 proxy 保存为 asset 已完成；本轮只补齐前端 API client 和测试，不做页面。
- 派发只读子 agent 审计后端已实现 endpoint 与当前 client diff，确认缺口是 `getProxy()`、`assignProxyToProfiles()`、`saveProfileProxyAsAsset()` 以及部分测试覆盖。

已完成：

- `frontend/src/lib/api.ts`
  - 新增 `ProxyAsset`、`ProxyCreateData`、`ProxyUpdateData`。
  - 新增 `ProxyBulkCheckResult`、`ProxyBulkCheckResponse`。
  - 新增 `ProxyAssignResult`、`ProxyAssignResponse`。
  - 新增 `ProxyFromProfileCreateData`，不包含 `url`。
  - 新增 proxy CRUD client：`listProxies()`、`getProxy()`、`createProxy()`、`updateProxy()`、`deleteProxy()`。
  - 新增 `checkProxy()`、`bulkCheckProxies()`。
  - 新增 `assignProxyToProfiles()`。
  - 新增 `saveProfileProxyAsAsset()`。
- `frontend/src/lib/api.test.ts`
  - 覆盖 list / get / create / update / delete。
  - 覆盖 check / bulk check。
  - 覆盖 assign 请求体 `{profile_ids}`。
  - 覆盖从 profile 当前 proxy 保存为 asset 时不向后端提交 `url`。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 追加本小闭环记录。
  - 不勾选 Proxy Manager 页面、前端分配入口、搜索筛选、CSV 导入或模块完成。

验证：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts
# 1 failed, 2 failed | 18 passed
# 红灯：api.assignProxyToProfiles / api.saveProfileProxyAsAsset 当前不存在

cd frontend && npm test -- --run src/lib/api.test.ts
# 1 passed, 21 passed

cd frontend && npm test -- --run
# 11 passed, 127 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

仍未做：

- 前端 Proxy Manager 页面。
- 前端 Proxy Manager 分配入口。
- 搜索、筛选、按国家/provider/tag 过滤。
- CSV 粘贴导入。
- 真实 UI 批量检测交互。
- `profiles.proxy` 到 `proxy_id` 的数据模型迁移。

## 41. 2026-05-26 Proxy Manager 前端只读页面小闭环

背景：

- 继续 04 Proxy Manager，基于已完成的后端 proxy API 和前端 API client，新增运营台里可访问的 Proxy Manager 页面。
- 本轮只做只读资产列表，不做搜索、筛选、批量检测、CSV、分配 UI 或其它 mutation。
- 使用 `ui-ux-pro-max` 查询 B2B SaaS operations dashboard / data table 方向：采用 data-dense dashboard、浅色高对比、稳定 hover/focus、表格横向滚动隔离。
- 派发两个只读子 agent：
  - 一个审计 App 架构、view 状态、测试 mock 和移动端约束。
  - 一个审计 ProxyAsset 字段、URL 脱敏契约和只读 action 边界。

已完成：

- `frontend/src/components/ProxyManagerPage.tsx`
  - 内部调用 `api.listProxies()`。
  - 展示 Proxy Manager header、summary tiles、只读 proxy assets table。
  - 列表展示 name、credential-safe URL、location、provider、health、last check、tags。
  - 使用 `redactUrlCredentials()` 对 URL 和 error 文本做额外防护。
  - 空状态和错误状态均不触发 mutation；Refresh 只重新拉取列表。
- `frontend/src/components/ProxyManagerPage.test.tsx`
  - 新增只读列表、统计、脱敏、空状态、错误重试、横向滚动隔离测试。
  - 明确断言页面不出现 delete / assign action。
- `frontend/src/App.tsx`
  - 新增顶层 `ConsoleSection = "profiles" | "proxies"`。
  - 顶栏新增 `Profiles` / `Proxy Manager` section switch。
  - Proxy Manager section 隐藏 Profile 专用 sidebar、`New Profile`、Launch/Stop、Profile table 和 inspector。
- `frontend/src/App.test.tsx`
  - 新增 section 切换测试，确认进入 Proxy Manager 后不渲染 Profile table 和 `New Profile`，返回 Profiles 后恢复。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 勾选 `前端新增 Proxy Manager 页面`。
  - 追加本小闭环记录，并明确其它未完成范围。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 1 failed, no tests
# 红灯：ProxyManagerPage 文件不存在

cd frontend && npm test -- --run src/App.test.tsx
# 1 failed
# 红灯：没有 Proxy Manager section 入口

cd frontend && npm test -- --run src/App.test.tsx src/components/ProxyManagerPage.test.tsx
# 2 passed, 21 passed

cd frontend && npm test -- --run
# 12 passed, 132 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- 第一轮在 `http://127.0.0.1:5173/` 上用 fetch patch 验证代理列表渲染和移动端宽度。
- 第二轮启动隔离 QA 后端 `127.0.0.1:8093`，再用临时 Vite config 在 `http://127.0.0.1:5176/` 代理 `/api` 到该后端。
- QA 后端 seed：
  - 1 个 `Proxy Manager QA Profile`。
  - 2 个 proxy assets：`Credential Pool` 和 `Broken JP Pool`。
  - 两个 proxy URL 和其中一个 `last_check_error` 都包含凭据，用于验证 UI 不泄露密码。
- 桌面 `1440x900`：
  - 顶栏 `Proxy Manager` 可进入页面。
  - `Proxy assets table` 可见，渲染 2 行。
  - 文本包含脱敏后的 `http://proxy.example:8080` 和 `socks5://jp.proxy.example:1080`。
  - 页面文本不包含 `hiddenpass`、`topsecret`、`user:`、`secret:`。
  - `document.documentElement.scrollWidth === window.innerWidth === 1440`。
- 移动 `390x844`：
  - `Proxy Manager` 页面可见。
  - `Proxy assets table` 自身横向滚动，body 不横向撑破。
  - `document.documentElement.scrollWidth === window.innerWidth === 390`。
  - 页面文本不包含 `hiddenpass` 或 `topsecret`。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-proxy-manager-v1-screens/desktop-proxy-manager.png`
- `/tmp/cloakbrowser-proxy-manager-v1-screens/mobile-proxy-manager.png`
- `/tmp/cloakbrowser-proxy-manager-v1-screens/desktop-proxy-manager-real-api.png`
- `/tmp/cloakbrowser-proxy-manager-v1-screens/mobile-proxy-manager-real-api.png`

仍未做：

- 搜索、筛选、按国家/provider/tag 过滤。
- 单个检测 / 批量检测 UI。
- 新建 / 编辑 / 删除 proxy UI。
- 前端 Proxy Manager 分配入口。
- CSV 粘贴导入。
- `profiles.proxy` 到 `proxy_id` 的数据模型迁移。

## 42. 2026-05-26 Proxy Manager 搜索与筛选小闭环

背景：

- 继续 04 Proxy Manager，基于已完成的只读 Proxy Manager 页面补齐客户端搜索与国家/provider/tag 筛选。
- 本轮保持只读资产列表语义，不接线检测、批量检测、分配、新建、编辑、删除或 CSV 导入。
- 派发 1 个只读子 agent 审计当前 Proxy Manager 页面、测试和脱敏边界；主 agent 本地按 TDD 实现。

已完成：

- `frontend/src/components/ProxyManagerPage.tsx`
  - 新增 `Search proxy assets` 输入框。
  - 新增 `Country filter`、`Provider filter`、`Tag filter`。
  - 筛选选项从 `ProxyAsset` 本地数据派生、去重、排序，并忽略空值。
  - 筛选选项和匹配逻辑共用 trim 后值；`All` 使用内部 sentinel，避免真实值 `all` 冲突。
  - 筛选采用 AND 语义，表格渲染 `filteredProxies`。
  - 新增 `{visible} of {total} visible` 结果计数，原 summary tiles 保持全量库存口径。
  - 新增过滤空态 `No proxy assets match filters` 和 `Clear proxy filters`。
  - 使用 `useDeferredValue(searchQuery)` 优化快速输入时的搜索渲染。
  - 修复 `last_check_error` 和 notes 泄露 raw proxy 凭据问题，显示文本与 tooltip 都走 `redactUrlCredentials()`。
- `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖搜索命中脱敏 endpoint、provider、tag。
  - 覆盖 country/provider/tag 组合筛选 AND 语义。
  - 覆盖筛选选项去重、忽略空值、trim 后仍能筛中来源行。
  - 覆盖过滤空态和 clear filters 恢复列表。
  - 覆盖 URL、`last_check_error` 和 notes 中的 proxy 凭据不会出现在正文或任何 `title` 属性。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 勾选 `支持按国家、provider、tag 筛选`。
  - 追加本小闭环记录。
  - 顶层 `支持搜索、筛选、批量检测` 仍未勾选，因为批量检测 UI 未完成。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 红灯：3 failed, 4 passed，筛选控件不存在

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 1 passed, 7 passed

cd frontend && npm test -- --run
# 12 passed, 135 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8094/`，FastAPI 服务当前 `frontend/dist` 生产 build，数据库隔离在 `/tmp/cloakbrowser-proxy-manager-filters-data-8094/profiles.db`。
- QA seed 额外覆盖了带空格的 country/provider/tag，以及真实 provider/tag 值为 `all` 的情况，验证 trim 匹配和内部 sentinel 不冲突。
- 桌面 `1440x900`：
  - Proxy Manager 可进入，3 条 proxy asset 可见。
  - 搜索 `jp.proxy.example` 后 `1 of 3 visible`。
  - 组合筛选 `JP + ProxyJP + asia` 后 `1 of 3 visible`，带空格来源字段可正确匹配。
  - 搜索 `does-not-exist` 后出现过滤空态和 clear action。
  - 正文和 `[title]` 属性均不包含 `hiddenpass`、`topsecret`、`user:`、`secret:`。
  - body 未横向撑破：`document.documentElement.scrollWidth === window.innerWidth === 1440`。
- 移动 `390x844`：
  - 筛选栏与表格可用。
  - 搜索 `proxyco` 后 `1 of 3 visible`。
  - body 未横向撑破：`document.documentElement.scrollWidth === window.innerWidth === 390`。
  - 正文和 `[title]` 属性均无 proxy 凭据泄露。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-proxy-manager-filters-screens/desktop-filtered-search.png`
- `/tmp/cloakbrowser-proxy-manager-filters-screens/desktop-empty-state.png`
- `/tmp/cloakbrowser-proxy-manager-filters-screens/mobile-full-list.png`
- `/tmp/cloakbrowser-proxy-manager-filters-screens/mobile-filtered-search.png`

仍未做：

- Proxy Manager 单个检测 / 批量检测 UI。
- Proxy Manager 分配入口。
- 新建 / 编辑 / 删除 proxy UI。
- CSV 粘贴导入。
- `profiles.proxy` 到 `proxy_id` 的数据模型迁移。

## 43. 2026-05-26 Proxy Manager 批量检测 UI 小闭环

背景：

- 继续 04 Proxy Manager，在搜索与筛选完成后补齐 Proxy Manager 表格里的批量检测入口。
- 本轮只接线已选 proxy asset 的 `bulkCheckProxies()`，不做单个检测、新建、编辑、删除、分配到 profile 或 CSV 导入。

已完成：

- `frontend/src/components/ProxyManagerPage.tsx`
  - 新增选择列、单行选择、`Select all visible proxy assets` 和 `selected` 计数。
  - 新增 `Check selected`，调用 `api.bulkCheckProxies(selectedIds)`。
  - 用响应中的 `results[].proxy` 局部刷新对应行 health。
  - 成功时展示 `Bulk check complete: X succeeded, Y failed`。
  - 异常时展示脱敏后的 `Bulk check failed: ...`。
  - 保持 create/update/delete/assign/CSV 等高风险 action 不出现。
  - 表格仍限制在自身容器横向滚动，移动端 body 不被撑宽。
- `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖多选后批量检测并刷新 row health。
  - 覆盖 `Select all visible` 只选择当前筛选后的可见 proxy。
  - 覆盖批量检测失败提示不泄露 proxy 凭据。
  - 覆盖页面仍不出现 delete / assign action。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 勾选 `支持搜索、筛选、批量检测`。
  - 追加本小闭环记录。
  - 仍不勾选 04 模块完成状态，因为分配入口、CSV、新建/编辑/删除等仍未做。

验证记录：

```bash
cd frontend && npm test -- --run
# 12 passed, 138 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8094/`，隔离数据库 `/tmp/cloakbrowser-proxy-manager-bulk-check-data-8094`。
- 桌面 `1440x900`：
  - `Select all visible` 后 `Check selected` 可用。
  - 批量检测后展示 `Bulk check complete: 2 succeeded, 1 failed`。
  - 正文和 `[title]` 属性均不包含 `hiddenpass`、`topsecret`、`user:`、`secret:`。
  - `document.documentElement.scrollWidth === window.innerWidth === 1440`。
- 移动 `390x844`：
  - 批量检测交互可用。
  - 批量检测后展示 `Bulk check complete: 2 succeeded, 1 failed`。
  - `document.documentElement.scrollWidth === window.innerWidth === 390`。
  - 表格区域 `overflowX=auto`，正文和 `[title]` 属性均无 proxy 凭据泄露。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-proxy-manager-bulk-check-screens/desktop-bulk-check-results.png`
- `/tmp/cloakbrowser-proxy-manager-bulk-check-screens/mobile-bulk-check-results.png`

仍未做：

- Proxy Manager 单个检测 UI。
- Proxy Manager 分配入口。
- 新建 / 编辑 / 删除 proxy UI。
- CSV 粘贴导入。
- `profiles.proxy` 到 `proxy_id` 的数据模型迁移。

## 44. 2026-05-26 Proxy Manager 前端分配入口小闭环

背景：

- 继续 04 Proxy Manager，在批量检测 UI 后补齐“将 proxy asset 分配到 profiles”的运营入口。
- 本轮只做 assignment UI 与 profile refresh 闭环，不做单个检测 UI、新建/编辑/删除 proxy UI、CSV 导入或数据模型迁移。
- 派发 1 个只读子 agent 核对文档 checkbox 与验收缺口；主 agent 本地用 TDD 修复两个 review 风险点。

已完成：

- `frontend/src/App.tsx`
  - 向 `ProxyManagerPage` 传入 `profiles` 和 `refresh`。
- `frontend/src/components/ProxyManagerPage.tsx`
  - 新增 `Assign to profiles` 操作，只有恰好选择一个 proxy asset 且存在 profiles 时可用。
  - 新增分配 dialog，支持 profile 搜索、单行勾选、`Select visible`。
  - 提交调用 `api.assignProxyToProfiles(selectedProxy.id, profileIds)`，成功后关闭 dialog、清理选择并刷新 Profile 数据。
  - assignment 已成功但 refresh 失败时，保留成功提示并追加 refresh 失败信息，不误报为 `Assign failed`。
  - assignment dialog 中 proxy URL、profile 当前 proxy、错误提示和 tooltip title 均保持 credential-safe。
- `frontend/src/lib/profileDisplay.ts`
  - `redactUrlCredentials()` 增加旧格式 `host:port:user:pass` 遮蔽，避免历史 profile proxy 在 assignment dialog 中泄露凭据。
- `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖 assignment 单选启用、profile 勾选分配、搜索后 select visible、assignment 错误脱敏。
  - 新增红绿回归：旧格式 proxy 凭据遮蔽。
  - 新增红绿回归：assignment 成功但 refresh 失败时不误报为 assign failure。
- `frontend/src/App.test.tsx`
  - 覆盖 App 将 profiles 与 refresh callback 传给 Proxy Manager。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 勾选 `支持将 proxy 分配到 profile` 和 `前端 Proxy Manager 分配入口`。
  - 追加本小闭环记录。
  - 未勾选 CSV，也未更新 `tasks/progress.md` 的 04 完成状态。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 红灯：2 failed, 14 passed

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 1 passed, 16 passed

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx src/App.test.tsx
# 2 passed, 34 passed

cd frontend && npm test -- --run
# 12 passed, 145 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8095/`，当前 `frontend/dist` 生产 build + `/tmp/cloakbrowser-user-test-8095/profiles.db` 隔离数据。
- 桌面 `1440x900`：
  - Proxy Manager -> 选择 `Credential Pool` -> 打开 `Assign to profiles`。
  - 搜索 `gamma`，`Select visible` 后分配成功。
  - dialog 中旧格式 proxy 只显示 `legacy.proxy.example:8080`。
  - 成功后展示 `Assigned proxy to 1 profile(s), 0 failed`，dialog 关闭。
  - API 验证 `Gamma Search Target.proxy` 已写入 raw proxy。
  - 页面正文和 `[title]` 属性无 proxy 凭据泄露；body 未横向撑破。
- 移动 `390x844`：
  - 搜索 `beta`，`Select visible` 后分配成功。
  - 成功后展示 `Assigned proxy to 1 profile(s), 0 failed`，dialog 关闭。
  - API 验证 `Beta Running Candidate.proxy` 已写入 raw proxy。
  - `document.documentElement.scrollWidth === window.innerWidth === 390`。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/desktop-proxy-manager-before-assign.png`
- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/desktop-assign-dialog-search.png`
- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/desktop-assign-success.png`
- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/mobile-assign-dialog-search.png`
- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/mobile-assign-success.png`

仍未做：

- Proxy Manager 单个检测 UI。
- 新建 / 编辑 / 删除 proxy UI。
- CSV 粘贴导入。
- `profiles.proxy` 到 `proxy_id` 的数据模型迁移。

## 45. 2026-05-26 Profile 运营台 All profiles 返回列表 bugfix

背景：

- 用户反馈：打开某个 profile 进入 edit/detail 页面后，点击左侧导航栏 `All profiles` 不会回到 All profiles 列表页。
- 根因：左侧 Saved views 只更新 `filters`，没有清空 `selectedId` 或把 `view` 从 `edit/view` 切回 `empty`；主表格只在 `section === "profiles" && view === "empty"` 时渲染。
- 派发 1 个只读子 agent 定位状态机和测试切入点；主 agent 本地按 TDD 修复。

已完成：

- `frontend/src/App.tsx`
  - 新增 `handleSidebarFiltersChange(nextFilters)`。
  - 左侧 `ProfileList onFiltersChange` 改为该 handler。
  - 点击左侧 Saved views 时同步设置 `section=profiles`、更新 filters、清空 `selectedId`、设置 `view=empty`。
  - 主区 toolbar 的 `ProfileFilters onChange={setFilters}` 保持不变。
- `frontend/src/App.test.tsx`
  - 新增回归测试：从主表格打开 `Alpha Good` 进入 `Edit Profile`，点击左侧 `All profiles` 后回到主表格，并确认筛选回到 `all`。
- `docs/ai-docs/v1/tasks/03-profile-operations-console.md`
  - 追加本 bugfix 小闭环记录；03 模块完成状态不变。

验证记录：

```bash
cd frontend && npm test -- --run src/App.test.tsx
# 红灯：1 failed, 18 passed

cd frontend && npm test -- --run src/App.test.tsx
# 1 passed, 19 passed

cd frontend && npm test -- --run
# 12 passed, 146 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8095/`，当前 `frontend/dist` 生产 build。
- 桌面 `1440x900`：
  - 初始主表格可见。
  - 点击 `Open Alpha Warmup` 进入 `Edit Profile`。
  - 点击左侧 `All profiles` 后回到 `Profile operations` 主表格，`Edit Profile` 消失。
  - JS 验证：`hasTable=true`、`hasEditHeading=false`、`allProfilesPressed="true"`、body 未横向撑破。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-all-profiles-nav-bugfix-screens/desktop-before-open.png`
- `/tmp/cloakbrowser-all-profiles-nav-bugfix-screens/desktop-edit-profile.png`
- `/tmp/cloakbrowser-all-profiles-nav-bugfix-screens/desktop-after-all-profiles.png`

## 46. 2026-05-26 Proxy Manager CSV 粘贴导入与交互动效小闭环

背景：

- 继续 04 Proxy Manager；CSV 粘贴导入第一版是当前模块最后一个未勾选项。
- Jeff 反馈当前页面整体风格可接受，但局部交互反馈偏生硬，需要加快推进并补交互动效。
- 派发两个只读子 agent：
  - `Volta` 审计 CSV 第一版字段、API 边界、测试与 checkbox 更新口径。
  - `Arendt` 审计当前 Proxy Manager UI/API/test 缺口和最值得补的动效反馈点。

子 agent 结论：

- CSV 第一版不新增后端 bulk import API，前端解析/预览后复用 `api.createProxy()` 逐条创建。
- 必填字段为 `name`、`url`；可选字段为 `country_code`、`city`、`asn`、`provider`、`tags`、`notes`。
- 不导入 `last_check_*`，不自动检测，不自动分配 profile，不做 update/upsert/delete。
- 动效优先补 dialog、notice、按钮 loading/active、choice 控件和导入新增行高亮，不大改表格和筛选。

已完成：

- `frontend/src/components/ProxyManagerPage.tsx`
  - 新增 `Import CSV` action。
  - 新增 `Import proxy CSV` dialog。
  - 支持粘贴 CSV、预览行、统计 `ready / blocked`、标记 `Missing name` / `Missing url`。
  - 有效行顺序调用 `api.createProxy()`；无效行不提交。
  - 部分失败继续执行，失败原因在 dialog 中保留并通过 `redactUrlCredentials()` 脱敏。
  - 成功后刷新 proxy 列表，并对新增行做短暂高亮。
- `frontend/src/styles/globals.css`
  - 新增 dialog / notice / proxy row enter keyframes。
  - 按钮、choice card、checkbox 增加克制的 hover / active / transform 反馈。
  - 保留 `prefers-reduced-motion` 降级。
- `frontend/src/components/ProxyManagerPage.test.tsx`
  - 新增 CSV 导入红绿测试：入口、预览、有效行提交、无效行跳过、刷新列表、部分失败、错误脱敏。
- `docs/ai-docs/v1/tasks/04-proxy-manager.md`
  - 勾选 `支持 CSV 粘贴导入第一版`。
  - 追加本小闭环记录。
- `docs/ai-docs/v1/tasks/progress.md`
  - 将 `04 Proxy Manager` 更新为完成。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 红灯：2 failed, 16 passed

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 1 passed, 18 passed

cd frontend && npm test -- --run
# 12 passed, 148 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8095/`。
- 桌面 `1440x900`：
  - Proxy Manager -> `Import CSV` -> 粘贴 1 条有效、1 条缺 URL。
  - 预览显示 `1 ready`、`1 blocked`、`Missing url`。
  - 导入后列表出现 `CSV Desktop Good`，提示 `Imported 1 proxy asset(s), 1 failed`。
- 移动 `390x844`：
  - 粘贴 1 条有效 CSV 并导入成功。
  - JS 验证：`hasMobileRow=true`、`hasNotice=true`、`scrollWidth=390`、`width=390`、正文和 `[title]` 无 `mobilepass` / `mobile-user:`。
- `agent-browser console --clear` 无相关前端错误；`agent-browser errors --clear` 无输出。

截图：

- `/tmp/cloakbrowser-proxy-manager-csv-import-screens/desktop-csv-import-success.png`
- `/tmp/cloakbrowser-proxy-manager-csv-import-screens/mobile-csv-import-preview.png`
- `/tmp/cloakbrowser-proxy-manager-csv-import-screens/mobile-csv-import-success.png`

边界：

- 没有新增后端 bulk import API。
- 没有修改 Project Mileage 仓库或业务逻辑。
- 没有引入 Chromium CDP 作为产品基础能力。
- 没有 push 到任何远端仓库。

## 47. 2026-05-26 ProfileForm 删除确认 Dialog 小闭环

背景：

- 04 Proxy Manager 已完成；`05 Project Mileage 会话 Broker` 文档要求实现前先确认 Project Mileage Contract Change Proposal 或任务级契约，因此本轮不越界进入跨仓会话 Broker。
- 按 CloakBrowser 独立成熟化继续推进 11 UI 视觉系统，优先处理一个低风险且高体感的问题：ProfileForm 删除还在使用浏览器原生 `confirm()`。
- 派发只读子 agent `Mencius` 审计当前删除流、最小替代方案、测试与 11 文档 checkbox。

子 agent 结论：

- 原生 confirm 位于 `frontend/src/components/ProfileForm.tsx` 的 `handleDelete()`。
- App 层删除事实流不需要改：`onDelete={handleDelete}` 仍由 App 执行删除、清空选中并回到主表。
- 最小方案是新增项目内 `ConfirmDialog`，ProfileForm 用本地 `deleteConfirmOpen` 控制弹层。
- 完成后可勾选 11 文档的 `用项目内 ConfirmDialog 替代原生 confirm`。

已完成：

- `frontend/src/components/ConfirmDialog.tsx`
  - 新增项目内确认弹层。
  - 支持 danger tone、subject、loading、Escape 关闭。
  - 使用现有 dialog 动效，保留 `role="dialog"` 和 `aria-modal="true"`。
- `frontend/src/components/ProfileForm.tsx`
  - 删除按钮改为打开 `Delete profile` dialog。
  - Cancel / Escape 只关闭 dialog，不调用删除。
  - Confirm 后才调用既有 `onDelete()`，删除完成后关闭 dialog。
  - 创建模式和未传 `onDelete` 的语义不变。
- `frontend/src/components/ProfileForm.test.tsx`
  - 新增红绿测试：点击 Delete 不再调用 `window.confirm`，Cancel 不删除，Confirm 才删除。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md`
  - 勾选 `用项目内 ConfirmDialog 替代原生 confirm`。
  - 追加本小闭环记录。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProfileForm.test.tsx
# 红灯：1 failed, 6 passed

cd frontend && npm test -- --run src/components/ProfileForm.test.tsx
# 1 passed, 7 passed

cd frontend && npm test -- --run
# 12 passed, 149 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8095/`。
- 桌面 `1440x900`：
  - `Alpha Warmup` 编辑页点击 Delete 后出现 app 内 `Delete profile` dialog。
  - `Cancel delete` 后 dialog 关闭，仍停留在编辑页。
  - 临时 QA profile `Confirm Dialog QA Delete` 走确认删除路径，删除后返回主表，API 验证临时 profile 已删除。
- 移动 `390x844`：
  - `Beta Running Candidate` 编辑页点击 Delete 后 dialog 可见。
  - JS 验证：`hasDialog=true`、`hasBeta=true`、`scrollWidth=384`、`width=390`。
  - Escape 关闭后 API 验证 `Beta Running Candidate` 仍存在。

截图：

- `/tmp/cloakbrowser-confirm-dialog-screens/desktop-delete-dialog.png`
- `/tmp/cloakbrowser-confirm-dialog-screens/mobile-delete-dialog.png`

边界：

- 没有修改后端。
- 没有改 App 删除事实源。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 52. 2026-05-26 Profile 批量 health inline feedback 小闭环

背景：

- 继续推进 `11 UI 视觉系统与体验升级` 的 `新增 toast 或 inline feedback`。
- 子 agent `Bernoulli` 只读审计确认：当前已有错误 banner 和 `Checking...` loading，但批量 `Check health` 成功后缺少完成反馈；最小范围应做 toolbar 内联反馈，不引入全局 toast 系统。
- 本轮不改后端 API，不解锁高风险批量动作，不引入新依赖。

已完成：

- `frontend/src/hooks/useProfiles.ts`
  - `checkHealth(ids)` 返回 `{ requestedCount, checkedCount, failedCount }`。
  - 保留成功更新 health cache、失败写入 `operationError` 的既有语义。
- `frontend/src/App.tsx`
  - 新增 Profile operations 本地 `bulkFeedback` 状态。
  - 开始 `Check health` 时清空旧 feedback。
  - 全成功显示 success inline feedback：`Health checked for N profiles.`。
  - 部分失败显示 warning inline feedback：`Health check finished: X checked, Y failed.`。
  - selection / filters / section 变化时清空旧 feedback，避免陈旧提示。
- `frontend/src/components/ProfileTable.tsx`
  - 透传 `bulkFeedback` 到 `BulkActionBar`。
- `frontend/src/components/BulkActionBar.tsx`
  - `Check health` 按钮旁新增紧凑 inline feedback pill。
  - success 使用 `role="status"`，warning 使用 `role="alert"`，统一 `aria-label="Profile operation feedback"`。
  - 保持 toolbar `h-11`，不改变 sticky 表头 offset。
- 测试覆盖：
  - `useProfiles.test.ts` 覆盖 bulk health result 返回值。
  - `ProfileTable.test.tsx` 覆盖 success / warning inline feedback。
  - `App.test.tsx` 覆盖真实点击 `Check health` 后 success / warning feedback。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md`
  - 勾选 `新增 toast 或 inline feedback`。
  - 追加本小闭环验证证据。

验证记录：

```bash
cd frontend && npm test -- --run src/App.test.tsx
# 红灯：2 failed, 20 passed
# 失败点：完成 bulk health 后没有 Profile operation feedback

cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileTable.test.tsx src/hooks/useProfiles.test.ts
# 3 passed, 83 passed

cd frontend && npm test -- --run
# 13 passed, 163 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- QA 地址：`http://127.0.0.1:8095/`，生产 build 来自 `frontend/dist`。
- 桌面 `1440x960`：
  - 选中 profile 后点击 `Check health`。
  - JS 验证：`feedback="Health checked for 4 profiles."`、`role="status"`、`bulkToolbar=true`、`bodyOverflow=false`、`width=1440`、`scrollWidth=1440`。
- 移动 `390x844`：
  - 选中 1 个 card 后点击 `Check health`。
  - JS 验证：`feedback="Health checked for 1 profile."`、`role="status"`、`bulkToolbar=true`、`bodyOverflow=false`、`width=390`、`scrollWidth=390`。

截图：

- `/tmp/cloakbrowser-inline-feedback-screens/desktop-profile-bulk-health-inline-feedback.png`
- `/tmp/cloakbrowser-inline-feedback-screens/mobile-profile-bulk-health-inline-feedback.png`

边界：

- 没有修改后端、runtime 或 Docker。
- 没有引入全局 toast provider。
- 没有解锁 Launch / Stop / Tag / Delete 批量高风险动作。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 50. 2026-05-26 Profile 运营台动效反馈 polish 小闭环

背景：

- Jeff 反馈当前页面整体风格已接近 SS，但部分交互没有动效，反馈生硬。
- 本轮继续推进 `11 UI 视觉系统与体验升级`，只处理 Profile 运营台高频交互的非布局型 motion，不改变业务语义、筛选、排序、批量动作、API 或虚拟滚动高度。

已完成：

- `frontend/src/styles/globals.css`
  - 新增 `animate-profile-preview` 和 `animate-inspector-in`。
  - 继续受全局 `prefers-reduced-motion: reduce` 降级。
- `frontend/src/components/ProfileTable.tsx`
  - previewed desktop row 增加 `animate-profile-preview`。
  - previewed mobile card 增加 `animate-profile-preview`。
  - 未使用 translate/scale 改变 table row/card 空间占用，保留固定高度虚拟滚动语义。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - profile inspector 内容包裹层增加 `animate-inspector-in`。
  - 不 key 整个 aside，保留 `role="complementary"` 语义。
- `frontend/src/components/ProfileList.tsx`
  - quick view button 增加 hover/active/focus 的 transform-aware transition。
  - selected shortcut 增加 `animate-profile-selection` 和左侧状态线。
  - 未对虚拟列表 item 使用 hover translate 或 margin 变化。
- 相关测试覆盖：
  - preview row/card motion class。
  - inspector content motion class。
  - active quick view 与 selected shortcut motion class。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md` 追加本小闭环验证证据。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileList.test.tsx
# 红灯：4 failed, 41 passed
# 失败点：preview row/card、inspector content、quick view/selected shortcut 尚无 motion class

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileList.test.tsx
# 3 passed, 45 passed

cd frontend && npm test -- --run
# 13 passed, 158 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 使用 `agent-browser`，QA 地址 `http://127.0.0.1:8095/`。
- 桌面 `1440x960`：
  - 点击 `Preview Beta Running Candidate` 后 JS 验证：`previewed=previewed`、`previewMotion=true`、`inspectorMotion=true`、`quickMotion=true`、`bodyOverflow=false`。
- 移动 `390x844`：
  - 点击移动 card 的 `Preview Beta Running Candidate` 后 JS 复验：`previewed=previewed`、`previewMotion=true`。
  - JS 验证：`bodyOverflow=false`、`width=390`、`scrollWidth=390`。

截图：

- `/tmp/cloakbrowser-motion-polish-screens/desktop-profile-motion-polish.png`
- `/tmp/cloakbrowser-motion-polish-screens/mobile-profile-motion-polish.png`

边界：

- 没有修改后端、Docker 或 runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 49. 2026-05-26 Profile 运营台 Badge 系统小闭环

背景：

- 继续推进 `11 UI 视觉系统与体验升级` 的第一个未完成任务：`health/runtime/proxy/country/tag` badge 系统。
- Jeff 反馈当前界面风格基本符合 SS 方向，但部分交互反馈仍生硬；本轮先把已进入 RED 状态的 badge 语义闭环收住，后续继续推进动效 polish。
- 本轮不改后端、runtime、筛选、排序、批量动作或虚拟滚动高度语义。

子 agent：

- `Hume` 只读调查 `Edit Profile -> All profiles` 不切回列表问题，确认当前源码已有 `handleSidebarFiltersChange()` 修复；本轮通过浏览器在当前 build 复验。
- `Halley` 只读审计下一轮 motion polish，建议优先处理 preview 行反馈、Inspector 切换、左侧 rail active/press、bulk confirm、移动侧栏进入反馈。

已完成：

- 新增 `frontend/src/components/Badge.tsx`：
  - `Badge` primitive，提供 `data-badge-type`。
  - `BadgeDot`、`TagBadge`、`CountryBadge`、`ProxyBadge`。
  - tag 保留自定义颜色。
- 新增 `frontend/src/components/Badge.test.tsx`。
- `HealthBadge` 改为 `Badge type="health"`，保留中文 label、aria-label、warning summary 和 compact 模式。
- `StatusIndicator` 复用 `BadgeDot`，running 继续保留 pulse。
- `ProfileTable` 接入 runtime / country / tag badge，保留桌面固定列宽、移动 card、高风险批量动作 disabled 和固定行高虚拟滚动。
- `ProfileList` 接入 proxy / country / tag badge，保留左侧 rail 搜索/筛选/虚拟滚动。
- `ProfileSummaryPanel` 接入 runtime / country / override tag badge，保留 inspector region、Open profile 和 proxy 脱敏展示。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md` 勾选 `新增 badge 系统`，追加验证证据。

验证记录：

```bash
cd frontend && npm test -- --run src/components/Badge.test.tsx src/components/HealthBadge.test.tsx src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileList.test.tsx
# 红灯：1 failed, 51 passed
# 失败点：BadgeDot pulse 测试仍断言内层 dot class 包含 animate-ping，和实际外层 pulse ring 结构不一致

cd frontend && npm test -- --run src/components/Badge.test.tsx src/components/HealthBadge.test.tsx src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileList.test.tsx
# 5 passed, 52 passed

cd frontend && npm test -- --run
# 13 passed, 157 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 使用 `agent-browser`，首次启动遇到 Chrome sandbox 限制，按提示改用 `--args "--no-sandbox"`。
- QA 地址：`http://127.0.0.1:8095/`，继续由 `/tmp/cloakbrowser_user_test_8095.py` 服务 `frontend/dist`。
- 桌面 `1440x960`：
  - JS 验证：`health=10`、`proxy=3`、`runtime=5`、`tag=10`，`bodyOverflow=false`，`tableOverflow=true`。
  - `Open Alpha Warmup` 进入 `Edit Profile` 后点击左侧 `All profiles`，JS 验证：`hasEdit=false`、`hasTable=true`、`activeAllProfiles=true`。
- 移动 `390x844`：
  - JS 验证：`health=10`、`proxy=3`、`runtime=5`、`tag=10`，`bodyOverflow=false`，`tableOverflow=false`。

截图：

- `/tmp/cloakbrowser-badge-system-screens/desktop-badge-system.png`
- `/tmp/cloakbrowser-badge-system-screens/desktop-all-profiles-after-edit.png`
- `/tmp/cloakbrowser-badge-system-screens/mobile-badge-system.png`

边界：

- 没有修改后端或 Docker/runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 49. 2026-05-26 Profile 运营台选中与批量操作微反馈小闭环

背景：

- Jeff 反馈当前 UI 美观度已经接近 SS 风格，但部分交互反馈仍生硬，需要继续加快做 UI/UE polish。
- 上一轮 Viewer EnvironmentStrip 已提交为 `4ac9481 polish viewer environment strip`。
- 本轮沿着子 agent `Boyle` 的候选建议，优先处理 Profile 运营台最高频的表格/卡片选择、bulk action bar 出现、批量 Check health 忙碌反馈。
- 本轮不改变虚拟滚动、不改变批量 health check 事实流、不解锁 Launch / Stop / Tag / Delete 等高风险批量动作。

已完成：

- `frontend/src/components/ProfileTable.tsx`
  - selected desktop row 增加 `animate-profile-selection`。
  - selected mobile card 增加 `animate-profile-selection`。
  - 保留 `data-state=selected` / `data-state=previewed` 优先级。
  - 保留 `PROFILE_TABLE_ROW_HEIGHT=64` 与 `PROFILE_CARD_ROW_HEIGHT=188` 固定行高语义。
- `frontend/src/components/BulkActionBar.tsx`
  - bulk action bar 根节点增加 `animate-bulk-action-in`。
  - `Check health` 忙碌态下 `HeartPulse` 图标增加 pulse 反馈。
  - 保留 `aria-busy`、disabled、高风险动作 disabled。
- `frontend/src/styles/globals.css`
  - 新增 `animate-profile-selection` 与 `animate-bulk-action-in` utilities。
  - 新增 `cloak-profile-selection` 与 `cloak-bulk-action-in` keyframes。
  - 继续由全局 `prefers-reduced-motion: reduce` 降级动画。
- `frontend/src/components/ProfileTable.test.tsx`
  - 新增 selected row/card 动效类断言。
  - 新增 bulk action bar 入场动效类断言。
  - 新增 `Checking health` 下 icon pulse 断言。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md`
  - 追加本小闭环记录和验证证据。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 红灯：4 failed, 30 passed

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx
# 1 passed, 34 passed

cd frontend && npm test -- --run
# 12 passed, 151 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8095/`。
- 桌面 `1440x900`：
  - 选择 `Alpha Warmup` 后出现 bulk action bar。
  - JS 验证：`selectedRowMotion=true`、`bulkMotion=true`、`actionsVisible=true`、`scrollWidth=1440`、`innerWidth=1440`。
  - 点击 `Check health` 后 JS 验证：`checkingVisible=true`、`ariaLabel=Checking health`、`iconPulse=true`、`toolbarBusy=true`。
- 移动 `390x844`：
  - 选择 `Alpha Warmup` card 后 bulk action bar 可见。
  - JS 验证：`selectedCardMotion=true`、`bulkMotion=true`、`scrollWidth=390`、`innerWidth=390`、`overflow=false`。
- `agent-browser console` 无输出；`agent-browser errors` 无输出。

截图：

- `/tmp/cloakbrowser-profile-motion-screens/desktop-selected-bulkbar.png`
- `/tmp/cloakbrowser-profile-motion-screens/desktop-health-checking.png`
- `/tmp/cloakbrowser-profile-motion-screens/mobile-card-selected-bulkbar.png`

边界：

- 没有修改后端或 runtime。
- 没有改变批量 health check API 调用。
- 没有解锁高风险批量操作。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 50. 2026-05-26 App shell loading 与 section 切换反馈小闭环

背景：

- Jeff 反馈页面已有 SS 风格，但交互反馈仍偏生硬。
- 上一轮 Profile 运营台选中与批量操作微反馈已提交为 `33dcb7d add profile operations motion feedback`。
- 本轮只处理 App shell loading skeleton 与 Profiles / Proxy Manager section 切换反馈，不改 API、hooks、Proxy Manager 内部加载逻辑或后端服务。

子 agent：

- `Hilbert` 只读审计 App shell 中切换/加载反馈位置。
- 建议用 `role=status`、`aria-label="Loading operations console"`、`data-console-section` 和 `animate-console-section-in` 做最小 TDD 小闭环。
- 提醒 class 断言不要过脆，因此测试保留语义断言为主，class 断言只覆盖关键反馈类。

已完成：

- `frontend/src/App.tsx`
  - 新增本地 `LoadingShell`。
  - 替换 auth checking 与 profiles loading 两处纯文本 `Loading...`。
  - loading shell 使用 `role="status"`、`aria-label="Loading operations console"`、3 条 skeleton row。
  - Profiles / Proxy Manager segmented control 增加 `transition-[background-color,color,box-shadow,transform]`、`active:translate-y-px`、`focus-visible`。
  - profiles / proxies 内容区增加 `data-console-section` 与 `animate-console-section-in`。
- `frontend/src/styles/globals.css`
  - 新增 `animate-app-skeleton` 与 `animate-console-section-in`。
  - 新增 `cloak-skeleton-pulse` 与 `cloak-console-section-in` keyframes。
  - 继续受全局 `prefers-reduced-motion: reduce` 降级。
- `frontend/src/App.test.tsx`
  - 新增 auth checking loading skeleton 测试。
  - 新增 profiles loading skeleton 测试。
  - 在 section 切换测试中覆盖 segmented control 和 content wrapper 反馈类。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md`
  - 追加本小闭环记录和验证证据。

验证记录：

```bash
cd frontend && npm test -- --run src/App.test.tsx
# 红灯：3 failed, 18 passed

cd frontend && npm test -- --run src/App.test.tsx
# 1 passed, 21 passed

cd frontend && npm test -- --run
# 12 passed, 153 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8095/`。
- 桌面 `1440x900`：
  - Profiles 视图 JS 验证：`profileSectionMotion=true`、`scrollWidth=1440`、`innerWidth=1440`。
  - 切到 Proxy Manager 后 JS 验证：`proxySectionMotion=true`、`hasProxyRegion=true`、`scrollWidth=1440`、`innerWidth=1440`。
- 移动 `390x844`：
  - Profiles 视图 JS 验证：`profileSectionMotion=true`、`scrollWidth=390`、`innerWidth=390`、`overflow=false`。
- `agent-browser console` 无输出；`agent-browser errors` 无输出。

截图：

- `/tmp/cloakbrowser-profile-motion-screens/desktop-profiles-section-motion.png`
- `/tmp/cloakbrowser-profile-motion-screens/desktop-proxy-section-motion.png`
- `/tmp/cloakbrowser-profile-motion-screens/mobile-profiles-section-motion.png`

边界：

- 没有修改后端或 runtime。
- 没有修改 Proxy Manager API 或内部加载状态机。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 48. 2026-05-26 Viewer 顶部 EnvironmentStrip 视觉升级小闭环

背景：

- Jeff 反馈当前页面整体风格已接近 SS，但部分交互反馈生硬，需要继续做 UI/UE 质感和动效 polish，同时加快推进。
- 04 Proxy Manager 已完成；05 Project Mileage 会话 Broker 仍要求契约确认，因此继续推进 11 UI 视觉系统。
- 本轮只处理 Viewer 顶部环境条，不改 VNC、Automation REST API、clipboard sync 或后端 runtime 事实流。

子 agent：

- `Faraday` 只读审计 Viewer strip 改动，指出短 ID 易混淆、窄屏换行挤压 VNC、fullscreen 只覆盖 canvas 导致工具条消失。
- `Boyle` 只读寻找下一轮动效 polish 候选，建议优先处理 ProfileTable 选中反馈、BulkActionBar 出现/忙碌反馈、ProfileFilters active/focus、loading skeleton、section segmented control active 过渡。

已完成：

- `frontend/src/components/ProfileViewer.tsx`
  - 顶部 toolbar 升级为 `Viewer environment` region。
  - 增加 connection、profile handle、Automation、Clipboard 状态 pill。
  - 右侧动作为 `Viewer actions` toolbar，icon button 增加 hover、active、focus-visible、disabled 和 copied 状态反馈。
  - profile handle 改为首尾短 ID，并保留完整 `title`。
  - 顶条改为单行 compact strip，左侧状态横向滚动，右侧动作不换行。
  - Fullscreen target 改为外层 viewer frame，fullscreen 下保留环境条和退出入口。
- `frontend/src/components/ProfileViewer.test.tsx`
  - 新增 EnvironmentStrip 状态与 action 可访问性测试。
  - 新增窄宽度 compact 行为和 fullscreen target 回归测试。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md`
  - 勾选 `Viewer 顶部 EnvironmentStrip 视觉升级`。
  - 勾选浏览器检查 `Viewer 工具条不遮挡 VNC`。
  - 追加本小闭环验证记录。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProfileViewer.test.tsx
# 红灯：2 failed, 4 passed

cd frontend && npm test -- --run src/components/ProfileViewer.test.tsx
# 1 passed, 6 passed

cd frontend && npm test -- --run
# 12 passed, 151 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:5177/`。
- 临时 harness 位于 `/tmp/cloak-viewer-strip-qa`，渲染真实 `ProfileViewer`，noVNC RFB mock 只触发 connect；视觉 CSS 使用本轮生产 build CSS。
- 桌面 `1440x900` JS 验证：`hasConnected=true`、`hasAutomation=true`、`hasClipboard=true`、`scrollWidth=1440`、`innerWidth=1440`、`stripHeight=45`、`toolbar=true`。
- 移动 `390x844` JS 验证：`hasConnected=true`、`hasAutomation=true`、`hasClipboard=true`、`scrollWidth=390`、`innerWidth=390`、`stripHeight=45`、`overflow=false`、`toolbar=true`。
- 新浏览器会话 `agent-browser errors` 无输出；console 只有 Vite/React dev 信息和现有 clipboard debug log。

截图：

- `/tmp/cloakbrowser-viewer-strip-screens/desktop-viewer-environment-strip.png`
- `/tmp/cloakbrowser-viewer-strip-screens/mobile-viewer-environment-strip.png`

边界：

- 没有修改后端或 runtime。
- 没有改变 VNC websocket、clipboard bridge、Automation REST API 契约。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 51. 2026-05-26 ProfileList 左侧 rail empty state 小闭环

背景：

- 继续推进 `11 UI 视觉系统与体验升级` 的 `新增 empty state 样式`。
- 子 agent `Euclid` 只读审计确认：`ProfileTable`、`ProfileSummaryPanel`、`ProxyManagerPage` 空态已基本够用，最小高收益范围是 `ProfileList` 左侧 rail。
- 本轮不改 profile 数据、筛选算法、虚拟滚动、主表空态或后端 API。

已完成：

- `frontend/src/components/ProfileList.tsx`
  - 新增本地 `ProfileListEmptyState`。
  - first-run 状态从纯文本升级为 `role="status"` 的 dashed panel，提供 `Create profile` 动作并调用 `onNew`。
  - filtered-empty 状态提供 `No matching profile shortcuts` status 和 `Clear filters` 动作，调用 `setFilters(defaultProfileFilters)`。
  - 样式尺寸控制在左侧 264px rail 内，不影响虚拟列表 item 高度。
- `frontend/src/components/ProfileList.test.tsx`
  - 覆盖 first-run rail empty state 和创建动作。
  - 覆盖 filtered rail empty state 和清空筛选动作。
- `frontend/src/App.test.tsx`
  - 集成测试改为按区域区分左侧 rail 空态和主表空态，避免同名 status / button 的全局查询歧义。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md`
  - 勾选 `新增 empty state 样式`。
  - 追加本小闭环验证证据。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProfileList.test.tsx
# 红灯：2 failed, 9 passed
# 失败点：ProfileList 仍是纯文本 No profiles yet / No matches

cd frontend && npm test -- --run src/components/ProfileList.test.tsx
# 1 passed, 11 passed

cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileTable.test.tsx src/components/ProxyManagerPage.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileList.test.tsx
# 红灯：App 集成测试因 rail 和主表同名空态/按钮出现全局查询歧义

cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileTable.test.tsx src/components/ProxyManagerPage.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileList.test.tsx
# 5 passed, 86 passed

cd frontend && npm test -- --run
# 13 passed, 160 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- QA 地址：`http://127.0.0.1:8095/`，生产 build 来自 `frontend/dist`。
- 当前真实服务有 4 个 profile；未清空真实数据。
- 桌面 `1440x960`：
  - 输入不存在搜索词后 JS 验证：`railEmpty=true`、`tableEmpty=true`、`clearButtons=2`、`bodyOverflow=false`、`width=1440`、`scrollWidth=1440`。
- 移动 `390x844`：
  - 保持不存在搜索词后 JS 验证：`railEmpty=true`、`tableEmpty=true`、`bodyOverflow=false`、`width=390`、`scrollWidth=390`。

截图：

- `/tmp/cloakbrowser-empty-state-screens/desktop-filtered-empty-state.png`
- `/tmp/cloakbrowser-empty-state-screens/mobile-filtered-empty-state.png`

边界：

- 没有修改后端、runtime 或 Docker。
- 没有删除或清空真实 profile 数据。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 52. 2026-05-26 ProfileForm 分组页签与 All profiles 导航回归小闭环

背景：

- Jeff 反馈：在某个 profile 的 Edit Profile 页面点击左侧 `All profiles` 后应回到 All Profiles 列表页。
- 当前分支已有 `handleSidebarFiltersChange` 修复 stopped edit 分支，本轮补充 running profile / VNC viewer 分支回归测试，并在 8095 浏览器实测。
- 继续推进 `11 UI 视觉系统与体验升级` 的 ProfileForm 分组页签。

已完成：

- `frontend/src/App.test.tsx`
  - 新增从 VNC viewer 点击侧栏 `All profiles` 回到主表的回归测试。
  - 创建/编辑集成测试按新 ProfileForm 页签路径填写 `Network` 和 `Advanced` 字段。
- `frontend/src/components/ProfileForm.tsx`
  - 表单改为 `Identity` / `Network` / `Device` / `Behavior` / `Advanced` 页签。
  - `form` state 和 `onSave(form)` 保持不变，跨页签字段不会丢失。
  - 删除确认仍使用 `ConfirmDialog`，按钮仍在页签外。
  - 不暴露当前阶段 unsupported 字段：`platform`、`user_agent`、`human_preset`、`geoip`、`headless`。
- `frontend/src/components/ProfileForm.test.tsx`
  - 覆盖页签可访问结构、默认 Identity、跨页签保存 payload、unsupported 字段隐藏、checkbox/tag/launch args/delete dialog。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md`
  - 勾选 `ProfileForm 改为分组页签`。
  - 勾选 `375px、768px、1024px、1440px 响应式检查`。
  - 勾选浏览器检查 `表单长字段不撑破容器`。

验证记录：

```bash
cd frontend && npm test -- --run src/App.test.tsx -t "returns to the all profiles table when selecting All profiles from the VNC viewer"
# 1 passed, 22 skipped

cd frontend && npm test -- --run src/components/ProfileForm.test.tsx
# 红灯：9 failed
# 失败点：当前 ProfileForm 尚无 tablist/tab

cd frontend && npm test -- --run src/components/ProfileForm.test.tsx
# 1 passed, 9 passed

cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileForm.test.tsx
# 2 passed, 32 passed

cd frontend && npm test -- --run
# 13 passed, 166 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- QA 地址：`http://127.0.0.1:8095/`，生产 build 来自 `frontend/dist`。
- 桌面 `1440x960`：
  - `Alpha Warmup` 编辑页页签可见并可切换。
  - 编辑页点击侧栏 `All profiles` 后 JS 验证：`hasTable=true`、`hasEditHeading=false`、`scrollWidth=1440`、`clientWidth=1440`。
- 移动 `390x844`：
  - 编辑页页签在窄屏可见。
  - 切到 `Advanced` 后 JS 验证：`selectedTab="Advanced"`、`hasLaunchArg=true`、`scrollWidth=390`、`clientWidth=390`。
- 额外宽度检查：
  - `375x844`、`768x900`、`1024x900`、`1440x960` 的 Network panel 均无 body 横向溢出。
- `agent-browser errors` 无输出；`agent-browser console` 无输出。

截图：

- `/tmp/cloakbrowser-profile-form-tabs-screens/desktop-profile-form-identity.png`
- `/tmp/cloakbrowser-profile-form-tabs-screens/desktop-profile-form-network.png`
- `/tmp/cloakbrowser-profile-form-tabs-screens/desktop-profile-form-advanced.png`
- `/tmp/cloakbrowser-profile-form-tabs-screens/desktop-all-profiles-after-edit.png`
- `/tmp/cloakbrowser-profile-form-tabs-screens/mobile-profile-form-identity.png`
- `/tmp/cloakbrowser-profile-form-tabs-screens/mobile-profile-form-advanced.png`

边界：

- 没有修改后端、runtime、Docker 或 Project Mileage 仓库。
- 没有改变 profile 保存 API、删除事实流、tags / launch args 提交语义。
- 没有 push 到任何远端仓库。

## 53. 2026-05-26 UI 不可验证承诺文案清扫小闭环

背景：

- 继续推进 `11 UI 视觉系统与体验升级` 的 `文案避免“保证安全”“保证不封号”等不可验证承诺`。
- 子 agent `Raman` 只读审计 `frontend/src`，没有发现明确高风险承诺，例如“保证安全”“不封号”“undetectable”“anti-ban”“guaranteed safe”“never banned”等。
- 本轮只改前端用户可见文案和测试，不改脱敏实现、API、后端或 runtime。

已完成：

- `frontend/src/App.tsx`
  - Proxy Manager 顶栏说明从 `credential-safe URLs` 改为 `redacted URLs`。
- `frontend/src/components/ProxyManagerPage.tsx`
  - `credential-safe checks` 改为 `credential-redacted checks`。
  - `URLs are rendered credential-safe` 改为 `URL credentials are hidden in the UI`。
- `frontend/src/components/ProfileForm.tsx`
  - 用户可见 `invisible_playwright` 文案改为 `browser engine`。
- `frontend/src/lib/health.ts`
  - 健康 good 状态 aria 文案从 `可继续启动或使用` 调整为 `可尝试启动或使用`。
- 测试更新：
  - `App.test.tsx`
  - `ProxyManagerPage.test.tsx`
  - `ProfileForm.test.tsx`
  - `HealthBadge.test.tsx`
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md`
  - 勾选 `文案避免“保证安全”“保证不封号”等不可验证承诺`。

验证记录：

```bash
cd frontend && npm test -- --run src/App.test.tsx src/components/ProxyManagerPage.test.tsx -t "redacted|switches between profile operations"
# 红灯：2 failed
# 失败点：当前 UI 仍显示 credential-safe 文案

cd frontend && npm test -- --run src/App.test.tsx src/components/ProxyManagerPage.test.tsx -t "redacted|switches between profile operations"
# 2 passed, 5 passed, 36 skipped

cd frontend && npm test -- --run src/App.test.tsx src/components/ProxyManagerPage.test.tsx src/components/ProfileForm.test.tsx src/components/HealthBadge.test.tsx -t "redacted|switches between profile operations|launch args|health badge"
# 3 passed, 6 passed, 49 skipped

cd frontend && npm test -- --run
# 13 passed, 166 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

搜索审计：

```bash
rg -n -i "保证|不封号|封号|无法检测|不可检测|检测不到|防封|安全保证|绝对安全|undetect|anti[- ]?ban|guaranteed safe|guarantee|never banned|ban-proof|risk-free|zero risk|cannot be detected|untraceable|anonymous|credential-safe|可继续启动|invisible_playwright" frontend/src
```

结果：

- 用户 UI 中未命中上述高风险承诺。
- 剩余命中只在测试断言 `not.toContain("credential-safe")` 中，用于防回归，不是用户可见产品文案。

浏览器 UI/UE 验证：

- QA 地址：`http://127.0.0.1:8095/`，生产 build 来自 `frontend/dist`。
- 桌面 `1440x960`：
  - Proxy Manager JS 验证：`hasRedactedTop=true`、`hasCredentialSafe=false`、`hasHiddenCredentialsCopy=true`、`scrollWidth=1440`、`clientWidth=1440`。
  - ProfileForm Advanced JS 验证：存在 `Custom Firefox arguments passed to the browser engine at launch.`，不存在 `invisible_playwright` 用户可见文案。
  - Profile table / rail 可见健康 good 状态文案：`健康检查通过，可尝试启动或使用`。
- `agent-browser errors` 无输出；`agent-browser console` 无输出。

截图：

- `/tmp/cloakbrowser-copy-polish-screens/desktop-proxy-copy.png`
- `/tmp/cloakbrowser-copy-polish-screens/desktop-profile-form-copy.png`

边界：

- 没有修改后端、runtime、Docker 或 Project Mileage 仓库。
- 没有改变 URL 凭证脱敏实现，只改用户可见说明文案。
- 没有 push 到任何远端仓库。

## 54. 2026-05-26 浅色主题对比度收口小闭环

背景：

- 继续推进 `11 UI 视觉系统与体验升级` 的最后一个浏览器检查项：`浅色默认主题对比度足够`。
- 使用 `ui-ux-pro-max` 查询 B2B SaaS / operations dashboard 的可访问性准则，按普通文本 4.5:1、大字 3:1 做浏览器抽样验证。
- Playwright MCP 初始失败原因为系统缺少 `/opt/google/chrome/chrome`；已按 Playwright 提示安装 Google Chrome，MCP 后续可正常打开 `http://127.0.0.1:8095/`。
- 本轮只处理 Profile operations 可见文本对比度和 tag badge 颜色算法，不改变虚拟滚动、批量操作、表格结构、后端、runtime 或 Project Mileage。

已完成：

- `frontend/src/components/Badge.tsx`
  - 自定义 `TagBadge` 保留业务色彩 tint。
  - 文本色按 tint 背景自动向 slate 深色混合，直到达到 4.5:1 对比度。
  - 非 hex 色回退到既有 muted badge。
- `frontend/src/components/ProfileList.tsx`
  - 左侧 rail 的 `shown`、`filtered`、quick view count 等辅助文本从过浅 slate 调整为可读 slate。
- `frontend/src/components/ProfileTable.tsx`
  - 表格/移动卡片中的 profile 短 ID、field label、空值和 Tags label 调整为可读 slate。
- `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector 空态、短 ID 和次级 section icon 文本色调整为可读 slate。
- `frontend/src/App.tsx`
  - Profile operations 统计说明在浅色背景上改为更稳的 `text-slate-600`。
- `frontend/src/components/Badge.test.tsx`
  - 覆盖自定义 tag 保留 tint，同时使用可读文本色。
- `docs/ai-docs/v1/tasks/11-ui-visual-system.md`
  - 勾选 `浅色默认主题对比度足够`。
- `docs/ai-docs/v1/tasks/progress.md`
  - 模块 `11 UI 视觉系统与体验升级` 已满足当前任务文档完成口径，可勾选为完成。

验证记录：

```bash
cd frontend && npm test -- --run src/components/Badge.test.tsx
# 红灯：1 failed, 2 passed
# 失败点：旧测试要求 custom tag 文本使用原始亮色，和 4.5:1 对比度目标冲突

cd frontend && npm test -- --run src/components/Badge.test.tsx
# 1 passed, 3 passed

cd frontend && npm test -- --run
# 13 passed, 166 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- QA 地址：`http://127.0.0.1:8095/`，生产 build 来自 `frontend/dist`。
- 桌面 `1440x960`：
  - 对当前 viewport 可见文本运行 contrast audit，普通文本阈值 4.5:1，大字阈值 3:1。
  - JS 验证：`totalFailures=0`。
- 移动 `390x844`：
  - JS 验证：`totalFailures=0`、`scrollWidth=390`、`clientWidth=390`。
- Playwright MCP console：0 errors、0 warnings。

截图：

- `/tmp/cloakbrowser-contrast-screens/desktop-profile-contrast.png`
- `/tmp/cloakbrowser-contrast-screens/mobile-profile-contrast.png`

边界：

- 没有修改后端、runtime、Docker 或 Project Mileage 仓库。
- 没有改变 profile API、批量 health check、批量高风险 disabled 语义、表格虚拟滚动或移动端横向滚动策略。
- 没有 push 到任何远端仓库。

## 55. 2026-05-26 Profile Template 后端基础 CRUD 小闭环

背景：

- `11 UI 视觉系统与体验升级` 已收口并在 `tasks/progress.md` 勾选。
- 继续推进 CloakBrowser 独立成熟化优先级，进入 `09 模板、批量创建与批量运营`。
- 子 agent `Archimedes` 只读调研确认：当前无 `profile_templates` 实现；后端最小闭环应新增 SQLite 表、DB helper、Pydantic models、CRUD API 和测试。
- 本轮只做 Profile Template 后端事实源，不做前端模板选择，不改变 profile 创建流程，不触碰 Project Mileage。

已完成：

- `backend/tests/test_templates.py`
  - 先写红灯测试，初始失败点为缺表、缺 DB helper、缺 API 路由。
  - 覆盖表创建、DB CRUD、API CRUD、not found、模板更新不静默改写已有 profile。
- `backend/database.py`
  - 新增 `profile_templates` 表。
  - 新增 `create_profile_template` / `list_profile_templates` / `get_profile_template` / `update_profile_template` / `delete_profile_template`。
  - `launch_args` 采用 JSON roundtrip。
- `backend/models.py`
  - 新增 `ProfileTemplateCreate` / `ProfileTemplateUpdate` / `ProfileTemplateResponse`。
- `backend/main.py`
  - 新增 `/api/profile-templates` CRUD API。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选 `新增 profile_templates 表`。
  - 勾选 `支持保存模板`。
  - 勾选 `模板变更不自动修改已有 profile`。
  - 勾选验收 `模板不会静默改写已有 profile`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 红灯：4 failed
# 失败点：缺 profile_templates 表、缺 create_profile_template helper、缺 API routes

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 237 passed
```

未覆盖范围：

- 前端模板列表/保存入口。
- 创建 profile 时选择模板并应用字段。
- CSV 批量导入、批量启动/停止/GeoIP/tag/proxy/export/delete。

边界：

- 没有修改前端 UI、runtime、Docker 或 Project Mileage 仓库。
- 没有把模板变更联动写回既有 profile，避免意外批量污染。
- 没有 push 到任何远端仓库。

## 56. 2026-05-26 Profile 创建应用模板后端契约小闭环

背景：

- 在 `profile_templates` 后端事实源基础上，继续推进 `09 模板、批量创建与批量运营`。
- 本轮只做后端契约：`POST /api/profiles` 可接收 `template_id` 并复制模板字段。
- 前端创建页模板下拉和保存模板入口还未做，因此 `09-templates-bulk-ops.md` 顶部 `创建 profile 时可选择模板` 暂不勾选。

已完成：

- `backend/tests/test_templates.py`
  - 先写红灯测试，初始失败点为 `template_id` 被忽略、missing template 仍创建成功。
  - 覆盖从模板创建 profile。
  - 覆盖显式 profile 字段覆盖模板字段。
  - 覆盖 missing template 返回 404。
- `backend/models.py`
  - `ProfileCreate` 新增可选 `template_id`。
- `backend/main.py`
  - 创建 profile 时如果传入 `template_id`，读取模板并复制 platform、screen、GPU、hardware concurrency、color scheme、humanize、human preset、launch args、geoip。
  - 使用 `model_fields_set` 区分显式字段和 Pydantic 默认值，避免默认 `windows` 覆盖模板中的 `macos/linux`。
  - 缺失模板返回 `404 Profile template not found`。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 记录后端契约小闭环和剩余前端范围。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 红灯：2 failed, 6 passed
# 失败点：template_id 被忽略，missing template 仍创建成功

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 8 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 240 passed
```

未覆盖范围：

- 前端创建 profile 时选择模板。
- 前端 API 类型暴露 `template_id`。
- 保存当前 profile 为模板。

边界：

- 没有修改前端 UI、runtime、Docker 或 Project Mileage 仓库。
- 没有把 Project Mileage 钱包、订单、权限逻辑写进 CloakBrowser。
- 没有 push 到任何远端仓库。

## 57. 2026-05-26 Profile 创建页模板选择小闭环

背景：

- 后端 `template_id` 创建契约完成后，继续补齐 Profile 创建页模板选择入口。
- 本轮只处理创建 Profile 表单，不做编辑页模板切换，不做保存当前 profile 为模板，不做 CSV 批量导入。

已完成：

- `frontend/src/App.test.tsx`
  - 先写红灯测试：mock 模板列表，点击 New Profile，预期出现 `Profile template` 下拉并提交 `template_id` 和模板字段。
  - 初始失败点：创建页没有模板下拉。
- `frontend/src/lib/api.ts`
  - 新增 `ProfileTemplate` / `ProfileTemplateCreateData` / `ProfileTemplateUpdateData`。
  - `ProfileCreateData` 新增可选 `template_id`。
  - 新增 profile template CRUD API client。
- `frontend/src/App.tsx`
  - 启动后读取 `/api/profile-templates`。
  - 创建 Profile 时把模板列表传给 `ProfileForm`。
- `frontend/src/components/ProfileForm.tsx`
  - 创建模式下显示 `Profile template` 下拉。
  - 选择模板后把 platform、screen、GPU、hardware concurrency、color scheme、humanize、human preset、launch args、geoip 应用到表单。
  - 编辑模式不显示模板选择，避免误把模板变更套到既有 profile。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选 `创建 profile 时可选择模板`。

验证记录：

```bash
cd frontend && npm test -- --run src/App.test.tsx -t "applies a profile template"
# 红灯：1 failed
# 失败点：创建页没有 Profile template 下拉

cd frontend && npm test -- --run src/App.test.tsx -t "applies a profile template"
# 1 passed, 23 skipped

cd frontend && npm test -- --run
# 13 passed, 167 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 重启本地 QA 服务 `http://127.0.0.1:8095/`，让服务加载新的后端和 `frontend/dist`。
- 通过 API 创建 QA 模板 `Mac warmup`。
- 桌面 `1440x960`：
  - 创建页可见 `Profile template` 下拉。
  - 选择 `Mac warmup` 后，Device 页显示 `1440 × 900`、hardware concurrency `8`、GPU `Apple / Apple M2`。
  - Behavior 页显示 humanize checked、color scheme `light`。
  - Advanced 页显示 `--private-window`。
  - 点击 Create 后，`/api/profiles` 返回 `Template QA Profile`，字段为 `macos / 1440x900 / Apple M2 / humanize=true / --private-window / geoip=false`。
  - `scrollWidth=1440`、`clientWidth=1440`。
- 移动 `390x844`：
  - 创建页模板下拉可见，页面未横向撑破。
- Playwright MCP console：0 errors、0 warnings。

截图：

- `/tmp/cloakbrowser-template-form-screens/desktop-template-select.png`
- `/tmp/cloakbrowser-template-form-screens/desktop-template-applied.png`
- `/tmp/cloakbrowser-template-form-screens/mobile-template-select.png`

未覆盖范围：

- 前端保存当前 profile 为模板。
- 模板列表管理页面。
- CSV 批量创建中的 `template` 字段。

边界：

- 没有修改后端模板/创建契约之外的 runtime 行为。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 58. 2026-05-26 Profile CSV 导入预览后端 API 小闭环

背景：

- 继续推进 09 模板、批量创建与批量运营。
- 子 agent 只读审计建议：先做 CSV paste/import preview，固定字段契约、模板解析和行级错误结构，再进入真正批量创建。
- 本轮只做后端 preview API，不写库、不做前端导入 UI、不触碰 Project Mileage。

已完成：

- `backend/tests/test_bulk.py`
  - 先写红灯测试，确认 `/api/profiles/import/preview` 不存在时返回 `405`。
  - 覆盖 CSV preview 应用模板、显式字段覆盖模板、proxy 响应脱敏、tags 解析、预览不写入 profiles。
  - 覆盖混合成功/失败行，失败行保留原因且不阻断有效行。
  - 覆盖空 CSV、无可用 header 返回 `422`。
- `backend/models.py`
  - 新增 Profile import preview 请求、行、profile payload、响应模型。
- `backend/profile_import.py`
  - 新增 CSV 解析、字段规范化、模板 id/name 解析、行级校验、preview payload 生成。
  - 抽出 `apply_profile_template_fields`，后续普通创建和批量创建可共用模板覆盖规则。
- `backend/main.py`
  - 新增 `POST /api/profiles/import/preview`。
  - `POST /api/profiles` 复用模板应用 helper，已有模板契约测试保持通过。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选 `导入前预览（后端 API；前端导入 UI 另起闭环）`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 红灯：3 failed, 1 passed
# 失败点：/api/profiles/import/preview 尚不存在，返回 405

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_templates.py -q
# 12 passed
```

未覆盖范围：

- 前端 CSV 粘贴导入 UI、无效行标红、导入后部分成功写入。
- 批量启动/停止/health check/GeoIP/tag/proxy/export/delete。

边界：

- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 62. 2026-05-26 Profile Config 批量导出后端 API 小闭环

背景：

- 继续推进 09 批量运营能力，选择低风险、只读的 profile config export。
- 子 agent 只读审计建议：`POST /api/profiles/export`，返回可重建 profile 的 config JSON；proxy 原文属于敏感备份能力，可以保留，但排除本机路径、运行态、VNC、automation、last_geoip。

已完成：

- `backend/tests/test_bulk.py`
  - 先写红灯测试，确认 `/api/profiles/export` 不存在时返回 `405`。
  - 覆盖多 profile 按输入顺序返回部分成功/失败。
  - 覆盖 missing profile 不阻断其他导出项。
  - 覆盖导出 config 包含可重建字段，并排除 `status`、`automation_url`、`vnc_ws_port`、`user_data_dir`。
  - 覆盖空 `profile_ids` 返回 `422`。
- `backend/models.py`
  - 新增 `ProfileExportRequest` / `ProfileConfigExport` / `ProfileExportResult` / `ProfileExportResponse`。
- `backend/main.py`
  - 新增 `POST /api/profiles/export`。
  - 返回 `schema_version=1`、`total/exported/failed/results`。
  - 失败项只返回 `Profile not found`，不带 profile 数据。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选 `批量导出 profile config（后端 API；前端下载入口另起闭环）`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 红灯：2 failed, 6 passed
# 失败点：/api/profiles/export 尚不存在，返回 405

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 8 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_templates.py -q
# 16 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 248 passed
```

未覆盖范围：

- 前端 `Export config` 下载入口。
- 批量启动/停止/health check/GeoIP/tag/proxy/delete。

边界：

- 没有修改前端 UI。
- 没有写导出文件到服务端磁盘。
- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 60. 2026-05-26 Profile CSV 批量创建后端 API 小闭环

背景：

- 在 CSV preview parser/validator 和前端 preview UI 完成后，继续推进真正批量创建的后端闭环。
- 子 agent 只读审计建议：新增 `POST /api/profiles/import`，复用 preview parser，成功行写库，失败行保留原因；不做前端提交按钮，不启动浏览器。

已完成：

- `backend/tests/test_bulk.py`
  - 先写红灯测试，确认 `/api/profiles/import` 不存在时返回 `405`。
  - 覆盖混合成功/失败：有效行创建 profile，无效行保留 `line_number/source/errors/profile:null`。
  - 覆盖模板字段复制和 CSV 显式字段覆盖模板字段。
  - 覆盖 tags 写入后可通过 `GET /api/profiles` 读回。
  - 覆盖 headerless CSV 返回 `422` 且不写库。
- `backend/profile_import.py`
  - 抽出 `parse_profile_csv_import`，preview 和 import 共用同一套 parser/validator。
  - 新增 `profile_create_data_for_import`，创建前移除 `template_id`。
  - Preview 响应继续脱敏，import 内部保留 raw normalized create data。
- `backend/models.py`
  - 新增 `ProfileImportResult` / `ProfileImportResponse`。
- `backend/main.py`
  - 新增 `POST /api/profiles/import`。
  - 成功行调用 `db.create_profile`，不调用 `browser_mgr.launch`。
  - 只要 CSV header 可解析，部分失败仍返回 `200`。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选 `支持 CSV 粘贴导入 profile（后端 API）`、`支持字段（CSV preview/import 后端契约）`、`部分导入成功，失败行保留原因（后端 API）`、`批量导入不会因为一行失败而全部失败（后端 API）`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 红灯：2 failed, 4 passed
# 失败点：/api/profiles/import 尚不存在，返回 405

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 6 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_templates.py -q
# 14 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 246 passed
```

未覆盖范围：

- 前端 `Import valid rows` / `Create valid profiles` 提交入口。
- 导入后的前端刷新、成功/失败反馈和重复提交保护。
- 批量启动/停止/health check/GeoIP/tag/proxy/export/delete。

边界：

- 没有修改前端 UI。
- 没有启动 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 61. 2026-05-26 Profile CSV 批量创建前端提交小闭环

背景：

- 后端 `POST /api/profiles/import` 完成后，继续把 Profile CSV preview 弹窗升级为可提交有效行的导入入口。
- 本轮只接入 batch import API，不改 ProfileTable、BulkActionBar、runtime 或 Project Mileage。

已完成：

- `frontend/src/lib/api.test.ts`
  - 先写红灯测试，确认 `api.importProfiles` 不存在。
- `frontend/src/lib/api.ts`
  - 新增 `ProfileImportResult` / `ProfileImportResponse`。
  - 新增 `api.importProfiles(csvText)`。
- `frontend/src/App.test.tsx`
  - 覆盖 preview 后点击 `Create valid profiles`。
  - 断言调用 batch import API，不调用单条 `create`。
  - 断言导入后调用 `refresh`，显示 `Imported N profile(s), M failed`，失败原因保留且不泄漏 credentials。
- `frontend/src/components/ProfileCsvPreviewDialog.tsx`
  - 增加 `Create valid profiles` 按钮。
  - 增加 creating/import result/import notice 状态。
  - 导入结果优先显示后端 `results`，失败行继续保留 errors。
  - 保留最近一次成功 preview 的原始 CSV 用于提交，UI textarea 继续显示脱敏 CSV。
- `frontend/src/App.tsx`
  - 传入 `onImported={refresh}`，导入成功后刷新 profile list。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 追加前端提交小闭环记录。

验证记录：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts -t "importProfiles"
# 红灯：1 failed
# 失败点：api.importProfiles is not a function

cd frontend && npm test -- --run src/lib/api.test.ts -t "importProfiles"
# 1 passed, 22 skipped

cd frontend && npm test -- --run src/App.test.tsx -t "imports valid profile CSV"
# 1 passed, 25 skipped

cd frontend && npm test -- --run
# 13 passed, 171 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 重启本地 QA 服务 `http://127.0.0.1:8095/`。
- 通过 API 创建 QA 模板 `CSV Import UI Mac`。
- 桌面 `1440x960`：
  - 打开 `Import profile CSV preview` 弹窗。
  - 粘贴 2 行 CSV 后点击 `Preview CSV`，显示 `2 total / 1 ready / 1 blocked`。
  - 点击 `Create valid profiles` 后显示 `Imported 1 profile(s), 1 failed`。
  - 左侧列表和主统计从 `5 profiles` 刷新为 `6 profiles`，并出现 `UI Batch Import`。
  - 失败行继续显示 `name is required`、`Template not found`、`platform must be one of...`。
  - 页面正文不包含 `hiddenpass` 或 `user:`。
- 移动 `390x844`：
  - 弹窗可见，导入结果提示保留。
  - `body.scrollWidth=390`、`body.clientWidth=390`。
- Playwright MCP console：当前交互后 0 errors、0 warnings。
- 截图：
  - `/tmp/cloakbrowser-profile-csv-import-screens/desktop.png`
  - `/tmp/cloakbrowser-profile-csv-import-screens/mobile.png`

未覆盖范围：

- 批量启动/停止/health check/GeoIP/tag/proxy/export/delete。

边界：

- 没有修改 ProfileTable 虚拟滚动、bulk Check health、Actions 列或移动端表格滚动语义。
- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 59. 2026-05-26 Profile CSV 导入预览前端 UI 小闭环

背景：

- 后端 `POST /api/profiles/import/preview` 完成后，继续补齐 Profile 运营台前端 preview 入口。
- 子 agent 只读审计建议：入口放 Profiles 顶栏，弹窗只 preview，不放入 `ProfileTable` / `BulkActionBar` / row Actions，避免破坏虚拟滚动和 bulk selection 语义。

已完成：

- `frontend/src/lib/api.test.ts`
  - 先写红灯测试：`api.previewProfileImport` 不存在。
- `frontend/src/lib/api.ts`
  - 新增 Profile CSV preview 类型和 `api.previewProfileImport(csvText)`。
- `frontend/src/App.test.tsx`
  - 先写红灯测试：Profile 顶栏缺少 `Import CSV`。
  - 覆盖弹窗提交 preview、显示 `1 ready / 1 blocked`、展示模板应用后的 profile 字段、显示无效行错误。
  - 覆盖不调用 `create`，确保本轮不创建 profile。
  - 覆盖 dialog 文本和 title 不泄漏 proxy 凭证。
- `frontend/src/components/ProfileCsvPreviewDialog.tsx`
  - 新增 `Import profile CSV preview` 弹窗。
  - 支持粘贴 CSV、调用后端 preview API、展示最多 60 行 preview。
  - 有效行展示 profile 摘要；无效行 amber 高亮并展示 errors。
  - Preview 成功后将 textarea 中 URL 凭证脱敏，降低截图和 UI 证据泄漏风险。
- `frontend/src/App.tsx`
  - Profile 顶栏新增 `Import CSV` 按钮，与 `New Profile` 并列。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选 `无效行标红（Profile CSV preview 前端弹窗）`。

验证记录：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts -t "previewProfileImport"
# 红灯：1 failed
# 失败点：api.previewProfileImport is not a function

cd frontend && npm test -- --run src/lib/api.test.ts -t "previewProfileImport"
# 1 passed, 21 skipped

cd frontend && npm test -- --run src/App.test.tsx -t "previews profile CSV import"
# 红灯：1 failed
# 失败点：Profiles 顶栏没有 Import CSV 按钮

cd frontend && npm test -- --run src/App.test.tsx -t "previews profile CSV import"
# 中间红灯：textarea 展示原始 proxy 凭证

cd frontend && npm test -- --run src/App.test.tsx -t "previews profile CSV import"
# 1 passed, 24 skipped

cd frontend && npm test -- --run
# 13 passed, 169 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 重启本地 QA 服务 `http://127.0.0.1:8095/`。
- 通过 API 创建 QA 模板 `CSV QA Mac`。
- 桌面 `1440x960`：
  - Profile 顶栏可见 `Import CSV`。
  - 打开 `Import profile CSV preview` 弹窗。
  - 粘贴 2 行 CSV 后点击 `Preview CSV`，显示 `2 total / 1 ready / 1 blocked`。
  - 有效行展示 `CSV QA Import`、`macos`、`ja-JP`、`Asia/Tokyo`、`asia/warmup`。
  - 无效行展示 `name is required`、`Template not found`、`platform must be one of...`。
  - 页面正文不包含 `hiddenpass` 或 `user:`，且没有出现 `Import valid rows`。
- 移动 `390x844`：
  - 弹窗可见，表格区域内部横向滚动。
  - `body.scrollWidth=390`、`body.clientWidth=390`。
- Playwright MCP console：当前交互后 0 errors、0 warnings。
- 截图：
  - `/tmp/cloakbrowser-profile-csv-preview-screens/desktop.png`
  - `/tmp/cloakbrowser-profile-csv-preview-screens/mobile.png`

未覆盖范围：

- 真正批量创建 profile 与部分成功写入。

边界：

- 没有修改 `ProfileTable` 虚拟滚动、bulk Check health、Actions 列、移动端 card/table 滚动语义。
- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 60. 2026-05-26 Profile Config 批量导出前端下载入口小闭环

背景：

- 后端 `POST /api/profiles/export` 已完成，本轮补齐 Profile 运营台里的前端下载入口。
- 只启用只读 `Export config`，继续保持批量启动/停止/tag/delete 等高风险操作 disabled。

已完成：

- `frontend/src/lib/api.ts`
  - 新增 profile config export 类型和 `api.exportProfiles(profileIds)`。
- `frontend/src/hooks/useProfiles.ts`
  - 新增 `exportProfileConfigs(ids)`，去重后调用 API，不修改 profile state。
- `frontend/src/components/BulkActionBar.tsx`
  - 新增 `Export config` 按钮和 exporting 状态。
  - `aria-busy` 纳入 exporting。
- `frontend/src/components/ProfileTable.tsx`
  - 从受控 selection 传完整选中 profile ids，保留虚拟滚动语义。
- `frontend/src/App.tsx`
  - 调用导出 API 后生成本地 JSON 下载。
  - 使用 bulk feedback 展示成功/部分失败摘要。
- 测试覆盖：
  - API body shape。
  - hook 去重和不改 state。
  - bulk bar 启用 export、exporting disabled、高风险动作仍 disabled。
  - App 下载 Blob、触发 anchor click、partial feedback、不把导出 proxy secret 渲染到 DOM。

验证记录：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts src/hooks/useProfiles.test.ts src/components/ProfileTable.test.tsx src/App.test.tsx
# 红灯：6 failed

cd frontend && npm test -- --run src/lib/api.test.ts src/hooks/useProfiles.test.ts src/components/ProfileTable.test.tsx src/App.test.tsx
# 4 passed, 114 passed

cd frontend && npm test -- --run
# 13 passed, 175 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 本地 QA 服务：`http://127.0.0.1:8095/`，进程 `1681096`。
- 桌面 `1440x960`：
  - 选中 2 个 profile 后显示 `Export config`。
  - 点击后触发 `POST /api/profiles/export` 并下载 `cloakbrowser-profile-configs-2026-05-26T13-15-52-514Z.json`。
  - 反馈显示 `Exported 2 profile configs.`。
  - Launch/Stop/Tag/Delete 仍 disabled。
- 移动 `390x844`：
  - bulk bar 与 profile cards 可用。
  - `body.scrollWidth=390`、`documentElement.scrollWidth=390`。
- Playwright MCP console：导出交互后 0 errors、0 warnings。
- 截图：
  - `/home/jeff/code/cloakbrowser-export-desktop.png`
  - `/home/jeff/code/cloakbrowser-export-mobile.png`

边界：

- 没有修改后端。
- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 63. 2026-05-26 Proxy Provider Preset 后端事实源 CRUD 小闭环

背景：

- Module 09 继续推进 Proxy Template 前置能力。
- 本轮只做后端事实源 CRUD，不做前端 preset 管理/选择，不做国家/标签 proxy 选择或随机分配策略。
- Preset 只保存 provider 元数据、国家和标签，不保存 proxy 凭证、provider API key、billing/account 信息。

已完成：

- `backend/database.py`
  - 新增 `proxy_provider_presets` 表。
  - 新增 `create_proxy_provider_preset` / `list_proxy_provider_presets` / `get_proxy_provider_preset` / `update_proxy_provider_preset` / `delete_proxy_provider_preset`。
  - 删除 preset 不影响已有 proxy assets。
- `backend/models.py`
  - 新增 `ProxyProviderPresetCreate` / `ProxyProviderPresetUpdate` / `ProxyProviderPresetResponse`。
- `backend/main.py`
  - 新增 `/api/proxy-provider-presets` CRUD API。
- `backend/tests/test_proxy_provider_presets.py`
  - 覆盖表创建、DB CRUD、API CRUD、not found、空名称拒绝。
  - 覆盖删除 preset 不影响 proxy assets。
  - 覆盖传入 `api_key` / `password` / `billing_account` 等字段不会进入响应和列表。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 将 `proxy provider preset` 拆成子项：后端事实源已完成，前端接入与策略联动仍未完成。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py -q
# 7 passed

. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py backend/tests/test_proxies.py -q
# 22 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 255 passed
```

边界：

- 没有修改 Proxy check/assign/GeoIP 行为。
- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 64. 2026-05-26 Proxy Provider Preset 前端消费小闭环

背景：

- 继续 Module 09 Proxy Template，基于后端 `proxy_provider_presets` 事实源做最小前端消费。
- 本轮把 preset 接入 Proxy Manager 的 proxy CSV import，用作导入默认值。
- 不做 preset CRUD 管理页，不做按国家/标签选择 proxy，不做随机分配策略，不改 runtime。

已完成：

- `frontend/src/lib/api.ts`
  - 新增 `ProxyProviderPreset` 类型和 provider preset CRUD API client。
- `frontend/src/components/ProxyManagerPage.tsx`
  - Proxy Manager 加载 provider presets。
  - `Import proxy CSV` 弹窗新增 `Provider preset` 下拉。
  - CSV preview/import 使用 preset 默认 `provider`、`country_code`、`notes`、`tags`。
  - 行内 CSV 显式字段优先，tags 按 preset tags + row tags 去重合并。
  - textarea 显示脱敏 URL，内部保留刚粘贴的 raw CSV 用于创建 proxy asset。
- 测试覆盖：
  - provider preset API client。
  - 选择 preset 后 CSV import 行继承 provider/country/notes/tags。
  - row tags 与 preset tags 合并。
  - UI 不渲染 `hiddenpass`。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选 `前端接入/选择（Proxy CSV import preset 默认值）`。
  - 保持顶层 `支持 proxy provider preset` 未完成，因为策略联动和管理入口仍未完成。

验证记录：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts -t "ProxyProviderPreset|listProxyProviderPresets|createProxyProviderPreset|updateProxyProviderPreset|deleteProxyProviderPreset"
# 4 passed, 24 skipped

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx -t "applies proxy provider preset defaults"
# 1 passed, 18 skipped

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 19 passed

cd frontend && npm test -- --run src/lib/api.test.ts
# 28 passed

cd frontend && npm test -- --run
# 13 passed, 180 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 本地 QA 服务：`http://127.0.0.1:8095/`。
- 创建 QA preset `QA Japan Mobile`。
- Proxy Manager -> Import CSV -> 选择 `QA Japan Mobile` -> 粘贴 `name,url,tags` CSV -> 预览 -> 导入。
- 结果：
  - Preview 显示 `ProxyJP`、`mobile, bulk`、`Ready`。
  - 新增 `QA Preset Import` proxy asset，列表显示 `JP`、`ProxyJP`、`Tokyo QA defaults`、`mobile/bulk`。
  - DOM 检查：`hiddenpass=false`、`userColon=false`。
  - 移动端 `body.scrollWidth=390`、`clientWidth=390`。
  - Playwright MCP console：0 errors、0 warnings。
- 截图：
  - `/home/jeff/code/cloakbrowser-proxy-preset-desktop.png`
  - `/home/jeff/code/cloakbrowser-proxy-preset-mobile.png`

边界：

- 没有修改 Profile CSV import 合约。
- 没有修改 Proxy check/assign/GeoIP 行为。
- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 65. 2026-05-26 Proxy 国家/标签候选过滤与随机分配后端 API 小闭环

背景：

- 继续 Module 09 Proxy Template 和批量运营前置能力。
- 本轮只做后端契约：按 provider preset / country / tags 筛选 proxy 候选，并随机分配给多个 profiles。
- 不做前端入口，不修改现有单 proxy assign，不碰 runtime、VNC、CDP、批量启动/停止/删除。

已完成：

- `backend/models.py`
  - 新增 `ProxyRandomAssignRequest` / `ProxyRandomAssignResult` / `ProxyRandomAssignResponse`。
  - 请求支持 `profile_ids`、`provider_preset_id`、`provider`、`country_code`、`tags`。
- `backend/main.py`
  - 新增 `POST /api/proxies/assign/random`。
  - `provider_preset_id` 注入 preset 的 provider/country/tags。
  - `country_code` trim + uppercase 后匹配。
  - tags 使用 preset tags + request tags 去重合并，当前语义为全部 tag 同时匹配。
  - 每个有效 profile 从候选 proxy 中随机选择一个，并写入 raw proxy URL。
  - missing profile 行级失败，不阻断其他 profile。
  - 候选为空返回 `400 No proxy assets match selection`，不修改 profile。
- `backend/tests/test_proxies.py`
  - 覆盖 provider preset + country + tag 候选过滤。
  - 覆盖 random assignment 的部分成功。
  - 覆盖响应不泄漏 proxy credentials，但数据库写入 raw proxy URL。
  - 覆盖候选为空返回 400 且 profile 原值不变。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选后端候选过滤 API、后端 random assignment API、provider preset 后端策略联动。
  - 前端运营入口继续保持未完成。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "random_proxy_assignment"
# 2 passed, 15 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q
# 17 passed

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py backend/tests/test_proxy_provider_presets.py -q
# 24 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 257 passed
```

边界：

- 没有修改前端。
- 没有修改 Profile CSV import 合约。
- 没有修改 Proxy check/assign/GeoIP 既有行为。
- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 66. 2026-05-26 Proxy 随机分配前端运营入口小闭环

背景：

- Module 09 继续推进 Proxy Template / 批量运营。
- 后端已经完成 `POST /api/proxies/assign/random`，本轮补前端运营入口。
- 保持 Project Mileage 不进入跨仓实现，不修改 browser runtime。

已完成：

- `frontend/src/lib/api.ts`
  - 新增 random proxy assignment request/response 类型。
  - 新增 `api.assignRandomProxyToProfiles`。
- `frontend/src/components/ProxyManagerPage.tsx`
  - Toolbar 新增 `Random assign`。
  - 按当前 `Country / Provider / Tag` filters 生成 selection，并把 `FILTER_ALL` sentinel 转为空字段。
  - 新增独立 `Random proxy assignment` 弹窗，不复用单 proxy assign 的 `selectedProxy` 状态，避免多选/无选 proxy 时被自动关闭。
  - 弹窗选择 profiles 后调用真实 random assignment API。
  - 成功后关闭弹窗、清空 selection、显示成功反馈，并触发 `onProfilesAssigned` 刷新 profile 数据。
  - 错误继续脱敏。
- `frontend/src/lib/api.test.ts`
  - 覆盖 endpoint `/api/proxies/assign/random` 与 request body。
- `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖 JP / ProxyJP / mobile filters 下随机分配给 2 个 profiles。
  - 覆盖成功 toast、弹窗关闭、refresh callback、凭证不渲染。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选按国家/标签选择 proxy 的前端运营入口。
  - 勾选随机分配策略的前端运营入口。

验证记录：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts -t "assignRandomProxyToProfiles"
# 1 passed, 28 skipped

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx -t "randomly assigns"
# 1 passed, 19 skipped

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 20 passed

cd frontend && npm test -- --run src/lib/api.test.ts
# 29 passed

cd frontend && npm test -- --run
# 13 passed, 182 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 本地 QA 服务：`http://127.0.0.1:8095/`，进程 `1749057`。
- 桌面 `1440x960`：
  - Proxy Manager 选择 `JP` / `ProxyJP` / `mobile` 后，`Random assign` 打开弹窗。
  - 弹窗显示 `1 candidate proxy`。
  - 选择 `Template QA Profile` 和 `Alpha Warmup` 后提交。
  - 真实请求 `POST /api/proxies/assign/random`：
    - `country_code=JP`
    - `provider=ProxyJP`
    - `tags=["mobile"]`
    - `profile_ids` 为 2 个 profile id。
  - 响应 `200 OK`，页面显示 `Random assigned proxy to 2 profile(s), 0 failed`。
- 移动 `390x844`：
  - `Random assign` 按钮可见。
  - `body.scrollWidth=390`、`documentElement.scrollWidth=390`。
- Playwright MCP console：0 errors、0 warnings。
- 截图：
  - `/home/jeff/code/cloakbrowser-random-assign-desktop.png`
  - `/home/jeff/code/cloakbrowser-random-assign-mobile.png`

边界：

- 没有修改后端。
- 没有修改 CSV import provider preset 行为。
- 没有修改单 proxy assign、bulk check、表格滚动结构。
- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 67. 2026-05-26 Proxy Provider Preset 前端完整管理入口小闭环

背景：

- Module 09 的 `proxy provider preset` 已完成后端 CRUD、CSV import 前端消费、后端候选过滤与随机分配策略联动。
- 本轮补齐 Proxy Manager 内的 provider preset 前端完整管理入口。
- 用户要求继续保持 CloakBrowser 独立成熟化，不进入 Project Mileage 跨仓实现。

已完成：

- `frontend/src/components/ProxyManagerPage.tsx`
  - Toolbar 新增 `Manage presets`。
  - 新增 `Manage provider presets` 弹窗。
  - 支持创建、编辑、删除 provider preset。
  - 表单字段收敛为 `name/provider/country_code/tags/notes`。
  - 不提供 provider API key、password、billing、account 等字段或文案。
  - 创建/编辑/删除后同步 `providerPresets`，CSV import 下拉即时更新。
  - 删除当前 import 选中的 preset 时清空选中值。
  - 保存/删除错误信息继续通过 `redactUrlCredentials` 脱敏。
  - 移动端弹窗 body 改为内部滚动，避免底部操作按钮被裁切；页面本体不横向撑破。
- `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖 provider preset create。
  - 覆盖 provider preset update/delete。
  - 覆盖管理弹窗不出现 `api key/password/billing/account` 等敏感 provider 字段文案。
- `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选 `支持 proxy provider preset`。
  - 勾选 `前端完整管理入口`。

验证记录：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx -t "proxy provider presets"
# 1 test file passed, 2 tests passed | 20 skipped

cd frontend && npm test -- --run
# 13 test files passed, 184 tests passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 本地 QA 服务：`http://127.0.0.1:8095/`，runtime `invisible-playwright`。
- 桌面 `1440x960`：
  - 打开 `Proxy Manager` -> `Manage presets`。
  - 创建 `QA UI Preset Temp` 成功。
  - `Import CSV` 的 `Provider preset` 下拉即时出现新 preset。
  - 选择新 preset 并粘贴仅含 `name,url` 的 CSV，preview 自动补入 `ProxyQA`、`US`、`ui, temp`。
  - 编辑为 `QA UI Preset Updated` 成功。
  - 删除临时 preset 成功。
  - 再打开 `Import CSV`，临时 preset 已从下拉移除。
- 移动 `390x844`：
  - 管理弹窗内部可滚动。
  - `body.scrollWidth=390`、`viewportWidth=390`。
- Playwright MCP console：0 errors、0 warnings。
- 截图：
  - `/home/jeff/code/cloakbrowser-provider-presets-desktop.png`
  - `/home/jeff/code/cloakbrowser-provider-presets-mobile.png`

边界：

- 没有修改后端。
- 没有修改 random assignment 为提交 `provider_preset_id`，前端仍按 country/provider/tag selection 调用。
- 没有修改 single proxy assign、bulk check、credential redaction、proxy table 横向滚动语义。
- 没有修改 Firefox/invisible_playwright runtime。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 68. 2026-05-26 会话切换前接力记录

本节是 2026-05-26 的历史接力状态，已被 2026-05-27 第 69 节接续；其中“未提交/尚未运行/生产代码尚未实现”仅描述当时状态。

背景：

- 用户要求当前会话停止继续功能实现，先完整更新交接文档，并在 `/home/jeff/code` 根目录生成下一会话可直接发送的 goal prompt。
- 当前 API 端点即将欠费，需要保留上下文，避免新会话丢失进度。

最新已完成并提交：

- Commit：`087097a add proxy provider preset manager`
- 完成 Module 09 的 `Proxy Provider Preset 前端完整管理入口` 小闭环。
- CloakBrowser 工作树在该提交后曾为干净状态。
- 不 push。

当时未提交工作：

- 新增文件：`backend/tests/test_session_broker.py`
- 这是 05 Session Broker 的 TDD 红灯测试草稿。
- 测试尚未运行。
- 生产代码尚未实现。
- 05 仍未完成，相关 checkbox 未勾选。

文档自查范围：

- 已更新 `docs/ai-docs/v1/2026-05-25-fingerprint-health-ops-plan.md`：
  - 当前关键提交更新到 `087097a`。
  - 增加 05 红灯测试草稿接力状态。
  - 更新最近验证基线说明。
- 已更新 `docs/ai-docs/v1/tasks/progress.md`：
  - 增加当前接力状态和下一步建议。
  - 05 仍保持未完成。
- 已更新 `docs/ai-docs/v1/tasks/05-session-broker-project-mileage.md`：
  - 增加 05 红灯测试草稿、边界和下一步。
  - 所有 checkbox 仍保持未完成。
- 已更新 `docs/ai-docs/v1/goal-prompt.md`：
  - 增加当前接力版本、未提交文件和下一步命令。
- 已更新 `docs/ai-docs/v1/2026-05-25-session-memory.md`：
  - 顶部当前服务/提交信息更新。
  - 文末追加本接力记录。
- 已创建仓库外根目录提示词：
  - `/home/jeff/code/CLOAKBROWSER_NEXT_GOAL_PROMPT.md`
- 已检查但未修改：
  - `proposal.md`
  - `high-level-design.md`
  - `detailed-design.md`
  - 其他已完成模块任务文档。它们是需求/历史完成记录，当前 05 接力不改变其事实。

当时红灯测试草稿意图：

- `RUNTIME_SERVICE_TOKEN` 使用 `X-Runtime-Service-Token` header。
- 无 runtime service token 不能创建 session。
- `POST /api/runtime/sessions`：
  - 输入 `external_session_id`。
  - 输入 `profile_id` 或 `template_id`。
  - 输入 `lease_seconds`。
  - 返回 runtime session id、profile id、lease expires、status。
- `GET /api/runtime/sessions/{id}` 返回已创建 session。
- 如果 profile 未运行，创建 session 时调用 `browser_mgr.launch(profile)`。
- template 创建路径会先创建 profile，再启动 profile。
- response 不包含 `wallet`、`order`、`billing` 字段。

只读子 agent 审计结论：

- 建议新增 `RUNTIME_SERVICE_TOKEN = os.environ.get("RUNTIME_SERVICE_TOKEN") or None`，不要复用 UI `AUTH_TOKEN`。
- Header 建议 `X-Runtime-Service-Token`，避免和 `Authorization: Bearer <AUTH_TOKEN>` 混淆。
- 如果 `AUTH_TOKEN` 启用，`AuthMiddleware` 需要允许 `/api/runtime/*` 交给 runtime service token 自己鉴权，否则 service token 请求会被 UI auth 先拦截。
- `runtime_sessions` 表字段按 05 文档：
  - `id`
  - `profile_id`
  - `external_session_id`
  - `status`
  - `lease_expires_at`
  - `viewer_token_hash`
  - `created_at`
  - `updated_at`
- 建议沿用 `database.py` 的 `get_db()`、`init_db()`、`_now()`、`uuid.uuid4()` 风格。

当时下一会话建议第一步：

```bash
cd /home/jeff/code/cloakbrowser-invisible-manager
git status --short --branch
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
```

当时预期：

- `git status` 会看到 `backend/tests/test_session_broker.py` 以及文档/根目录 goal prompt 交接改动。
- pytest 预期红灯，因为 runtime session API 尚未实现。

当时实现边界：

- 只做 CloakBrowser 侧最小 runtime session API。
- 不改 Project Mileage app/payload。
- 不做钱包、订单、用户权限判断。
- 不让 Project Mileage 前端绕过 Payload 直接访问 CloakBrowser runtime service API。
- viewer token、terminate、renew、audit、Payload 授权扣费联动留给后续小闭环。

## 69. 2026-05-27 CloakBrowser 侧最小 runtime session API 小闭环

背景：

- 用户要求完成 05 的当前小闭环后更新 session memory、运行后端验证和 `git diff --check`，提交 CloakBrowser 仓库 commit，但不要 push。
- 明确要求“全完则不要勾选 05”：本轮只完成 05 的最小 runtime session API，不代表 viewer token、terminate、renew、audit 和 Payload 联动完成，因此 `tasks/progress.md` 顶层 05 保持未勾选。

已完成：

- 保留并运行 `backend/tests/test_session_broker.py`，确认初始红灯：
  - `/api/runtime/sessions` 返回 `405`。
  - 4 个测试失败。
- `backend/models.py`
  - 新增 `RuntimeSessionCreate`。
  - 新增 `RuntimeSessionResponse`。
  - 校验 `profile_id` 与 `template_id` 必须且只能提供一个。
  - Runtime session API 响应不暴露内部 `viewer_token_hash`。
- `backend/database.py`
  - 新增 `runtime_sessions` 表。
  - 新增 `create_runtime_session()`。
  - 新增 `get_runtime_session()`。
- `backend/main.py`
  - 新增 `RUNTIME_SERVICE_TOKEN`。
  - `AuthMiddleware` 对 `/api/runtime/*` 放行到 runtime service token 自身鉴权，避免 UI `AUTH_TOKEN` 抢先拦截。
  - 新增 `POST /api/runtime/sessions`。
  - 新增 `GET /api/runtime/sessions/{session_id}`。
  - 从 `template_id` 创建 runtime profile 时复制 template 指纹字段，并命名为 `Runtime <external_session_id>`。
  - 创建 runtime session 时如果 profile 未运行，会调用 `browser_mgr.launch(profile)`。
- `docs/ai-docs/v1/tasks/05-session-broker-project-mileage.md`
  - 勾选已实际完成的 service token、`POST`、`GET`、runtime session 表、创建时启动 profile、无 service token 拒绝、Runtime session 不包含钱包逻辑。
  - 追加本轮验证记录。
- `docs/ai-docs/v1/tasks/progress.md`
  - 记录 05 最小 runtime session API 已完成。
  - 顶层 `05 Project Mileage 会话 Broker` 仍保持未勾选。
- `docs/ai-docs/v1/2026-05-25-fingerprint-health-ops-plan.md`
  - 更新当前接力状态，移除过期“红灯未实现”描述。
- `docs/ai-docs/v1/goal-prompt.md`
  - 更新为 2026-05-27 接力状态。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 262 passed

git diff --check
# passed
```

仍未完成：

- `POST /api/runtime/sessions/{id}/viewer-token`。
- `POST /api/runtime/sessions/{id}/terminate`。
- `POST /api/runtime/sessions/{id}/renew`。
- runtime audit。
- viewer token 到期、session 终止后的 VNC 访问失效。
- Project Mileage Payload 侧授权、扣费、续期后调用 runtime API。

边界：

- 没有修改 Project Mileage app/payload。
- 没有把钱包、订单、用户权限判断写入 CloakBrowser。
- 没有让 Project Mileage 前端绕过 Payload 直接访问 CloakBrowser runtime service API。
