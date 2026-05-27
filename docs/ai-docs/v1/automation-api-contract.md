# Automation API 契约

日期：2026-05-27

## 目标

本文固定 CloakBrowser 当前 Automation REST API 的可用契约，供后续 Script Runner、运营台和 Project Mileage 远程账号工作台间接接入时参考。

Automation API 只操作已经运行中的 profile browser context。它不负责 Project Mileage 的用户权限、订单、钱包、扣费、续期或账号归属判断；这些业务事实必须留在 Project Mileage Payload。

## 通用规则

- 所有接口基于 `Firefox / invisible_playwright` 的 Playwright page API，不依赖 Chromium CDP。
- 所有 page 级接口都要求 profile 已运行，否则返回 `404 Profile not running`。
- `page_ref` 可以是 page index，也可以是 pages list 返回的 `page_id`。
- Playwright 操作失败统一返回 `400`，page 不存在返回 `404`。
- 成功的 page 操作默认返回 `AutomationPageResponse`：

```json
{
  "page_id": "uuid",
  "index": 0,
  "url": "https://example.com/",
  "title": "Example"
}
```

## 已有接口

### 获取 Automation 信息

```http
GET /api/profiles/{profile_id}/automation
```

返回：

```json
{
  "profile_id": "profile-id",
  "engine": "invisible_playwright",
  "status": "running",
  "pages_url": "/api/profiles/profile-id/automation/pages"
}
```

### Page 列表

```http
GET /api/profiles/{profile_id}/automation/pages
```

返回：

```json
{
  "pages": [
    {
      "page_id": "uuid",
      "index": 0,
      "url": "about:blank",
      "title": "Blank"
    }
  ]
}
```

### 新建 Page

```http
POST /api/profiles/{profile_id}/automation/pages
```

成功返回新 page 的 `AutomationPageResponse`，状态码 `201`。

### 关闭 Page

```http
DELETE /api/profiles/{profile_id}/automation/pages/{page_ref}
```

返回：

```json
{"ok": true}
```

### 跳转 URL

```http
POST /api/profiles/{profile_id}/automation/pages/{page_ref}/goto
```

请求：

```json
{
  "url": "https://example.com",
  "wait_until": "load",
  "timeout_ms": 30000
}
```

字段：

- `wait_until`: `commit | domcontentloaded | load | networkidle`，默认 `load`。
- `timeout_ms`: `1..300000`，默认 `30000`。

### 等待 Selector

```http
POST /api/profiles/{profile_id}/automation/pages/{page_ref}/wait-for-selector
```

请求：

```json
{
  "selector": "#ready",
  "state": "visible",
  "timeout_ms": 30000
}
```

字段：

- `selector`: 长度 `1..10000`。
- `state`: `attached | detached | visible | hidden`，默认 `visible`。
- `timeout_ms`: `1..300000`，默认 `30000`。

### Click

```http
POST /api/profiles/{profile_id}/automation/pages/{page_ref}/click
```

请求：

```json
{
  "selector": "#submit",
  "timeout_ms": 30000
}
```

### Fill

```http
POST /api/profiles/{profile_id}/automation/pages/{page_ref}/fill
```

请求：

```json
{
  "selector": "#email",
  "value": "user@example.com",
  "timeout_ms": 30000
}
```

字段：

- `value`: 长度上限 `1048576`。

### Keyboard Type

```http
POST /api/profiles/{profile_id}/automation/pages/{page_ref}/keyboard/type
```

请求：

```json
{
  "text": "hello world",
  "delay_ms": 0
}
```

字段：

- `text`: 长度 `1..1048576`。
- `delay_ms`: `0..10000`，默认 `0`。

### Scroll

```http
POST /api/profiles/{profile_id}/automation/pages/{page_ref}/scroll
```

请求：

```json
{
  "delta_x": 0,
  "delta_y": 600
}
```

字段：

- `delta_x`: `-100000..100000`，默认 `0`。
- `delta_y`: `-100000..100000`，默认 `0`。

实现使用页面内 `window.scrollBy(deltaX, deltaY)`，不依赖鼠标滚轮底层实现。

### Evaluate

```http
POST /api/profiles/{profile_id}/automation/pages/{page_ref}/evaluate
```

请求：

```json
{
  "expression": "document.title"
}
```

字段：

- `expression`: 长度 `1..200000`。

返回：

```json
{
  "result": "Example"
}
```

### Screenshot

