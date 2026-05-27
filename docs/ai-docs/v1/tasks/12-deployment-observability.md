# 12 部署、观测与资源治理

## 目标

让产品在 Docker 中长期稳定运行，并能观察运行状态、资源压力和失败原因。

## 任务清单

### Docker

- [ ] 保持 Dockerfile 可构建。
- [ ] healthcheck 覆盖 `/api/status`。
- [ ] 数据目录 `/data` 可持久化。
- [ ] 文档说明 backup/restore。
- [ ] 支持 `AUTH_TOKEN`。
- [ ] 支持 service token。

### Resource Limits

- [x] 配置最大同时运行 profile 数。
- [x] 配置批量启动并发。
- [x] 启动前检查可用 display / ws port。
- [x] 停止时释放 VNC 和 browser context。
- [x] 清理 stale process。

### Observability

- [x] `/api/status` 增加：
  - running_count。
  - launching_count。
  - failed_count。
  - profiles_total。
  - proxy_count。
  - task_queue_count。
  - automation_task_counts。
- [x] 新增 `/api/diagnostics`。
- [x] 日志中包含 profile id 和 action。
- [x] 错误响应稳定。
- [ ] 前端 settings/diagnostics 页面显示系统状态。

### Backup

- [ ] 备份 SQLite。
- [ ] 备份 profile dirs。
- [ ] 导出配置不含敏感字段。
- [ ] 恢复后可启动 profile。

## 验证

```bash
docker build --network=host --platform linux/amd64 -t invisible-browser-manager:latest .
docker run --rm -p 8080:8080 -v invisible-browser-profiles-test:/data invisible-browser-manager:latest
```

## 验收标准

- [ ] 容器 healthcheck 通过。
- [ ] 重启后 profiles 仍存在。
- [ ] 强杀后再次启动 profile 不因 lock/session restore 卡死。
- [ ] status 能反映运行中数量。

## 2026-05-28 前端 System diagnostics 页面小闭环

背景：

- 后端已提供受保护的 `/api/diagnostics` 低敏诊断快照，但前端还没有入口。
- 远程工作台底层进入商业化运行前，运营侧需要能看到运行计数、worker 配置和 storage 基础状态，同时不能展示 profile/proxy/task 明细或任何 secret。
- 本轮只修改 CloakBrowser 本仓，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `frontend/src/lib/api.ts`
  - 新增 `SystemDiagnostics` DTO 类型。
  - 新增 `api.getDiagnostics()`，调用受保护的 `GET /api/diagnostics`。
- `frontend/src/components/SystemDiagnosticsPage.tsx`
  - 新增只读 System diagnostics 页面。
  - 展示低敏字段：status、binary version、storage bool、profile/proxy/task 计数、active display/VNC port 数字、`MAX_RUNNING_PROFILES` 解析结果、automation worker 解析后配置和 task status count。
  - 支持手动刷新。
  - 失败时只显示固定 `Unable to load diagnostics`，不渲染后端异常原文。
- `frontend/src/App.tsx`
  - 顶部新增 `System` 分段入口，和 Profiles / Proxy Manager / Automation 并列。
  - 进入 System 时不显示 profile 创建、启动、停止等操作按钮。
- 测试：
  - `SystemDiagnosticsPage.test.tsx` 覆盖低敏渲染、刷新和错误脱敏。
  - `App.test.tsx` 覆盖 System 分段切换。
  - `api.test.ts` 覆盖 diagnostics API adapter。

边界：

- 页面不渲染真实 `DATA_DIR`/`DB_PATH` 路径、profile id、profile notes、proxy URL/host/username/password、automation steps/result/error、URL/query/fragment、selector、fill value、keyboard text、evaluate expression/result、cookie/local storage、viewer token、runtime service token、AUTH_TOKEN、headers 或 Project Mileage 钱包/订单/权限/审计事实。
- 该页面仍是 CloakBrowser 本地可信管理台功能；未来 Project Mileage 远程工作台如需诊断能力，必须由 Payload 通过安全 DTO 重新定义，App 不能直连 CloakBrowser `/api/diagnostics`。

验证记录：

