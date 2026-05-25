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
- [ ] 新增 `ProfileTable`：
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
- [ ] 新增多选状态。
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

- [ ] 1440px 显示 dense table。
- [ ] 768px 表格不溢出。
- [ ] 375px 显示 card 模式或可用横向滚动。
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
