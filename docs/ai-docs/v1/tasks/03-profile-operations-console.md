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
- [ ] 新增 `ProfileFilters`：
  - search。
  - status。
  - health。
  - proxy exists。
  - country。
  - tag。
- [ ] 新增排序：
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
