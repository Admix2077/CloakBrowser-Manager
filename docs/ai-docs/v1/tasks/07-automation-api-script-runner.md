# 07 Automation API 与脚本运行器

## 目标

扩展现有 Automation REST API，并在其上实现可记录、可重试、可批量运行的 Script Runner。

## 当前基础

已有：

- `/api/profiles/{id}/automation`
- pages list。
- page create。
- page close。
- goto。
- wait for selector。
- click。
- fill。
- keyboard type。
- scroll。
- console logs。
- network summary。
- evaluate。
- screenshot。
- clipboard get/set。

## 任务清单

- [x] 补齐 Automation API 文档。
- [x] 新增 page create。
- [x] 新增 page close。
- [x] 新增 wait for selector。
- [x] 新增 click。
- [x] 新增 fill。
- [x] 新增 keyboard input。
- [x] 新增 scroll。
- [x] 新增 console logs。
- [x] 新增 network summary。
- [x] 新增 task 表：
  - id。
  - profile_id。
  - status。
  - steps。
  - result。
  - error。
  - created_at。
  - started_at。
  - finished_at。
- [x] 新增 `POST /api/tasks`。
- [x] 新增 `GET /api/tasks`。
- [x] 新增 `GET /api/tasks/{id}`。
- [x] 新增 `POST /api/tasks/{id}/cancel`。
- [x] 支持第一版 step：
  - [x] open_url。
  - [x] wait。
  - [x] wait_for_selector。
  - [x] click。
  - [x] fill。
  - [x] keyboard_type。
  - [x] scroll。
  - [x] evaluate。
  - [x] screenshot。
- [x] 支持并发限制。
- [x] 支持失败重试。
- [x] 支持 running task 协作式取消。
- [x] 前端新增 Automation 页面。
- [x] 前端新增 task log viewer。

## 典型脚本

账号 warm-up：

```json
[
  {"type": "open_url", "url": "https://example.com"},
  {"type": "wait", "ms": 3000},
  {"type": "scroll", "direction": "down", "amount": 600},
  {"type": "screenshot", "full_page": false}
]
```

## 验证

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [ ] 不依赖 Chromium CDP。
- [ ] 脚本失败能看到失败 step 和错误。
- [ ] 运行中 profile 才能执行脚本。
- [ ] 脚本不能绕过权限直接读取敏感配置。

## API 契约文档

当前 Automation REST API 契约已整理到：

- `../automation-api-contract.md`

该文档覆盖现有 endpoint、请求/响应字段、Script Runner step 复用建议，以及 console logs / network summary 的敏感信息边界。

## 2026-05-27 Automation task 表小闭环

当前状态：

- 已新增 `automation_tasks` 表。
- 已新增 DB CRUD：
  - `create_automation_task()`。
  - `get_automation_task()`。
  - `list_automation_tasks()`。
  - `update_automation_task()`。
- 表字段覆盖：
  - `id`。
  - `profile_id`。
  - `status`。
  - `steps`。
  - `result`。
  - `error`。
  - `created_at`。
  - `started_at`。
  - `finished_at`。
- `steps` 和 `result` 以 JSON 存储，读取时恢复为结构化对象。
- 本小闭环只完成持久层，不开放 `/api/tasks`，不执行脚本，不引入并发限制或重试。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_database.py::test_init_db_creates_tables backend/tests/test_database.py::test_create_and_get_automation_task_roundtrip backend/tests/test_database.py::test_update_automation_task_status_result_and_error backend/tests/test_database.py::test_list_automation_tasks_for_profile -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests/test_database.py -q
# 34 passed
```

## 2026-05-27 Automation task 最小 API 小闭环

当前状态：

- 已新增 `POST /api/tasks`。
- 已新增 `GET /api/tasks/{id}`。
- 请求模型：
  - `profile_id`：必填。
  - `steps`：必填，长度 `1..200`。
- 响应模型覆盖：
  - `id`。
  - `profile_id`。
  - `status`。
  - `steps`。
  - `result`。
  - `error`。
  - `created_at`。
  - `started_at`。
  - `finished_at`。
- `POST /api/tasks` 当前只创建 `queued` task，不执行脚本，不启动 profile，不读取敏感配置。
- create/get/list/cancel/run 的对外 `AutomationTaskResponse.steps` 统一走白名单脱敏；`open_url.url`、query、fragment 和未知 step 字段不会在响应中回显。
- profile 不存在时返回 `404`。
- 当前未实现并发限制、失败重试和 step 执行器。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_create_automation_task_queues_steps_without_running_script backend/tests/test_api.py::test_get_automation_task_returns_persisted_task backend/tests/test_api.py::test_create_automation_task_rejects_missing_profile -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 70 passed
```

## 2026-05-27 Automation task 列表与取消小闭环

当前状态：

- 已新增 `AutomationTasksResponse`。
- 已新增 `GET /api/tasks`：
  - 返回所有已持久化 task。
  - 按 `created_at desc` 排序，最新 task 在前。
  - 对外响应中的 `steps` 统一走白名单脱敏。
  - 支持可选 `profile_id` query 过滤；profile 不存在时返回 `404 Profile not found`。
  - 支持可选 `limit` 和 `offset` query 分页；`limit` 范围 `1..500`，`offset` 默认 `0` 且不能为负数。
  - 当前未提供权限隔离，只能视为 CloakBrowser 本地管理 API，不能直接暴露给 Project Mileage App。
