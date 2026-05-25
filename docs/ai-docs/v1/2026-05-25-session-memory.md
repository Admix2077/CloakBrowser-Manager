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
   - 多选状态。
   - `BulkActionBar` 只显示选中数量、清空选择和安全占位动作。
   - 第一批真实批量动作建议从 `health check` 开始，`delete` 必须单独确认闭环。
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