```http
POST /api/profiles/{profile_id}/automation/pages/{page_ref}/screenshot
```

请求：

```json
{
  "full_page": false
}
```

返回 `image/png`。

### Console Logs

```http
GET /api/profiles/{profile_id}/automation/pages/{page_ref}/console-logs
```

返回：

```json
{
  "logs": [
    {
      "type": "log",
      "text": "ready",
      "location": {
        "url": "https://example.com/app.js",
        "lineNumber": 4,
        "columnNumber": 2
      }
    }
  ]
}
```

边界：

- 通过 `page.on("console", ...)` 捕获。
- 只保存在运行中 page 对象的进程内内存字段。
- 每个 page 最多保留最近 200 条。
- 不新增 DB 表，不写 `audit_events`，不把 console 文本写入 logger。
- profile stop 后缓存随 page 对象释放。

### Network Summary

```http
GET /api/profiles/{profile_id}/automation/pages/{page_ref}/network-summary
```

返回：

```json
{
  "events": [
    {
      "event": "request",
      "method": "GET",
      "url": "https://example.com/api/items",
      "resource_type": "xhr",
      "status": null,
      "failure": null
    }
  ]
}
```

边界：

- 通过 `page.on("request" | "response" | "requestfailed", ...)` 捕获。
- 只保存在运行中 page 对象的进程内内存字段。
- 每个 page 最多保留最近 200 条。
- URL 只保留 scheme、host、port 和 path。
- URL 必须丢弃 username、password、query、fragment、params。
- 不采集 headers、cookie、Authorization、request body、response body。
- 不新增 DB 表，不写 `audit_events`，不把 network URL 或失败详情写入 logger。
- `requestfailed` 只返回固定 `failure: "request_failed"`。

## Clipboard

已有独立 clipboard API：

```http
POST /api/profiles/{profile_id}/clipboard
GET /api/profiles/{profile_id}/clipboard
```

`POST` 请求：

```json
{
  "text": "clipboard text"
}
```

`text` 长度上限为 `1048576`。

## Automation Tasks

### 创建 Task

```http
POST /api/tasks
```

请求：

```json
{
  "profile_id": "profile-id",
  "steps": [
    {"type": "wait", "ms": 1000}
  ]
}
```

当前行为：

- 只创建 `queued` task。
- `steps` 长度为 `1..200`。
- profile 不存在时返回 `404`。
- 不执行脚本，不启动 profile，不读取敏感配置。
- 对外响应中的 `steps` 统一走白名单脱敏；`open_url.url`、query、fragment 和未知 step 字段不会在响应中回显。
- 入库前会按 step 类型做执行字段白名单裁剪，保留 runner 必须使用的字段，丢弃未知字段；例如 `screenshot` 仅持久化 `type/page_ref/full_page`，不会持久化调用方附带的 `path`、`filename`、`base64` 或 `note`。

返回：

```json
{
  "id": "task-id",
  "profile_id": "profile-id",
  "status": "queued",
  "steps": [{"type": "wait", "ms": 1000}],
  "result": null,
  "error": null,
  "created_at": "2026-05-27T00:00:00+00:00",
  "started_at": null,
  "finished_at": null
}
```

### Task 列表

```http
GET /api/tasks
```

可选 query：

- `profile_id`: 指定 profile 时只返回该 profile 的 task；profile 不存在时返回 `404 Profile not found`。
- `limit`: 可选，范围 `1..500`；不传时保持兼容行为，返回匹配条件下的全部 task。
- `offset`: 可选，范围 `0..`，默认 `0`；仅在传入 `limit` 时生效。

返回：

```json
{
  "tasks": [
    {
      "id": "task-id",
      "profile_id": "profile-id",
      "status": "queued",
      "steps": [{"type": "wait", "ms": 1000}],
      "result": null,
      "error": null,
      "created_at": "2026-05-27T00:00:00+00:00",
      "started_at": null,
      "finished_at": null
    }
  ]
}
```

当前行为：

- 未传 `profile_id` 时返回所有已持久化 task；传入 `profile_id` 时仅返回该 profile 的 task。
- 按 `created_at desc` 排序，最新 task 在前。
- `limit/offset` 在 profile 过滤后应用，用于前端 task log viewer 或运营台分页加载。
- 对外响应中的 `steps` 统一走白名单脱敏；`open_url.url`、query、fragment 和未知 step 字段不会在响应中回显。
- 对外响应不包含内部 worker lease 元数据；即使 DB 中存在 `lease_owner` 或 `lease_expires_at`，`create/get/list/cancel/retry/run` 仍只返回 `AutomationTaskResponse` 白名单字段。
- 当前未提供权限隔离，只能视为 CloakBrowser 本地管理 API，不能直接暴露给 Project Mileage App。
- Project Mileage 后续需要 task 列表时，必须由 Payload 按账号归属、权限和审计策略输出安全 DTO。