```bash
cd frontend && npm test -- --run src/App.test.tsx -t "System diagnostics"
# RED: 1 failed；旧 UI 没有 System 入口

cd frontend && npm test -- --run src/components/SystemDiagnosticsPage.test.tsx
# RED: import ./SystemDiagnosticsPage failed；页面尚不存在

cd frontend && npm test -- --run src/lib/api.test.ts -t "api.getDiagnostics"
# RED: api.getDiagnostics is not a function

cd frontend && npm test -- --run src/App.test.tsx -t "System diagnostics"
# 1 passed, 28 skipped

cd frontend && npm test -- --run src/components/SystemDiagnosticsPage.test.tsx
# 3 passed

cd frontend && npm test -- --run src/lib/api.test.ts -t "api.getDiagnostics"
# 1 passed, 38 skipped

cd frontend && npm test -- --run src/App.test.tsx src/components/SystemDiagnosticsPage.test.tsx src/lib/api.test.ts
# 3 files passed, 71 tests passed

cd frontend && npm test -- --run
# 16 files passed, 221 tests passed

cd frontend && npm run build
# tsc -b && vite build succeeded

. .venv/bin/activate && python - <<'PY'
# 临时把 backend.database.DATA_DIR / DB_PATH 指向 /tmp/cloakbrowser-system-diagnostics-ui，
# 然后启动 uvicorn backend.main:app --host 127.0.0.1 --port 18083。
PY
# http://127.0.0.1:18083 可访问；/api/diagnostics 返回 200。

Playwright MCP:
# 打开 http://127.0.0.1:18083，页面标题 Invisible Browser Manager。
# 点击顶部 System。
# DOM 可见 System diagnostics、Status: ok、Profiles: 0、Running: 0、Max running: unlimited、Tasks: none。
# 页面非空白，无 framework error overlay。
# browser_console_messages(level=warning, all=false): Total messages: 0 (Errors: 0, Warnings: 0)。
# 截图证据：cloakbrowser-system-diagnostics-page.png。
```

## 2026-05-28 `/api/status` 低敏运行计数小闭环

背景：

- Docker healthcheck 已调用 `/api/status`，该接口免登录；因此 status 只能返回低敏计数，不能为了观测加载或回显 profile/proxy/task 明细。
- 本轮只修改 CloakBrowser 本仓，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `backend/models.py`
  - `StatusResponse` 增加 `launching_count`、`failed_count`、`proxy_count`、`task_queue_count` 和 `automation_task_counts`。
- `backend/database.py`
  - 新增 `count_profiles()`、`count_proxies()` 和 `count_automation_tasks_by_status()`，只执行 `COUNT(*)` / `GROUP BY status`，不读取完整 profile、proxy 或 automation task rows。
- `backend/main.py`
  - `/api/status` 使用低敏 count helper 计算运行态概览。
  - `running_count` 来自当前 browser manager running map。
  - `launching_count` 来自 browser manager 内部启动中集合计数，不回显 profile id。
  - `failed_count` 来自 failed automation task 计数。
  - `task_queue_count` 来自 queued automation task 计数。
- `frontend/src/lib/api.ts`
  - 同步 `SystemStatus` 类型。
- `frontend/src/lib/api.test.ts`
  - 覆盖前端 adapter 能读取新增低敏计数字段。

边界：

- `/api/status` 不返回 proxy URL、proxy host、username/password、profile notes、`user_data_dir`、automation steps/result/error、URL/query/fragment、selector、fill value、keyboard text、evaluate expression/result、cookie、local storage、viewer token、runtime service token、AUTH_TOKEN、headers 或 Project Mileage 钱包/订单/权限/审计事实。
- `/api/status` 仍作为 Docker healthcheck 免登录接口；更详细的排障信息留给后续 `/api/diagnostics`，并需要单独确认访问控制与脱敏边界。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_status backend/tests/test_api.py::test_system_status_uses_count_queries_without_loading_sensitive_rows -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_database.py -q
# 43 passed

cd frontend && npm test -- --run src/lib/api.test.ts -t "api.getStatus"
# 1 passed, 37 skipped

. .venv/bin/activate && python -m pytest backend/tests -q
# 480 passed in 31.39s

cd frontend && npm test -- --run
# 15 files passed, 215 tests passed