- 已新增 `POST /api/tasks/{id}/cancel`：
  - 只允许取消 `queued` task。
  - 成功后将 task 状态更新为 `cancelled`。
  - 成功后写入 `finished_at`。
  - task 不存在时返回 `404`。
  - 非 `queued` task 返回 `409`，避免把运行中、已完成或失败 task 伪装成可取消成功。
  - 当前不停止运行中的 Playwright 操作；运行中 task 的中断、补偿和幂等语义留给后续 step runner 小闭环。
- 本小闭环不执行脚本，不启动 profile，不读取敏感配置，不写 Project Mileage 钱包、订单、权限或续期逻辑。
- 当前仍未实现并发限制、失败重试和 step 执行器。

## 2026-05-27 Automation task profile 过滤小闭环

当前状态：

- `GET /api/tasks` 支持可选 `profile_id` query。
- 未传 `profile_id` 时保持原行为：返回所有已持久化 task，并按 `created_at desc` 排序。
- 传入 `profile_id` 时只返回该 profile 的 task，并继续按 `created_at desc` 排序。
- profile 不存在时返回 `404 Profile not found`，避免把无效 profile 误读为空任务列表。
- 过滤后的对外响应继续复用统一 `AutomationTaskResponse` 脱敏：`open_url.url`、query、fragment、token 和未知字段不会回显。
- 当前仍未提供权限隔离；该接口仍只能视为 CloakBrowser 本地可信管理 API，不能直接暴露给 Project Mileage App。
- 本小闭环不修改 Project Mileage app/payload，不写钱包、订单、权限、扣费、续期或 viewer token 逻辑。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_list_automation_tasks_filters_by_profile -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_list_automation_tasks_filter_rejects_missing_profile -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_list_automation_tasks_filter_keeps_steps_redacted -q
# 1 passed
```

## 2026-05-27 Automation task 列表分页小闭环

当前状态：

- `GET /api/tasks` 支持可选 `limit` 和 `offset` query。
- `limit` 范围为 `1..500`；超过范围返回 FastAPI `422`。
- `offset` 默认 `0`，范围为非负整数；负数返回 FastAPI `422`。
- 未传 `limit` 时保持兼容行为：返回匹配条件下的全部 task。
- 分页在 `profile_id` 过滤后应用，排序仍为 `created_at desc`，最新 task 在前。
- DB 层 `list_automation_tasks(profile_id=None, limit=None, offset=0)` 支持同样的分页语义，避免 API 事后切片。
- 分页后的对外响应继续复用统一 `AutomationTaskResponse` 脱敏。
- 当前仍未提供权限隔离；该接口仍只能视为 CloakBrowser 本地可信管理 API，不能直接暴露给 Project Mileage App。
- 本小闭环为后续前端 Automation 页面 / task log viewer 提供基础，不修改 Project Mileage app/payload，不写钱包、订单、权限、扣费、续期或 viewer token 逻辑。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_list_automation_tasks_paginates_newest_tasks backend/tests/test_api.py::test_list_automation_tasks_rejects_invalid_pagination backend/tests/test_database.py::test_list_automation_tasks_paginates_after_profile_filter -q
# 3 passed
```

## 2026-05-27 前端 Automation task log viewer 小闭环

当前状态：

- 前端新增 `Automation` 顶部分段入口，和 `Profiles`、`Proxy Manager` 同级。
- 新增 `frontend/src/components/AutomationTaskLogViewer.tsx`，只读展示最近 50 条 Automation task。
- 新增 `api.listAutomationTasks({ profileId?, limit?, offset? })`，通过统一 API adapter 请求 `/api/tasks`，支持 `profile_id`、`limit`、`offset` query。
- task log viewer 展示：
  - task 短 ID。
  - profile 短 ID。
  - task status。
  - 低敏 step 摘要。
  - 低敏 result step 摘要。
  - task 固定错误文案。
  - created/finished 时间。
- task log table 每行提供只读 `Details` 入口；打开后在 drawer 中展示该 task 的完整低敏 steps 和完整低敏 result steps，不再受表格摘要 4 条截断限制。
- viewer 不提供 `run`、`cancel`、`retry` 按钮，不新增脚本执行入口，不启动 profile，不终止浏览器，不修改 task 状态。
- detail drawer 同样不提供 `run`、`cancel`、`retry` 按钮，不调用新的后端接口，不改变 task 状态。
- viewer 只渲染白名单字段：`type/page_ref/ms/wait_until/state/timeout_ms/delay_ms/delta_x/delta_y/full_page` 和 `result.steps[].index/type/status`。
- 即使 API mock 或历史数据带有 `open_url.url`、query、fragment、token、selector、value、keyboard text、evaluate expression、screenshot base64/path、result raw URL 或表单值，前端组件也不会渲染这些字段。
- detail drawer 复用同一套低敏渲染边界，不渲染 `open_url.url`、URL query、fragment、token、selector、fill value、keyboard text、evaluate expression/result、screenshot bytes/base64/path、clipboard、console/network URL、headers、body 或未知字段。
- 该页面仍然只面向 CloakBrowser 本地可信管理台；`GET /api/tasks` 当前没有 Project Mileage 账号归属、订单、权限或审计隔离，不能直接暴露给 Project Mileage App。
- 本小闭环不修改 Project Mileage app/payload，不写钱包、订单、权限、扣费、续期、viewer token、VNC token 或屏幕流逻辑。