### 前端 Task Log Viewer

当前 CloakBrowser 管理台前端提供只读 `Automation` 页面：

- 入口：顶部 `Automation` 分段按钮。
- 数据源：`api.listAutomationTasks({ limit: 50 })` 调用 `GET /api/tasks?limit=50`。
- 展示内容：
  - task 短 ID。
  - profile 短 ID。
  - status。
  - step 低敏摘要。
  - `result.steps[]` 低敏摘要。
  - task 固定错误文案。
  - created/finished 时间。
- 支持本地 status filter segmented control：
  - `All`：展示最近 50 条。
  - `Running`：展示 `running | cancel_requested`。
  - `Failed`：展示 `failed`。
  - `Finished`：展示 `succeeded | cancelled`。
- status filter 只过滤当前已加载的最近 50 条 task，不新增 API query，不改变 task 状态，不触发 run/cancel/retry。
- 支持本地 task/profile 搜索框：
  - 搜索只匹配 `task.id` 和 `task.profile_id`。
  - 搜索与 status filter 组合生效。
  - 搜索只过滤当前已加载的最近 50 条 task，不新增 API query，不调用新的后端接口。
  - 搜索不匹配、不读取、不渲染 `steps`、`result`、`error` 或任何自动化 payload 内容。
- 表格行提供只读详情入口，打开后在 drawer 中展示该 task 的完整低敏 `steps` 和完整低敏 `result.steps[]`，不再使用表格摘要的 4 条截断上限。
- 前端只渲染 step 白名单字段：`type/page_ref/ms/wait_until/state/timeout_ms/delay_ms/delta_x/delta_y/full_page`。
- 前端只渲染 result 白名单字段：`index/type/status`。
- 前端不渲染 `open_url.url`、URL query、fragment、token、selector、fill value、keyboard text、evaluate expression/result、screenshot bytes/base64/path、clipboard、console text、network URL、headers、body 或未知字段。
- 前端不提供 `run`、`cancel`、`retry` 按钮，详情 drawer 也不提供这些动作，避免在日志页面制造高权限自动化入口。
- 该页面仍属于 CloakBrowser 本地可信管理台，不是 Project Mileage App 对接面；Project Mileage App 后续只能通过 Payload 安全 DTO 获取经过账号归属、订单、权限和审计裁剪后的数据。

### Task 详情

```http
GET /api/tasks/{id}
```

task 不存在时返回 `404`。对外响应中的 `steps` 统一走白名单脱敏。

### 取消 Task

```http
POST /api/tasks/{id}/cancel
```

当前行为：

- `queued` task 取消后状态更新为 `cancelled`，并写入 `finished_at`。
- `running` task 取消后不会伪造已停止，而是更新为 `cancel_requested`，`finished_at` 保持 `null`，等待 runner 在 step 边界协作式收束。
- 已经处于 `cancel_requested` 的 task 重复取消会幂等返回当前 task。
- task 不存在时返回 `404`。
- 已结束 task 返回 `409 Only queued or running automation tasks can be cancelled`。
- 当前取消接口不终止浏览器、不强制打断正在 await 的 Playwright 操作、不修改 Project Mileage 订单、钱包、权限或续期状态。
- 对外响应中的 `steps` 统一走白名单脱敏。
- `cancel_requested` 会继续占用同一 `profile_id` 的 task 执行槽；同 profile 新 task run 返回 `409 Automation profile already has a running task`，直到原 task 被 runner 收束为 `cancelled`。
- runner 在每个 step 开始前检查 `cancel_requested`；如果已请求取消，当前未执行 step 会在 `result.steps[]` 中记录为低敏 `cancelled` 摘要。
- 对 `wait` step，runner 会在 sleep 返回后再次检查取消请求；如果后面还有 step，会把下一步记录为 `cancelled` 且不执行它。

### 重试 Task

```http
POST /api/tasks/{id}/retry
```

当前行为：