cd frontend && npm run build
# tsc -b && vite build succeeded

git diff --check
# passed
```

## 2026-05-28 `/api/diagnostics` 低敏诊断小闭环

背景：

- `/api/status` 继续作为 Docker healthcheck 免登录接口，只适合返回最小低敏健康计数。
- 运维排障需要比 status 更多的信息，但不能读取或回显 profile/proxy/task 明细，也不能把诊断接口直接暴露给 Project Mileage App。
- 本轮只修改 CloakBrowser 本仓，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `backend/models.py`
  - 新增 `DiagnosticsResponse` 及其 storage、counts、runtime、automation worker 子结构。
- `backend/main.py`
  - 新增 `GET /api/diagnostics`。
  - 该接口不加入 `_AUTH_EXEMPT`，因此 `AUTH_TOKEN` 开启时必须通过本地管理侧认证。
  - 返回 `status`、`binary_version`、`data_dir_exists`、`db_exists`、运行/启动中/profile/proxy/task 计数、active display/ws port 数值列表，以及 automation worker 的解析后配置。
  - 计数继续使用 `count_profiles()`、`count_proxies()` 和 `count_automation_tasks_by_status()`，不加载完整 rows。
- `backend/tests/test_api.py`
  - 覆盖 diagnostics 响应低敏字段和 count-only 查询边界。
- `backend/tests/test_auth.py`
  - 覆盖 `/api/diagnostics` 不是 healthcheck，开启 `AUTH_TOKEN` 时未认证返回 401。

边界：

- `/api/diagnostics` 不返回真实 `DATA_DIR`/`DB_PATH` 路径、profile id、profile notes、proxy URL/host/username/password、automation steps/result/error、URL/query/fragment、selector、fill value、keyboard text、evaluate expression/result、cookie、local storage、viewer token、runtime service token、AUTH_TOKEN、headers 或 Project Mileage 钱包/订单/权限/审计事实。
- automation worker 配置只返回解析后的 boolean/number，不回显原始 env 值；无效 env 值仍按既有 helper 回退默认值。
- 该接口仍是 CloakBrowser 本地可信管理 API；未来 Project Mileage 远程工作台如需诊断能力，必须由 Payload 通过安全 DTO 重新定义，不允许 App 直连 CloakBrowser runtime/diagnostics API。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows backend/tests/test_auth.py::test_diagnostics_requires_auth -q
# RED: 2 failed, 1 passed; diagnostics API 返回 404

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows backend/tests/test_auth.py::test_diagnostics_requires_auth -q
# 3 passed
```

## 2026-05-28 direct Automation API 错误响应稳定小闭环

背景：

- direct Automation API 的页面动作失败路径此前会把 Playwright/运行时异常原文写入响应和 warning 日志。
- `goto` 异常可能包含完整 URL、query token 或 fragment；`evaluate` 异常可能包含表达式和业务敏感值。
- 本轮只修改 CloakBrowser 本仓，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `backend/main.py`
  - 新增 `_raise_automation_page_action_failed()` 统一处理 direct Automation page action 失败。
  - `new_page/goto/evaluate/wait_for_selector/click/fill/keyboard_type/scroll/screenshot/close_page` 失败响应统一为固定 `400 Automation page action failed`。
  - warning 日志统一为低敏 key-value：`action=automation.<action>_failed profile_id=... page_index=... error_type=...`。
- `backend/tests/test_api.py`
  - 覆盖 `goto` 失败时响应和日志都不泄露完整 URL、query token 或 fragment。
  - 覆盖 `evaluate` 失败时响应和日志都不泄露 expression 或 token 字样。

边界：