验证记录：

```bash
cd frontend && npm test -- src/components/AutomationTaskLogViewer.test.tsx
# 4 passed

cd frontend && npm test -- src/lib/api.test.ts
# 31 passed

cd frontend && npm test -- src/App.test.tsx
# 28 passed

cd frontend && npm test -- --run
# 14 files / 200 tests passed

cd frontend && npm run build
# passed
```

## 2026-05-27 Automation running task 协作式取消小闭环

当前状态：

- `POST /api/tasks/{id}/cancel` 仍支持 queued task 直接取消：`queued -> cancelled`，并写入 `finished_at`。
- `POST /api/tasks/{id}/cancel` 现在支持 running task 请求取消：`running -> cancel_requested`，`finished_at` 保持 `null`，不伪造已经停止。
- 已经处于 `cancel_requested` 的 task 重复取消会幂等返回当前 task。
- 已结束 task 取消返回 `409 Only queued or running automation tasks can be cancelled`。
- `cancel_requested` task 会继续占用同一 `profile_id` 的执行槽；同 profile 新 queued task run 返回 `409 Automation profile already has a running task`，直到原 task 被 runner 收束。
- runner 在每个 step 开始前检查 `cancel_requested`；如果发现取消请求，当前未执行 step 记录为低敏 `cancelled` 结果，并将 task 收束为 `cancelled`。
- `wait` step 在 sleep 返回后也会检查取消请求；如果还有下一步，会把下一步记录为低敏 `cancelled` 结果且不执行它。
- 该取消是协作式边界检查，不承诺打断正在 await 的 Playwright 操作，不终止浏览器，不停止 profile，不修改 Project Mileage 钱包、订单、权限、扣费、续期、viewer token 或审计事实源。
- cancel/get/list/run 的对外响应继续统一脱敏；`open_url.url`、query、fragment、token、未知字段、selector、表单值、keyboard text、evaluate expression/result、screenshot 内容不会回显。
- 本小闭环不实现后台队列、全局 worker 池、强杀 Playwright 操作、跨系统补偿或 Project Mileage App/Payload 对接。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_cancel_running_automation_task_requests_cooperative_cancel_without_leaking_payload backend/tests/test_api.py::test_cancel_requested_automation_task_blocks_same_profile_run_without_leaking_payload backend/tests/test_api.py::test_run_automation_task_honors_cancel_request_at_step_boundary_without_running_next_step -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_cancel_queued_automation_task_marks_cancelled backend/tests/test_api.py::test_retry_automation_task_rejects_active_status backend/tests/test_api.py::test_run_automation_task_rejects_non_queued_status backend/tests/test_api.py::test_run_automation_task_rejects_concurrent_task_for_same_profile_without_leaking_payload backend/tests/test_api.py::test_run_automation_task_allows_running_task_on_different_profile -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_wait_automation_task_marks_succeeded backend/tests/test_api.py::test_run_automation_task_requires_running_profile backend/tests/test_api.py::test_run_automation_task_fails_unknown_step_without_leaking_payload backend/tests/test_api.py::test_run_automation_task_marks_failed_for_invalid_wait_ms backend/tests/test_api.py::test_run_open_url_step_navigates_existing_page_without_leaking_query backend/tests/test_api.py::test_run_wait_for_selector_step_waits_existing_page_without_leaking_selector backend/tests/test_api.py::test_run_click_step_clicks_existing_page_without_leaking_selector backend/tests/test_api.py::test_run_fill_step_fills_existing_page_without_leaking_selector_or_value backend/tests/test_api.py::test_run_keyboard_type_step_types_existing_page_without_leaking_text backend/tests/test_api.py::test_run_evaluate_step_evaluates_existing_page_without_leaking_expression_or_result backend/tests/test_api.py::test_run_screenshot_step_captures_existing_page_without_returning_png backend/tests/test_api.py::test_run_scroll_step_scrolls_existing_page -q
# 12 passed
```

## 2026-05-27 Automation task 响应脱敏收口小闭环

当前状态：

- create/get/list/cancel/run 的所有对外 `AutomationTaskResponse.steps` 统一走白名单脱敏。
- `wait` step 仅回显 `type/ms`。
- `open_url` step 仅回显 `type/page_ref/wait_until/timeout_ms`。
- `open_url.url`、query、fragment、未知 step 字段、表单值、token、cookie、secret 不会在 task 响应中回显。
- `result` 对外响应也统一做白名单脱敏；即使历史持久化数据或后续 runner 误写入 `raw_url`、完整 step payload、URL query、fragment 或 token 字段，对外也只返回 `result.steps[]` 的 `index/type/status`。
- 当前 `steps` 仍作为内部脚本定义持久化；调用方不得提交 secret。后续若要对 Project Mileage 暴露 task 能力，必须由 Payload 输出安全 DTO，App 不能直连 CloakBrowser task API。
- `open_url` 任意 `http/https` 跳转仍属于可信管理 API 能力，不能直接暴露给 Project Mileage App。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_redact_persisted_result_steps -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_redact_open_url_steps -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_create_automation_task_queues_steps_without_running_script backend/tests/test_api.py::test_get_automation_task_returns_persisted_task backend/tests/test_api.py::test_list_automation_tasks_returns_newest_tasks backend/tests/test_api.py::test_cancel_queued_automation_task_marks_cancelled backend/tests/test_api.py::test_run_wait_automation_task_marks_succeeded backend/tests/test_api.py::test_run_open_url_step_navigates_existing_page_without_leaking_query backend/tests/test_api.py::test_run_open_url_step_marks_failed_for_invalid_url_without_leaking_payload backend/tests/test_api.py::test_automation_task_responses_redact_open_url_steps -q
# 8 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 81 passed
```

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_list_automation_tasks_returns_newest_tasks backend/tests/test_api.py::test_cancel_queued_automation_task_marks_cancelled backend/tests/test_api.py::test_cancel_running_automation_task_requests_cooperative_cancel_without_leaking_payload -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 73 passed
```

## 2026-05-27 Automation Script Runner scroll step 小闭环

当前状态：

- `POST /api/tasks/{id}/run` 已支持 `scroll` step。
- step 格式：
  - `type`: `scroll`。
  - `page_ref`: 可选，默认 `"0"`，可传 page index 或 page id。
  - `delta_x`: 可选整数，范围 `-100000..100000`，默认 `0`。
  - `delta_y`: 可选整数，范围 `-100000..100000`，默认 `0`。
- 执行时复用已运行 profile 的既有 page 和 `window.scrollBy(deltaX, deltaY)`，不自动启动 profile，不创建新 page。
- 成功后 task 按既有状态机进入 `succeeded`；非法 delta 进入 `failed` 并返回 `400`。
- task 对外响应对 `scroll` step 做白名单脱敏：只回显 `type/page_ref/delta_x/delta_y`。
- `result.steps[]` 只记录 `index/type/status`，不复制完整 step payload。
- 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_scroll_step_scrolls_existing_page backend/tests/test_api.py::test_run_scroll_step_marks_failed_for_invalid_delta_without_leaking_payload -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_wait_automation_task_marks_succeeded backend/tests/test_api.py::test_run_open_url_step_navigates_existing_page_without_leaking_query backend/tests/test_api.py::test_run_scroll_step_scrolls_existing_page backend/tests/test_api.py::test_run_scroll_step_marks_failed_for_invalid_delta_without_leaking_payload backend/tests/test_api.py::test_automation_task_responses_redact_open_url_steps -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 83 passed
```

