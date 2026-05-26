# 03 Profile 运营台

## 目标

把首页从简单 sidebar + 表单升级为多 profile 运营台，让用户一眼看到账号池状态，并能进行筛选、排序、多选和批量操作。

## 主要文件

预计修改：

- `frontend/src/App.tsx`
- `frontend/src/components/ProfileList.tsx`
- `frontend/src/components/ProfileForm.tsx`
- `frontend/src/hooks/useProfiles.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/styles/globals.css`

预计新增：

- `frontend/src/components/ProfileTable.tsx`
- `frontend/src/components/ProfileFilters.tsx`
- `frontend/src/components/BulkActionBar.tsx`
- `frontend/src/components/ProfileSummaryPanel.tsx`
- `frontend/src/lib/filters.ts`
- `frontend/src/components/*.test.tsx`

## 任务清单

- [x] 定义运营台布局：
  - top bar。
  - left filter rail。
  - main profile table。
  - right summary panel。
- [x] 新增 `ProfileTable`：
  - select。
  - name。
  - status。
  - health。
  - proxy。
  - IP。
  - country。
  - timezone。
  - locale。
  - tags。
  - last checked。
  - actions。
- [x] 新增 `ProfileFilters`：
  - search。
  - status。
  - health。
  - proxy exists。
  - country。
  - tag。
- [x] 新增排序：
  - name。
  - status。
  - health。
  - country。
  - last_geoip_resolved_at。
- [x] 左侧 `ProfileList` 大列表虚拟滚动。
- [x] 主区 `ProfileTable` 大列表虚拟滚动。
- [x] 新增多选状态。
- [x] 新增 `BulkActionBar`。
- [x] 接入批量 launch。
- [x] 接入批量 stop。
- [x] 接入批量 health check。
- [x] 接入批量 set tags。
- [x] 接入批量 delete，必须有确认。
- [x] 新增 `ProfileSummaryPanel`：
  - health。
  - runtime。
  - GeoIP。
  - manual override。
  - proxy。
  - device。
  - quick actions。
- [x] 保留创建/编辑 profile 能力。
- [x] 保留 VNC viewer 能力。
- [x] 空态拆分：
  - 无 profile。
  - 筛选无结果。
  - health 未检测。
- [x] 窄屏降级为 card list。

## 验证命令

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 浏览器验收

- [x] 1440px 显示 dense table。
- [x] 768px 表格不溢出。
- [x] 375px 显示 card 模式或可用横向滚动。
- [x] 批量选择后 action bar 不遮挡主要操作。
- [x] 长 proxy、长 tag、长 profile name 不撑破布局。

## 2026-05-26 列表筛选与排序小闭环

已完成：

- 新增 `frontend/src/lib/filters.ts`：
  - `ProfileFilterState`
  - `defaultProfileFilters`
  - `filterAndSortProfiles()`
  - `getProfileFilterOptions()`
- 新增 `frontend/src/components/ProfileFilters.tsx`，在现有 sidebar/list header 内提供紧凑筛选控件。
- 支持筛选：
  - profile name search。
  - runtime status。
  - health status。
  - proxy exists。
  - country。
  - tag。
- 支持排序：
  - risk first（默认，`error -> warning -> unknown -> good`）。
  - last checked。
  - name。
  - runtime。
  - country。
- `last checked` 语义：
  - 优先使用 `health.checked_at`。
  - 若无 health，则 fallback 到 `profile.last_geoip_resolved_at`。
  - 缺失值稳定排到末尾。
- 搜索仍只匹配 profile name，不把 health 中文状态、tag 或 GeoIP 文案纳入 search。
- 选择筛选后的 profile、点击 `New Profile` 仍保持原有流程。

验证：

```bash
cd frontend && npm test -- --run src/lib/filters.test.ts src/components/ProfileFilters.test.tsx src/components/ProfileList.test.tsx
# 3 passed, 11 passed

cd frontend && npm test -- --run
# 8 passed, 41 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 后端使用临时 QA 数据目录 `/tmp/cloakbrowser-manager-qa-data`。
- Vite dev server：`http://127.0.0.1:5173/`。
- 使用 `agent-browser` 走查：
  - 桌面视口 `1440x900`。
  - 移动视口 `390x844`。
  - 默认风险排序显示 `不可用 -> 需关注 -> 未检测 -> 可继续`。
  - health 过滤 `不可用` 后只显示 invalid proxy profile。
  - proxy 过滤 `With proxy` 后只显示带 proxy profile。
  - country 过滤 `US` 后只显示有 US GeoIP 的 profile。
  - 搜索 `Good` 后只显示 `QA Good Health`。
  - 点击筛选结果能进入编辑页，`Launch` 按钮仍可见。
  - 点击 `New Profile` 能进入创建页。
  - 控制台无相关应用错误。

范围说明：

- 本小闭环没有新增多选、批量操作或完整 `ProfileTable`，避免把当前 `selectedId` 编辑对象和后续批量选择集合混在一起。
- 后续继续 03 时，应基于 `filters.ts` 迁移到 dense table / card list，而不是重写筛选规则。

## 2026-05-26 只读 ProfileTable 主区小闭环

已完成：

- [x] 新增 `frontend/src/components/ProfileTable.tsx`，作为 `view === "empty"` 的主区 dense table。
- [x] 表格展示 profile、runtime、health、proxy、IP、country、timezone、locale、tags、last checked、actions。
- [x] 表格 `Open` action 复用现有 `onSelect(profile.id)`，进入原有 edit / VNC viewer 流。
- [x] `AppContent` 上提 `ProfileFilterState`，让 sidebar list 和 main table 共享同一组筛选、排序结果。
- [x] `ProfileTable` 只消费传入 rows，不在组件内二次默认排序，避免覆盖用户选择的排序方式。
- [x] proxy 列显示可诊断但不暴露账号密码的标签：有效 URL 显示 `protocol//host`，无效 URL 显示 `Invalid proxy`；可见文本与 `title` 都不保留 proxy 凭据。
- [x] 窄屏初始收起 sidebar，让 390px 视口优先显示主表格；用户仍可通过 top bar 按钮打开筛选 sidebar。
- [x] 新增 `frontend/src/App.test.tsx`，覆盖 sidebar 筛选/排序同步主表格，以及窄屏默认收起 sidebar。
- [x] 新增 `frontend/src/components/ProfileTable.test.tsx`，覆盖 dense columns、传入顺序、open action 和筛选空态。

验证：

```bash
cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileTable.test.tsx src/components/ProfileList.test.tsx
# 3 passed, 13 passed

cd frontend && npm test -- --run
# 10 passed, 49 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 后端继续使用临时 QA 数据目录 `/tmp/cloakbrowser-manager-qa-data`。
- Vite dev server：`http://127.0.0.1:5173/`。
- 使用 `agent-browser`；当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox` 才能启动浏览器。
- 桌面 `1440x900`：
  - dense table 可见。
  - 默认风险排序为 `不可用 -> 需关注 -> 未检测 -> 可继续`。
  - proxy 列对无效 proxy 显示 `Invalid proxy`，有效 proxy 只显示 `protocol//host`，可见文本和 `title` 均不暴露账号密码。
- 平板 `768x900`：
  - 页面 body 没有横向撑破。
  - table 在主区内横向滚动，sidebar 不挤破页面。
- 移动 `390x844`：
  - 初始 sidebar 收起，主表格占满首屏。
  - 点击 top bar sidebar 按钮后，筛选 sidebar 可打开。
  - 主表格仍可横向滚动。
- 交互：
  - sidebar 选择 `Sort profiles = Name` 后，主表格同步按名称排序。
  - sidebar 选择 `Health status = 不可用` 后，主表格只显示 invalid proxy profile。
  - 点击表格 `Open QA Invalid Proxy` 进入原有编辑表单，`Launch` 按钮、`Delete`、`Cancel`、`Save` 仍可见。
  - 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。

范围说明：

- 本小闭环仍不实现多选 checkbox、批量 action bar、批量 launch/stop/delete/health check、右侧 summary panel 或 card list。
- 顶层 `新增 ProfileTable` 在后续多选状态小闭环完成后再统一勾选。

## 2026-05-26 ProfileTable 多选状态小闭环

已完成：

- [x] `ProfileTable` 新增 `Select` 列。
- [x] 每行新增 profile checkbox，点击只切换多选状态，不触发 `Open`。
- [x] 表头新增 `Select all visible profiles` checkbox，只作用当前筛选后的可见 rows。
- [x] 表头 checkbox 支持半选态。
- [x] `AppContent` 新增独立 `selectedProfileIds`，和现有 `selectedId` / `view` 详情流分离。
- [x] 筛选后隐藏的已选 profile 会自动清理，避免后续批量动作误作用到不可见 rows。
- [x] 选择后显示轻量选择条：`N selected` + `Clear`。
- [x] 空表格 `colSpan` 已随 Select 列更新。

验证：

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
- 使用 `agent-browser`，当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
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

## 2026-05-26 左侧 ProfileList 虚拟滚动小闭环

背景：

- Jeff 反馈：几百个 profile 时，左侧列表全量渲染会卡顿。
- 本小闭环只优化左侧 `ProfileList` 渲染数量，不改 API，不做服务端分页，不改筛选/排序语义。

已完成：

- [x] `ProfileList` 在过滤结果超过 80 条时启用无依赖固定高度虚拟窗口。
- [x] 列表项高度收敛为 112px，左侧列表继续定位为导航/扫视区；长 warning、GeoIP、tag 仍截断，完整信息继续在主表格或详情里查看。
- [x] 虚拟窗口包含 overscan，减少滚动时的空白感。
- [x] 筛选条件变化后重置左侧列表滚动位置，避免筛选后停留在旧滚动区导致空白窗口。
- [x] 虚拟窗口起点做边界 clamp，列表数量从多变少时不会越界。
- [x] `New Profile` 按钮仍固定在左侧底部，不受虚拟滚动影响。
- [x] 选择 profile 仍按 `profile.id` 调用 `onSelect`。

