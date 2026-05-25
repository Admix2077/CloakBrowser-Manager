# CloakBrowser Invisible Manager V1 总控主文档

日期：2026-05-25

## 1. 文档用途

本文是 `docs/ai-docs/v1` 的主控入口。后续开启新的 Codex session 或使用 `/goal` 推进时，优先读取本文，再按本文链接继续读取需求、概要设计、详细设计和任务拆分。

所有相关文档都必须留在：

```text
/home/jeff/code/cloakbrowser-invisible-manager/docs/ai-docs/v1
```

不要把本文档树写到上级目录，不要写到 `project-mileage-v3-app` 或 `project-mileage-v3-payload`，除非后续进入真正跨仓实现阶段并另行确认。

## 2. 最终目标

把 `cloakbrowser-invisible-manager` 从“本地 profile 配置面板 + VNC Viewer”升级成一个成熟的指纹浏览器与远程账号运行时平台。

终局产品形态：

- `cloakbrowser-invisible-manager` 负责浏览器运行时、profile、指纹参数、代理、GeoIP、VNC、自动化、健康检测、批量运营和运行审计。
- `project-mileage-v3-app` 的用户端“远程工作台”和运营端“远程监控”负责业务入口、订单/账号上下文、用户操作界面和运营管理界面。
- `project-mileage-v3-payload` 负责业务事实源：用户权限、账号订单、钱包扣费、会话授权、审计记录和敏感数据白名单。
- 三者通过明确 API 契约协作：Project Mileage 不直接暴露浏览器内核和 VNC token；CloakBrowser 不直接决定业务扣费、账号归属和运营权限。

最终用户体验：

- 用户购买或获得远程账号权限后，可以在 Project Mileage 的远程工作台一键进入隔离浏览器环境。
- 运营可以在 Project Mileage 的远程监控中查看远程会话状态、账号池健康、异常风险和审计记录。
- 管理员可以在 CloakBrowser Manager 中管理底层 profile、代理、指纹健康、批量动作、自动化脚本和运行资源。
- 系统能自动保持出口 IP、timezone、locale、language、screen、GPU、hardware concurrency 等指纹状态一致，并能提示风险。

## 3. 文档树

基础设计文档：

- [需求文档 proposal.md](./proposal.md)
- [概要设计 high-level-design.md](./high-level-design.md)
- [详细设计 detailed-design.md](./detailed-design.md)
- [Session 记忆 2026-05-25-session-memory.md](./2026-05-25-session-memory.md)

任务总览：

- [任务总进度 tasks/progress.md](./tasks/progress.md)

模块任务文档：

- [01 契约边界与事实源](./tasks/01-contract-and-boundaries.md)
- [02 指纹健康引擎](./tasks/02-health-engine.md)
- [03 Profile 运营台](./tasks/03-profile-operations-console.md)
- [04 Proxy Manager](./tasks/04-proxy-manager.md)
- [05 Project Mileage 会话 Broker](./tasks/05-session-broker-project-mileage.md)
- [06 远程工作台与 VNC 会话](./tasks/06-vnc-remote-workspace.md)
- [07 Automation API 与脚本运行器](./tasks/07-automation-api-script-runner.md)
- [08 Cookie、Profile 导入导出](./tasks/08-cookie-profile-import-export.md)
- [09 模板、批量创建与批量运营](./tasks/09-templates-bulk-ops.md)
- [10 审计、安全与权限](./tasks/10-audit-security-rbac.md)
- [11 UI 视觉系统与体验升级](./tasks/11-ui-visual-system.md)
- [12 部署、观测与资源治理](./tasks/12-deployment-observability.md)
- [13 总回归、交付与上线门禁](./tasks/13-regression-release.md)

## 4. 当前事实基线

当前仓库：

```text
/home/jeff/code/cloakbrowser-invisible-manager
```

当前关键提交：

```text
aa84726 fix: sync geoip language timezone fingerprints
```

当前已具备能力：

- FastAPI 后端。
- React + Vite 前端。
- SQLite profile 数据库。
- `invisible_playwright` / Firefox 内核。
- KasmVNC + noVNC Viewer。
- profile CRUD。
- proxy、timezone、locale、screen、GPU、hardware concurrency、color scheme、humanize、launch args。
- GeoIP fallback：`ip-api.com` -> `ipapi.co` -> `ipwho.is`。
- `last_geoip_*` 自动检测结果。
- `timezone` / `locale` 手动覆盖字段。
- Automation REST API。
- clipboard sync。
- Docker 部署。

最近已验证：

- 后端测试：`205 passed`。
- 前端测试：`22 passed`。
- 前端 build：通过。
- BrowserScan 复验：`Browser fingerprint authenticity: 100%`。
- BrowserScan 文本中无 `Language mismatch` / `Different time zones`。

## 5. Project Mileage 集成事实

`project-mileage-v3-app` 当前已有安全占位：

- `/app/remote-workspace`
- `/app/remote-workspace/[id]/vnc`
- `/ops/remote-monitor`

这些页面目前明确不接入真实远程能力，因为 Payload contract 尚未确认：

- 用户端远程账号列表。
- 会话列表。
- 会话激活。
- 续期。
- 进入远程桌面。
- 会话详情。
- 屏幕流。
- 控制 mutation。
- VNC token 生命周期。
- 钱包扣费。
- 屏幕访问权限。
- 审计 metadata。
- 异常恢复策略。