## 2026-05-27 Automation Script Runner wait_for_selector step 小闭环

当前状态：

- `POST /api/tasks/{id}/run` 已支持 `wait_for_selector` step。
- step 格式：
  - `type`: `wait_for_selector`。
  - `selector`: 必填字符串，长度 `1..10000`。
  - `page_ref`: 可选，默认 `"0"`，可传 page index 或 page id。
  - `state`: 可选，`attached | detached | visible | hidden`，默认 `visible`。
  - `timeout_ms`: 可选整数，范围 `1..300000`，默认 `30000`，不接受 `bool`。
- 执行时复用已运行 profile 的既有 page 和 `page.wait_for_selector(selector, state=state, timeout=timeout_ms)`，不自动启动 profile，不创建新 page。
- 成功后 task 按既有状态机进入 `succeeded`；非法 selector、state 或 timeout 进入 `failed` 并返回 `400`。
- Playwright wait_for_selector 执行异常进入 `failed` 并返回固定低敏错误 `Wait for selector step failed`，不回显异常原文。
- task 对外响应对 `wait_for_selector` step 做白名单脱敏：只回显 `type/page_ref/state/timeout_ms`，不回显 selector 或未知字段。
- `result.steps[]` 只记录 `index/type/status`，不复制 selector、完整 step payload 或异常原文。
- 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_redact_wait_for_selector_steps backend/tests/test_api.py::test_run_wait_for_selector_step_waits_existing_page_without_leaking_selector backend/tests/test_api.py::test_run_wait_for_selector_step_marks_failed_for_invalid_selector_without_leaking_payload backend/tests/test_api.py::test_run_wait_for_selector_step_marks_failed_for_invalid_state backend/tests/test_api.py::test_run_wait_for_selector_step_marks_failed_for_bool_timeout backend/tests/test_api.py::test_run_wait_for_selector_step_uses_defaults backend/tests/test_api.py::test_run_wait_for_selector_step_failure_uses_redacted_error -q
# 7 passed
```

## 2026-05-27 Automation Script Runner evaluate step 小闭环

当前状态：

- `POST /api/tasks/{id}/run` 已支持 `evaluate` step。
- step 格式：
  - `type`: `evaluate`。
  - `expression`: 必填字符串，长度 `1..200000`。
  - `page_ref`: 可选，默认 `"0"`，可传 page index 或 page id。
- 执行时复用已运行 profile 的既有 page 和 `page.evaluate(expression)`，不自动启动 profile，不创建新 page。
- 成功后 task 按既有状态机进入 `succeeded`；非法 expression 进入 `failed` 并返回 `400`。
- Playwright evaluate 执行异常进入 `failed` 并返回固定低敏错误 `Evaluate step failed`，不回显异常原文。
- task 对外响应对 `evaluate` step 做白名单脱敏：只回显 `type/page_ref`，不回显 expression 或未知字段。
- `result.steps[]` 只记录 `index/type/status`，不复制 expression、evaluate 返回值、完整 step payload 或异常原文。
- 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_redact_persisted_result_steps backend/tests/test_api.py::test_automation_task_responses_redact_evaluate_steps backend/tests/test_api.py::test_run_evaluate_step_evaluates_existing_page_without_leaking_expression_or_result backend/tests/test_api.py::test_run_evaluate_step_marks_failed_for_invalid_expression_without_leaking_payload backend/tests/test_api.py::test_run_evaluate_step_marks_failed_for_non_string_expression_without_leaking_payload backend/tests/test_api.py::test_run_evaluate_step_failure_uses_redacted_error -q
# 6 passed
```