验证：

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
- 使用 `agent-browser`，当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
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

## 2026-05-26 主区 ProfileTable 虚拟滚动小闭环

背景：

- 左侧 `ProfileList` 已完成大列表虚拟滚动，但主区 `ProfileTable` 仍会全量渲染过滤结果。
- Jeff 进一步确认信息架构方向：运营台应以主区域表格、搜索筛选和批量操作为核心；左侧只应逐步降级为最近、分组、快捷入口和性能兜底。

已完成：

- [x] `ProfileTable` 在过滤结果超过 120 条时启用固定行高虚拟窗口。
- [x] 保留原生 `table` / `thead` / `tbody` / `tr` 语义，用顶部和底部 spacer row 撑出总高度。
- [x] 表格行高度收敛为 64px，tag 区域限制最大高度，避免长 tag 撑破虚拟滚动估算。
- [x] 虚拟窗口包含 overscan，减少滚动时的空白感。
- [x] `Profile operations table` 成为主表滚动根，sticky 选择条和 sticky 表头仍在同一容器内工作。
- [x] 筛选结果变化后重置主表滚动位置，避免从大列表中段切到少量结果时出现空白窗口。
- [x] 表头 `Select all visible profiles` 继续作用于当前筛选后的全部 rows，而不是当前虚拟窗口 rows。
- [x] 滚动后可见行的 checkbox 和 `Open` action 仍按正确 profile id 工作。
- [x] proxy 列继续只显示脱敏后的 `protocol//host` 或 `Invalid proxy`，不暴露 proxy 凭据。

验证：

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
  - 主表 `scrollHeight` 正常增大，滚动条可用。
  - 滚动到中段后 `Perf Table Profile 120` 出现在主表窗口内，`Perf Table Profile 000` 不在主表 DOM 内。
  - 点击 `Select Perf Table Profile 120` 后显示 `1 selected`。
  - 点击表头 `Select all visible profiles` 后显示 `240 selected`，证明全选语义仍是当前筛选结果全集。
  - 搜索 `239` 后主表回到顶部，只显示 `Perf Table Profile 239`，没有旧虚拟窗口残留。
- 移动 `390x844`：
  - 刷新后 sidebar 默认收起。
  - 主表仍只渲染窗口内行。
  - `body.scrollWidth === viewportWidth`，页面本体没有横向撑破。
  - 主表自身保留横向滚动，`scrollWidth` 为 1040，`scrollLeft` 可移动到右侧列。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。
- 截图保存到：
  - `/tmp/cloak-profile-table-virtualized-desktop.png`
  - `/tmp/cloak-profile-table-virtualized-mobile.png`
  - `/tmp/cloak-profile-table-virtualized-mobile-initial.png`

范围说明：

- 本小闭环不引入 `react-window` 或 `@tanstack/react-virtual`；当前固定行高表格足以覆盖数百到低千级 profile。
- 本小闭环不做服务端分页。服务端分页应等批量操作、全选筛选结果和服务端排序/筛选契约稳定后再进入。
- 左侧虚拟滚动方向不撤销，但产品定位应从“全量 profile 管理入口”逐步调整为最近、分组、收藏、状态快捷过滤和导航兜底。

## 2026-05-26 BulkActionBar 安全壳小闭环

背景：

- `ProfileTable` 已有多选状态和轻量 `N selected + Clear` 选择条。
- 本小闭环只把选择条升级为独立 `BulkActionBar` 组件，为后续批量动作提供稳定 UI 容器。
- 当前不接入任何批量 mutation，不伪造批量 launch / stop / health check / tag / delete 成功态。

已完成：

- [x] 新增 `frontend/src/components/BulkActionBar.tsx`。
- [x] `ProfileTable` 用 `BulkActionBar` 替换原 inline 选择条，保留 `sticky top-0` 和 40px 高度，避免破坏 sticky table header 的 `top-10` 偏移。
- [x] `BulkActionBar` 只消费受控 `selectedProfileIds` 派生出的 `selectedProfiles`，不持有选择状态。
- [x] 展示：
  - selected count。
  - running count。
  - stopped count。
  - issue count（`error` / `warning` health）。
  - `Clear`。
- [x] 预留 `Check health`、`Launch selected`、`Stop selected`、`Tag selected`、`Delete selected` 按钮，但全部 disabled，不调用 API。
- [x] 不展示 proxy、cookie、token 等敏感字段。

验证：

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
  - `body.scrollWidth === viewportWidth`，页面本体没有横向撑破。
  - 主表自身保留横向滚动，`scrollLeft` 可移动到右侧列。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。
- 截图保存到：
  - `/tmp/cloak-bulk-action-bar-desktop.png`
  - `/tmp/cloak-bulk-action-bar-mobile.png`

范围说明：

- 本小闭环只完成 `BulkActionBar` 容器和只读摘要。
- 不接入批量 launch / stop / health check / set tags / delete。
- 下一步建议优先接入批量 health check，因为它是最低风险真实批量动作；delete 仍必须单独确认闭环。

## 2026-05-26 Profile 运营台 UI/UE 质感小闭环

背景：

- Jeff 反馈当前前端整体质感偏低，运营台 UE 不够专业；本轮暂停继续堆功能，优先做 Profile 运营台 UI/UE 小闭环。
- 使用 `ui-ux-pro-max` 生成设计系统，推荐方向为 `Data-Dense Dashboard`，默认浅色 B2B 运营台，而不是继续加重深色开发面板。
- `/home/jeff/code/repo/sasskit` 不存在，实际参考目录为 `/home/jeff/code/reference-repos/saas_kit`；参考 `ai-shipany-template-two` 的 admin 截图、`ai-mksaas-template` 的 dashboard sidebar / users table / data-table toolbar。

已完成：

- [x] 将默认视觉从低质感深色面板切到浅色 B2B operations console：
  - `surface` / `border` / `accent` token 改为 slate + blue + low-noise surfaces。
  - body、按钮、输入、select、textarea、scrollbar、focus ring 调整为浅色可读体系。
- [x] 左侧从“全量 profile 长列表主入口”降级为 operations rail：
  - `All profiles`。
  - `Running profiles`。
  - `Stopped profiles`。
  - `Unavailable profiles`。
  - `Needs attention`。
  - `No proxy`。
  - quick views 直接写入现有 `ProfileFilterState`，不新增假状态。
- [x] 主区升级为运营台核心：
  - 顶部状态摘要。
  - 主区搜索、筛选、排序 toolbar。
  - 表格卡片 surface。
  - fixed column layout，1440px 桌面可直接看到 `Actions` 列。
- [x] 保留既有功能语义：
  - profile 创建 / 编辑 / 删除流。
  - 单 profile launch / stop。
  - VNC viewer。
  - `Open` 进入原详情 / VNC 流。
  - proxy 脱敏显示，不在 table 文本或 `title` 暴露凭据。
- [x] 保留既有性能语义：
  - 左侧 `ProfileList` 超过 80 条虚拟滚动。
  - 主区 `ProfileTable` 超过 120 条虚拟滚动。
  - 表头全选仍作用当前筛选结果全集，不局限于虚拟窗口。
  - 筛选变化后滚动回顶部。
- [x] 移动端 sidebar 改为 overlay 抽屉：
  - 初始窄屏仍默认收起 sidebar。
  - 主区搜索筛选仍可用。
  - 打开 sidebar 不再把 body 撑宽。
  - 主表自身保留横向滚动。
- [x] 新增 `frontend/src/App.test.tsx` 覆盖：
  - quick views 驱动主运营表格。
  - 窄屏 sidebar 收起时主区筛选仍可用。

验证：

```bash
cd frontend && npm test -- --run src/App.test.tsx src/components/ProfileList.test.tsx src/components/ProfileFilters.test.tsx src/components/ProfileTable.test.tsx
# 4 passed, 25 passed

cd frontend && npm test -- --run src/components/ProfileTable.test.tsx src/App.test.tsx
# 2 passed, 16 passed

cd frontend && npm test -- --run
# 10 passed, 59 passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-qa-data` 写入 240 个 profiles。
- 后端：`http://127.0.0.1:8080`。
- Vite dev server：`http://127.0.0.1:5173/`。
- 使用 `agent-browser`，当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 左侧 rail 显示 quick views，不再把全量 profile 列表作为唯一入口。
  - 主区显示状态摘要、搜索筛选 toolbar 和 dense table。
  - `Actions` 列在 1440px 桌面可见。
  - 点击 `Needs attention` 后 `Health status` select 同步为 `warning`，主表行数为 26。
  - 选择首行后显示 `Bulk profile actions`，`1 selected` 可见。
- 移动 `390x844`：
  - 初始 sidebar 收起。
  - 主区搜索筛选可用。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表横向滚动保留，`tableScrollWidth=1068`、`tableClientWidth=358`。
  - 打开 sidebar 后为 overlay 抽屉，body 仍不横向撑破。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。
- 截图保存到：
  - `/tmp/cloak-ui-refresh-desktop.png`
  - `/tmp/cloak-ui-refresh-quick-view.png`
  - `/tmp/cloak-ui-refresh-bulk.png`
  - `/tmp/cloak-ui-refresh-mobile.png`
  - `/tmp/cloak-ui-refresh-mobile-sidebar.png`

范围说明：

- 本小闭环不接入批量 launch / stop / health check / set tags / delete。
- 本小闭环不新增后端 API，不改变健康计算、筛选排序、虚拟滚动和 proxy 脱敏契约。
- 下一步继续 03 时，建议优先接入最低风险的批量 `health_check`；后续再考虑把 `Open` 从整页切换改为“表格 + 详情抽屉/右栏”的连续运营形态。

## 2026-05-26 ProfileSummaryPanel 右侧摘要小闭环

背景：

