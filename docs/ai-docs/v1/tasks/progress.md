# CloakBrowser Invisible Manager V1 任务总进度

## 目标

把 `cloakbrowser-invisible-manager` 推进为成熟的指纹浏览器运行时平台，并为 Project Mileage 的远程账号工作台提供底层浏览器能力。

## 使用方式

新 session 或 `/goal` 推进时：

1. 读取 `../2026-05-25-fingerprint-health-ops-plan.md`。
2. 读取 `../proposal.md`、`../high-level-design.md`、`../detailed-design.md`。
3. 读取本文。
4. 找到第一个未完成模块。
5. 读取对应模块文档并逐项执行。
6. 每完成一个小闭环，更新模块文档和本文 checkbox。

## 模块进度

- [x] 01 契约边界与事实源：`01-contract-and-boundaries.md`
- [x] 02 指纹健康引擎：`02-health-engine.md`
- [x] 03 Profile 运营台：`03-profile-operations-console.md`
- [x] 04 Proxy Manager：`04-proxy-manager.md`
- [ ] 05 Project Mileage 会话 Broker：`05-session-broker-project-mileage.md`
- [ ] 06 远程工作台与 VNC 会话：`06-vnc-remote-workspace.md`
- [ ] 07 Automation API 与脚本运行器：`07-automation-api-script-runner.md`
- [ ] 08 Cookie、Profile 导入导出：`08-cookie-profile-import-export.md`
- [ ] 09 模板、批量创建与批量运营：`09-templates-bulk-ops.md`
- [ ] 10 审计、安全与权限：`10-audit-security-rbac.md`
- [x] 11 UI 视觉系统与体验升级：`11-ui-visual-system.md`
- [ ] 12 部署、观测与资源治理：`12-deployment-observability.md`
- [ ] 13 总回归、交付与上线门禁：`13-regression-release.md`

## 当前接力状态（2026-05-27）

最新已提交小闭环：

- 本轮继续 07 Automation API 与脚本运行器，完成 Automation task 响应脱敏收口小闭环：
  - create/get/list/cancel/run 的所有对外 `AutomationTaskResponse.steps` 统一走白名单脱敏。
  - `wait` step 仅回显 `type/ms`。
  - `open_url` step 仅回显 `type/page_ref/wait_until/timeout_ms`。
  - `open_url.url`、query、fragment、未知 step 字段、表单值、token、cookie、secret 不会在 task 响应中回显。
  - `result.steps[]` 仍只记录 `index/type/status`。
  - 当前 `steps` 仍作为内部脚本定义持久化；调用方不得提交 secret。
  - `open_url` 任意 `http/https` 跳转仍属于可信管理 API 能力，不能直接暴露给 Project Mileage App。
- 本轮继续 07 Automation API 与脚本运行器，完成 Script Runner open_url step 小闭环：
  - `POST /api/tasks/{id}/run` 已支持 `open_url` step。
  - `open_url` 只支持 `http` 和 `https` URL。
  - 可选 `page_ref`，默认 `"0"`；可选 `wait_until`，默认 `load`；可选 `timeout_ms`，默认 `30000`。
  - 执行时复用已运行 profile 的既有 page 和 `page.goto()`，不自动启动 profile，不创建新 page。
  - 非法 URL 或非法参数进入 `failed` 并返回 `400`。
  - `run` 响应对 `open_url` step 做白名单脱敏，只回显 `type/page_ref/wait_until/timeout_ms`，不回显完整 URL、query 或 fragment。
  - `result.steps[]` 只记录 `index`、`type`、`status`，不复制 URL、console log、network URL、evaluate result、screenshot、clipboard、表单值或完整 step payload。
  - 当前仍未实现后台队列、并发限制、失败重试、running cancel、click/fill/scroll/evaluate/screenshot step。