## 2026-05-27 Automation Script Runner screenshot step 小闭环

当前状态：

- `POST /api/tasks/{id}/run` 已支持 `screenshot` step。
- step 格式：
  - `type`: `screenshot`。
  - `page_ref`: 可选，默认 `"0"`，可传 page index 或 page id。
  - `full_page`: 可选布尔值，默认 `false`，不接受字符串、数字或其他类型。
- 执行时复用已运行 profile 的既有 page 和 `page.screenshot(type="png", full_page=full_page)`，不自动启动 profile，不创建新 page，不开放 `path`、`clip`、`quality` 或下载 URL。
- 成功后 task 按既有状态机进入 `succeeded`；非法 `full_page` 进入 `failed` 并返回固定低敏错误 `Invalid screenshot step`。
- Playwright screenshot 执行异常进入 `failed` 并返回固定低敏错误 `Screenshot step failed`，不回显异常原文。
- task 对外响应对 `screenshot` step 做白名单脱敏：只回显 `type/page_ref/full_page`，不回显 `path`、`filename`、`base64`、`note` 或未知字段。
- 创建 task 时会先按 step 类型做执行字段白名单裁剪；`screenshot` 入库仅保留 `type/page_ref/full_page`，不持久化调用方附带的 `path`、`filename`、`base64`、`note` 等未知字段。
- runner 会调用 screenshot 但丢弃返回的 PNG bytes；`result.steps[]` 只记录 `index/type/status`，不复制 PNG bytes、base64、路径、下载 URL、完整 step payload 或异常原文。
- 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_redact_screenshot_steps backend/tests/test_api.py::test_create_automation_task_persists_sanitized_screenshot_step backend/tests/test_api.py::test_automation_task_responses_redact_persisted_result_steps backend/tests/test_api.py::test_run_screenshot_step_captures_existing_page_without_returning_png backend/tests/test_api.py::test_run_screenshot_step_uses_default_full_page backend/tests/test_api.py::test_run_screenshot_step_marks_failed_for_non_bool_full_page_without_leaking_payload backend/tests/test_api.py::test_run_screenshot_step_failure_uses_redacted_error -q
# 7 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_wait_automation_task_marks_succeeded backend/tests/test_api.py::test_run_open_url_step_navigates_existing_page_without_leaking_query backend/tests/test_api.py::test_run_wait_for_selector_step_waits_existing_page_without_leaking_selector backend/tests/test_api.py::test_run_click_step_clicks_existing_page_without_leaking_selector backend/tests/test_api.py::test_run_fill_step_fills_existing_page_without_leaking_selector_or_value backend/tests/test_api.py::test_run_keyboard_type_step_types_existing_page_without_leaking_text backend/tests/test_api.py::test_run_evaluate_step_evaluates_existing_page_without_leaking_expression_or_result backend/tests/test_api.py::test_run_scroll_step_scrolls_existing_page backend/tests/test_api.py::test_run_screenshot_step_captures_existing_page_without_returning_png backend/tests/test_api.py::test_automation_task_responses_redact_open_url_steps backend/tests/test_api.py::test_automation_task_responses_redact_wait_for_selector_steps backend/tests/test_api.py::test_automation_task_responses_redact_evaluate_steps backend/tests/test_api.py::test_automation_task_responses_redact_screenshot_steps backend/tests/test_api.py::test_automation_task_responses_redact_persisted_result_steps -q
# 14 passed
```

## 2026-05-27 Automation task profile 并发限制小闭环

当前状态：

- `POST /api/tasks/{id}/run` 已增加 profile 级并发限制。
- 同一个 `profile_id` 已存在其他 `running` 或 `cancel_requested` task 时，新的 queued task run 返回 `409`。
- 该限制只按 profile 生效；不同 profile 的 running task 不阻塞当前 profile 的 queued task。
- 被拒绝的 queued task 保持 `queued`，不写 `started_at`、`finished_at` 或 `result`，便于稍后重试。
- 错误 detail 固定为 `Automation profile already has a running task`，不回显 step payload、URL query、token、selector、表单值或未知字段。
- 该小闭环不实现后台队列、全局 worker 池或失败重试；不修改 Project Mileage app/payload。
- 当前仍未实现后台队列。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_automation_task_rejects_concurrent_task_for_same_profile_without_leaking_payload backend/tests/test_api.py::test_run_automation_task_allows_running_task_on_different_profile -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_wait_automation_task_marks_succeeded backend/tests/test_api.py::test_run_automation_task_rejects_non_queued_status backend/tests/test_api.py::test_run_automation_task_requires_running_profile backend/tests/test_api.py::test_run_automation_task_fails_unknown_step_without_leaking_payload backend/tests/test_api.py::test_run_automation_task_marks_failed_for_invalid_wait_ms backend/tests/test_api.py::test_run_open_url_step_navigates_existing_page_without_leaking_query backend/tests/test_api.py::test_run_wait_for_selector_step_waits_existing_page_without_leaking_selector backend/tests/test_api.py::test_run_click_step_clicks_existing_page_without_leaking_selector backend/tests/test_api.py::test_run_fill_step_fills_existing_page_without_leaking_selector_or_value backend/tests/test_api.py::test_run_keyboard_type_step_types_existing_page_without_leaking_text backend/tests/test_api.py::test_run_evaluate_step_evaluates_existing_page_without_leaking_expression_or_result backend/tests/test_api.py::test_run_screenshot_step_captures_existing_page_without_returning_png backend/tests/test_api.py::test_run_scroll_step_scrolls_existing_page backend/tests/test_api.py::test_run_automation_task_rejects_concurrent_task_for_same_profile_without_leaking_payload backend/tests/test_api.py::test_run_automation_task_allows_running_task_on_different_profile -q
# 15 passed
```