- 前一轮 UI/UE 质感升级已把信息架构调整为左侧 quick views + 主区运营表格，但右侧 summary panel 仍未接入。
- 本小闭环补齐 `Data-Dense + Drill-Down` 的右侧摘要，让数百 profile 场景下的主表格继续承担管理核心，右侧只做快速判断和下一步入口。

已完成：

- [x] 新增 `frontend/src/components/ProfileSummaryPanel.tsx`。
- [x] 新增 `frontend/src/lib/profileDisplay.ts`，复用 proxy 脱敏和 timestamp 格式化。
- [x] `AppContent` 新增独立 `previewProfileId`，不复用 `selectedId` / `view` / `selectedProfileIds`：
  - 点击表格 profile name 只更新右侧摘要。
  - 不触发 `LaunchButton`、编辑页或 VNC viewer。
  - 当前预览 profile 被筛选隐藏后，自动回到当前可见第一项；无结果时显示空摘要。
- [x] `ProfileSummaryPanel` 展示：
  - health。
  - runtime。
  - GeoIP。
  - manual override。
  - proxy。
  - device。
  - `Open profile` quick action。
- [x] `Open profile` 继续调用现有 `handleSelect()`，保留原有 edit / VNC 详情流。
- [x] 桌面布局调整为 `main table + 320px right summary panel`。
- [x] 窄屏下 summary panel 落在表格下方，不撑宽 body；主表仍保留自身横向滚动。
- [x] proxy 可见文本和 `title` 继续只显示 `protocol//host` 或 `Invalid proxy`，不泄露用户名/密码。
- [x] health warning 文本和 `title` 增加 proxy 凭据脱敏；后端 proxy 校验错误也不再返回 `user:password@host`。

验证：

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

浏览器 UI/UE 验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-qa-data` 写入 244 个 profiles。
- 后端：`http://127.0.0.1:8080`。
- Vite dev server：`http://127.0.0.1:5173/`。
- 使用 `agent-browser`，当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 默认显示主表格 + 右侧 `Profile summary`。
  - 搜索 `QA Summary` 后主表显示 3 个匹配 profile。
  - 点击 `Preview QA Summary Good` 后右侧 summary 更新为 `QA Summary Good`，主表格仍存在，未进入 `Edit Profile`。
  - 右侧 `Open profile` 进入原编辑流，`Edit Profile`、`Launch`、`Delete`、`Cancel`、`Save` 可见。
  - DOM 中未出现 `hiddenpass`，proxy 密码未泄露。
  - `QA Summary Secret Missing Port` 的后端 health warning 显示为 `Proxy URL missing port: http://proxy-secret.example`，DOM 中未出现 `hiddenpass` 或 `user:hiddenpass`。
- 移动 `390x844`：
  - 搜索和主表可用。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身保留横向滚动，`tableScrollWidth=1068`、`tableClientWidth=358`。
  - summary panel 在表格下方可滚动查看，不遮挡表格操作。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。
- 截图保存到：
  - `/tmp/cloak-summary-panel-desktop.png`
  - `/tmp/cloak-summary-panel-preview.png`
  - `/tmp/cloak-summary-panel-mobile.png`
  - `/tmp/cloak-summary-panel-mobile-summary.png`
  - `/tmp/cloak-summary-panel-secret-redaction.png`

范围说明：

- 本小闭环不接入批量 launch / stop / health check / set tags / delete。
- 本小闭环不新增后端 API，不改变健康计算、筛选排序、虚拟滚动、批量选择和 proxy 脱敏契约。
- 下一步继续 03 时，推荐优先接入最低风险的批量 `health_check`，再做批量 launch/stop；批量 delete 必须单独确认闭环。

## 2026-05-26 Profile 运营台 IA/视觉二次收口与批量 health check 小闭环

背景：

- Jeff 反馈当前前端整体质感仍偏低，运营台 UE 需要从“继续堆功能”切换到“先把 Profile 管理体验打磨到专业运营台”。
- 本轮使用 `ui-ux-pro-max` 生成 B2B SaaS operations dashboard 设计方向，并审阅 `/home/jeff/code/reference-repos/saas_kit`。用户给出的 `/home/jeff/code/repo/sasskit` 在本机不存在，实际参考目录为 `reference-repos/saas_kit`。
- 参考结论：采用浅色、低噪声、data-dense B2B 运营台；借鉴 `ai-mksaas-template` 的数据表格/toolbar 方向和 `ai-supastarter-template` 的 app shell 克制感，不采用营销 hero、大面积渐变或紫色官网风格。

已完成：

- [x] 左侧从“全量 profile 管理主入口”进一步收敛为 operations rail：
  - `Quick views` 文案调整为 `Saved views`。
  - `Matching profiles / virtualized` 调整为 `Profile shortcuts / filtered`，移除实现味文案。
  - 保留左侧列表虚拟滚动和选择能力，但定位为快捷入口和兜底导航。
- [x] 主区成为核心运营台：
  - 顶部增加主操作 `New Profile`。
  - 主区拆成标题/指标 strip、筛选 toolbar、表格 + inspector。
  - 主筛选 toolbar 增加可见短标签：`Search / Runtime / Health / Proxy / Country / Tag / Sort`。
  - 桌面 rail 从 280px 收敛到 264px，右侧 inspector 从 320px 收敛到 280px。
  - 主表 `min-width` 从 1068px 收敛到 840px，1440px 桌面可直接看到 `Actions` 列。
- [x] 表格视觉和交互细节收口：
  - 行、表头、checkbox、preview button、open button 的 hover/focus 状态更清楚。
  - 表格列继续保留 profile、runtime、health、proxy、IP、country、timezone、locale、tags、last checked、actions。
  - 保留主区 `ProfileTable` 超过 120 条虚拟滚动，表头全选仍作用当前筛选结果全集。
- [x] 右侧 summary 改成 inspector 风格：
  - header 使用轻背景，`Open profile` 为主按钮。
  - section 使用 divider 分隔，减少卡片套卡片感。
  - 保留 health、runtime、GeoIP、manual override、proxy、device 信息。
- [x] `BulkActionBar` 的 `Check health` 接入真实批量健康检测：
  - 复用已有 `api.checkProfileHealth(id)`。
  - 不新增后端 bulk API。
  - `useProfiles.checkHealth(ids)` 做去重、过滤空 id、最多 6 并发。
  - 成功项写入 `healthByProfileId`，失败项不清空旧 health。
  - 部分失败时设置 `Failed to check health for N profile(s)`。
  - `Launch selected`、`Stop selected`、`Tag selected`、`Delete selected` 继续 disabled，不伪造能力。

保留语义：

- profile 创建 / 编辑 / 删除流保留。
- 单 profile launch / stop / VNC viewer 流保留。
- 表格 profile name 仍只做 preview，不进入编辑或 viewer。
- `Open` 和右侧 `Open profile` 仍走原 `handleSelect()`。
- 筛选、排序、多选、全选当前过滤结果、筛选后清理不可见选择语义保留。
- proxy 可见文本、`title` 和 health warning 继续脱敏，不暴露用户名/密码。

验证：

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

浏览器 UI/UE 验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-ui-qa-data`，共 180 个 profiles。
- 后端：`http://127.0.0.1:8080`。
- Vite dev server：`http://127.0.0.1:5173/`。
- 使用 `agent-browser`，当前 Linux 环境需要 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 主区显示标题/指标 strip、带可见标签的筛选 toolbar、dense table 和右侧 inspector。
  - 左侧显示 `Saved views` 和 `Profile shortcuts`，不再出现 `virtualized` 实现文案。
  - 主表 `Actions` 列可直接看到，不需要先横向滚动。
  - 选择首行后显示 `Bulk profile actions`，`Check health` 可点击，其他批量动作仍 disabled。
  - 点击 `Check health` 后该 profile health 重新检测，summary `Last checked` 更新时间。
- 移动 `390x844`：
  - 初始 sidebar 收起，主区筛选可用。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身横向滚动，`tableScrollWidth=840`、`tableClientWidth=352`。
  - 打开 sidebar 后为 overlay 抽屉，body 不横向撑破。
- 控制台无相关应用错误，仅有 Vite debug 与 React DevTools info。
- 截图保存到：
  - `/tmp/cloak-ui-ue-refresh-desktop-compact.png`
  - `/tmp/cloak-ui-ue-refresh-bulk-selected.png`
  - `/tmp/cloak-ui-ue-refresh-bulk-checked.png`
  - `/tmp/cloak-ui-ue-refresh-mobile.png`
  - `/tmp/cloak-ui-ue-refresh-mobile-sidebar.png`

范围说明：

- 本小闭环没有接入批量 launch / stop / set tags / delete。
- 本小闭环没有做服务端分页；当前固定行高虚拟滚动覆盖数百 profile 场景。
- 下一步继续 03 时，建议做“保留创建/编辑 profile 能力”的运营台内连续体验复核，或进入批量 launch/stop 的资源并发设计。

## 2026-05-26 批量 launch 小闭环

背景：

- `BulkActionBar` 已经接入批量 health check，本小闭环继续接入批量 launch。
- 不新增后端 bulk API，前端复用现有单 profile `/api/profiles/{id}/launch`，避免扩大运行时契约面。
- 批量 launch 只作用当前选中且 `status === "stopped"` 的 profiles；running profiles 跳过，不触发 409。

已完成：

- [x] `frontend/src/hooks/useProfiles.ts` 新增 `launchProfiles(ids)`：
  - 去重、过滤空 id。
  - 基于当前 profile 列表只启动 stopped profiles。
  - 最多 2 并发，降低多实例启动时的运行时资源冲击。
  - 每个 profile 复用现有 `api.launchProfile(id)`。
  - 批量完成后统一 `refresh()` 一次，成功项再刷新 health。
  - 部分失败不阻断其他 profile。
  - 失败提示包含去重后的后端错误摘要，并通过 `redactUrlCredentials()` 防御性脱敏。
  - 后台列表 refresh 成功不会清掉用户操作错误，避免失败 banner 只闪一下。