- 本轮继续 07 Automation API 与脚本运行器，完成 Script Runner wait step 小闭环：
  - 新增 `POST /api/tasks/{id}/run`。
  - 第一版 run endpoint 只执行已创建的 `queued` task，不让 `POST /api/tasks` 隐式执行脚本。
  - 第一版同步执行并返回最终 `AutomationTaskResponse`。
  - 支持 `wait` step，格式为 `{"type": "wait", "ms": 1..300000}`。
  - 成功状态机：`queued -> running -> succeeded`；失败状态机：`queued -> running -> failed`。
  - 非 `queued` task run 返回 `409`。
  - 执行前要求 profile 已存在且正在运行；run 不自动启动 profile，不读取 proxy/cookie/token/secret。
  - `run` 响应对 `steps` 做白名单脱敏：只回显 step `type`，并仅对 `wait` 回显安全的 `ms`。
  - `result.steps[]` 只记录 `index`、`type`、`status`，不复制 console log、network URL、evaluate result、screenshot、clipboard、表单值或完整 step payload。
  - 当前仍未实现后台队列、并发限制、失败重试、running cancel、click/fill/scroll/evaluate/screenshot step。
- 本轮继续 07 Automation API 与脚本运行器，完成 task 列表与取消小闭环：
  - 新增 `AutomationTasksResponse`。
  - 新增 `GET /api/tasks`：返回所有已持久化 task，并按 `created_at desc` 让最新 task 在前。
  - 新增 `POST /api/tasks/{id}/cancel`：只允许取消 `queued` task。
  - 取消成功后 task 状态更新为 `cancelled`，并写入 `finished_at`。
  - task 不存在时返回 `404`；非 `queued` task 返回 `409`，避免把运行中、已完成或失败 task 伪装成可取消成功。
  - `GET /api/tasks` 当前未提供分页、profile 过滤或权限隔离，只能视为 CloakBrowser 本地管理 API，不能直接暴露给 Project Mileage App。
  - cancel 当前不停止运行中的 Playwright 操作；运行中 task 的中断、补偿和幂等语义留给后续 step runner 小闭环。
  - 本小闭环不执行脚本，不启动 profile，不读取敏感配置，不写 Project Mileage 钱包、订单、权限或续期逻辑。
  - 当前仍未实现并发限制、失败重试和 step 执行器。
- 本轮继续 07 Automation API 与脚本运行器，完成 task 最小 API 小闭环：
  - 新增 `AutomationTaskCreate` 和 `AutomationTaskResponse`。
  - 新增 `POST /api/tasks`：只创建 `queued` task，不执行脚本，不启动 profile，不读取敏感配置。
  - 新增 `GET /api/tasks/{id}`：读取已持久化 task。
  - profile 不存在时返回 `404`。
  - 当前未实现并发限制、失败重试和 step 执行器。
- 本轮继续 07 Automation API 与脚本运行器，完成 automation task 表持久层小闭环：
  - 新增 `automation_tasks` 表，字段覆盖 `id/profile_id/status/steps/result/error/created_at/started_at/finished_at`。
  - 新增 `create_automation_task()`、`get_automation_task()`、`list_automation_tasks()`、`update_automation_task()`。
  - `steps` 和 `result` 以 JSON 存储，读取时恢复结构化对象。
  - 当前未开放 `/api/tasks`，未执行脚本，未引入并发限制或重试。
- 本轮补齐 07 Automation API 中文契约文档：
  - 新增 `../automation-api-contract.md`。
  - 覆盖现有 Automation REST endpoint、请求/响应字段、错误规则、Script Runner step 复用建议。
  - 明确 console logs 和 network summary 只保留进程内 ring buffer，不写 DB、audit 或普通日志。
  - 明确 Project Mileage App 不能直接调用 CloakBrowser Automation/runtime API，只能经 Payload 安全 DTO 间接接入。
- 本轮继续 07 Automation API 与脚本运行器，完成 network summary 小闭环：
  - 新增 `AutomationNetworkEvent` 和 `AutomationNetworkSummaryResponse`。
  - 新增 `GET /api/profiles/{profile_id}/automation/pages/{page_ref}/network-summary`。
  - 通过 Playwright `request`、`response`、`requestfailed` 事件捕获低敏摘要。
  - 每个 page 仅在进程内内存保留最近 200 条，不新增 DB 表，不写 `audit_events`，不把 network URL 或失败详情写入 logger。
  - URL 丢弃 username、password、query、fragment、params；不采集 headers、cookie、Authorization、body。
  - 目标红灯：`404 Not Found`。
  - 目标绿灯：`test_automation_network_summary_redacts_urls_and_returns_recent_events` 和 `test_automation_network_summary_keeps_recent_redacted_events` 通过。