- 只允许对已结束 task 创建重试任务，允许状态为 `failed | cancelled | succeeded`。
- `queued`、`running` 或 `cancel_requested` task 返回 `409 Only finished automation tasks can be retried`。
- task 不存在时返回 `404`。
- profile 不存在时返回 `404 Profile not found`。
- 成功后创建一个新的 `queued` task，并返回新 task，状态码 `201`。
- 原 task 保持原状态、`result`、`error`、`started_at` 和 `finished_at` 不变。
- retry 不会自动运行脚本，不启动 profile，不绕过 `run` 的 profile running 检查或 profile 级并发限制。
- retry 复制的是已持久化并裁剪过的内部 `steps`，对外响应继续统一脱敏；`open_url.url`、query、fragment、selector、表单值、evaluate expression、screenshot 内容、token 和未知字段不会在响应中回显。
- retry 只是显式再排队一次，不判断 step 是否有副作用；涉及点击、填写、跳转等副作用脚本时，调用方必须在可信管理侧确认可重复执行。
- 当前 retry 不写 Project Mileage 订单、钱包、权限、扣费、续期或 viewer token 状态。
- Project Mileage 后续需要 retry 能力时，必须由 Payload 按账号归属、订单状态、权限、审计和幂等策略输出安全 DTO；App 不能直连该接口。

### 运行 Task

```http
POST /api/tasks/{id}/run
```

当前行为：

- 只允许运行 `queued` task；非 `queued` task 返回 `409`。
- task 不存在时返回 `404`。
- profile 不存在时返回 `404 Profile not found`。
- profile 未运行时返回 `404 Profile not running`。
- 同一 `profile_id` 已存在其他 `running` 或 `cancel_requested` task 时返回 `409 Automation profile already has a running task`；被拒绝的 queued task 保持 `queued`，不写 `started_at`、`finished_at` 或 `result`。
- profile 级并发限制不影响不同 profile 的 task 并行运行。
- 第一版同步执行，响应返回最终 `AutomationTaskResponse`。
- 不自动启动 profile，不读取 proxy/cookie/token/secret，不修改 Project Mileage 订单、钱包、权限或续期状态。
- 状态机：
  - 成功：`queued -> running -> succeeded`。
  - 失败：`queued -> running -> failed`。
  - 协作式取消：`queued -> running -> cancel_requested -> cancelled`。
- 当前支持的 step：
  - `open_url`：`{"type": "open_url", "url": "https://example.com", "page_ref": "0", "wait_until": "load", "timeout_ms": 30000}`。
  - `wait_for_selector`：`{"type": "wait_for_selector", "selector": "#ready", "page_ref": "0", "state": "visible", "timeout_ms": 30000}`。
  - `click`：`{"type": "click", "selector": "#submit", "page_ref": "0", "timeout_ms": 30000}`。
  - `fill`：`{"type": "fill", "selector": "#email", "value": "user@example.com", "page_ref": "0", "timeout_ms": 30000}`。
  - `keyboard_type`：`{"type": "keyboard_type", "text": "hello", "page_ref": "0", "delay_ms": 25}`。
  - `evaluate`：`{"type": "evaluate", "expression": "document.title", "page_ref": "0"}`。
  - `screenshot`：`{"type": "screenshot", "page_ref": "0", "full_page": false}`。
  - `scroll`：`{"type": "scroll", "page_ref": "0", "delta_x": 0, "delta_y": 600}`。
  - `wait`：`{"type": "wait", "ms": 1..300000}`，内部执行 `asyncio.sleep(ms / 1000)`。