- [x] `BulkActionBar` 的 `Launch selected` 变为真实动作：
  - 仅在有 stopped 选中项时启用。
  - 执行中显示 `Launching...` 并禁用按钮。
  - `Stop selected`、`Tag selected`、`Delete selected` 仍保持 disabled。
- [x] `ProfileTable` 只把 selected 中 stopped profiles 传给 launch handler。
- [x] `AppContent` 接入 `bulkLaunching` 状态，不改变单 profile launch / stop / VNC viewer 流。

验证：

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

浏览器 UI/UE 验证：

- 临时 QA 数据库 `/tmp/cloakbrowser-manager-bulk-launch-qa-data`，共 2 个 stopped/headless/no-proxy profiles：
  - `Bulk Launch QA A`
  - `Bulk Launch QA B`
- 后端 `http://127.0.0.1:8080`，Vite `http://127.0.0.1:5173/`。
- 使用 `agent-browser`，环境变量 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 选中两个 stopped profiles 后显示 `2 selected`、`0 running`、`2 stopped`。
  - `Launch selected` 可点击。
  - 点击后前端发起批量 launch，后端日志显示两个 profile 都尝试启动。
  - 当前本机环境没有 `Xvnc`，后端返回 `500 {"detail":"Failed to launch browser"}`，profile 仍为 `stopped`。
  - 前端显示 `Failed to launch 2 profile(s): Failed to launch browser`。
  - 等待 3.5 秒后台轮询后，失败 banner 仍保持可见，没有被 `refresh()` 清掉。
  - 清空 console 后重跑当前流程，无相关前端 console error。
- 移动 `390x844`：
  - 失败 banner 可见。
  - `body.scrollWidth === window.innerWidth === 390`，页面本体不横向撑破。

截图：

- `/tmp/cloak-bulk-launch-error-persist-desktop.png`
- `/tmp/cloak-bulk-launch-error-persist-mobile.png`
- 早期定位截图：
  - `/tmp/cloak-bulk-launch-before.png`
  - `/tmp/cloak-bulk-launch-selected.png`
  - `/tmp/cloak-bulk-launch-after-click.png`

运行时限制：

- 本机 `command -v Xvnc` 为空，仅有 `/usr/bin/firefox`。
- 因此本轮无法在本机直接验证 profile 进入 `running` / VNC 可连状态。
- Dockerfile 的生产镜像会安装 KasmVNC；真实 running 状态建议在容器环境或安装 `Xvnc` 的运行时环境补验。

范围说明：

- 本小闭环不新增后端 bulk launch API。
- 本小闭环不接入批量 stop / set tags / delete。
- 批量 delete 仍必须单独确认闭环；批量 stop 需要下一轮定义 running-only、部分失败和选择保留语义。

## 2026-05-26 批量 stop 小闭环

背景：

- `BulkActionBar` 已经接入批量 health check 和批量 launch，本小闭环继续接入批量 stop。
- 不新增后端 bulk API，前端复用现有单 profile `/api/profiles/{id}/stop`。
- 后端对非 running profile 的 stop 返回 404 `Profile is not running`，所以前端批量 stop 必须只作用当前选中且 `status === "running"` 的 profiles；stopped profiles 跳过，不作为错误。

已完成：

- [x] `frontend/src/hooks/useProfiles.ts` 新增 `stopProfiles(ids)`：
  - 去重、过滤空 id。
  - 基于当前 profile 列表只 stop running profiles。
  - stopped profiles 计入 `skippedStoppedCount`，不打 API。
  - 最多 2 并发，避免批量 teardown 过度冲击运行时。
  - 每个 profile 复用现有 `api.stopProfile(id)`。
  - 批量完成后统一 `refresh()` 一次，成功项再刷新 health。
  - 部分失败不阻断其他 profile。
  - 失败提示包含去重后的后端错误摘要，并通过 `redactUrlCredentials()` 统一防御性脱敏。
- [x] `BulkActionBar` 的 `Stop selected` 变为真实动作：
  - 仅在有 running 选中项时启用。
  - 执行中显示 `Stopping...` 并禁用按钮。
  - `Tag selected`、`Delete selected` 仍保持 disabled。
- [x] `ProfileTable` 只把 selected 中 running profiles 传给 stop handler。
- [x] `AppContent` 接入 `bulkStopping` 状态，不改变单 profile launch / stop / VNC viewer 流。
- [x] 操作后不主动清空选择；在 All 视图下保留选择，方便继续 tag/delete/health check；在过滤视图中仍由既有筛选清理 effect 剪掉不可见选择。

验证：

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

浏览器 UI/UE 验证：

- 当前本机缺 `Xvnc`，不能通过真实 launch 构造 running profile。
- 本轮使用临时 QA 后端在 8081 端口 monkeypatch `browser_mgr.running` 和 `browser_mgr.stop()`，只模拟 running profile 与 stop API 成功；前端通过 5174 静态代理访问该 QA 后端。
- 临时 QA 数据库 `/tmp/cloakbrowser-manager-bulk-stop-qa-data`，共 2 个 profiles：
  - `Bulk Stop QA Running`，初始 `status=running`，`vnc_ws_port=6100`。
  - `Bulk Stop QA Stopped`，初始 `status=stopped`。
- 桌面 `1440x900`：
  - 选中 running + stopped 后显示 `2 selected`、`1 running`、`1 stopped`。
  - `Stop selected` 可点击，`Tag selected` / `Delete selected` 仍 disabled。
  - 点击后 API status 变为 `running_count: 0`。
  - 表格中 `Bulk Stop QA Running` 从 `running` 变为 `stopped`。
  - toolbar 保留 `2 selected`，显示 `0 running`、`2 stopped`，`Stop selected` 变 disabled。
  - 清空 console 后重跑当前流程，无相关前端 console error。
- 移动 `390x844`：
  - 停止后状态可见。
  - `body.scrollWidth === window.innerWidth === 390`，页面本体不横向撑破。

截图：

- `/tmp/cloak-bulk-stop-selected-desktop.png`
- `/tmp/cloak-bulk-stop-after-desktop.png`
- `/tmp/cloak-bulk-stop-after-mobile.png`

运行时限制：

- 本轮浏览器验证没有覆盖真实 XvNC / KasmVNC teardown、真实 noVNC websocket 断开、真实 `browser_mgr.running` 清理后的 VNC 进程退出。
- 真实运行时 stop 语义仍由后端测试覆盖；完整端到端需要在安装 `Xvnc` 或 Docker/KasmVNC 环境补验。

范围说明：

- 本小闭环不新增后端 bulk stop API。
- 本小闭环不接入批量 set tags / delete。
- 批量 delete 仍必须单独确认闭环。

## 2026-05-26 Profile 运营台控件质感 UI polish 小闭环

背景：

- Jeff 反馈当前界面质感和细节还不够，复选框等控件显得 low。
- 本轮继续使用 `ui-ux-pro-max` / frontend design 方向做高质感 polish，但不破坏既有真实功能、测试、性能语义和虚拟滚动。
- 参考 `/home/jeff/code/reference-repos/saas_kit` 的 B2B SaaS app shell / data table 视觉规律，只吸收低噪声 surface、ring、shadow、table row 和 checkbox 处理方式；没有复制其业务/auth/db/payment/schema。

设计判断：

- 当前 low 的主要原因不是信息架构，而是控件细节：
  - 原生 checkbox 视觉不稳定，indeterminate 态质感弱。
  - bulk toolbar 过蓝，所有按钮同权，状态层级抢表格主体注意力。
  - table row 只靠大面积背景色表达 selected / previewed，缺少精细状态线。
  - toolbar filter 与 inspector surface 细节偏普通，边框和阴影层级不够。
- 本轮视觉方向保持数据密集 B2B 运营台：
  - 白底 + slate/blue 主体系。
  - subtle ring / hairline shadow。
  - amber/red 只用于风险与高风险语义。
  - 不引入炫技动效，不做 marketing dashboard。

已完成：

- [x] `SelectionCheckbox` 改为自定义视觉层 + 真实 `input[type=checkbox]`：
  - 保留 `aria-label`、`checked`、`disabled`、indeterminate。
  - 半选态增加 `aria-checked="mixed"`。
  - checked / mixed 使用稳定蓝色填充和 lucide `Check` / `Minus`。
  - focus-visible ring 保留键盘可见状态。
- [x] `BulkActionBar` 质感升级：
  - 从整条强蓝提示改为 neutral contextual toolbar。
  - `selected count`、runtime/issue summary pill 降低噪声。
  - `Check health` 保持真实可用并作为主动作。
  - `Launch selected` / `Stop selected` 仍按 selected 中 stopped/running profiles 启用。
  - `Tag selected`、`Delete selected` 保持 disabled。
  - 按钮 `whitespace-nowrap`，避免桌面窄表格下文字折行。
- [x] `ProfileTable` row polish：
  - selected row 加左侧 blue indicator。
  - previewed row 加较弱 slate indicator。
  - hover / selected 背景降低饱和度，减少和 health badge 抢层级。
  - 表头改为低噪声 sticky header，不改变 `top-11/top-0` 语义。
- [x] `ProfileFilters` toolbar polish：
  - 搜索框更强主控感。
  - filter select 使用 compact border/ring/hover/focus 状态。
- [x] `ProfileSummaryPanel` inspector polish：
  - header surface 更轻。
  - `Open profile` 从强 primary 改为 secondary action，避免压过 health/runtime 信息。
  - section icon 增加小型 icon container，row 信息层级更清晰。
- [x] 测试补充：
  - header checkbox 半选 `indeterminate` 和 `aria-checked="mixed"`。
  - 有 selection handler 时 checkbox input 可聚焦。
  - 无 selection handler 时 checkbox input disabled。

保持不变的语义：