- 本轮继续 07 Automation API 与脚本运行器，完成 console logs 小闭环：
  - 新增 `AutomationConsoleLogEntry` 和 `AutomationConsoleLogsResponse`。
  - 新增 `GET /api/profiles/{profile_id}/automation/pages/{page_ref}/console-logs`。
  - 通过 Playwright `page.on("console", ...)` 捕获 console 消息。
  - 每个 page 仅在进程内内存保留最近 200 条，不新增 DB 表，不写 `audit_events`，不把 console 文本写入 logger。
  - 目标红灯：`404 Not Found`。
  - 目标绿灯：`test_automation_console_logs_returns_in_memory_page_logs` 和 `test_automation_console_logs_captures_recent_console_messages` 通过。
- 本轮继续 07 Automation API 与脚本运行器，完成 scroll 小闭环：
  - 新增 `AutomationScrollRequest`。
  - 新增 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/scroll`。
  - 复用既有运行中 profile / page 查找与 `AutomationPageResponse`。
  - 不依赖 Chromium CDP；继续基于 Firefox/invisible_playwright 的 Playwright page API。
  - 目标红灯：`405 Method Not Allowed`。
  - 目标绿灯：`test_automation_scroll_scrolls_page_and_returns_page` 通过。
- 本轮继续 07 Automation API 与脚本运行器，完成 keyboard type 小闭环：
  - 新增 `AutomationKeyboardTypeRequest`。
  - 新增 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/keyboard/type`。
  - 复用既有运行中 profile / page 查找与 `AutomationPageResponse`。
  - 不依赖 Chromium CDP；继续基于 Firefox/invisible_playwright 的 Playwright page API。
  - 目标红灯：`405 Method Not Allowed`。
  - 目标绿灯：`test_automation_keyboard_type_types_text_and_returns_page` 通过。
- 本轮继续 07 Automation API 与脚本运行器，完成 fill 小闭环：
  - 新增 `AutomationFillRequest`。
  - 新增 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/fill`。
  - 复用既有运行中 profile / page 查找与 `AutomationPageResponse`。
  - 不依赖 Chromium CDP；继续基于 Firefox/invisible_playwright 的 Playwright page API。
  - 目标红灯：`405 Method Not Allowed`。
  - 目标绿灯：`test_automation_fill_fills_selector_and_returns_page` 通过。
- 本轮继续 07 Automation API 与脚本运行器，完成 click 小闭环：
  - 新增 `AutomationClickRequest`。
  - 新增 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/click`。
  - 复用既有运行中 profile / page 查找与 `AutomationPageResponse`。
  - 不依赖 Chromium CDP；继续基于 Firefox/invisible_playwright 的 Playwright page API。
  - 目标红灯：`405 Method Not Allowed`。
  - 目标绿灯：`test_automation_click_clicks_selector_and_returns_page` 通过。