## 2026-05-27 Automation task 显式重试小闭环

当前状态：

- 已新增 `POST /api/tasks/{id}/retry`。
- retry 只允许对已结束 task 创建新 queued task：
  - `failed`。
  - `cancelled`。
  - `succeeded`。
- `queued`、`running` 或 `cancel_requested` task retry 返回 `409 Only finished automation tasks can be retried`，避免给未结束任务制造重复执行入口。
- task 不存在时返回 `404 Automation task not found`。
- profile 不存在时返回 `404 Profile not found`。
- 成功后返回新创建的 queued task，状态码 `201`。
- retry 不修改原 task 的 `status/result/error/started_at/finished_at`，不伪造原 task 已恢复。
- retry 不自动执行脚本，不启动 profile，不绕过 `run` 的 profile running 检查或 profile 级并发限制。
- retry 复制的是已持久化并裁剪过的内部 `steps`；对外响应继续走统一白名单脱敏，`open_url.url`、query、fragment、selector、表单值、evaluate expression、screenshot 内容、token 和未知字段不会回显。
- retry 只是显式再排队一次，不判断 step 是否有副作用；涉及点击、填写、跳转等副作用脚本时，调用方必须在可信管理侧确认可重复执行。
- 本小闭环不实现后台队列、自动 retry worker、重试次数上限、指数退避或跨系统补偿。
- 本小闭环不修改 Project Mileage app/payload，不写钱包、订单、权限、扣费、续期、viewer token 或审计事实源。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_retry_failed_automation_task_creates_new_queued_task_without_running_script backend/tests/test_api.py::test_retry_automation_task_rejects_active_status backend/tests/test_api.py::test_retry_automation_task_rejects_missing_profile backend/tests/test_api.py::test_retry_automation_task_keeps_steps_redacted -q
# 4 passed
```

## 2026-05-27 Automation Script Runner click step 小闭环

当前状态：

- `POST /api/tasks/{id}/run` 已支持 `click` step。
- step 格式：
  - `type`: `click`。
  - `selector`: 必填字符串，长度 `1..10000`。
  - `page_ref`: 可选，默认 `"0"`，可传 page index 或 page id。
  - `timeout_ms`: 可选整数，范围 `1..300000`，默认 `30000`，不接受 `bool`。
- 执行时复用已运行 profile 的既有 page 和 `page.click(selector, timeout=timeout_ms)`，不自动启动 profile，不创建新 page。
- 成功后 task 按既有状态机进入 `succeeded`；非法 selector 或 timeout 进入 `failed` 并返回 `400`。
- Playwright click 执行异常进入 `failed` 并返回固定低敏错误 `Click step failed`，不回显异常原文。
- task 对外响应对 `click` step 做白名单脱敏：只回显 `type/page_ref/timeout_ms`，不回显 selector 或未知字段。
- `result.steps[]` 只记录 `index/type/status`，不复制 selector、完整 step payload 或异常原文。
- 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_click_step_clicks_existing_page_without_leaking_selector backend/tests/test_api.py::test_run_click_step_marks_failed_for_invalid_selector_without_leaking_payload backend/tests/test_api.py::test_run_click_step_marks_failed_for_bool_timeout backend/tests/test_api.py::test_run_click_step_failure_uses_redacted_error -q
# 4 passed
```

## 2026-05-27 Automation Script Runner keyboard_type step 小闭环

当前状态：

- `POST /api/tasks/{id}/run` 已支持 `keyboard_type` step。
- step 格式：
  - `type`: `keyboard_type`。
  - `text`: 必填字符串，长度 `1..1048576`。
  - `page_ref`: 可选，默认 `"0"`，可传 page index 或 page id。
  - `delay_ms`: 可选整数，范围 `0..10000`，默认 `0`，不接受 `bool`。