- direct Automation API 仍属于 CloakBrowser 本地可信管理侧能力，不能直接暴露给 Project Mileage App。
- 失败响应和日志不记录 URL/query/fragment、selector、fill value、keyboard text、evaluate expression/result、screenshot bytes/path、headers、body、cookie/local storage、viewer token、runtime service token、proxy password 或 Project Mileage 钱包/订单/权限/审计事实。
- 正常成功路径保留既有返回；本小闭环只收口失败时的错误文案和日志。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_goto_failure_uses_fixed_error_without_leaking_url backend/tests/test_api.py::test_automation_evaluate_failure_uses_fixed_error_without_leaking_expression -q
# RED: 2 failed；旧实现响应 detail 和 warning 日志均包含 secret URL / expression

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_goto_failure_uses_fixed_error_without_leaking_url backend/tests/test_api.py::test_automation_evaluate_failure_uses_fixed_error_without_leaking_expression -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "automation_goto or automation_evaluate or automation_wait_for_selector or automation_click or automation_fill or automation_keyboard_type or automation_scroll or automation_screenshot or automation_page_close or automation_create_page" -q
# 10 passed, 196 deselected
```

## 2026-05-28 `MAX_RUNNING_PROFILES` 运行资源限制小闭环

背景：

- 远程工作台底层同时运行多个浏览器/VNC 会快速消耗 CPU、内存、display 和 ws port。
- 限制必须放在 CloakBrowser runtime 启动入口内部，不能只放在前端批量启动逻辑里；否则 runtime session broker 仍可绕过限制。
- 本轮只修改 CloakBrowser 本仓，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `backend/browser_manager.py`
  - 新增 `MAX_RUNNING_PROFILES` 可选环境变量。
  - 默认未设置时不限制；设置为合法正整数时，`len(running) + len(launching) >= limit` 会在 VNC allocate 前拒绝新启动。
  - 无效值、非整数、小于 1 的值会回退为不限制，并只记录配置名，不记录原始 env 值。
  - 新增 `BrowserResourceLimitError("Maximum running profiles reached")`，作为资源闸门的固定错误。
- `backend/main.py`
  - 普通 `POST /api/profiles/{profile_id}/launch` 和 runtime `POST /api/runtime/sessions` 都把 `BrowserResourceLimitError` 映射为固定 `409 Maximum running profiles reached`。
  - `/api/diagnostics.runtime.max_running_profiles` 返回解析后的正整数或 `null`，不回显原始环境变量。
- `backend/tests/test_api.py`
  - 覆盖普通 profile launch 达到限制时返回 409，且不调用 VNC allocate。
  - 覆盖 diagnostics 返回解析后的 `max_running_profiles`。
- `backend/tests/test_session_broker.py`
  - 覆盖 runtime session broker 达到限制时返回 409，不调用 VNC allocate，不创建 runtime session audit。

边界：

- `MAX_RUNNING_PROFILES` 只限制新启动，不自动停止已有 profile，不修改订单、钱包、权限、续期或 runtime session 事实。
- 返回错误固定为 `Maximum running profiles reached`，不包含 profile id、display、ws port、proxy、路径、环境变量原文、token 或 Project Mileage 订单/钱包/权限/审计事实。
- 该限制是 CloakBrowser 本地 runtime 资源保护；未来 Project Mileage 业务侧套餐/订单并发限制仍必须由 Payload 作为事实源实现，App 不能直连 CloakBrowser API 作为权限判断。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_rejects_when_max_running_profiles_reached_without_allocating_vnc backend/tests/test_session_broker.py::test_runtime_session_create_respects_max_running_profiles -q
# RED: 2 failed；当前会继续走到 VNC allocate 并最终 500

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_launch_rejects_when_max_running_profiles_reached_without_allocating_vnc backend/tests/test_session_broker.py::test_runtime_session_create_respects_max_running_profiles -q
# 3 passed
```

## 2026-05-28 `VITE_BULK_LAUNCH_CONCURRENCY` 前端批量启动并发小闭环

背景：

- 前端批量启动此前写死为 2 并发。
- 在低资源 Docker/VPS 或 Project Mileage 远程工作台内测环境中，需要能保守降低批量启动并发，避免 UI 一次性触发过多 launch 请求。
- 本轮只修改 CloakBrowser 本仓，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `frontend/src/hooks/useProfiles.ts`
  - 新增 `VITE_BULK_LAUNCH_CONCURRENCY` 构建时配置读取。
  - 默认仍为 2。
  - 非法值、缺失值回退默认 2；合法值钳制在 `1..8`。
  - 批量启动 `launchProfiles()` 使用解析后的并发数。