- 本轮转入 07 Automation API 与脚本运行器，完成 wait-for-selector 小闭环：
  - 新增 `AutomationWaitForSelectorRequest`。
  - 新增 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/wait-for-selector`。
  - 复用既有运行中 profile / page 查找与 `AutomationPageResponse`。
  - 不依赖 Chromium CDP；继续基于 Firefox/invisible_playwright 的 Playwright page API。
  - 目标红灯：`405 Method Not Allowed`。
  - 目标绿灯：`test_automation_wait_for_selector_waits_and_returns_page` 通过。
  - 07 文档同步标记既有 page create/page close 与本轮 wait-for-selector 已完成。
- `087097a add proxy provider preset manager` 是本轮开始前最新 commit。
- 本轮完成 05/06 的 CloakBrowser 侧最小 runtime session API、runtime viewer token、runtime terminate、runtime renew、runtime audit 和 runtime VNC viewer audit 小闭环：
  - `RUNTIME_SERVICE_TOKEN` / `X-Runtime-Service-Token`。
  - `runtime_sessions` 表和最小 CRUD。
  - `POST /api/runtime/sessions`。
  - `GET /api/runtime/sessions/{id}`。
  - `POST /api/runtime/sessions/{id}/viewer-token`。
  - `WebSocket /api/runtime/sessions/{id}/vnc`。
  - `POST /api/runtime/sessions/{id}/terminate`。
  - `POST /api/runtime/sessions/{id}/renew`。
  - 通用 `audit_events` 表。
  - runtime service API 成功动作写 audit。
  - runtime VNC 成功 connected/disconnected 写 audit。
  - runtime VNC 失败事件写低敏 reason code audit。
  - EnvironmentStrip 支持低敏业务 session 标识和可选 runtime viewer URL。
  - viewer 访问失败时显示固定安全提示，不把 viewer token、内部 ticket、完整 VNC URL、noVNC 原始 reason 或初始化异常 message 渲染到 UI。
  - 从 profile 创建 runtime session。
  - 从 template 创建 runtime session 并复制 template 指纹字段。
  - runtime response 不包含 wallet/order/billing 字段，也不暴露内部 `viewer_token_hash`。
  - viewer token 过期或错误时不能连接 runtime VNC。
  - terminate 后 session 标记为 `terminated`，viewer token 被撤销，runtime VNC 失效。
  - renew 后 active session lease 延长，短生命周期 viewer token 保持自身 TTL。
  - audit metadata 不记录 viewer token、viewer URL、viewer token hash、runtime service token、proxy password、cookie、Origin 原文、请求头或 URL query。
  - runtime VNC failure audit metadata 仅记录固定 `reason_code`，不记录 Origin 原文、后端 VNC 地址或异常 message。
- 05/06 模块整体仍保持未完成；不要勾选顶层 05 或 06。
- Project Mileage 跨仓契约提案已落地：`../project-mileage-remote-workspace-contract-proposal.md`。未确认前不改 app/payload。

下一步建议：

1. 继续 CloakBrowser 独立侧 07 Automation API，小步实现第一版 Script Runner executor 的最小 step，例如 `wait`，保持不启动 profile、不读取敏感配置、不把 console/network/evaluate/screenshot 输出默认写入 task result/log。
2. 等 Jeff/主 agent 确认 Project Mileage remote workspace contract proposal 的 API、DTO、权限、扣费、viewer token 刷新和补偿策略。
3. 未确认前不改 Project Mileage app/payload；runtime viewer token 失效/不可用的 CloakBrowser 前端固定安全提示已完成，但不替代 Payload/App 的刷新、重开和权限契约。
4. 确认跨仓契约后，Payload 先做只读 remote accounts/session 数据模型，再逐步做 session 创建、viewer token、renew、terminate。

## 推荐执行顺序

第一阶段：CloakBrowser 独立成熟化。

1. 01 契约边界与事实源。
2. 02 指纹健康引擎。
3. 03 Profile 运营台。
4. 11 UI 视觉系统与体验升级。
5. 04 Proxy Manager。
6. 09 模板、批量创建与批量运营。

第二阶段：运行时平台化。

1. 10 审计、安全与权限。
2. 07 Automation API 与脚本运行器。
3. 08 Cookie、Profile 导入导出。
4. 12 部署、观测与资源治理。

第三阶段：Project Mileage 联动。

1. 05 Project Mileage 会话 Broker。
2. 06 远程工作台与 VNC 会话。
3. 13 总回归、交付与上线门禁。

## 全局验证命令

Manager 后端：

```bash
. .venv/bin/activate && python -m pytest backend/tests -q
```

Manager 前端：

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

Docker：

```bash
docker build --network=host --platform linux/amd64 -t invisible-browser-manager:latest .
```

Project Mileage 跨仓阶段才运行：

```bash
cd /home/jeff/code/project-mileage-v3-app && pnpm test
cd /home/jeff/code/project-mileage-v3-app && pnpm lint
cd /home/jeff/code/project-mileage-v3-app && pnpm build
cd /home/jeff/code/project-mileage-v3-payload && pnpm vitest run
cd /home/jeff/code/project-mileage-v3-payload && pnpm lint
cd /home/jeff/code/project-mileage-v3-payload && pnpm build
```

## 全局禁止事项

- 不把 Chromium CDP 当成基础能力。
- 不覆盖用户未授权的 git 改动。
- 不把 Project Mileage 的钱包、订单、权限逻辑写进 CloakBrowser。
- 不在 Project Mileage 前端伪造远程会话、VNC token、倒计时或成功态。
- 不把 proxy 密码、cookie、VNC token、AUTH_TOKEN 写入日志或审计 metadata。
- 不用第三方检测站抓取结果作为 V1 必需依赖。