- 主表 `min-w-[840px]` 与自身横向滚动保留。
- 移动端 body 不横向撑破。
- `Actions` 列在桌面可见，移动端可通过表格横向滚动访问。
- `Check health` 真实可用。
- `Launch selected` / `Stop selected` 已完成的真实批量动作保留。
- `Tag selected` / `Delete selected` 继续 disabled。
- 主表超过 120 条仍用固定 64px 行高虚拟滚动。
- 左侧列表超过 80 条仍用固定 112px item 虚拟滚动。
- proxy visible text / title 仍不暴露凭据。

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

浏览器 UI/UE 验证：

- 使用临时 QA 数据目录 `/tmp/cloakbrowser-manager-ui-polish-data`，共 240 个 profiles。
- 后端 QA 端口：`http://127.0.0.1:8082`。
- 静态前端代理端口：`http://127.0.0.1:5175/`。
- 使用 `agent-browser`，环境变量 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 首屏显示 operations rail、summary tiles、toolbar、主表和 inspector。
  - `Actions` 列直接可见。
  - 选中首行后 `Bulk profile actions` 可见，checkbox checked/mixed 视觉稳定。
  - `Check health` 可点击，`Tag selected` / `Delete selected` disabled。
  - 点击 `Check health` 后首行 `Last checked` 更新时间，选择仍保留。
  - 主表滚动到中段后只渲染窗口内约 26 个 Open 按钮，表格区域不包含顶部行，虚拟滚动语义保持。
- 移动 `390x844`：
  - 初始 sidebar 收起。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身横向滚动，`table.scrollWidth=840`、`table.clientWidth=352`。
  - 横向滚到右侧后 `Actions` / `Open` 可见。
  - 打开 sidebar 后为 overlay，body 仍不横向撑破。
- 清空 console 后无相关前端 console error。

截图：

- `/tmp/cloak-profile-polish-desktop.png`
- `/tmp/cloak-profile-polish-bulk-selected.png`
- `/tmp/cloak-profile-polish-bulk-checked.png`
- `/tmp/cloak-profile-polish-mobile.png`
- `/tmp/cloak-profile-polish-mobile-table-actions.png`
- `/tmp/cloak-profile-polish-mobile-sidebar.png`
- `/tmp/cloak-profile-polish-virtual-scroll.png`

范围说明：

- 本小闭环不接入批量 set tags / delete。
- 本小闭环不做服务端分页。
- 本小闭环不把 Profile 详情/VNC viewer 改成抽屉式连续运营形态。
- 本小闭环不做窄屏 card list；移动端继续采用 table 自身横向滚动。

## 2026-05-26 批量 set tags 与控件 polish 收口小闭环

背景：

- Jeff 继续反馈：当前界面质感和细节还不够，复选框等控件显得 low。
- 上一轮 UI polish 后，`Tag selected` 仍是预留动作；本轮把它接成真实批量 set tags，同时继续压实 checkbox / bulk action / table row / toolbar / inspector 的高质感细节。
- 继续参考 `/home/jeff/code/reference-repos/saas_kit` 的 B2B SaaS app shell / data table 设计思想；没有迁入 auth、db、payment、schema 或业务 action。

已完成：

- [x] `useProfiles.addTagsToProfiles(profileIds, tags)`：
  - 对 profile ids 去重。
  - 对 incoming tags trim / 去空 / 去重。
  - 以当前 `profiles` 中的 `profile.tags` 为事实基础合并。
  - 只调用 `api.updateProfile(id, { tags })`，不 spread 整个 profile，避免误写 proxy / fingerprint / runtime 字段。
  - 已存在同名 tag 时保留原 tag / color，不覆盖运营已有标签含义。
  - 未变化的 profile 直接跳过，不调用 update / refresh。
  - 选中态与列表刷新发生竞态时，已消失的 profile id 明确计入 failedCount，不静默丢失。
  - 批量并发限制为 4；成功后 refresh profiles，并对成功 ids refresh health cache。
  - 部分失败汇总 `operationError`，错误消息继续走 `redactUrlCredentials`。
- [x] `BulkActionBar` 接入真实 tag form：
  - `Tag selected` 可打开内联 tag form。
  - 输入框自动 focus，支持 Escape 取消。
  - 表单提交后清空输入并关闭。
  - `Delete selected` 继续 disabled，且 disabled danger 样式降噪，不再像可点击危险主按钮。
  - 可见文案压缩为 `Health / Launch / Stop / Tag / Delete`，保留 `aria-label="Check health" / "Launch selected" / "Stop selected" / "Tag selected" / "Delete selected"`，减少桌面窄表格下 action bar 被横向裁切。
- [x] `App.tsx` 接线：
  - 从 `useProfiles()` 解构 `addTagsToProfiles`。
  - 新增 `bulkTagging` 状态。
  - 传入 `ProfileTable.onAddTagsToSelectedProfiles` 和 `taggingSelectedProfiles`。
- [x] UI polish 追加：
  - checkbox 视觉从 16px 基础框升级为 18px 低噪声 custom control，保留真实 input、focus ring、mixed state。
  - selected / previewed row 改为更克制的横向渐变 + 左侧状态线。
  - tag chip 增加轻微 inset highlight。
  - inspector header 增加 `Previewing / Inspector` 轻量上下文，强化“表格预览、Open 进入详情”的信息架构。

保持不变：

- 主表 `min-w-[840px]`、表格自身横向滚动、桌面 `Actions` 列可见。
- 移动端 body 不横向撑破。
- 主表超过 120 条固定 64px 行高虚拟滚动。
- 左侧超过 80 条固定 112px item 虚拟滚动。
- `Check health` / bulk launch / bulk stop 真实动作语义保留。
- `Delete selected` 高风险动作仍 disabled。
- proxy visible text / title 仍不暴露凭据。

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

浏览器 UI/UE 验证：

- 临时 QA 数据目录：`/tmp/cloakbrowser-manager-qa-data-polish`。
- QA 后端：`http://127.0.0.1:8092/`，后端启动时 patch `backend.database.DATA_DIR/DB_PATH` 指向临时目录。
- 使用 `agent-browser`，环境变量 `AGENT_BROWSER_ARGS=--no-sandbox`。
- 桌面 `1440x900`：
  - 选择 `QA Existing Tag` 和 `QA Plain Profile` 后，bulk toolbar 显示 `2 selected`。
  - `Check health` 可用；`Launch` 可用；`Stop` disabled；`Tag` 可用；`Delete` disabled 且弱态。
  - 打开 tag form 后输入框自动 focus，输入 `qa` 时 action bar 不折行。
  - 实际提交 `ops` 后：
    - `QA Existing Tag` 保留 `existing`，追加 `ops`。
    - `QA Plain Profile` 追加 `ops`。
    - tag filter 出现 `ops`。
  - 点击 `Check health` 后 health 状态、GeoIP、Last checked 更新，批量健康检测真实可用。
  - console / errors 无相关前端错误。
- 移动 `390x844`：
  - 初始 sidebar 收起。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身横向滚动，`table.scrollWidth=840`、`table.clientWidth=358`。

截图：

- `/tmp/cloak-polish-selected-desktop.png`
- `/tmp/cloak-polish-bulk-tag-form-desktop.png`
- `/tmp/cloak-polish-bulk-tag-applied-desktop.png`
- `/tmp/cloak-polish-health-check-desktop.png`
- `/tmp/cloak-polish-mobile.png`

范围说明：

- 本 UI polish 小闭环当时未接入批量 delete；后续已在“批量 delete 确认小闭环”中接入。
- 本小闭环不做服务端分页；当前继续以固定行高虚拟滚动覆盖数百 profile。
- 本小闭环不改 Profile 创建/编辑/VNC viewer 的现有流，只保持不破坏。
- 窄屏 card list、空态细分、Profile/VNC 连续运营抽屉形态仍待 03 后续小闭环。

## 2026-05-26 批量 delete 确认小闭环

已完成：

- [x] `frontend/src/hooks/useProfiles.ts`
  - 新增 `deleteProfiles(profileIds)`，复用真实 `DELETE /api/profiles/{id}`。
  - 批量层只删除 `status === "stopped"` 的 profile，跳过 running，避免批量误删正在使用的 VNC / Automation 会话。
  - 删除并发限制为 2，避免大量 profile 数据目录删除同时打满 IO。
  - 支持去重、部分失败继续执行、失败原因脱敏、成功后清理 `profiles` 和 `healthByProfileId`。
  - 返回 `deletedIds`，供 App 清理 selection / preview / detail 引用。
- [x] `frontend/src/components/BulkActionBar.tsx`
  - `Delete selected` 从 disabled 占位接入为真实 danger action。
  - 只有存在 stopped selection 时可用；running-only selection 下保持 disabled，并提示先 stop。
  - 点击后打开确认面板，明确提示浏览器数据会永久删除。
  - 必须输入大写 `DELETE` 才能确认；取消和 Escape 不触发删除。
- [x] `frontend/src/components/ProfileTable.tsx`
  - 向 bulk toolbar 传递 stopped ids，不破坏现有 table `min-w-[840px]`、横向滚动和虚拟滚动。
- [x] `frontend/src/App.tsx`
  - 新增 `bulkDeleting` 状态。
  - 删除成功后只清理成功删除的 profile selection。
  - 如果当前 preview / detail 命中已删除 profile，回到可用状态，避免 stale view。

测试更新：

- `useProfiles.test.ts`
  - 覆盖批量删除去重、成功删除、health cache 清理。
  - 覆盖 running profile 跳过。
  - 覆盖部分失败时成功项仍删除、失败原因脱敏。
  - 覆盖 selection 中 profile 已消失时返回失败。
- `ProfileTable.test.tsx`
  - 覆盖必须输入 `DELETE` 才能确认。
  - 覆盖取消确认不会删除。
  - 覆盖 running-only selection 下 delete disabled。
