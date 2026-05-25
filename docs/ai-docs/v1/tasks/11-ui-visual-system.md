# 11 UI 视觉系统与体验升级

## 目标

把 UI 从朴素配置面板升级为成熟、专业、高密度的指纹浏览器运营台。

## 设计方向

- 专业安全运营台。
- 默认浅色 B2B / data-dense dashboard。
- 使用 slate / blue / low-noise surfaces，降低开发面板感。
- 高密度但清晰。
- 健康状态使用 emerald。
- 警告使用 amber。
- 错误使用 red。
- 使用 lucide 图标。
- 不做营销 hero。
- 不做夸张 cyberpunk。
- 不用大面积渐变装饰。
- 深色模式后续可做，但不作为当前默认主视觉。

## 任务清单

- [x] 统一 CSS token。
- [x] 重写按钮状态：
  - default。
  - hover。
  - active。
  - disabled。
  - loading。
- [x] 重写 input/select/textarea 样式。
- [ ] 新增 badge 系统：
  - health。
  - runtime。
  - proxy。
  - country。
  - tag。
- [x] 新增 table 样式。
- [ ] 新增 empty state 样式。
- [x] 新增 error banner。
- [ ] 新增 toast 或 inline feedback。
- [ ] 用项目内 ConfirmDialog 替代原生 `confirm`。
- [ ] ProfileForm 改为分组页签：
  - Identity。
  - Network。
  - Device。
  - Behavior。
  - Advanced。
- [ ] Viewer 顶部 EnvironmentStrip 视觉升级。
- [ ] 375px、768px、1024px、1440px 响应式检查。
- [ ] 文案避免“保证安全”“保证不封号”等不可验证承诺。

## 验证

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

浏览器检查：

- [x] Profile table 无溢出。
- [ ] 表单长字段不撑破容器。
- [ ] Viewer 工具条不遮挡 VNC。
- [x] 批量操作栏不挡住主操作。
- [ ] 浅色默认主题对比度足够。

## 2026-05-26 Profile 运营台 UI/UE 质感小闭环

已完成第一轮视觉系统落地，范围集中在 Profile 运营台：

- `tailwind.config.ts` 中 `surface` / `border` / `accent` token 改为浅色 B2B 运营台体系。
- `globals.css` 更新 body、button、input、select、textarea、focus ring、scrollbar。
- `ProfileTable` 改为 table-fixed，长 profile name、proxy、IP、timezone、tag 和 last checked 均截断，不撑破布局。
- `BulkActionBar` 改为浅色 sticky command bar，仍只保留 disabled 安全壳。
- `ProfileList` 改为 quick views + matching profiles rail。
- `App` 主区增加 operations toolbar 和 summary tiles。
- `LoginPage`、`ProfileForm`、`ProfileViewer`、`LaunchButton` 做浅色 token 兼容，避免浅色默认主题下文本不可读。

验证记录见 `03-profile-operations-console.md` 的 `2026-05-26 Profile 运营台 UI/UE 质感小闭环`。