- 执行时复用已运行 profile 的既有 page 和 `page.keyboard.type(text, delay=delay_ms)`，不自动启动 profile，不创建新 page。
- 成功后 task 按既有状态机进入 `succeeded`；非法 text 或 delay 进入 `failed` 并返回 `400`。
- Playwright keyboard type 执行异常进入 `failed` 并返回固定低敏错误 `Keyboard type step failed`，不回显异常原文。
- task 对外响应对 `keyboard_type` step 做白名单脱敏：只回显 `type/page_ref/delay_ms`，不回显 text 或未知字段。
- `result.steps[]` 只记录 `index/type/status`，不复制 text、完整 step payload 或异常原文。
- 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_keyboard_type_step_types_existing_page_without_leaking_text backend/tests/test_api.py::test_run_keyboard_type_step_marks_failed_for_bool_delay backend/tests/test_api.py::test_run_keyboard_type_step_uses_default_delay backend/tests/test_api.py::test_run_keyboard_type_step_marks_failed_for_empty_text backend/tests/test_api.py::test_run_keyboard_type_step_failure_uses_redacted_error -q
# 5 passed
```

## 2026-05-27 Automation Script Runner fill step 小闭环

当前状态：

- `POST /api/tasks/{id}/run` 已支持 `fill` step。
- step 格式：
  - `type`: `fill`。
  - `selector`: 必填字符串，长度 `1..10000`。
  - `value`: 必填字符串，长度 `0..1048576`，允许空字符串用于清空输入。
  - `page_ref`: 可选，默认 `"0"`，可传 page index 或 page id。
  - `timeout_ms`: 可选整数，范围 `1..300000`，默认 `30000`，不接受 `bool`。
- 执行时复用已运行 profile 的既有 page 和 `page.fill(selector, value, timeout=timeout_ms)`，不自动启动 profile，不创建新 page。
- 成功后 task 按既有状态机进入 `succeeded`；非法 selector、value 或 timeout 进入 `failed` 并返回 `400`。
- Playwright fill 执行异常进入 `failed` 并返回固定低敏错误 `Fill step failed`，不回显异常原文。
- task 对外响应对 `fill` step 做白名单脱敏：只回显 `type/page_ref/timeout_ms`，不回显 selector、value 或未知字段。
- `result.steps[]` 只记录 `index/type/status`，不复制 selector、value、完整 step payload 或异常原文。
- 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_fill_step_fills_existing_page_without_leaking_selector_or_value backend/tests/test_api.py::test_run_fill_step_marks_failed_for_invalid_value_without_leaking_payload backend/tests/test_api.py::test_run_fill_step_allows_empty_value backend/tests/test_api.py::test_run_fill_step_marks_failed_for_bool_timeout backend/tests/test_api.py::test_run_fill_step_failure_uses_redacted_error -q
# 5 passed
```

## 2026-05-27 Automation Script Runner open_url step 小闭环

当前状态：

- `POST /api/tasks/{id}/run` 已支持 `open_url` step。
- step 格式：
  - `type`: `open_url`。
  - `url`: 必填，只支持 `http` 和 `https` URL。
  - `page_ref`: 可选，默认 `"0"`，可传 page index 或 page id。
  - `wait_until`: 可选，`commit | domcontentloaded | load | networkidle`，默认 `load`。
  - `timeout_ms`: 可选，`1..300000`，默认 `30000`。
- 执行时复用已运行 profile 的既有 page 和 `page.goto()`，不自动启动 profile，不创建新 page。
- 成功后 task 按既有状态机进入 `succeeded`；非法 URL 或非法参数进入 `failed` 并返回 `400`。
- `run` 响应对 `open_url` step 做白名单脱敏：只回显 `type/page_ref/wait_until/timeout_ms`，不回显完整 URL、query 或 fragment。
- `result.steps[]` 只记录 `index`、`type`、`status`，不复制 URL、console log、network URL、evaluate result、screenshot、clipboard、表单值或完整 step payload。
- 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_open_url_step_navigates_existing_page_without_leaking_query backend/tests/test_api.py::test_run_open_url_step_marks_failed_for_invalid_url_without_leaking_payload -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_wait_automation_task_marks_succeeded backend/tests/test_api.py::test_run_automation_task_rejects_non_queued_status backend/tests/test_api.py::test_run_automation_task_requires_running_profile backend/tests/test_api.py::test_run_automation_task_fails_unknown_step_without_leaking_payload backend/tests/test_api.py::test_run_automation_task_marks_failed_for_invalid_wait_ms backend/tests/test_api.py::test_run_open_url_step_navigates_existing_page_without_leaking_query backend/tests/test_api.py::test_run_open_url_step_marks_failed_for_invalid_url_without_leaking_payload -q
# 7 passed
```

## 2026-05-27 Automation Script Runner wait step 小闭环

当前状态：

- 已新增 `POST /api/tasks/{id}/run`。
- 第一版 run endpoint 只执行已创建的 `queued` task，不让 `POST /api/tasks` 隐式执行脚本。
- 第一版同步执行，响应返回最终 `AutomationTaskResponse`。
- 已支持 `wait` step：
  - step 格式：`{"type": "wait", "ms": 1..300000}`。
  - 执行方式：`asyncio.sleep(ms / 1000)`。
- 状态机：
  - 成功：`queued -> running -> succeeded`。
  - 失败：`queued -> running -> failed`。
  - 非 `queued` task run 返回 `409`。
- 执行前要求 profile 已存在且正在运行；profile 不存在返回 `404 Profile not found`，profile 未运行返回 `404 Profile not running`。
- run 不自动启动 profile，不读取 proxy/cookie/token/secret，不写 Project Mileage 钱包、订单、权限或续期逻辑。
- 当前 `run` 响应会对 `steps` 做白名单脱敏：只回显 step `type`，并仅对 `wait` 回显安全的 `ms`；未知 step 的其他字段不会出现在 run 响应中。
- `result.steps[]` 只记录 `index`、`type`、`status`，不复制 console log、network URL、evaluate result、screenshot、clipboard、表单值或完整 step payload。
- 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_run_wait_automation_task_marks_succeeded backend/tests/test_api.py::test_run_automation_task_rejects_non_queued_status backend/tests/test_api.py::test_run_automation_task_requires_running_profile backend/tests/test_api.py::test_run_automation_task_fails_unknown_step_without_leaking_payload backend/tests/test_api.py::test_run_automation_task_marks_failed_for_invalid_wait_ms -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 78 passed
```