- `App.test.tsx`
  - 覆盖确认后调用 `deleteProfiles`，删除成功后清理 selection。
  - 覆盖 mixed selection 只传 stopped，并保留 running selection。

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

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8092/`。
- QA 数据目录：`/tmp/cloakbrowser-bulk-delete-qa-data`，后端启动时 patch `backend.database.DATA_DIR/DB_PATH` 指向临时目录。
- QA 数据：150 个 `QA Bulk Profile`，用于验证数百 profile 级别 table 虚拟滚动和批量删除。
- 桌面 `1440x900`：
  - 首屏可见 operations rail、summary tiles、filter toolbar、dense table、inspector。
  - 选择 `QA Bulk Profile 000` 和 `QA Bulk Profile 001` 后 bulk bar 显示 `2 selected`，`Delete` 可用。
  - 点击 `Delete` 后确认面板显示 `Delete 2 stopped profiles?` 和永久删除提示。
  - 未输入 `DELETE` 时 `Confirm bulk delete` disabled。
  - 输入 `DELETE` 后真实删除 2 个 profile，列表从 150 变为 148，selection 清理。
  - 点击 `Check health` 对选中 profile 真实调用健康检测；被检测 profile 从 risk-first 首屏位置移动，说明 health 状态参与排序。
  - 主表滚动到约第 120 行后早期 profile 离开 DOM，可见 `QA Bulk Profile 122` 至 `130`，虚拟滚动仍生效。
- 移动 `390x844`：
  - 初始 sidebar 收起。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 主表自身横向滚动，`tableOverflow === "auto"`。
  - 横向滚动到右侧后 `Actions` / `Open` 仍可访问。
- console / errors 无相关前端错误。

截图：

- `/tmp/cloak-bulk-delete-desktop.png`
- `/tmp/cloak-bulk-delete-confirm.png`
- `/tmp/cloak-bulk-delete-after.png`
- `/tmp/cloak-bulk-delete-health-check.png`
- `/tmp/cloak-bulk-delete-virtual-scroll.png`
- `/tmp/cloak-bulk-delete-mobile.png`
- `/tmp/cloak-bulk-delete-mobile-actions.png`

## 2026-05-26 Profile 运营台高质感控件 polish 小闭环

背景：

- Jeff 继续反馈当前界面质感和细节还不够，复选框等控件显得 low。
- 本轮继续使用 `ui-ux-pro-max` / frontend design 方向做最小 UI polish，不继续堆新功能。
- 参考 `/home/jeff/code/reference-repos/saas_kit` 的 B2B SaaS app shell / data table 质感，只借鉴控件密度、低噪声 command bar、表格行态和 inspector 层级；没有复制整仓，也没有迁入 auth、db、payment、schema 或业务逻辑。

设计判断：

- 当前 Profile 运营台的信息架构方向继续保持：左侧 rail 做最近、分组、筛选和快捷入口，主区 table 承担数百 profile 的搜索、筛选、批量和核心运营。
- 本轮问题集中在控件系统：通用按钮、输入框、表单 section、choice checkbox、token chip、row selection、bulk toolbar、inspector header 的圆角、阴影、边框和 focus 状态不够统一。
- 对数据密集运营台，不追求强装饰；目标是长期管理数百 profile 时清晰、稳定、低疲劳。
- `ui-ux-pro-max` 本轮设计系统建议为 Data-Dense + Drill-Down：浅色背景、蓝色主操作、琥珀风险提示、稳定 focus、低动画；React 侧重点是稳定 key 和表单控件 label 关联。

已完成：

- [x] `frontend/src/styles/globals.css`
  - 统一 `.btn` / `.input` / `.label` 为更克制的 `rounded-md`、低噪声 border / shadow / focus ring。
  - 新增 `.form-section`、`.section-title`、`.choice-card`、`.choice-checkbox`、`.token-chip`、`.icon-action`，让表单、复选框、tag chip 和 icon button 有统一控件语言。
- [x] `frontend/src/components/ProfileForm.tsx`
  - 创建/编辑页改为更像运营配置面板的 section 布局，保持真实 create / update / delete / cancel 流程。
  - 核心字段补齐 `id` / `htmlFor`，包括 Profile Name、Fingerprint Seed、Proxy、Timezone、Locale、Screen Resolution、Width / Height、Hardware Concurrency、GPU Preset / Vendor / Renderer、Color Scheme、Notes。
  - 行为 checkbox 改为可点击 choice card，保留真实 checkbox、键盘 focus 和 checked 语义。
  - tag swatch 增加 `aria-label` / `aria-pressed`，tag / launch arg 删除按钮增加明确 `aria-label`。
- [x] `frontend/src/components/BulkActionBar.tsx`
  - bulk bar 继续收敛为低噪声 command bar，保留 `Check health` 主动作、tag form、delete confirm、running / stopped 过滤语义。
  - 高风险动作没有扩大权限：批量 delete 仍必须输入 `DELETE` 确认，running-only selection 下 disabled；本轮未新增其他危险 mutation。
- [x] `frontend/src/components/ProfileTable.tsx`
  - checkbox 命中区和视觉尺寸更适合密表，保留真实 input、半选态、`aria-checked="mixed"`、selection、preview 和 row action。
  - selected / previewed / hover row 降低噪声，保留 `data-state`、左侧状态线、64px 固定行高、120 条阈值虚拟滚动。
  - 保留 `min-w-[840px]` 与 table region 自身横向滚动，避免移动端 body 横向撑破。
- [x] `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector header、section icon、字段行 hover 进一步降噪，保持只读审计面板感和 proxy 凭据脱敏语义。
- [x] `frontend/src/App.tsx`
  - 移动端顶部 `New Profile` 主按钮保持单行和稳定高度，避免窄屏折成两行。

测试更新：

- `frontend/src/App.test.tsx`
  - 补充创建 / 编辑 profile 能力保留用例。
  - 修正 `New Profile` heading 查询，避免按钮与标题同名时测试不稳定。
- `frontend/src/components/ProfileForm.test.tsx`
  - 补充 label 关联、行为 checkbox 可访问和可切换、tag swatch / removable chip 可访问测试。
- `frontend/src/components/ProfileTable.test.tsx`
  - 补充 bulk toolbar `aria-busy` 断言，保持批量动作 loading 语义可感知。

保持不变：

- table `Actions` 列和 `Open ...` 按钮在桌面和移动横向滚动后仍可访问。
- 移动端 `body.scrollWidth === window.innerWidth`，横向滚动只发生在 table region。
- `Check health` 批量动作仍真实调用后端。
- 批量 launch / stop / tag / delete 沿用既有运行态过滤、disabled 和确认语义，本轮未新增未确认高风险动作。
- 主表数百 profile 继续使用固定行高虚拟滚动；左侧大列表虚拟滚动语义不变。

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

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8092/`。
- QA 数据目录：`/tmp/cloakbrowser-ui-polish-qa-data`。
- QA 数据：180 个 `Polish QA Profile`，加 `QA Good Health`、`QA Invalid Proxy`，浏览器流程中又创建并编辑 profile，最终约 184 个 profiles。
- 桌面 `1440x900`：
  - 首屏可见左侧 rail、summary tiles、filter toolbar、dense table、right inspector。
  - 选择 profile 后 bulk bar 显示 selection summary，`Check health` 主动作可用。
  - `Tag selected` 输入 `polish-v2` 后真实更新选中 profile，tag filter 和 row tag 均出现 `polish-v2`。
  - 点击 `Check health` 对选中 profile 真实发起健康检测。
  - 主表滚动到约第 140 行后早期 rows 离开 DOM，可见 `Polish QA Profile 139+`，虚拟滚动仍生效。
  - 点击 `New Profile` 后进入创建页，提交后进入 `Edit Profile`；编辑 profile name 后 sidebar 文案同步更新。
- 移动 `390x844`：
  - `body.scrollWidth === window.innerWidth === 390`。
  - `Profile operations table` region 自身横向滚动，`clientWidth=352`、`scrollWidth=846`。
  - 横向滚动到右侧后 `Actions` / `Open` 仍可见。
  - 顶部 `New Profile` 主按钮保持单行，不再折成两行。
  - 打开 sidebar overlay 后 body 仍不横向撑破。
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

- VNC viewer 能力复核未做。
- 空态拆分未做。
- 窄屏 card list 未做；当前窄屏继续采用 table region 横向滚动。
- 服务端分页未做；当前继续以固定行高虚拟滚动覆盖数百 profile。

## 2026-05-26 VNC viewer 能力保留小闭环

背景：

- 03 Profile 运营台已把默认首页改成 dense table / summary inspector / bulk actions，需要明确原有 running profile 的 VNC viewer 入口没有被运营台改造破坏。
- 本轮只做 VNC viewer 能力保留复核，不改 VNC proxy、KasmVNC、noVNC 生产逻辑。

已完成：

- [x] `frontend/src/App.test.tsx`
  - mock `ProfileViewer`，覆盖 running profile 从 operations table 点击 `Open` 后进入 VNC viewer。
  - 覆盖 viewer `onDisconnect` 后回到 `Edit Profile`，保留原有断线后编辑/停止恢复路径。
- [x] `frontend/src/components/ProfileViewer.test.tsx`
  - mock 可构造的 noVNC `RFB`，断言连接 URL 为 `ws://<host>/api/profiles/<profile_id>/vnc`。
  - 断言 noVNC 使用 `wsProtocols: ["binary"]`。
  - 断言 `scaleViewport=true`、`resizeSession=false`、`showDotCursor=true` 保留。
  - 触发 noVNC `disconnect` 事件，断言回调上层 `onDisconnect`。
- [x] 浏览器走查：
  - 使用临时 QA 后端和 fake RFB WebSocket 注入一个 running profile。
  - 从运营台 table 点击 `Open QA Running VNC Profile` 后进入 viewer。
  - viewer 显示 `Connected`，页面生成 noVNC canvas，Automation API copy action 可见。
  - 点击顶部 `Stop` 后回到 `Edit Profile`，运行数归零，`Launch` 按钮恢复。

保持不变：

