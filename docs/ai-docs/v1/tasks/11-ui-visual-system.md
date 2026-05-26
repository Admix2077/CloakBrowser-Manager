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
- [x] 用项目内 ConfirmDialog 替代原生 `confirm`。
- [ ] ProfileForm 改为分组页签：
  - Identity。
  - Network。
  - Device。
  - Behavior。
  - Advanced。
- [x] Viewer 顶部 EnvironmentStrip 视觉升级。
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
- [x] Viewer 工具条不遮挡 VNC。
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

## 2026-05-26 Profile 运营台控件质感四次 polish

本轮继续根据 Jeff 对 checkbox / bulk action / table row / toolbar / inspector 质感的反馈做更克制的 B2B 运营台 polish：

- 使用 `ui-ux-pro-max` 确认 data-dense operations console 方向：浅色、低噪声、清晰边界、少渐变、明确 focus。
- 参考 `/home/jeff/code/reference-repos/saas_kit/ai-mksaas-template` 的 data table / action bar / checkbox 质感，但未复制业务代码，未迁入 auth / db / payment / schema。
- `ProfileTable` checkbox 改为 18px 控件 + 7px hit target + solid checked state + 明确 focus ring，保留真实 input、半选态和虚拟滚动。
- `BulkActionBar` 改为单层浅色工具条，summary / commands 分组更清晰，并新增 `Escape` 清空 selection 微交互。
- `ProfileFilters` 输入控件统一轻 shadow / focus ring。
- `ProfileSummaryPanel` 改成更像属性 inspector 的 header、section icon、warning block 和 property row。
- `App` 主区的 top pill、filter band、table panel 做轻量 polish，减少卡片堆叠感。
- `globals.css` 增加 form controls font inherit 与 `prefers-reduced-motion: reduce`。

验证记录见 `03-profile-operations-console.md` 的 `2026-05-26 Profile 运营台控件质感四次 polish 小闭环`。

## 2026-05-26 Profile 运营台控件质感五次降噪 polish

本轮继续根据 Jeff 对 checkbox / bulk action / table row / toolbar / inspector 质感的反馈做小范围降噪 polish：

- 使用 `ui-ux-pro-max` 和只读子 agent 审计，确认当前功能语义已稳，问题主要是阴影、ring、边框和卡片套卡片感偏重。
- `BulkActionBar` 新增 `Primary bulk action` / `Secondary bulk actions` 可访问分组，保持 `Check health` 作为一级文字动作，其他批量命令保持次级图标动作。
- `ProfileTable` 的 header、row、card、checkbox、tag chip、Open button 去掉过重 shadow，保留真实 input、半选态、focus ring、状态线和固定行高虚拟滚动。
- `ProfileFilters` 降低 search/select 控件的 shadow / ring 堆叠。
- `ProfileSummaryPanel` 改为更平的 inspector section，减少卡片套卡片感。
- `App` 主区 filter band 和 table panel 继续降噪，保持主区 table + 右侧 inspector 信息架构。

验证记录见 `03-profile-operations-console.md` 的 `2026-05-26 Profile 运营台控件质感五次降噪 polish 小闭环`。

## 2026-05-26 Profile 运营台控件质感六次精修 polish

本轮继续根据 Jeff 对 checkbox / bulk action / table row / toolbar / inspector 质感的反馈做最小 UI polish：

- 使用 `ui-ux-pro-max` 确认 data-dense operations console 方向。
- 子 agent 只读审计当前实现与 `/home/jeff/code/reference-repos/saas_kit/ai-mksaas-template`，只吸收 data table、action bar、checkbox、inspector 的视觉原则，不复制业务代码，不迁入 auth / db / payment / schema。
- `ProfileFilters` 增加 active filter 视觉语义，避免 toolbar 像普通表单控件堆叠。
- `ProfileTable` 强化 checkbox 控件、selected / previewed row 状态线、Open action hover 质感，同时保留固定行高虚拟滚动。
- `BulkActionBar` 保持顶置 sticky 形态，summary / commands 分组改为更稳定的白色 data-table surface；`Check health` 真实可用，Launch / Stop / Tag / Delete 锁定为 disabled。
- `ProfileSummaryPanel` 增加 section priority 语义，Health / Runtime 更像 operational inspector 的优先信息。
- `App` 主区 surface / shadow / tile token 继续收口，减少卡片堆叠感。

验证记录见 `03-profile-operations-console.md` 的 `2026-05-26 Profile 运营台控件质感六次精修 polish 小闭环`。