- `frontend/src/hooks/useProfiles.test.ts`
  - 覆盖 `VITE_BULK_LAUNCH_CONCURRENCY=1` 时，3 个待启动 profile 的最大并发为 1。

边界：

- 该配置只影响 CloakBrowser 前端批量启动按钮触发的并发，不改变单个 `api.launchProfile()` 确认语义，不绕过后端 `MAX_RUNNING_PROFILES`。
- 该配置不是 Project Mileage 套餐/订单/权限限制；业务侧能否启动、能启动多少环境，未来仍必须由 Payload 作为事实源判断，App 不能直连 CloakBrowser runtime API。
- 不读取、不记录、不回显任何 secret、profile id、proxy、viewer token 或订单/钱包/审计事实。

验证记录：

```bash
npm test -- --run src/hooks/useProfiles.test.ts -t "honors configured bulk launch concurrency"
# RED: expected 2 to be 1，说明旧实现仍固定 2 并发

npm test -- --run src/hooks/useProfiles.test.ts -t "honors configured bulk launch concurrency"
# 1 passed, 26 skipped
```

## 2026-05-28 VNC display / ws port 启动前可用性检查小闭环

背景：

- 如果旧 Xvnc 残留、外部进程或系统状态占用了 `:display` 或 WebSocket port，旧实现可能仍分配该资源，直到 `start_vnc()` 或后续连接阶段才失败。
- 资源冲突应该在 `VNCManager.allocate()` 阶段尽早跳过，降低启动失败概率。
- 本轮只修改 CloakBrowser 本仓，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `backend/vnc_manager.py`
  - `allocate()` 不再只看内部 `_allocated`，还会调用 `_is_resource_available(display, ws_port)`。
  - display 检查 `/tmp/.X{display}-lock` 和 `/tmp/.X11-unix/X{display}` 是否存在。
  - ws port 检查尝试 bind `127.0.0.1:{port}`。
  - 不可用时跳过该 display/port 组合，继续尝试下一个。
  - warning 只记录 display 数字或 port 数字，不记录 profile id、路径以外的业务数据、proxy、token 或请求体。
- `backend/tests/test_vnc_manager.py`
  - 覆盖 `:100/6100` 不可用时，`allocate()` 跳到 `:101/6101`，且不登记不可用 display。

边界：

- 该检查只保护 CloakBrowser 本地 VNC 资源分配，不创建、不停止、不修改 profile/runtime session/订单/钱包/权限事实。
- 该检查不替代 `cleanup_stale()`；残留进程清理仍由现有启动清理逻辑负责。
- Project Mileage 远程工作台如果需要展示资源不足或启动失败原因，仍必须通过 Payload 安全 DTO 定义，不允许 App 直连 CloakBrowser runtime API。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py::test_allocate_skips_unavailable_display_or_ws_port -q
# RED: AttributeError，当前没有 _is_resource_available 钩子

. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py::test_allocate_skips_unavailable_display_or_ws_port backend/tests/test_vnc_manager.py::test_allocate_first backend/tests/test_vnc_manager.py::test_allocate_sequential backend/tests/test_vnc_manager.py::test_allocate_fills_gap -q
# 4 passed
```

## 2026-05-28 stop 释放 browser context / VNC 验收收口小闭环

背景：

- 12 Resource Limits 要求停止 profile 时释放浏览器 context 和 VNC 资源。
- 现有 launch/stop 测试已覆盖 runner 分支：`BrowserManager.stop()` 会调用 invisible_playwright runner 的 `__aexit__()`，随后释放 VNC。
- 本轮补齐无 runner 分支的测试证据，确保直接持有 Playwright browser context 时也会关闭 context 并释放 VNC。
- 本轮只修改 CloakBrowser 本仓测试和文档，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `backend/tests/test_browser_manager.py`
  - 新增 `test_stop_without_runner_closes_context_and_releases_vnc`。
  - 手动构造 `RunningProfile(runner=None)`，调用 `BrowserManager.stop()`。
  - 断言 `context.close()` 被 await 一次。
  - 断言 `vnc.stop_vnc(display)` 被 await 一次。
  - 断言 `running` map 已移除目标 profile。
- `backend/browser_manager.py`
  - 生产代码无需修改；现有实现已满足该验收口径。

边界：

- stop 只释放 CloakBrowser 本地运行态资源；不删除 profile、不删除订单、不修改钱包/支付/权限/续期事实。
- 日志只包含 profile id 和固定 action，不记录 proxy、cookie/local storage、viewer token、runtime service token、headers 或 Project Mileage 订单/钱包/权限/审计事实。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_stop_without_runner_closes_context_and_releases_vnc -q
# 1 passed
```