- stopped profile 仍进入 `Edit Profile`。
- running profile 的 table `Open`、sidebar profile item、summary inspector `Open profile` 仍复用同一个 `handleSelect` 入口。
- `ProfileViewer` 仍通过后端 `/api/profiles/{profile_id}/vnc` WebSocket proxy 连接，不引入 Chromium CDP 或绕过后端 proxy。
- noVNC toolbar 的 Automation API copy、clipboard sync、fullscreen 控件仍保留。

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

浏览器验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8093/`。
- QA 数据目录：`/tmp/cloakbrowser-vnc-retain-qa-data`。
- QA 方式：
  - 本机 host 环境 `command -v Xvnc` 无输出，不能直接启动真实 KasmVNC。
  - 临时 QA 后端注入 `QA Running VNC Profile` 为 running 状态。
  - 临时 fake RFB WebSocket 服务模拟 KasmVNC 的最小 RFB handshake，用于验证前端 noVNC viewer、后端 VNC proxy 路径和运营台入口。
- 桌面 `1440x900`：
  - 首屏 table 可见 `QA Running VNC Profile`，runtime 为 running，inspector 显示 `VNC :6119`。
  - 点击 table `Open` 后进入 viewer。
  - viewer 显示 `Connected`，存在 canvas，Automation API endpoint copy action 可用。
  - 点击 `Stop` 后返回 `Edit Profile`，top bar 显示 `Launch`，运行数从 1 变为 0。
- `agent-browser errors --clear` 无相关应用错误。

截图：

- `/tmp/cloak-vnc-retain-viewer-connected.png`
- `/tmp/cloak-vnc-retain-stop-edit.png`

范围说明：

- 本轮没有改 VNC proxy / noVNC 生产实现。
- 本轮没有做真实 KasmVNC 二进制启动复验；当前 host 环境缺少 `Xvnc`，真实端到端 VNC 启动应在 Docker/运行时回归中补验。
- 当时 03 模块仍未完成：空态拆分、窄屏 card list 待后续；本轮后空态拆分已完成。

## 2026-05-26 Profile 运营台空态拆分小闭环

背景：

- 03 模块剩余空态拆分：无 profile、筛选无结果、health 未检测。
- 本轮在已完成的高质感 UI polish、批量动作和虚拟滚动语义上补齐空态体验，不重构主表和批量能力。
- 继续采用 `ui-ux-pro-max` 的 Data-Dense Dashboard 方向：浅色、低噪声、明确 CTA、稳定 hover/focus，不做炫技装饰。

已完成：

- [x] `frontend/src/components/ProfileTable.tsx`
  - 新增 `totalProfileCount`、`hasActiveFilters`、`onCreateProfile`、`onClearFilters` props。
  - `profiles.length === 0 && totalProfileCount === 0` 显示 `No profiles yet`，提供 `Create profile` CTA。
  - `profiles.length === 0 && totalProfileCount !== 0` 显示 `No profiles match these filters`，提供 `Clear filters` CTA。
  - 可见 rows 全部缺失 health 或 health 为 `unknown` 时显示轻量 `Health not checked yet` 提示；不隐藏 table rows，不影响 `Open` action。
  - 保持 table region `overflow-auto`、内层 `min-w-[840px]`、12 列、select-all disabled、固定行高和 120 条阈值虚拟滚动。
- [x] `frontend/src/App.tsx`
  - 增加 `profileFiltersEqual()`，计算 `hasActiveFilters`。
  - 向 `ProfileTable` 传入 profile 总数、筛选状态、创建 profile 和清空筛选动作。
- [x] `frontend/src/components/ProfileTable.test.tsx`
  - 覆盖首次无 profile 空态和 `Create profile`。
  - 覆盖筛选无结果空态和 `Clear filters`。
  - 覆盖 health 未检测提示不遮挡 rows。
  - 覆盖虚拟滚动 reset 后不残留旧 row。
- [x] `frontend/src/App.test.tsx`
  - 覆盖空库时从空态一键进入创建页。
  - 覆盖搜索无结果后 `Clear filters` 恢复 table。
  - 覆盖 all-unknown health 提示存在且 table `Open` 仍可进入编辑页。

保持不变：

- `Actions` / `Open` 仍在桌面和移动横向滚动中可访问。
- 移动端 body 不横向撑破；横向滚动只发生在 table region。
- 批量 `Check health` 仍真实调用后端。
- 批量 delete 仍需 `DELETE` 确认；高风险动作没有放开。
- 数百 profile 主表虚拟滚动和左侧列表虚拟滚动语义不变。

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

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:18181/`。
- QA 数据目录：`/tmp/cloakbrowser-empty-qa-data`。
- 桌面 `1440x900`：
  - 空库显示 `No profiles yet`，`Create profile` CTA 可见。
  - 创建 2 个 QA profile 后，health 未检测提示显示在 table 上方，rows 和 `Open` action 仍可见。
  - select all 后 bulk bar 显示，`Check health` 真实调用后端；检测后 good / error health 状态参与 risk-first 排序。
  - 搜索 `does-not-exist` 后显示 `No profiles match these filters`，点击 `Clear filters` 恢复 2 行 table。
- 移动 `390x844`：
  - 初始 sidebar 收起，主区保留 filter toolbar 和 table。
  - `body.scrollWidth === window.innerWidth === 390`。
  - `Profile operations table` 的 `overflow` 为 `auto`，横向滚动仍由 table 自身承担。
- `agent-browser console --clear` / `agent-browser errors --clear` 无相关应用错误。

截图：

- `/tmp/cloakbrowser-polish-screens/no-profiles-desktop.png`
- `/tmp/cloakbrowser-polish-screens/health-unknown-desktop.png`
- `/tmp/cloakbrowser-polish-screens/bulk-selected-desktop.png`
- `/tmp/cloakbrowser-polish-screens/bulk-check-health-after.png`
- `/tmp/cloakbrowser-polish-screens/filtered-empty-desktop.png`
- `/tmp/cloakbrowser-polish-screens/mobile-table.png`

仍未做：

- 当时窄屏 card list 未做；当前已在后续小闭环完成。

## 2026-05-26 窄屏 card list 与高质感控件 polish 收口小闭环

背景：

- Jeff 反馈：当前界面质感和细节还不够，复选框等控件显得 low；同时要求不要破坏已完成的真实功能、测试、性能语义和虚拟滚动。
- 本轮继续使用 `ui-ux-pro-max` / frontend design 方向，并参考 `/home/jeff/code/reference-repos/saas_kit` 的 B2B SaaS app shell / data table 质感。
- 本轮只收口 Profile 运营台，不引入 Project Mileage 业务逻辑，不迁入参考仓库 auth/db/payment/schema。

设计判断：

- 数百 profile 的核心管理仍由主区 table / search / filter / bulk action 承担；左侧继续作为 saved views / shortcuts / 兜底导航。
- `<768px` 下继续用主区承载管理，但从宽表横向滚动降级为 card list；桌面仍使用 dense table。
- UI polish 重点不是炫技，而是降低噪声、统一控件状态、稳定 sticky 层级和避免移动端横向撑破。

已完成：

- [x] `frontend/src/components/ProfileTable.tsx`
  - `<768px` 渲染 `ProfileCardList`，桌面仍渲染 `ProfileDesktopTable`，避免 table/card 双 DOM 重复。
  - card list 保留 selection checkbox、`Select all visible profiles`、bulk action bar、preview、`Open`、health、proxy 脱敏、GeoIP fallback、tags、last checked。
  - card list 超过 120 条继续使用固定高度虚拟滚动，`PROFILE_CARD_ROW_HEIGHT = 188`；全选仍作用完整过滤结果集合，不局限当前虚拟窗口。
  - 选中后移动 card selection toolbar 使用 `top-11`，避免和 `BulkActionBar` sticky top 重叠。
  - table row / card selected / previewed 状态改为更克制的左侧状态线和低噪声渐变，保留 64px table 行高。
- [x] `frontend/src/components/BulkActionBar.tsx`
  - 降低 bulk toolbar 视觉噪声，保留 `Check health` 主动作。
  - `Launch` / `Stop` / `Tag` / `Delete` 的真实动作、运行态过滤、disabled 和 typed delete 确认语义不变。
- [x] `frontend/src/components/ProfileFilters.tsx`
  - 主筛选 strip 增加 `role="toolbar"` / `aria-label="Profile filters"`，保持 search/filter/sort 的可访问结构。
- [x] `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector header 和 section icon 降噪，保持只读 drill-down 语义。
- [x] `frontend/src/App.tsx`
  - 主区 surface 的阴影/ring 降噪，减少“卡片套卡片”。
  - top bar 在移动 edit 页补 `overflow-hidden` 和更小横向 padding，修掉 card `Open` 进入编辑页后的 2px body 横向 overflow。
- [x] `frontend/src/styles/globals.css`
  - 增加全局 `button:not(:disabled)` pointer 和 disabled cursor 规则。
- [x] 测试补充：
  - 窄屏 card list 不重复桌面 table。
  - 窄屏 selection / select all 仍绑定完整过滤结果。
  - 窄屏 preview / open 分离。
  - card DOM 不泄露 proxy 凭据。
  - 窄屏 card 虚拟滚动可滚到中段并保持 full-set selection。
  - card selection toolbar 在 bulk bar 存在时带 `top-11`。
  - filter strip 暴露 toolbar 语义。

保持不变：

- 桌面 table `Actions` / `Open` 可见。
- 移动端 body 不横向撑破；移动 card list 不再依赖主表横向滚动。
- `Check health` 继续真实调用后端。
- 批量 launch / stop / tag / delete 保留既有真实动作和高风险确认语义。
- 主表超过 120 条和左侧超过 80 条的虚拟滚动语义不变。
- proxy 可见文本和 `title` 继续不暴露用户名/密码。

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

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:18183/`。
- QA 数据目录：`/tmp/cloakbrowser-ui-card-polish-data`，共 180 个 `Polish Card Profile`。
- 桌面 `1440x900`：
  - dense table 可见，card list 不渲染。
  - `body.scrollWidth === window.innerWidth === 1440`。
  - `Actions` / `Open` 首屏可见。
  - 选择首行后 bulk toolbar 可见，`1 selected` 可见，`Check health` 可点击。
  - 点击 `Check health` 后无前端 alert，selection 保留。
  - 表格滚动到中段后早期 table rows 离开 `Profile operations table` region，仍只渲染窗口内 rows。
