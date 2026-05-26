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

## 2026-05-26 Profile 运营台 IA/视觉二次收口

本轮根据 Jeff 的 UI/UE 反馈暂停继续堆功能，先做 Profile 运营台的小闭环打磨：

- 使用 `ui-ux-pro-max` 生成 B2B SaaS operations dashboard 方向。
- 审阅 `/home/jeff/code/reference-repos/saas_kit`，借鉴 `ai-mksaas-template` 的数据表格/toolbar 和 `ai-supastarter-template` 的 B2B app shell 克制感。
- 左侧从全量列表主入口进一步收敛为 `Saved views` / `Profile shortcuts` rail。
- 主区变成核心运营面：标题/指标 strip、可见标签筛选 toolbar、dense table、右侧 inspector。
- 主表压缩到 840px 最小宽度，桌面 1440px 可直接看到 `Actions` 列；移动端仍由表格自身横向滚动承载宽表。
- summary panel 改成 inspector 分区样式，减少卡片套卡片。
- `BulkActionBar` 接入真实 `Check health`，保留其他高风险批量动作 disabled。

验证记录见 `03-profile-operations-console.md` 的 `2026-05-26 Profile 运营台 IA/视觉二次收口与批量 health check 小闭环`。

## 2026-05-26 Profile 运营台控件质感二次 polish

本轮继续根据 Jeff 对“控件显 low”的反馈做最小 UI polish，范围集中在 Profile 运营台高频控件：

- 使用 `ui-ux-pro-max` 重新确认 B2B data-dense dashboard 方向。
- 只读审阅 `/home/jeff/code/reference-repos/saas_kit` 的 data table / action bar / inspector 参考，不复制业务代码，不迁入 auth、db、payment、schema。
- `ProfileTable` 的 selection checkbox 增加显式 `data-state`，保留真实 input、半选态、键盘 focus 和虚拟滚动。
- `BulkActionBar` 增加 summary / commands 分组，并把 secondary actions 收成图标按钮，避免 1440px + sidebar + inspector 时命令条拥挤。
- `ProfileSummaryPanel` 的 Health / Runtime / GeoIP / Proxy / Device 分区改为可访问 region，视觉上更像 inspector。
- 保留桌面 `Actions` 可见、移动 card list、body 不横向撑破、批量 `Check health` 真实可用、proxy 脱敏和数百 profile 固定行高虚拟滚动语义。

验证记录见 `03-profile-operations-console.md` 的 `2026-05-26 Profile 运营台控件质感二次 polish 小闭环`。