## 2026-05-27 Automation wait-for-selector 小闭环

当前状态：

- 已补齐 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/wait-for-selector`。
- 该接口只操作运行中 profile 的既有 Playwright page，不引入 Chromium CDP。
- 请求体包含：
  - `selector`：必填，长度 `1..10000`。
  - `state`：`attached | detached | visible | hidden`，默认 `visible`。
  - `timeout_ms`：`1..300000`，默认 `30000`。
- 成功后返回现有 `AutomationPageResponse`，便于脚本 runner 后续复用页面摘要。
- Playwright 等待失败沿用现有 automation 模式返回 `400`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_wait_for_selector_waits_and_returns_page -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 59 passed
```

## 2026-05-27 Automation click 小闭环

当前状态：

- 已补齐 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/click`。
- 该接口只操作运行中 profile 的既有 Playwright page，不引入 Chromium CDP。
- 请求体包含：
  - `selector`：必填，长度 `1..10000`。
  - `timeout_ms`：`1..300000`，默认 `30000`。
- 成功后返回现有 `AutomationPageResponse`。
- Playwright click 失败沿用现有 automation 模式返回 `400`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_click_clicks_selector_and_returns_page -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 60 passed
```

## 2026-05-27 Automation fill 小闭环

当前状态：

- 已补齐 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/fill`。
- 该接口只操作运行中 profile 的既有 Playwright page，不引入 Chromium CDP。
- 请求体包含：
  - `selector`：必填，长度 `1..10000`。
  - `value`：待填入文本，长度上限 `1048576`。
  - `timeout_ms`：`1..300000`，默认 `30000`。
- 成功后返回现有 `AutomationPageResponse`。
- Playwright fill 失败沿用现有 automation 模式返回 `400`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_fill_fills_selector_and_returns_page -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 61 passed
```

## 2026-05-27 Automation keyboard type 小闭环

当前状态：

- 已补齐 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/keyboard/type`。
- 该接口只操作运行中 profile 的既有 Playwright page，不引入 Chromium CDP。
- 请求体包含：
  - `text`：待输入文本，长度 `1..1048576`。
  - `delay_ms`：每个字符之间的延迟，`0..10000`，默认 `0`。
- 成功后返回现有 `AutomationPageResponse`。
- Playwright keyboard type 失败沿用现有 automation 模式返回 `400`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_keyboard_type_types_text_and_returns_page -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 62 passed
```

## 2026-05-27 Automation scroll 小闭环

当前状态：

- 已补齐 `POST /api/profiles/{profile_id}/automation/pages/{page_ref}/scroll`。
- 该接口只操作运行中 profile 的既有 Playwright page，不引入 Chromium CDP。
- 请求体包含：
  - `delta_x`：横向滚动量，`-100000..100000`，默认 `0`。
  - `delta_y`：纵向滚动量，`-100000..100000`，默认 `0`。
- 实现通过页面内 `window.scrollBy(deltaX, deltaY)` 完成，不依赖鼠标滚轮底层实现。
- 成功后返回现有 `AutomationPageResponse`。
- Playwright evaluate 失败沿用现有 automation 模式返回 `400`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_scroll_scrolls_page_and_returns_page -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 63 passed
```

## 2026-05-27 Automation console logs 小闭环

当前状态：

- 已补齐 `GET /api/profiles/{profile_id}/automation/pages/{page_ref}/console-logs`。
- 该接口只读取运行中 profile 的既有 Playwright page，不引入 Chromium CDP。
- console 消息通过 `page.on("console", ...)` 捕获，存放在 page 对象的进程内内存字段。
- 每个 page 最多保留最近 200 条 console log，超出后丢弃旧记录。
- 响应结构为：
  - `logs[].type`
  - `logs[].text`
  - `logs[].location`
- 不新增 DB 表，不写 `audit_events`，不把 console 文本写入 logger。
- profile stop 后运行中 page 对象释放，console log 缓存随之释放。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_console_logs_returns_in_memory_page_logs backend/tests/test_api.py::test_automation_console_logs_captures_recent_console_messages -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 65 passed
```

## 2026-05-27 Automation network summary 小闭环

当前状态：

- 已补齐 `GET /api/profiles/{profile_id}/automation/pages/{page_ref}/network-summary`。
- 该接口只读取运行中 profile 的既有 Playwright page，不引入 Chromium CDP。
- network 事件通过 `page.on("request" | "response" | "requestfailed", ...)` 捕获，存放在 page 对象的进程内内存字段。
- 每个 page 最多保留最近 200 条 network event，超出后丢弃旧记录。
- 响应结构为：
  - `events[].event`
  - `events[].method`
  - `events[].url`
  - `events[].resource_type`
  - `events[].status`
  - `events[].failure`
- URL 只保留 scheme、host、port 和 path；丢弃 username、password、query、fragment、params。
- 不采集 headers、cookie、Authorization、request/response body。
- 不新增 DB 表，不写 `audit_events`，不把 network URL 或失败详情写入 logger。
- request failed 只返回固定 `failure: "request_failed"`，不透传底层 failure 字符串。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_network_summary_redacts_urls_and_returns_recent_events backend/tests/test_api.py::test_automation_network_summary_keeps_recent_redacted_events -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 67 passed
```