- 当前不支持的 step 会让 task 进入 `failed`，并返回 `400`。
- 当前非法 `wait.ms` 会让 task 进入 `failed`，并返回 `400`。
- 当前非法 `open_url.url`、`wait_until` 或 `timeout_ms` 会让 task 进入 `failed`，并返回 `400`。
- 当前非法 `wait_for_selector.selector`、`state` 或 `timeout_ms` 会让 task 进入 `failed`，并返回 `400`。
- 当前非法 `click.selector` 或 `timeout_ms` 会让 task 进入 `failed`，并返回 `400`。
- 当前非法 `fill.selector`、`value` 或 `timeout_ms` 会让 task 进入 `failed`，并返回 `400`。
- 当前非法 `keyboard_type.text` 或 `delay_ms` 会让 task 进入 `failed`，并返回 `400`。
- 当前非法 `evaluate.expression` 会让 task 进入 `failed`，并返回 `400`。
- 当前非法 `screenshot.full_page` 会让 task 进入 `failed`，并返回 `400`；`full_page` 必须是布尔值。
- 当前非法 `scroll.delta_x` 或 `scroll.delta_y` 会让 task 进入 `failed`，并返回 `400`。
- `cancel_requested` 只在 step 边界生效，不承诺中断正在执行或正在 await 的 Playwright 操作；收束为 `cancelled` 后 `result.steps[]` 只包含已执行 step 的 `succeeded/failed` 低敏摘要和一个未执行 step 的 `cancelled` 低敏摘要。
- 所有 task 对外响应，包括 create/get/list/cancel/run，都会对 `steps` 做白名单脱敏：只回显 step `type`；对 `wait` 回显安全的 `ms`；对 `open_url` 只回显 `page_ref/wait_until/timeout_ms`，不回显完整 URL、query 或 fragment；对 `wait_for_selector` 只回显 `page_ref/state/timeout_ms`，不回显 selector；对 `click` 只回显 `page_ref/timeout_ms`，不回显 selector；对 `fill` 只回显 `page_ref/timeout_ms`，不回显 selector 或 value；对 `keyboard_type` 只回显 `page_ref/delay_ms`，不回显 text；对 `evaluate` 只回显 `page_ref`，不回显 expression；对 `screenshot` 只回显 `page_ref/full_page`，不回显 PNG bytes、base64、path、filename 或下载 URL；对 `scroll` 只回显 `page_ref/delta_x/delta_y`；未知 step 的其他字段不会出现在响应中。task 创建时的内部持久化也会先按执行字段白名单裁剪，降低未知字段落库风险。
- 所有 task 对外响应也会对 `result` 做白名单脱敏：即使历史持久化数据或后续 runner 误写入完整 step payload、`raw_url`、URL query/fragment、token、业务敏感 URL、evaluate expression、evaluate 返回值、screenshot bytes、base64 或本地路径，响应也只返回 `result.steps[]` 的 `index`、`type`、`status`。
- 当前已提供内部 worker 单次运行入口和内部 loop 骨架，但不启动后台常驻任务或全局 worker 池；失败重试当前仅支持显式 `POST /api/tasks/{id}/retry` 创建新 queued task，不自动执行。

### 内部 Task Claim / Lease

当前已提供后台队列的内部前置能力，但没有开放公开 REST API：

- `automation_tasks` 内部字段：
  - `lease_owner`：内部 worker 标识。
  - `lease_expires_at`：内部 worker 租约过期时间。
- `claim_next_automation_task(lease_owner, lease_seconds)` 会原子选择最早可执行 task：
  - 优先重领已过期 lease 的 `running` task。
  - 否则选择最早 `queued` task。
  - 如果同一 `profile_id` 已有 `running` 或 `cancel_requested` task 且租约仍有效，则跳过该 profile 的 queued task，避免同 profile 并发。
- `renew_automation_task_lease(task_id, lease_owner, lease_seconds)` 只允许当前 lease owner 对仍处于允许状态的 task 续租，续租时间按服务器当前时间或调用方传入 `now` 重新计算为 `now + lease_seconds`。
- `finish_claimed_automation_task(task_id, lease_owner, status, result, error)` 只允许当前 lease owner 把允许来源状态收束为 `succeeded | failed | cancelled`，并清空内部 lease 字段；默认来源状态是 `running`，worker 处理取消请求时可显式允许 `cancel_requested -> cancelled`。
- `run_automation_worker_once(lease_owner, lease_seconds=60)` 是内部单次 worker 入口：
  - 无可领取 task 时返回 `None`，不修改 DB。
  - 通过 `claim_next_automation_task()` 领取 task 后只复用已运行 profile 执行脚本，不自动启动 profile。
  - 执行期间启动内部 lease heartbeat，按 `lease_seconds` 的半周期（最低 0.1 秒，最高 30 秒）调用 `renew_automation_task_lease()` 续租，降低长 step 或长 wait 期间 lease 过期后被其他 worker 重领的风险。
  - profile 不存在或未运行时把已领取 task 用匹配 `lease_owner` 收束为 `failed`，`result.steps` 为空，错误固定为 `Profile not found` 或 `Profile not running`。
  - 运行中遇到 page not found 等内部 HTTP step 错误时，收束为 `failed`，`error` 固定为 `Automation step failed`，`result.steps[]` 只记录当前 step 的 `index/type/status=failed`。
  - 成功、失败或取消收束均通过 `finish_claimed_automation_task()` 校验当前 worker owner，并清空 `lease_owner` / `lease_expires_at`。
  - heartbeat 是内部 DB 续租能力，不写公开响应、不写 task result、不记录 step payload，不承诺强制打断正在 await 的 Playwright 操作。