## 2026-05-28 stale process 清理验收收口小闭环

背景：

- 容器重启或异常退出后可能残留 Xvnc 或 invisible_playwright Firefox 进程。
- 12 Resource Limits 要求启动时清理 stale process。
- 现有 lifespan 已调用 `browser_mgr.cleanup_stale()`；`BrowserManager.cleanup_stale()` 已先调用 `vnc.cleanup_stale()`，再清理 scoped invisible_playwright Firefox 进程。
- 本轮补齐 VNC stale 清理命令测试，并整理文档证据；生产代码无需修改。
- 本轮只修改 CloakBrowser 本仓测试和文档，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `backend/tests/test_vnc_manager.py`
  - 新增 `test_cleanup_stale_kills_scoped_xvnc_processes`。
  - mock `subprocess.run()`，断言 VNC 清理只调用 `["pkill", "-f", r"Xvnc :[0-9]"]`。
  - 断言没有使用泛化 `firefox` 或 `.*` 模式。
- `backend/tests/test_browser_manager.py`
  - 既有 `test_cleanup_stale_kills_scoped_invisible_playwright_firefox` 覆盖 BrowserManager 会调用 VNC stale 清理，并只清理 `INVISIBLE_FIREFOX_PROCESS_PATTERN` 匹配的 invisible_playwright Firefox。
- `backend/main.py`
  - 既有 lifespan 启动阶段调用 `await browser_mgr.cleanup_stale()`。

边界：

- stale 清理只针对 CloakBrowser runtime 相关本地进程，不读取 profile dir 内容，不删除 profile 数据，不修改 runtime session、订单、钱包、支付、权限或审计事实。
- 测试要求清理命令保持 scoped，不允许退化为通用 `pkill firefox`。
- Project Mileage 远程工作台如果需要展示 stale cleanup 结果，仍必须由 Payload 安全 DTO 定义，不允许 App 直连 CloakBrowser runtime API。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py::test_cleanup_stale_kills_scoped_xvnc_processes backend/tests/test_browser_manager.py::test_cleanup_stale_kills_scoped_invisible_playwright_firefox -q
# 2 passed
```

## 2026-05-28 profile 生命周期日志 action / profile_id 小闭环

背景：

- 运维排障需要能按 action 和 profile id 检索关键生命周期日志。
- 旧日志是自然语言，例如 `Launched profile ...` / `Stopping profile ...`，不利于机器筛选，也没有 stop 完成日志。
- 本轮只修改 CloakBrowser 本仓，不新增 Project Mileage DTO，不修改 Project Mileage app/payload。

已完成：

- `backend/browser_manager.py`
  - launch 成功日志改为 `action=profile.launch_succeeded profile_id=... display=:... ws_port=... engine=...`。
  - stop 请求日志改为 `action=profile.stop_requested profile_id=...`。
  - stop 完成新增 `action=profile.stop_finished profile_id=...`。
  - browser close 回调日志改为 `action=profile.browser_closed profile_id=...`。
- `backend/tests/test_browser_manager.py`
  - 新增 `test_launch_and_stop_logs_include_action_and_profile_id`。
  - 覆盖 launch/stop 日志包含稳定 `action` 和 `profile_id`。
  - 断言日志不包含 `user_data_dir` 路径。

边界：

- 生命周期日志只记录低敏 runtime 观测字段：action、profile_id、display、ws_port、engine。
- 不记录 profile dir、proxy URL/host/username/password、cookie/local storage、viewer token、runtime service token、headers、请求体、automation payload 或 Project Mileage 订单/钱包/权限/审计事实。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_and_stop_logs_include_action_and_profile_id -q
# RED: 缺少 action=profile.launch_succeeded profile_id=...

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_and_stop_logs_include_action_and_profile_id -q
# 1 passed
```
