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
- evaluate。
- screenshot。
- clipboard get/set。

## 任务清单

- [ ] 补齐 Automation API 文档。
- [x] 新增 page create。
- [x] 新增 page close。
- [x] 新增 wait for selector。
- [x] 新增 click。
- [x] 新增 fill。
- [x] 新增 keyboard input。
- [ ] 新增 scroll。
- [ ] 新增 console logs。
- [ ] 新增 network summary。
- [ ] 新增 task 表：
  - id。
  - profile_id。
  - status。
  - steps。
  - result。
  - error。
  - created_at。
  - started_at。
  - finished_at。
- [ ] 新增 `POST /api/tasks`。
- [ ] 新增 `GET /api/tasks`。
- [ ] 新增 `GET /api/tasks/{id}`。
- [ ] 新增 `POST /api/tasks/{id}/cancel`。
- [ ] 支持第一版 step：
  - open_url。
  - wait。
  - click。
  - fill。
  - scroll。
  - evaluate。
  - screenshot。
- [ ] 支持并发限制。
- [ ] 支持失败重试。
- [ ] 前端新增 Automation 页面。
- [ ] 前端新增 task log viewer。

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
