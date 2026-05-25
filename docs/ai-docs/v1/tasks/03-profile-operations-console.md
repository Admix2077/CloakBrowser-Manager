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

- [ ] 定义运营台布局：
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
- [x] 新增多选状态。
- [ ] 新增 `BulkActionBar`。
- [ ] 接入批量 launch。
- [ ] 接入批量 stop。
- [ ] 接入批量 health check。
- [ ] 接入批量 set tags。
- [ ] 接入批量 delete，必须有确认。
- [ ] 新增 `ProfileSummaryPanel`：
  - health。
  - runtime。
  - GeoIP。
  - manual override。
  - proxy。
  - device。
  - quick actions。
- [ ] 保留创建/编辑 profile 能力。
- [ ] 保留 VNC viewer 能力。
- [ ] 空态拆分：
  - 无 profile。
  - 筛选无结果。
  - health 未检测。
- [ ] 窄屏降级为 card list。

## 验证命令

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 浏览器验收

- [x] 1440px 显示 dense table。
- [x] 768px 表格不溢出。
- [x] 375px 显示 card 模式或可用横向滚动。
- [ ] 批量选择后 action bar 不遮挡主要操作。
- [ ] 长 proxy、长 tag、长 profile name 不撑破布局。

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