## 2026-05-26 ProfileForm 删除确认 Dialog 小闭环

背景：

- ProfileForm 删除 profile 仍使用浏览器原生 `confirm()`，交互生硬且不符合当前 B2B 运营台视觉系统。
- 本小闭环只替换编辑页单 profile 删除确认，不改变 App 的删除事实流，不触碰批量删除、后端或 Project Mileage。

已完成：

- [x] `frontend/src/components/ConfirmDialog.tsx`
  - 新增项目内确认弹层，支持 danger/default tone、subject、loading、Escape 关闭。
  - 使用现有 dialog / notice 动效 token，保持 `role="dialog"`、`aria-modal="true"`。
- [x] `frontend/src/components/ProfileForm.tsx`
  - 删除按钮改为打开 `Delete profile` dialog。
  - Cancel / Escape 只关闭 dialog，不调用 `onDelete`。
  - 点击 `Confirm delete profile` 后才调用既有 `onDelete()`；删除完成后关闭 dialog。
  - 创建模式和未传 `onDelete` 时仍不显示删除入口。
- [x] `frontend/src/components/ProfileForm.test.tsx`
  - 覆盖点击 Delete 不再调用 `window.confirm`。
  - 覆盖 Cancel 不删除、Confirm 才删除。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileForm.test.tsx
# 红灯：1 failed, 6 passed
# window.confirm 仍被调用

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
- QA 地址：`http://127.0.0.1:8095/`，生产 build 来自 `frontend/dist`。
- 桌面 `1440x900`：
  - 打开 `Alpha Warmup` 编辑页，点击 `Delete` 后出现 app 内 `Delete profile` dialog。
  - 点击 `Cancel delete` 后 dialog 关闭，仍停留在 `Edit Profile`，profile 未删除。
  - 新建临时 QA profile `Confirm Dialog QA Delete`，打开编辑页并确认删除后返回主表，API 验证该临时 profile 已删除。
- 移动 `390x844`：
  - 打开 `Beta Running Candidate` 编辑页，点击 `Delete` 后 dialog 可见。
  - JS 验证：`hasDialog=true`、`hasBeta=true`、`scrollWidth=384`、`width=390`。
  - Escape 关闭后未删除 `Beta Running Candidate`。
- 截图：
  - `/tmp/cloakbrowser-confirm-dialog-screens/desktop-delete-dialog.png`
  - `/tmp/cloakbrowser-confirm-dialog-screens/mobile-delete-dialog.png`

## 2026-05-26 Viewer 顶部 EnvironmentStrip 视觉升级小闭环

背景：

- Jeff 反馈当前 UI 已接近 SS 风格，但部分交互反馈偏生硬。
- 本小闭环只处理 Viewer 顶部环境条，不改变 VNC 连接、Automation REST API、clipboard sync 或后端运行时语义。
- 派发两个只读子 agent：
  - `Faraday` 审计 Viewer strip 当前改动的交互、响应式和可访问性风险。
  - `Boyle` 寻找下一轮低风险动效 polish 候选。

已完成：

- [x] `frontend/src/components/ProfileViewer.tsx`
  - 顶部 toolbar 升级为 `Viewer environment` region，展示 connection、profile handle、Automation、Clipboard 状态。
  - 右侧动作组升级为 `Viewer actions` toolbar，icon button 增加 hover、active、focus-visible、disabled 和 copied 状态反馈。
  - profile handle 改为首尾短 ID，保留完整 `title`，避免多个 profile 只显示同一前缀造成误认。
  - 顶条改为单行 compact strip，左侧状态在窄屏横向滚动，右侧动作不换行，避免挤压 VNC 高度。
  - Fullscreen target 改为包含 strip + VNC 的外层 viewer frame，进入 fullscreen 后仍保留退出入口和环境信息。
- [x] `frontend/src/components/ProfileViewer.test.tsx`
  - 增加 EnvironmentStrip 可见状态、copy/clipboard/fullscreen action 可访问性断言。
  - 增加窄宽度下 strip / toolbar 不换行、fullscreen 覆盖整个 viewer frame 的回归测试。

验证：