- `run_automation_worker_loop(lease_owner, lease_seconds=60, max_runs=None, max_idle_cycles=1, idle_sleep_seconds=1.0, stop_event=None)` 是内部 loop 骨架：
  - 持续调用 `run_automation_worker_once()`，直到达到 `max_runs`、达到 `max_idle_cycles` 或 `stop_event` 已设置。
  - 返回低敏 summary：`claimed/succeeded/failed/cancelled/idle_cycles`，不包含 task id、profile id、step payload、URL、selector、表单值、异常原文或 lease owner。
  - 如果单次 worker 因租约已不再归当前 owner 而抛出固定 `409 Automation task lease no longer owned by worker`，loop 不向外抛异常，只在 summary 中计为一次 `claimed` 和一次 `failed`；task 仍保持 DB 当前状态，避免覆盖其他 worker 已接管的状态。
  - 空闲时仅按 `idle_sleep_seconds` sleep；达到最后一次允许空闲周期后直接退出，避免额外等待。
  - `stop_event` 在每轮 claim 前检查；如果已设置，不领取 queued task，不修改 task 状态。
- 应用 lifespan 已支持可选启动一个内部 worker loop：
  - 默认关闭：未设置 `AUTOMATION_WORKER_ENABLED=true` 时不会启动后台 worker，不会自动执行 queued task。
  - 显式启用后，lifespan 使用随机低敏 `lease_owner` 启动一个内部 `run_automation_worker_loop()` task。
  - 可配置 `AUTOMATION_WORKER_LEASE_SECONDS`、`AUTOMATION_WORKER_IDLE_SLEEP_SECONDS`、`AUTOMATION_WORKER_SHUTDOWN_TIMEOUT_SECONDS`；无效值回退默认值。
  - shutdown 时先设置内部 `stop_event`，等待 worker 自然退出；超过 shutdown timeout 后取消内部 task。
  - 该能力不新增公开 REST API、调度器 API 或 Project Mileage DTO；不自动启动 profile，不写钱包、订单、权限、扣费、续期、viewer token 或屏幕流逻辑。
- 内部 `lease_owner` / `lease_expires_at` 不属于前端或 Project Mileage DTO，不应出现在 task API、前端 task log、审计 metadata 或跨仓契约响应中。

## Script Runner 接入建议

第一版 Script Runner 可以直接复用以下 endpoint 作为 step：

- `open_url` -> `goto`
- `wait` -> runner 内部 sleep
- `wait_for_selector` -> `wait-for-selector`
- `click` -> `click`
- `fill` -> `fill`
- `keyboard_type` -> `keyboard/type`
- `scroll` -> `scroll`
- `evaluate` -> `evaluate`
- `screenshot` -> `screenshot`

Script Runner 的 task result/log 不应默认复制 console log、network URL、evaluate result、screenshot 或 clipboard 内容。需要展示时，应按白名单和长度上限返回。

当前 `POST /api/tasks/{id}/run` 已实现第一版 `open_url`、`wait_for_selector`、`click`、`fill`、`keyboard_type`、`evaluate`、`screenshot`、`scroll` 和 `wait` step。后续接入 page 级 step 时继续复用现有 Automation REST helper，但不得把 URL query/fragment、`wait_for_selector.selector`、`click.selector`、`fill.selector/value`、`keyboard_type.text`、`evaluate.expression/result`、screenshot 内容、clipboard 内容、console text、network URL/query/header/body 直接写入 task result/log。

## 安全边界

- Automation API 是高权限运行时接口，不应直接暴露给 Project Mileage App 前端。
- Project Mileage App 只能通过 Payload 安全 DTO 间接接入，不能直接调用 CloakBrowser runtime API。
- CloakBrowser 不判断 Project Mileage 用户是否有权操作账号，不扣费，不续期，不创建订单成功态。
- 不读取或提交 `.env`、secret、cookie、token、数据库 dump 或 `_archive`。
- 不把 proxy password、cookie、Authorization、viewer token、runtime service token、URL query、headers、body 写入 DB、audit metadata 或普通日志。

## 验证命令

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
. .venv/bin/activate && python -m pytest backend/tests -q
git diff --check
```