- 移动 `390x844`：
  - card list 可见，desktop table 不渲染。
  - `body.scrollWidth === window.innerWidth === 390`。
  - 首屏约 20 张 card 在 DOM 中，证明 180 条没有全量渲染。
  - 选择首张 card 后 bulk toolbar 可见，card selection toolbar class 包含 `top-11`，没有 sticky 重叠。
  - 点击 `Check health` 后无前端 alert，body 仍不横向撑破。
  - 滚动到中段后早期 card 离开 `Profile operations table` region，仍只渲染约 20 张 card。
  - 点击移动 card `Open` 进入 `Edit Profile`，`body.scrollWidth` 小于 `window.innerWidth`。
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

范围说明：

- 本轮不做服务端分页；当前继续以固定行高虚拟滚动覆盖数百 profile。
- 本轮不把 Profile 详情 / VNC viewer 改为抽屉式连续运营形态。
- 本轮不新增新的高风险批量能力。
- 03 模块任务清单已全部完成，`tasks/progress.md` 已更新 03 为完成。

## 2026-05-26 Profile 运营台控件质感二次 polish 小闭环

背景：

- Jeff 继续反馈当前界面质感和细节还不够，尤其是 checkbox、bulk action、table row、toolbar、inspector 这些高频控件显得不够高级。
- 本轮继续使用 `ui-ux-pro-max` / frontend design 方向；参考 `/home/jeff/code/reference-repos/saas_kit` 的 B2B SaaS app shell / data table 质感，只借鉴密度、层级、控件状态和分组方式。
- 本轮只做 Profile 运营台 UI polish，不迁入参考仓库 auth、db、payment、schema，不引入 Project Mileage 业务逻辑，不改 Firefox / invisible_playwright / Automation REST API 边界。

设计判断：

- 信息架构继续保持：左侧 rail 做 saved views / shortcuts，主区 table/card 承担数百 profile 的搜索、筛选、批量和核心运营，右侧 inspector 做只读扫视。
- 当前低质感主要不是缺功能，而是控件状态颗粒度不足：checkbox 没有显式状态层，bulk toolbar 没有 summary / commands 分组，table row selected / previewed 状态噪声偏高，inspector section 不是清晰的可访问 region。
- 本轮不继续堆功能，不改筛选/排序/虚拟滚动算法，不改批量 API 数据流。

已完成：

- [x] `frontend/src/components/ProfileTable.tsx`
  - `SelectionCheckbox` 增加 `data-state="checked|unchecked|indeterminate"`，保留真实 checkbox input、`aria-checked="mixed"`、键盘 focus 和半选态。
  - checkbox 视觉层补充 18px 控件盒、轻量 focus ring、hover surface 和 inset highlight，解决原生 checkbox 质感偏低的问题。
  - table header 改为更干净的 white sticky header，保留 `min-w-[840px]`、12 列、`Actions` 列和表格自身横向滚动。
  - table row / card selected / previewed 状态改为低噪声底色 + 左侧状态线，保留 64px table 行高和 188px card 行高。
- [x] `frontend/src/components/BulkActionBar.tsx`
  - bulk toolbar 增加 `Selected profile summary` 和 `Bulk action commands` 两个 `role="group"`，结构更接近专业 data table command bar。
  - secondary actions 收敛成图标按钮，保留 `aria-label` / `title` / loading 文案，避免 1440px + sidebar + inspector 时末尾 `Clear` 被挤出可视区域。
  - `Check health` 仍是主动作且真实调用后端；launch / stop / tag / delete 的既有运行态过滤、disabled、typed delete 确认语义不变。
- [x] `frontend/src/components/ProfileSummaryPanel.tsx`
  - inspector section 增加 `aria-label`，Health / Runtime / GeoIP / Proxy / Device 现在是可访问 region。
  - header 和 section surface 降噪，字段行 hover / spacing 更稳定，减少“普通配置面板”感。
- [x] 测试补充：
  - checkbox label 暴露 checked / unchecked / indeterminate 状态。
  - bulk toolbar 暴露 summary / commands 分组。
  - inspector 分区可通过 region 角色访问。

保持不变：

- 桌面 table `Actions` / `Open` 仍可见。
- 移动端 body 不横向撑破；card list 继续替代窄屏 table。
- `Check health` 批量动作仍真实调用后端。
- 批量 launch / stop / tag / delete 保留既有真实动作、运行态过滤和高风险确认语义。
- 主表超过 120 条、左侧超过 80 条的固定行高虚拟滚动语义不变。
- proxy 可见文本和 `title` 继续不暴露用户名/密码。

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
  - table/card 没有重复渲染，dense table 可见。
  - 选择 2 个 profile 后 bulk toolbar 显示 `2 selected`，`Selected profile summary` / `Bulk action commands` 分组存在。
  - `Check health` 可点击并完成，selection 保留。
  - `Actions` / `Open` 可见，`Clear` 在当前 viewport 内可见。
  - `body.scrollWidth === window.innerWidth === 1440`，table region `overflow: auto`。
- 移动 `390x844`：
  - card list 可见，desktop table 不渲染。
  - 选择 1 个 profile 后 bulk toolbar 显示 `1 selected`，summary / commands 分组存在。
  - `body.scrollWidth === window.innerWidth === 390`，sidebar 初始收起。
  - DOM 中约 21 张 card，数百 profile 仍不是全量渲染。
- `agent-browser errors` / `agent-browser console` 无输出。

截图：

- `/tmp/cloakbrowser-ui-polish-v3-screens/desktop-table-bulk-inspector.png`
- `/tmp/cloakbrowser-ui-polish-v3-screens/mobile-card-selected.png`

范围说明：

- 本轮不做服务端分页；当前继续以固定行高虚拟滚动覆盖数百 profile。
- 本轮不改 ProfileForm 页签、Viewer EnvironmentStrip 或 Proxy Manager 页面。
- 本轮不处理 04 Proxy Manager 的 `POST /api/proxies/{id}/check` 红灯测试；该后端小闭环仍待继续。

## 2026-05-26 Profile 运营台控件质感三次 polish 小闭环

背景：

- Jeff 继续反馈当前界面质感和细节还不够，尤其是 checkbox / bulk action / table row / toolbar / inspector。
- 本轮继续使用 `ui-ux-pro-max` 和 frontend design 方向，并让子 agent 只读审计当前 Profile 运营台与 `/home/jeff/code/reference-repos/saas_kit`。
- 参考结论：只吸收 B2B SaaS app shell / data table 的密度、低噪声状态、ring / shadow、控件分组和 inspector 层级；不复制参考仓库代码，不迁入 auth / db / payment / schema。

设计判断：

- 信息架构继续保持：左侧 rail 是 saved views / shortcuts，主区 table/card 承担数百 profile 的搜索、筛选、批量和核心运营，右侧 inspector 做只读扫视。
- 参考仓库常见的底部浮动 bulk toolbar 暂不迁移；当前 ProfileTable 的 sticky header、移动 card selection toolbar 和虚拟滚动已经围绕 `h-11` / `top-11` 成熟，改成底部浮动会引入新的遮挡和回归面。
- 本轮只做可验证小 polish，不改筛选/排序、批量 API、固定行高虚拟滚动、proxy 脱敏或高风险动作确认语义。

已完成：

- [x] `frontend/src/components/ProfileTable.tsx`
  - `SelectionCheckbox` 继续保留真实 checkbox input、`data-state`、`aria-checked="mixed"`、键盘 focus 和 disabled 语义。
  - checkbox 命中区增加低噪声 hover border / surface / inset highlight。
  - checkbox 视觉层改为 white-to-slate / blue gradient 和更稳定 inset highlight，提升 checked / mixed 状态质感。
- [x] `frontend/src/components/BulkActionBar.tsx`
  - 保持 `sticky top-0 h-11` 不变，不破坏 table header 和 card selection toolbar 的 `top-11` 偏移。
  - summary group / command group 改为更克制的 gradient surface 和更轻 shadow。
  - `Check health` 与 inline `Apply tag` 主按钮增加低噪声 blue gradient 和 inset highlight；真实动作、loading、disabled 语义不变。
- [x] `frontend/src/components/ProfileSummaryPanel.tsx`
  - 空 inspector 从普通 dashed panel 改为带 `Inspector` header、icon container 和内层空态 surface 的审计面板空态。
  - 已选 profile 的 inspector section / proxy 脱敏 / region 可访问语义不变。
- [x] 测试补充：
  - 桌面 selected 后 `thead` 仍包含 `top-11`，锁住 bulk bar 与 sticky header 的 offset。
  - 桌面和窄屏 selected + previewed 同时存在时，`selected` 状态优先。
  - 窄屏 card checkbox 也暴露 checked / unchecked / indeterminate `data-state`。
  - bulk tag form 和 delete confirm 支持 Escape 关闭且不触发 mutation。
  - 空 inspector 有明确可访问文本。

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
  - 选择首行后 bulk toolbar 显示 `1 selected`，`Selected profile summary` / `Bulk action commands` 分组存在。
  - 表头 `Select all visible profiles` 为 `aria-checked="mixed"`，`thead` 保留 `top-11`。
  - 点击 `Check health` 后 selection 保留，无前端 alert。
  - 主表滚动到中段后 early rows 离开 table region，窗口内显示 `Polish QA Profile 115+`，虚拟滚动仍生效。
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

范围说明：

- 本轮不做服务端分页。
- 本轮不把 bulk toolbar 改成底部浮动形态。
- 本轮不改 ProfileForm 页签、Viewer EnvironmentStrip 或 Proxy Manager 页面。
- 03 模块仍保持完成状态；当前继续按用户反馈在已完成模块上做 UI polish 小闭环。