```bash
cd frontend && npm test -- --run src/components/ProfileViewer.test.tsx
# 红灯：2 failed, 4 passed
# 旧实现短 ID 易混淆、缺少 toolbar 语义、fullscreen 只覆盖 VNC canvas

cd frontend && npm test -- --run src/components/ProfileViewer.test.tsx
# 1 passed, 6 passed

cd frontend && npm test -- --run
# 12 passed, 151 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:5177/`，临时 harness 渲染真实 `ProfileViewer`，noVNC RFB mock 只用于触发 connect；视觉 CSS 使用本轮 `frontend/dist/assets/index-B1ZhK8Yv.css`。
- 桌面 `1440x900`：
  - `Connected`、`Automation ready`、`Clipboard sync off` 可见。
  - JS 验证：`scrollWidth=1440`、`innerWidth=1440`、`stripHeight=45`、`toolbar=true`。
- 移动 `390x844`：
  - 顶条保持单行，不挤出页面横向滚动。
  - JS 验证：`scrollWidth=390`、`innerWidth=390`、`stripHeight=45`、`overflow=false`、`toolbar=true`。
- 新浏览器会话 `agent-browser errors` 无输出；console 只有 Vite/React dev 信息和现有 clipboard debug log。
- 截图：
  - `/tmp/cloakbrowser-viewer-strip-screens/desktop-viewer-environment-strip.png`
  - `/tmp/cloakbrowser-viewer-strip-screens/mobile-viewer-environment-strip.png`

边界：

- 没有修改后端或 runtime。
- 没有改变 VNC websocket、clipboard bridge、Automation REST API 契约。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。

## 2026-05-26 Profile 运营台选中与批量操作微反馈小闭环

背景：

- Jeff 反馈当前页面美观度已经接近 SS 风格，但交互反馈仍偏生硬。
- 本小闭环优先处理 Profile 运营台最高频的表格/卡片选择、批量操作栏出现、批量 Check health 忙碌反馈。
- 不改变虚拟滚动固定行高、不改变真实批量 `Check health` 逻辑、不解锁 Launch / Stop / Tag / Delete 等高风险批量动作。

已完成：

- [x] `frontend/src/components/ProfileTable.tsx`
  - selected desktop row 与 mobile card 增加 `animate-profile-selection` 轻量反馈类。
  - 保留 `data-state=selected` / `data-state=previewed` 优先级，行高仍由 `PROFILE_TABLE_ROW_HEIGHT` / `PROFILE_CARD_ROW_HEIGHT` 控制。
- [x] `frontend/src/components/BulkActionBar.tsx`
  - bulk action bar 出现时增加 `animate-bulk-action-in`。
  - `Check health` 忙碌态下 `HeartPulse` 图标增加 pulse 反馈，保留 `aria-busy=true` 和 disabled 状态。
- [x] `frontend/src/styles/globals.css`
  - 新增 `cloak-profile-selection` 与 `cloak-bulk-action-in` keyframes。
  - 继续复用现有 `prefers-reduced-motion: reduce` 全局降级。
- [x] `frontend/src/components/ProfileTable.test.tsx`
  - 覆盖 selected row/card 动效类。
  - 覆盖 bulk action bar 入场动效类。
  - 覆盖 `Checking health` 时 icon pulse、disabled 和 `aria-busy`。

验证：

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
- QA 地址：`http://127.0.0.1:8095/`，生产 build 来自 `frontend/dist`。
- 桌面 `1440x900`：
  - 选择 `Alpha Warmup` 后出现 bulk action bar。
  - JS 验证：`selectedRowMotion=true`、`bulkMotion=true`、`actionsVisible=true`、`scrollWidth=1440`、`innerWidth=1440`。
  - 点击 `Check health` 后 JS 验证：`checkingVisible=true`、`ariaLabel=Checking health`、`iconPulse=true`、`toolbarBusy=true`。
- 移动 `390x844`：
  - 选择 `Alpha Warmup` card 后 bulk action bar 可见。
  - JS 验证：`selectedCardMotion=true`、`bulkMotion=true`、`scrollWidth=390`、`innerWidth=390`、`overflow=false`。
- `agent-browser console` 无输出；`agent-browser errors` 无输出。
- 截图：
  - `/tmp/cloakbrowser-profile-motion-screens/desktop-selected-bulkbar.png`
  - `/tmp/cloakbrowser-profile-motion-screens/desktop-health-checking.png`
  - `/tmp/cloakbrowser-profile-motion-screens/mobile-card-selected-bulkbar.png`

边界：

- 没有修改后端或 runtime。
- 没有改变批量 health check API 调用。
- 没有解锁高风险批量操作。
- 没有修改 Project Mileage 仓库。
- 没有 push 到任何远端仓库。