所以本项目的最终设计必须遵守边界：

- CloakBrowser 可以提供运行时 API，但不能绕过 Payload 直接决定用户是否有权进入某个账号。
- Project Mileage App 可以展示远程工作台，但不能在前端伪造 VNC token、模拟远程画面或本地倒计时成功态。
- Payload 必须成为远程会话授权、扣费、审计和敏感字段白名单的事实源。

## 6. 产品路线

### Phase 0：契约和文档准备

目标：把最终产品拆成可执行文档树，明确三仓边界。

产物：

- 本文。
- `proposal.md`
- `high-level-design.md`
- `detailed-design.md`
- `tasks/progress.md`
- 各模块任务文档。

### Phase 1：CloakBrowser 独立成熟化

目标：即使不接 Project Mileage，也让 manager 成为可独立使用的成熟指纹浏览器运营台。

范围：

- 指纹健康引擎。
- Profile 运营台。
- 轻检测。
- 批量 launch/stop/check。
- Viewer 环境条。
- Proxy Manager 第一版。
- UI 视觉升级。

### Phase 2：运行时平台化

目标：把 manager 从单机工具升级为可被业务系统调用的运行时服务。

范围：

- 运行时 API key / service token。
- profile lease。
- session broker。
- 临时 VNC access token。
- 运行状态 webhook。
- operation audit。
- 资源限制和并发策略。

### Phase 3：Project Mileage 远程工作台联动

目标：让用户端远程工作台和运营端远程监控接入真实浏览器会话。

范围：

- Payload 会话模型。
- 钱包扣费和续期。
- 用户端远程账号列表。
- 会话启动和进入远程桌面。
- 运营远程监控。
- 审计与异常恢复。

### Phase 4：自动化、模板、批量运营

目标：达到成熟指纹浏览器产品常见的高效率运营能力。

范围：

- Profile template。
- Proxy template。
- 批量创建。
- CSV 导入导出。
- Cookie 导入导出。
- Script Runner。
- Cookie warm-up。
- 批量打开 URL。
- 窗口编排。

### Phase 5：团队化、风控和商业化能力

目标：支持多人运营、权限分层、审计、风控和规模化运行。

范围：

- RBAC。
- 操作审计中心。
- 风险评分。
- profile 使用历史。
- 异常告警。
- resource quota。
- team workspace。
- 租户隔离。

## 7. 成熟产品能力池

竞品调研后的可内化能力：

- AdsPower 类能力：
  - 批量 profile 创建。
  - proxy list。
  - proxy tag。
  - 动态 IP 自动匹配 timezone/location。
  - RPA。
  - synchronizer。
  - team members。
  - action logs。
- GoLogin 类能力：
  - folders。
  - tags。
  - bulk actions。
  - cookie bot。
  - cookie import/export。
  - profile CSV import/export。
  - team sharing。
- Multilogin 类能力：
  - profile template。
  - proxy template。
  - profile export。
  - team roles。
  - CLI/API/script runner。
- Dolphin Anty 类能力：
  - profile status。
  - notes。
  - folders。
  - synchronizer。
  - scenarios。
  - teamwork。
- Octo Browser 类能力：
  - bulk profile creation。
  - quick edit。
  - profile history。
  - API 启动。
  - profile transfer。
  - action log。
- MoreLogin 类能力：
  - profile list 快速搜索。
  - quick edit。
  - proxy detection。
  - bulk operations。
  - Local API。

内化原则：

- 先做能被当前 Firefox/invisible_playwright 支撑的能力。
- 不为了模仿竞品而引入无法验证的“安全承诺”。
- 不把 Chromium CDP 当成基础假设。
- 不把 Project Mileage 的业务权限放到 CloakBrowser 内部私自判断。

## 8. /goal 推进方式

建议后续新 session 使用以下口径：

1. 读取本文。
2. 读取 `proposal.md`、`high-level-design.md`、`detailed-design.md`。
3. 读取 `tasks/progress.md`。
4. 找到第一个未完成模块。
5. 读取对应模块任务文档。
6. 按任务文档逐项推进。
7. 每完成一个小闭环：
   - 跑对应测试。
   - 更新对应模块任务文档 checkbox。
   - 更新 `tasks/progress.md`。
   - 如果有代码改动，按仓库规则提交。

如果进入跨仓实现阶段：

- `cloakbrowser-invisible-manager`、`project-mileage-v3-app`、`project-mileage-v3-payload` 必须分别检查状态、分别验证、分别提交。
- 不允许把三个仓库的变更混成一个含糊状态。

## 9. 当前待确认问题

这些问题不会阻止 CloakBrowser 独立成熟化，但会影响 Project Mileage 联动阶段：

- 远程会话是按分钟扣费、按次扣费，还是随账号订单赠送？
- 用户是否允许同时打开多个远程账号？
- 运营是否允许实时接管用户正在使用的会话？
- 远程会话是否需要录屏、截图或只保留审计事件？
- Profile 与 Project Mileage 账号库存是一对一、一对多，还是按会话临时绑定？
- Proxy 成本和归属是否要计入订单或运营成本？
- 是否需要团队/租户隔离，还是先做单管理员单机部署？
- 是否允许自动化脚本在用户远程会话中运行，还是只允许运营后台运行？

默认策略：

- 未确认前，Project Mileage 继续保持远程工作台安全占位。
- CloakBrowser 先独立完成底层运行时能力。
