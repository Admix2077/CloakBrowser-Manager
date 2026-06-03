# 12 部署、观测与资源治理

## 目标

让产品在 Docker 中长期稳定运行，并能观察运行状态、资源压力和失败原因。

## 任务清单

### Docker

- [ ] 保持 Dockerfile 可构建。
- [x] healthcheck 覆盖 `/api/status`。
- [x] 数据目录 `/data` 可持久化。
- [x] 文档说明 backup/restore。
- [x] 支持 `AUTH_TOKEN`。
- [x] 支持 service token。

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
- [x] 前端 settings/diagnostics 页面显示系统状态。

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

## 2026-05-28 Backup/Restore runbook 与安全边界小闭环

背景：

- 12 模块需要部署备份/恢复说明，但当前不适合直接实现真实 backup/restore API：`/data/profiles.db` 和 `/data/profiles/` 可能包含 cookie、local storage、proxy password、runtime/session/audit 等敏感事实。
- 本轮先用 runbook 明确人工备份恢复边界和验收步骤，避免部署者误以为可以热备、只备份 DB、只备份 profile dir，或把备份包提交到仓库。
- 本轮只修改 CloakBrowser 自仓文档和 guardrail 测试，不读取真实 `/data`、不读取 `.env`，不进入 Project Mileage app/payload。

已完成：

- 新增 `docs/ai-docs/v1/deployment-backup-restore-runbook.md`
  - 明确 `/data/profiles.db` 与 `/data/profiles/` 必须作为同一快照整体备份。
  - 明确当前不支持热备，备份/恢复前推荐 `docker compose down`。
  - 明确恢复前先备份当前 `/data`，避免覆盖现场后无法回滚。
  - 明确恢复后先用 `/api/status` 做低敏健康检查，再手动启动低风险 profile 做浏览器/VNC 验收。
  - 明确不要提交备份包、`.env`、SQLite dump、profile dir archive、cookie、local storage、proxy password、`AUTH_TOKEN`、`RUNTIME_SERVICE_TOKEN`、viewer token 或任何 secret。
- `backend/tests/test_deployment_config.py`
  - 新增 runbook guardrail 测试，锁住数据范围、停服务备份、不支持热备、恢复前回滚备份、`/api/status` 验收和 Project Mileage 边界。

边界：

- 本轮没有实现自动 backup/restore API，没有打包真实 `/data`，没有读取 profile dir 内容，没有导出 SQLite dump。
- 本轮不标记 `备份 SQLite`、`备份 profile dirs`、`恢复后可启动 profile` 为完成，因为还没有真实命令和浏览器恢复验收证据。
- Project Mileage app/payload 当前不参与备份恢复；App 不能直连 CloakBrowser runtime、diagnostics、backup 或 restore 能力。未来如需远程账号工作台展示备份/恢复状态，必须先由 Payload 通过安全 DTO 定义，并由 Payload 持有服务端凭证。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_deployment_config.py -q
# RED: 3 failed；runbook 文件不存在，12 文档尚未标记 backup/restore 文档说明完成

. .venv/bin/activate && python -m pytest backend/tests/test_deployment_config.py -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_deployment_config.py backend/tests/test_auth.py backend/tests/test_session_broker.py -q
# 51 passed
```

## 2026-05-28 Docker runtime service token 配置与文档小闭环

背景：

- CloakBrowser 已有 `RUNTIME_SERVICE_TOKEN` / `X-Runtime-Service-Token`，用于未来由 Project Mileage Payload 服务端调用 `/api/runtime/*`。
- `docker-compose.yml` 之前只透传 `AUTH_TOKEN`，容易让部署者误以为 local admin token 可复用为 runtime service token。
- 本轮只修改 CloakBrowser 自仓配置、README 和测试，不进入 Project Mileage app/payload。

已完成：

- `docker-compose.yml`
  - 继续只绑定 `127.0.0.1:8080:8080`。
  - 继续把 `~/.invisible-browser-manager` 挂载到 `/data`。
  - 透传 `AUTH_TOKEN=${AUTH_TOKEN:-}`。
  - 新增透传 `RUNTIME_SERVICE_TOKEN=${RUNTIME_SERVICE_TOKEN:-}`。
- `README.md`
  - 说明 `AUTH_TOKEN` 是本地管理台/API 的 local admin 凭证。
  - 说明 `RUNTIME_SERVICE_TOKEN` 只用于服务端到服务端的 `/api/runtime/*`，请求头为 `X-Runtime-Service-Token`。
  - 明确 Project Mileage App 不能直连 CloakBrowser runtime API，不能持有 runtime service token；未来必须由 Payload 校验订单、钱包、权限和审计后再调用 CloakBrowser。
  - 明确不要把 `RUNTIME_SERVICE_TOKEN` 放进前端环境变量、URL、日志、截图、issue 或提交记录。
- `backend/tests/test_deployment_config.py`
  - 新增配置/文档 guardrail 测试，锁住 Compose token 透传、local-only 端口绑定、`/data` 挂载和 README token 边界。

边界：

- 本轮不读取 `.env`，不写入任何真实 token。
- 本轮不修改 Project Mileage app/payload，不新增 Payload DTO，不实现钱包、订单、权限、扣费、续期、viewer token 或远程屏幕流逻辑。
- App 仍禁止直连 CloakBrowser runtime API；`RUNTIME_SERVICE_TOKEN` 只能由服务端持有。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_deployment_config.py -q
# RED: 2 failed；Compose 未透传 RUNTIME_SERVICE_TOKEN，README 未记录 runtime service token 边界

. .venv/bin/activate && python -m pytest backend/tests/test_deployment_config.py -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_deployment_config.py backend/tests/test_auth.py backend/tests/test_session_broker.py -q
# 48 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 496 passed in 29.73s

AUTH_TOKEN=local-admin-token RUNTIME_SERVICE_TOKEN=runtime-service-token docker compose config >/tmp/cloakbrowser-compose-config.txt && rg -n "AUTH_TOKEN|RUNTIME_SERVICE_TOKEN|/data" /tmp/cloakbrowser-compose-config.txt
# 输出包含 AUTH_TOKEN、RUNTIME_SERVICE_TOKEN 和 /data 挂载；未读取或输出真实 secret。

git diff --check
# passed
```

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

## 2026-06-03 direct Automation console/network 摘要低敏小闭环

背景：

- release smoke 和运维排障会查看 direct Automation API 的 console/network 摘要。
- network summary 已经只保留低敏 URL，但 console log capture 此前会原样保存 `message.text` 和 `message.location.url`。
- console 文本和 location URL 可能包含 URL query token、fragment、Bearer token、cookie、password 或其他敏感键值。

已完成：

- `backend/main.py`
  - 新增 `_automation_redact_text()`，清理 console text 中的 URL、敏感键值和 Bearer token。
  - `_automation_console_log_entry()` 现在对 `message.text` 和 `location.url` 做低敏处理。
  - URL 低敏口径与 `_automation_safe_url()` 一致：保留 scheme、host、port 和 path，移除 userinfo、query、fragment。
- `backend/tests/test_api.py`
  - 新增 console log redaction guardrail，覆盖 text 和 location URL 中的 `token`、`authorization`、userinfo、query、fragment、Bearer token 不进入响应。
  - 复跑 console/network summary 和 automation 切片，确认既有 ring buffer、URL summary 和任务脱敏不被破坏。

边界：

- console/network summary 仍是 CloakBrowser 本地可信管理侧能力，不能直接暴露给 Project Mileage App。
- 摘要只适合低敏排障；不能记录或转发 headers、body、cookie/local storage、真实 proxy URL、token、完整 console payload、截图或 profile dir 内容。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_console_logs_redacts_sensitive_text_and_location_urls -q
# RED: 1 failed；旧实现原样返回 sensitive console text 和 location URL

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_console_logs_redacts_sensitive_text_and_location_urls backend/tests/test_api.py::test_automation_console_logs_returns_in_memory_page_logs backend/tests/test_api.py::test_automation_console_logs_captures_recent_console_messages backend/tests/test_api.py::test_automation_network_summary_redacts_urls_and_returns_recent_events backend/tests/test_api.py::test_automation_network_summary_keeps_recent_redacted_events -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "automation" -q
# 75 passed, 132 deselected
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

## 2026-06-03 diagnostics Firefox identity 小闭环

背景：

- Pixelscan root-cause 诊断需要反复确认 Manager 对外 managed UA 版本、底层 Firefox `application.ini` 版本和 BuildID。
- 之前只能临时进入 Docker 镜像读取 `invisible_playwright` 二进制目录，排障成本高，也容易把路径或完整 UA 混入临时记录。
- 本轮只新增低敏 diagnostics 摘要，不暴露完整 UA、profile id、profile dir、proxy、headers、cookie、local storage、token 或页面内容。

已完成：

- `backend/browser_manager.py`
  - 新增 `managed_firefox_identity_summary()`。
  - 从 managed UA 常量提取 `managed_user_agent_version`。
  - 从已安装包 metadata 提取 `invisible_playwright_version`，只返回版本号，不返回安装路径。
  - 从底层 Firefox `application.ini` 读取 `firefox_binary_version` 和 `firefox_binary_build_id`；读取失败时返回 `None`。
- `GET /api/diagnostics`
  - `runtime` 节点新增：
    - `managed_user_agent_version`
    - `invisible_playwright_version`
    - `firefox_binary_version`
    - `firefox_binary_build_id`
- 前端 System diagnostics Runtime 区块显示 Managed UA、Engine package、Firefox binary 和 Firefox BuildID。

边界：

- diagnostics 仍不加载 profile/proxy/task 明细；继续使用 count helper。
- 不返回完整 UA 字符串、包安装路径、二进制路径、profile dir、proxy URL/host、username/password、automation steps/result、headers、cookie/local storage、viewer token、runtime service token、AUTH_TOKEN 或 Project Mileage 订单/钱包/权限/审计事实。
- 该改动只提高观测能力，不代表 Pixelscan/IPhey gate 已通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# RED: KeyError: 'managed_user_agent_version'

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx
# RED: Unable to find group "Managed UA: Firefox 149.0"

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# RED: KeyError: 'invisible_playwright_version'

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx
# RED: Unable to find group "Engine package: invisible_playwright 0.1.8"

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 2 passed

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 508 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully
```

## 2026-06-03 Firefox identity diagnostics version redaction

背景：

- `managed_user_agent_version`、`invisible_playwright_version`、`firefox_binary_version` 和 `firefox_binary_build_id` 是 Pixelscan/BrowserScan 排障用的低敏 identity 摘要。
- 旧实现直接信任 managed UA 常量、package metadata 和 Firefox `application.ini` 值；如果这些元数据异常或被污染，非版本文本可能进入 diagnostics。

已覆盖：

- 版本字段只允许数字段版本格式，例如 `149.0`、`0.1.8`、`150.0.1`。
- Firefox BuildID 只允许 8 到 20 位数字。
- 非白名单值返回 `None`，前端继续显示 `unknown`。
- 当前本地有效 summary 仍保留 `managed_user_agent_version=149.0`、`invisible_playwright_version=0.1.8`、`firefox_binary_version=150.0.1`、`firefox_binary_build_id=20260521160037`。

边界：

- 不改变 UA override、Firefox binary、`invisible_playwright` package、stealth prefs、seed、WebGL、WebRTC 或 profile launch 行为。
- 不返回完整 UA、package path、binary path、profile dir、proxy data、headers、cookies/local storage、automation payload、viewer token 或 runtime service token。
- 这是 diagnostics redaction guardrail，不代表 Pixelscan/IPhey gate 已通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_managed_firefox_identity_summary_discards_non_public_version_metadata -q
# RED: 149.0-token-super-secret was returned as managed_user_agent_version

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_managed_firefox_identity_summary_discards_non_public_version_metadata -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_managed_firefox_identity_summary_discards_non_public_version_metadata backend/tests/test_browser_manager.py::test_stealth_pref_category_normalizes_sensitive_pref_keys backend/tests/test_browser_manager.py::test_invisible_stealth_pref_summary_degrades_without_full_package backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# 4 passed

. .venv/bin/activate && python - <<'PY'
from backend import browser_manager as bm
bm._firefox_application_ini_metadata.cache_clear()
bm._invisible_stealth_pref_summary.cache_clear()
print(bm.managed_firefox_identity_summary())
PY
# {'managed_user_agent_version': '149.0', 'invisible_playwright_version': '0.1.8', 'firefox_binary_version': '150.0.1', 'firefox_binary_build_id': '20260521160037', 'stealth_pref_count': 29, 'stealth_pref_categories': ['audio', 'canvas', 'debugger', 'fingerprint', 'font', 'hardware', 'screen', 'storage', 'timezone', 'voices', 'webgl', 'webrtc']}

. .venv/bin/activate && python -m pytest backend/tests -q
# 515 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

## 2026-06-03 automation task page_ref redaction guardrail

背景：

- Automation task response 之前会按 step 类型隐藏 URL、selector、fill value、keyboard text、evaluate expression 和 screenshot payload，但仍原样回显并持久化调用方提交的 `page_ref`。
- `page_ref` 契约上只应是十进制 page index 或 pages list 返回的 UUID page_id；如果调用方把 URL、token、路径或任意业务文本塞进该字段，旧实现会把它写入 task 表并通过 create/get/list/cancel/run 响应回显。

已完成：

- 新增 page_ref sanitizer：
  - 十进制 page index 保留。
  - UUID page_id 规范化为小写 UUID。
  - 其他字符串或非字符串值统一保存/回显为低敏 `invalid`。
- `_automation_task_persisted_steps()` 入库前清洗 `page_ref`，避免敏感调用方文本落库。
- `_automation_task_redacted_steps()` 响应时重复清洗 `page_ref`，防御历史任务数据。
- 新增回归测试覆盖 create/get/list/cancel 响应和 persisted task 均不包含敏感 `page_ref` URL/query/fragment。

边界：

- task runner 仍只支持 page index 或 UUID page_id；`invalid` page_ref 会在执行时走既有 page-not-found / step failure 路径，不会默认落到 page 0。
- 该改动只收紧 Automation task redaction 和存储边界，不修改底层 Firefox / `invisible_playwright` fingerprint masking 行为。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_page_ref_before_persisting_or_responding -q
# RED: response echoed https://app.example.com/dashboard?token=page-ref-super-secret#frag

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_page_ref_before_persisting_or_responding backend/tests/test_api.py::test_automation_task_responses_redact_evaluate_steps backend/tests/test_api.py::test_automation_worker_run_once_fails_http_step_errors_without_leaking_payload backend/tests/test_api.py::test_automation_page_id_remains_stable_when_page_order_changes -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 509 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

## 2026-06-03 automation task status aggregate redaction

背景：

- `/api/status` 和 `/api/diagnostics` 都通过 `automation_task_counts` 暴露 automation task status 聚合。
- 旧实现直接把 DB 中的 `automation_tasks.status` 作为 response key；如果历史或损坏 row 含有非白名单 status，token/path/secret 风格文本可能成为可见状态名。
- 该问题与 runtime session status diagnostics redaction 属同类低敏聚合边界。

已覆盖：

- `count_automation_tasks_by_status()` 只保留低敏公开状态：
  - `queued`
  - `running`
  - `cancel_requested`
  - `cancelled`
  - `failed`
  - `succeeded`
- 其他 status 统一归并到 `unknown`。
- `/api/status` 和 `/api/diagnostics` 测试均覆盖 corrupted automation task status 不出现在响应序列化文本中，且 `unknown` 计数正确累加。

边界：

- 不改变 automation task 表结构、创建/claim/renew/finish/cancel/retry/run 行为。
- 不改变 task detail/list 的 step/result payload 脱敏策略。
- 不返回 automation task steps、URL query、selector、form value、lease owner、lease timestamp、profile/proxy/runtime session 详情。
- 这不是 Pixelscan fingerprint masking 修复；只加固 release diagnostics/status 的低敏聚合面。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_status backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# RED: automation_task_counts did not include unknown for corrupted status

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_status backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_status backend/tests/test_api.py::test_system_status_uses_count_queries_without_loading_sensitive_rows backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully
```

## 2026-06-03 diagnostics stealth pref surface observability

背景：

- Pixelscan no-proxy root-cause 已稳定收敛到 `PXLSCN-FINGERPRINT-MASKING` / `Masking detected Fingerprint`。
- 本地 `invisible_playwright` 包通过 `translate_profile_to_prefs()` 写入 `zoom.stealth.*` prefs；后续排障需要能快速比较当前 runtime 的 stealth pref 结构面，但不能把 seed、host IP、完整 pref key/value、profile dir 或 proxy 信息写入 diagnostics。

已完成：

- `backend/browser_manager.py`
  - 新增低敏 stealth pref summary helper。
  - 只统计 `zoom.stealth.*` pref 数量，并把 key prefix 归一化成粗分类。
  - `seed` / `fpp` 归类为 `fingerprint`，`hw_concurrency` 归类为 `hardware`，`webgl2` 归类为 `webgl`，避免暴露 `hw_seed` 等原始 key。
  - 完整 `invisible_playwright` package 不可用时返回 `stealth_pref_count=None` 和空分类，不让 diagnostics 硬失败。
- `GET /api/diagnostics`
  - `runtime` 节点新增：
    - `stealth_pref_count`
    - `stealth_pref_categories`
- 前端 System diagnostics Runtime 区块显示 Stealth prefs 和 Stealth categories。

边界：

- 不返回任何 `zoom.stealth.*` 原始 key。
- 不返回 pref value、seed、WebRTC host IP、timezone value、font list、GPU renderer value、完整 UA、包路径、profile dir、proxy URL/host、automation payload、headers、cookie/local storage、viewer token 或 runtime service token。
- 该改动只提升 Pixelscan root-cause 的低敏观测能力，不改变 Firefox / `invisible_playwright` 行为，不代表 Pixelscan/IPhey gate 已通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# RED: KeyError: 'stealth_pref_count'

npm --prefix frontend test -- --run src/components/SystemDiagnosticsPage.test.tsx src/lib/api.test.ts -t "diagnostics"
# RED: Unable to find group "Stealth prefs: 29 keys"

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_browser_manager.py::test_stealth_pref_category_normalizes_sensitive_pref_keys backend/tests/test_browser_manager.py::test_invisible_stealth_pref_summary_degrades_without_full_package -q
# 3 passed

npm --prefix frontend test -- --run src/components/SystemDiagnosticsPage.test.tsx src/lib/api.test.ts -t "diagnostics"
# 2 files / 3 tests passed, 39 skipped

. .venv/bin/activate && python -m pytest backend/tests -q
# 511 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

## 2026-06-03 stealth pref category diagnostics redaction

背景：

- `stealth_pref_categories` 是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 排障用的低敏粗分类。
- 旧 helper 会把未知 `zoom.stealth.<category>` 的 `<category>` 原样作为 diagnostics category 返回。
- 虽然当前 `invisible_playwright` 包只返回已知 category，但 diagnostics 边界仍应防御底层包未来新增异常 key，避免 token/path/secret 风格文本成为公开分类。

已覆盖：

- 新增 `PUBLIC_STEALTH_PREF_CATEGORIES` 白名单。
- `seed` / `fpp` / `hw_concurrency` / `webgl2` alias 保持原有归一化。
- 非白名单 category 统一返回 `unknown`。
- 当前本地完整 package summary 仍为 29 个 stealth prefs，分类为 `audio/canvas/debugger/fingerprint/font/hardware/screen/storage/timezone/voices/webgl/webrtc`，没有被误归并。

边界：

- 不改变 `invisible_playwright` prefs、seed、WebGL、WebRTC、UA 或 Firefox 启动行为。
- 不返回原始 `zoom.stealth.*` key、pref value、seed、`hw_seed`、WebRTC host IP、font list、profile dir、proxy data、headers、cookies/local storage、automation payload、viewer token 或 runtime service token。
- 这是 diagnostics redaction guardrail，不代表 Pixelscan/IPhey gate 已通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_stealth_pref_category_normalizes_sensitive_pref_keys -q
# RED: api-token-super-secret was returned as a category

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_stealth_pref_category_normalizes_sensitive_pref_keys -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_stealth_pref_category_normalizes_sensitive_pref_keys backend/tests/test_browser_manager.py::test_invisible_stealth_pref_summary_degrades_without_full_package backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# 3 passed

. .venv/bin/activate && python - <<'PY'
from backend import browser_manager as bm
bm._invisible_stealth_pref_summary.cache_clear()
print(bm._invisible_stealth_pref_summary())
PY
# {'stealth_pref_count': 29, 'stealth_pref_categories': ['audio', 'canvas', 'debugger', 'fingerprint', 'font', 'hardware', 'screen', 'storage', 'timezone', 'voices', 'webgl', 'webrtc']}

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

## 2026-06-03 automation task type/result summary redaction guardrail

背景：

- Automation task redaction 已隐藏 URL、selector、表单值、evaluate expression、screenshot payload 和 `page_ref` 中的敏感调用方文本。
- 继续检查时发现 step `type` 本身也是调用方可控字段：未知 step type 会原样持久化、响应并写入 audit `step_types`。
- 历史或异常 task result 中的 `result.steps[].index/type/status` 虽然是摘要字段，但旧实现仍会原样回显非整数 index、非白名单 type/status。

已完成：

- 新增 automation step type 白名单。
- 未知或非字符串 step `type` 在入库、响应、run result 和 audit metadata 中统一收口为低敏 `unknown`。
- `result.steps[]` 摘要继续只返回 `index/type/status`，并进一步清洗：
  - `index` 必须是非负整数，否则返回 `null`。
  - `type` 必须是支持的 automation step type，否则返回 `unknown`。
  - `status` 必须是 `succeeded | failed | cancelled`，否则返回 `unknown`。
- 前端 Automation task result index 类型调整为 `number | null`，`null` 显示为 `-`。

边界：

- 不改变支持的 step 类型或 runner 行为。
- 不把未知 step type 的调用方原文写入 task response、persisted task、result summary 或 audit metadata。
- 该改动只收紧 Automation task redaction 和历史数据防御，不修改底层 Firefox / `invisible_playwright` fingerprint masking 行为。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_unknown_step_type_before_persisting_responding_or_audit backend/tests/test_api.py::test_automation_task_result_summary_sanitizes_corrupted_summary_fields -q
# RED: unknown step type and corrupted result summary fields leaked raw sensitive values

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_unknown_step_type_before_persisting_responding_or_audit backend/tests/test_api.py::test_automation_task_result_summary_sanitizes_corrupted_summary_fields backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_page_ref_before_persisting_or_responding backend/tests/test_api.py::test_automation_task_responses_redact_persisted_result_steps backend/tests/test_api.py::test_automation_task_create_cancel_retry_and_run_write_redacted_audit_events -q
# 5 passed

npm --prefix frontend test -- --run src/components/AutomationTaskLogViewer.test.tsx
# 1 file / 6 tests passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 513 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

## 2026-06-03 launch failure stage diagnostics

背景：

- Pixelscan / IPhey 外站 smoke 排障需要区分“浏览器已正常启动但 fingerprint masking 被检测”与“runtime/profile/VNC/engine 启动链路不稳”。
- 旧 diagnostics 只有 `launching` 数量；一次 launch 失败后没有低敏 stage 摘要，排障只能依赖日志或现场复现。
- 旧 launch 失败日志会插入异常消息，异常消息可能包含 URL、proxy host、profile path 或 token 文本。

已覆盖：

- `BrowserManager` 新增内存级 launch failure stage 计数。
- 固定 stage 包括 `allocate_vnc`、`cleanup_startup_state`、`start_vnc`、`resolve_network_fingerprint`、`build_launch_kwargs`、`enter_browser`、`configure_context`、`bootstrap_page`、`fit_window`、`resource_limit` 等。
- `GET /api/diagnostics` 的 `runtime` 节点新增：
  - `launch_failure_count`
  - `launch_failure_stage_counts`
- 前端 System diagnostics Runtime 区块显示 Launch failures 和 Launch failure stages。
- profile launch 和 runtime session launch 的 500 日志改为记录固定错误类型，不再记录异常消息正文。

边界：

- launch failure summary 只保存在当前 Manager 进程内存中，不持久化，不做跨重启统计。
- diagnostics 不返回 profile id、profile dir、proxy URL/host/username/password、异常消息、完整 traceback、headers、cookie/local storage、viewer token、runtime service token、automation payload 或页面内容。
- 本轮只提升 runtime 启动链路低敏观测能力，不修改底层 Firefox / `invisible_playwright` fingerprint masking 行为，不代表 Pixelscan/IPhey gate 已通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_clears_launching_state_when_vnc_allocation_fails backend/tests/test_browser_manager.py::test_launch_releases_vnc_when_startup_state_cleanup_fails backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_reports_low_sensitive_launch_failure_summary -q
# RED: BrowserManager had no launch_failure_summary; diagnostics runtime had no launch_failure_count / launch_failure_stage_counts

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx api.test.ts
# RED: System diagnostics page did not render Launch failures / Launch failure stages

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_clears_launching_state_when_vnc_allocation_fails backend/tests/test_browser_manager.py::test_launch_releases_vnc_when_startup_state_cleanup_fails backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_reports_low_sensitive_launch_failure_summary -q
# 4 passed

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx api.test.ts
# 2 files / 42 tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_rejects_when_max_running_profiles_reached_without_allocating_vnc backend/tests/test_api.py::test_launch_invalid_proxy_real_validation_400 backend/tests/test_api.py::test_launch_failure_500 backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows backend/tests/test_session_broker.py::test_runtime_session_create_respects_max_running_profiles backend/tests/test_browser_manager.py::test_launch_uses_invisible_playwright_on_vnc_display -q
# 6 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

## 2026-06-03 runtime session diagnostics summary

背景：

- Runtime session / viewer VNC 链路已有 service token、viewer credential、audit redaction 和 WebSocket 拒绝路径测试。
- 但 `GET /api/diagnostics` 只显示 browser runtime / automation worker 状态，不显示 runtime session 状态面；排查 Project Mileage viewer 或 VNC 入口时缺少低敏聚合信号。
- 该诊断必须避免读取或返回 runtime session id、external session id、profile id、viewer credential、viewer hash、viewer URL、audit rows 或 profile/proxy 详情。

已覆盖：

- `backend/database.py` 新增 runtime session 聚合查询：
  - `count_runtime_sessions_by_status()`
  - `count_live_runtime_sessions()`
  - `count_active_runtime_viewer_tokens()`
- `GET /api/diagnostics` 新增 top-level `runtime_sessions`：
  - `status_counts`
  - `live_count`
  - `active_viewer_token_count`
- 前端 System diagnostics 新增 Runtime sessions 区块：
  - Live sessions
  - Viewer credentials
  - Runtime session statuses

边界：

- diagnostics 只返回聚合数字和固定状态名。
- 不返回 runtime session id、external session id、profile id、viewer credential/hash/URL、lease timestamp、headers、cookie/local storage、automation payload、audit rows、proxy data 或 page content。
- 本轮不改变 runtime session 创建、续期、终止、viewer credential TTL、VNC proxy 或底层 Firefox fingerprint 行为。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# RED: diagnostics response had no runtime_sessions node

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx api.test.ts
# RED: System diagnostics page did not render Live sessions / Viewer credentials / Runtime session statuses

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 2 passed

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx api.test.ts
# 2 files / 42 tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 30 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

## 2026-06-03 runtime session status diagnostics redaction

背景：

- Runtime session diagnostics 已新增 `runtime_sessions.status_counts`。
- 该字段来自数据库聚合；如果历史或损坏 DB row 含有非白名单 status，旧实现会把原始 status 字符串作为 diagnostics key 返回。
- status 字段通常由服务端写入，但 diagnostics 边界仍应防御历史数据、手工修复或导入异常，不让 token/path/secret 风格文本成为可见状态名。

已覆盖：

- `count_runtime_sessions_by_status()` 只保留低敏公开状态：
  - `active`
  - `terminated`
- 其他 status 统一归并到 `unknown`。
- diagnostics 测试覆盖 corrupted status 不出现在响应序列化文本中，且 `unknown` 计数正确累加。

边界：

- 不改变 runtime session 表结构。
- 不修改 create/renew/terminate/viewer credential/VNC proxy 行为。
- 不返回 runtime session id、external session id、profile id、viewer credential/hash/URL、lease timestamp、audit rows 或 profile/proxy 详情。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# RED: status_counts did not include unknown and raw corrupted status remained available

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 30 passed

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx api.test.ts
# 2 files / 42 tests passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

## 2026-06-03 Firefox BuildID init script redaction guardrail

背景：

- Firefox identity diagnostics 已经只公开数字版本和数字 BuildID。
- `_browser_init_script()` 仍通过 `_firefox_build_id_override()` 读取 `application.ini` 的原始 BuildID，用于覆盖 `navigator.buildID`。
- 如果未来 patched Firefox metadata 被污染，原始 BuildID 文本可能进入页面 init script，破坏低敏诊断边界。

已覆盖：

- `_firefox_build_id_override()` 复用 `_public_firefox_build_id()` 白名单。
- 只允许 8-20 位数字 BuildID 进入 init script。
- 非字符串或带 token/path/secret 风格后缀的 BuildID 会降为 `None`，页面 init script 中对应 `const __managerBuildID = null`。
- 回归测试覆盖污染 BuildID 不出现在 script 文本中，合法数字 BuildID 覆盖仍保留。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_browser_init_script_drops_non_public_firefox_build_id -q
# RED: polluted BuildID was present in browser init script

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_browser_init_script_drops_non_public_firefox_build_id backend/tests/test_browser_manager.py::test_browser_init_script_overrides_stale_navigator_build_id backend/tests/test_browser_manager.py::test_managed_firefox_identity_summary_discards_non_public_version_metadata -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 516 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA 或 patched Firefox 行为。
- 不记录或公开 full UA、profile id、profile dir、proxy、headers、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 browser locale public-value guardrail

背景：

- profile `locale` 会进入三处浏览器身份面：`invisible_playwright` launch kwargs、`Accept-Language` header、页面 init script 中的 `navigator.language(s)`。
- 该字段来自 profile/API/CSV 导入等自由文本路径；如果传入 header fragment、URL、token 或路径风格文本，旧逻辑会把它直接传播到浏览器上下文和 header。

已覆盖：

- 新增公开 locale normalizer，只允许常见 BCP47 风格语言标签，支持 `en-US`、`zh_CN`、`ja`、`es-419` 这类低敏值并规范大小写/下划线。
- 非公开格式统一降级为 `en-US`。
- `_build_invisible_kwargs()`、`_accept_language_header()` 和 `_browser_init_script()` 共用同一 locale normalizer。
- 回归测试覆盖污染 locale 不进入 launch kwargs、Accept-Language header 或 init script。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_accept_language_header_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_browser_init_script_drops_non_public_locale_text -q
# RED: polluted locale reached launch kwargs, Accept-Language, and init script

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_accept_language_header_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_browser_init_script_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_accept_language_header_includes_base_language backend/tests/test_browser_manager.py::test_browser_init_script_aligns_navigator_languages_with_accept_language_fallback backend/tests/test_browser_manager.py::test_launch_resolves_missing_timezone_and_locale_before_invisible_launch -q
# 6 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 55 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、timezone、proxy 或 patched Firefox 行为。
- 不记录或公开 raw locale input、headers、profile dir、proxy、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 browser timezone public-value guardrail

背景：

- profile `timezone` 会进入 `invisible_playwright` launch kwargs，并影响页面端 timezone 指纹。
- 该字段来自 profile/API/CSV 导入等自由文本路径；如果传入 header fragment、token、URL 或路径风格文本，旧逻辑会把它直接传播到浏览器启动参数。

已覆盖：

- 新增公开 timezone normalizer，只允许低敏 IANA/zoneinfo 可解析时区名。
- 非公开格式、空值或 zoneinfo 不存在的值统一降为空字符串，保持既有“未指定 timezone”语义。
- `_build_invisible_kwargs()` 在生成浏览器启动参数时使用该 normalizer。
- 回归测试覆盖污染 timezone 不进入 launch kwargs；相邻 launch tests 覆盖合法 timezone 仍保留。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_timezone_text -q
# RED: polluted timezone reached launch kwargs

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_timezone_text backend/tests/test_browser_manager.py::test_build_invisible_kwargs_maps_manager_profile backend/tests/test_browser_manager.py::test_build_invisible_kwargs_omits_empty_optional_values backend/tests/test_browser_manager.py::test_launch_resolves_missing_timezone_and_locale_before_invisible_launch -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 56 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、proxy、GeoIP 填充或 profile 存储行为。
- 不记录或公开 raw timezone input、headers、profile dir、proxy、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 GPU/WebGL launch pin public-value guardrail

背景：

- `gpu_vendor` / `gpu_renderer` 会进入 invisible fingerprint pin，并影响 BrowserLeaks/Pixelscan 的 Hardware/WebGL 证据面。
- 这些字段来自 profile/API/CSV/template 自由文本路径；如果传入 header、URL、token 或 path 风格文本，旧逻辑会把它带进 launch pin 或 coherent WebGL renderer。

已覆盖：

- `_build_invisible_pin()` 只把短的公开可见 GPU/WebGL 文本写入 `gpu.vendor` / `gpu.renderer` pin。
- URL、header、token、password、secret、cookie、query/fragment 或控制字符风格文本会从 launch pin 中移除。
- `_coherent_webgl_renderer_override()` 对非公开 renderer 文本回落到固定 Firefox WebGL renderer bucket。
- profile 存储、模板和前端展示语义不变；guardrail 只作用于浏览器启动身份面。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_non_public_gpu_text backend/tests/test_browser_manager.py::test_with_coherent_webgl_identity_drops_non_public_renderer_text -q
# RED: polluted GPU/WebGL text reached pin/coherent renderer

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_non_public_gpu_text backend/tests/test_browser_manager.py::test_with_coherent_webgl_identity_drops_non_public_renderer_text backend/tests/test_browser_manager.py::test_build_invisible_pin_screen_gpu_hardware_dark_theme backend/tests/test_browser_manager.py::test_coherent_webgl_renderer_collapses_modern_nvidia_to_firefox_sanitize_bucket backend/tests/test_browser_manager.py::test_with_coherent_webgl_identity_rewrites_profile_renderer -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 58 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebRTC、UA、locale、timezone、proxy、GeoIP 填充或 profile 存储行为。
- 不记录或公开 raw GPU input、headers、profile dir、proxy、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 screen and hardware launch pin public-value guardrail

背景：

- `screen_width`、`screen_height` 和 `hardware_concurrency` 会进入 invisible fingerprint pin，并影响 BrowserLeaks/Pixelscan 的 Screen/Hardware 证据面。
- 这些字段来自 profile/API/CSV/template 路径；极端值会形成异常 fingerprint，损坏/污染文本还可能在 `int()` 转换时造成 launch failure。

已覆盖：

- `_build_invisible_pin()` 只把合理范围内的 screen dimension 写入 `screen.*` pin。
- `hardware.concurrency` 只接受常见低敏公开核心数。
- 极端数值、布尔值、不可转换文本、header/token/cookie 风格字符串不会进入 launch pin，也不会在 pin 构建阶段抛异常。
- profile 存储、模板和前端展示语义不变；guardrail 只作用于浏览器启动身份面。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_non_public_screen_and_hardware_values -q
# RED: extreme screen and hardware values reached launch pin

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_non_public_screen_and_hardware_values backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_corrupted_screen_and_hardware_text backend/tests/test_browser_manager.py::test_build_invisible_pin_screen_gpu_hardware_dark_theme backend/tests/test_browser_manager.py::test_build_invisible_pin_uses_realistic_1080p_available_height backend/tests/test_browser_manager.py::test_build_invisible_kwargs_maps_manager_profile -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 60 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充或 profile 存储行为。
- 不记录或公开 raw screen/hardware input、headers、profile dir、proxy、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 VNC/window display dimension launch guardrail

背景：

- 前一轮已经清洗 `screen_width` / `screen_height` / `hardware_concurrency` 的 invisible fingerprint pin。
- `BrowserManager.launch()` 仍把 profile 原始 screen 值传给 KasmVNC，并在 window fit 阶段直接 `int()` 转换；污染文本或极端值可能造成 VNC 尺寸异常、launch failure，或把非公开文本留在调用参数中。

已覆盖：

- 新增共享 display 尺寸 helper，复用现有公开 screen dimension 范围。
- VNC start 和 Firefox window fit 现在使用同一组安全 display dimensions。
- 非公开、污染或不可转换 screen 值回落到 `1920x1080`，不再进入 VNC/window fit 调用参数，也不会在 fit 阶段触发 `ValueError`。
- fingerprint pin 语义不变；无效 screen 仍不会被写入 invisible pin。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_uses_safe_display_dimensions_for_non_public_screen_values -q
# RED: polluted screen text caused fit_window ValueError

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_uses_safe_display_dimensions_for_non_public_screen_values -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 61 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充或 profile 存储行为。
- 不记录或公开 raw screen input、headers、profile dir、proxy、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 BrowserManager lifecycle log redaction guardrail

背景：

- `BrowserManager.launch()` 的主失败日志已经只记录固定 stage，但若 teardown/stop/auto-launch 边界发生异常，部分日志仍会输出 raw exception message。
- auto-launch 成功/失败日志还会输出 profile name；profile name 是用户可控自由文本，可能来自导入、运营备注或外部系统命名。

已覆盖：

- stop runner close failure 与 context close failure 现在只记录固定 action、profile_id 和 error_type。
- launch error cleanup 与 browser closed cleanup 的 debug 日志也只记录固定 action、profile_id 和 error_type。
- auto-launch 成功日志只记录 profile_id；auto-launch 失败日志只记录 profile_id 和 error_type，不再记录 profile name 或 raw exception text。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_stop_logs_fixed_error_type_without_runner_exception_text backend/tests/test_browser_manager.py::test_stop_logs_fixed_error_type_without_context_exception_text backend/tests/test_browser_manager.py::test_auto_launch_all_logs_profile_ids_and_error_types_without_sensitive_text -q
# RED: lifecycle logs exposed raw exception text and auto-launch profile names

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_stop_logs_fixed_error_type_without_runner_exception_text backend/tests/test_browser_manager.py::test_stop_logs_fixed_error_type_without_context_exception_text backend/tests/test_browser_manager.py::test_auto_launch_all_logs_profile_ids_and_error_types_without_sensitive_text -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 64 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸或 profile 存储行为。
- 不记录或公开 raw exception text、profile name、raw screen input、headers、profile dir、proxy、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 GeoIP/proxy lookup log redaction guardrail

背景：

- GeoIP lookup 是 no-proxy/proxy-country smoke、timezone/locale 填充和 Pixelscan/IPhey triage 的关键路径。
- 旧日志会输出无效 GeoIP env 原值、provider failure message/reason，以及 lookup exception text；这些文本可能包含 token、proxy host、URL、query 或 provider 返回的非低敏内容。

已覆盖：

- GeoIP timeout/cache config 无效时只记录固定配置名和 fallback 值，不记录 raw env value。
- ip-api、ipapi.co、ipwho.is 返回失败时只记录固定 provider source，不记录 provider message/reason。
- provider 请求异常时只记录 provider 名和 exception type，不记录 raw exception message。
- GeoIP fallback、proxy lookup、timezone/locale/profile `_geoip_result` 语义不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py::test_geoip_timeout_config_warning_does_not_log_raw_env_value backend/tests/test_geoip.py::test_geoip_provider_failure_warning_does_not_log_raw_response_message backend/tests/test_geoip.py::test_resolve_network_geo_warning_does_not_log_raw_lookup_exception -q
# RED: GeoIP logs exposed raw env/provider/exception text

. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py::test_geoip_timeout_config_warning_does_not_log_raw_env_value backend/tests/test_geoip.py::test_geoip_provider_failure_warning_does_not_log_raw_response_message backend/tests/test_geoip.py::test_resolve_network_geo_warning_does_not_log_raw_lookup_exception -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py -q
# 14 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸或 profile 存储行为。
- 不记录或公开 raw env value、provider message/reason、raw exception text、proxy host/credentials、headers、profile dir、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 VNC proxy failure log redaction guardrail

背景：

- regular profile VNC 和 runtime viewer session 共享 `_proxy_running_vnc()`。
- 旧 VNC proxy 连接失败、client→backend 转发失败、backend→client 转发失败、websocket close failure 日志会拼接 raw exception message；这些异常文本可能包含 viewer URL、proxy/backend URL、token、端口或内部路径。

已覆盖：

- VNC backend connect failure 现在只记录固定 `action=vnc.proxy_connect_failed`、profile_id 和 error_type。
- client→backend、backend→client、websocket close failure 日志只记录固定 action、profile_id、error_type 和低敏 message count。
- runtime viewer backend failure audit 语义不变，仍只记录 reason_code。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_error_type_without_raw_exception -q
# RED: VNC proxy connect error logged raw exception text

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_error_type_without_raw_exception -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_ws_rejects_cross_origin backend/tests/test_api.py::test_ws_allows_same_origin backend/tests/test_api.py::test_ws_allows_no_origin backend/tests/test_api.py::test_vnc_proxy_connects_websockify_path backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_error_type_without_raw_exception -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_vnc_backend_connect_failure_writes_redacted_failure_audit backend/tests/test_session_broker.py::test_runtime_vnc_accepts_valid_viewer_token_and_proxies_to_profile_vnc backend/tests/test_session_broker.py::test_runtime_vnc_success_writes_redacted_connect_and_disconnect_audit -q
# 3 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸、viewer token issuance 或 profile 存储行为。
- 不记录或公开 raw exception text、viewer URL/token、backend URL、proxy host/credentials、headers、profile dir、cookies、local storage、runtime service token、automation payload 或页面内容。

## 2026-06-03 BrowserManager diagnostics/bootstrap debug log redaction guardrail

背景：

- Firefox identity metadata、invisible_playwright stealth pref summary、window fit、existing page init script、bootstrap page creation 都属于 release smoke/triage 的 BrowserManager 诊断路径。
- 旧 debug 日志会拼接 raw exception message；异常文本可能包含 Firefox binary/application.ini path、profile dir、URL、token、provider text 或内部路径。

已覆盖：

- Firefox application.ini metadata detection failure 只记录固定 `action=browser.firefox_metadata_detection_skipped` 和 error_type。
- invisible_playwright stealth pref summary failure 只记录固定 `action=browser.stealth_pref_summary_skipped` 和 error_type。
- Firefox window fit failure 只记录固定 `action=profile.fit_window_skipped`、display 和 error_type。
- existing page init script failure 与 bootstrap page creation failure 只记录固定 action、profile_id 和 error_type。
- 原有 best-effort 降级语义不变；metadata/stealth summary 仍返回低敏 fallback，window/bootstrap/init 失败仍不阻断正常 launch。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_identity_metadata_debug_logs_error_type_without_raw_exception backend/tests/test_browser_manager.py::test_stealth_pref_summary_debug_logs_error_type_without_raw_exception backend/tests/test_browser_manager.py::test_fit_firefox_window_debug_log_uses_error_type_without_raw_exception backend/tests/test_browser_manager.py::test_launch_debug_logs_init_and_bootstrap_error_types_without_raw_exception -q
# RED: BrowserManager debug logs exposed raw exception text

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_identity_metadata_debug_logs_error_type_without_raw_exception backend/tests/test_browser_manager.py::test_stealth_pref_summary_debug_logs_error_type_without_raw_exception backend/tests/test_browser_manager.py::test_fit_firefox_window_debug_log_uses_error_type_without_raw_exception backend/tests/test_browser_manager.py::test_launch_debug_logs_init_and_bootstrap_error_types_without_raw_exception -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 68 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储或 launch fallback 行为。
- 不记录或公开 raw exception text、Firefox binary/application.ini path、profile dir、URL、token、proxy host/credentials、headers、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 Health GeoIP lookup failure log redaction guardrail

背景：

- `/api/profiles/{profile_id}/health/check` 是 release smoke 里的 proxy/GeoIP/timezone/locale triage 路径。
- 旧 GeoIP lookup failure 日志会拼接 raw exception message；异常文本可能包含 provider URL、proxy host、credentials、token 或 query。

已覆盖：

- Health GeoIP lookup failure 现在只记录固定 `action=profile.health_geoip_lookup_failed`、profile_id 和 error_type。
- health response、health audit、last_geoip fallback/cache 行为不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_check_lookup_failure_logs_error_type_without_raw_exception -q
# RED: health GeoIP failure log exposed raw provider exception text

. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_check_lookup_failure_logs_error_type_without_raw_exception -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q
# 18 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、health status/warning/audit 语义或 launch fallback 行为。
- 不记录或公开 raw exception text、provider URL/message/reason、proxy host/credentials、headers、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 Automation/clipboard introspection debug log redaction guardrail

背景：

- clipboard read fallback 和 automation page summary 都会在 release smoke / VNC viewer / automation debugging 中读取页面状态。
- 旧 debug 日志会拼接 raw exception message；异常文本可能包含页面 URL、token、profile path 或页面内容片段。

已覆盖：

- Clipboard page evaluate failure 只记录固定 `action=profile.clipboard_page_read_failed`、profile_id 和 error_type。
- Clipboard context/pages failure 只记录固定 `action=profile.clipboard_context_read_failed`、profile_id 和 error_type。
- Automation page title failure 只记录固定 `action=automation.page_title_failed`、profile_id、page_index 和 error_type。
- Clipboard fallback 到 xclip、automation pages title 空字符串 fallback 和响应结构保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_get_clipboard_page_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_get_clipboard_context_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_automation_page_title_failure_logs_error_type_without_raw_exception -q
# RED: clipboard/page-title debug logs exposed raw exception text

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_get_clipboard_page_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_get_clipboard_context_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_automation_page_title_failure_logs_error_type_without_raw_exception -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_set_clipboard_not_running backend/tests/test_api.py::test_get_clipboard_not_running backend/tests/test_api.py::test_set_clipboard_success backend/tests/test_api.py::test_get_clipboard_from_page backend/tests/test_api.py::test_get_clipboard_page_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_get_clipboard_context_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_automation_pages_lists_existing_pages backend/tests/test_api.py::test_automation_page_title_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_automation_pages_hide_internal_about_home_from_numeric_refs backend/tests/test_api.py::test_automation_pages_create_new_page -q
# 10 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、clipboard text source order、automation page response shape 或 launch fallback 行为。
- 不记录或公开 raw exception text、page URL、profile dir/path、headers、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 VNCManager start log redaction guardrail

背景：

- VNCManager `start_vnc()` 是 profile launch、runtime viewer 和 VNC smoke 的底层路径。
- 旧启动日志会输出内部 Xvnc log path，log 读取失败时还会输出 raw exception message；这些文本可能包含内部路径或环境相关细节。

已覆盖：

- Xvnc start request 日志只记录固定 `action=vnc.start_requested`、display、ws_port、width、height。
- Xvnc log read failure 只记录固定 `action=vnc.start_log_read_failed`、display 和 error_type。
- VNC allocation、Popen command、process tracking、stop/cleanup 行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py::test_start_vnc_logs_action_without_internal_log_path backend/tests/test_vnc_manager.py::test_start_vnc_log_read_failure_logs_error_type_without_raw_exception -q
# RED: VNCManager logs exposed /tmp Xvnc log path and raw read exception text

. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py::test_start_vnc_logs_action_without_internal_log_path backend/tests/test_vnc_manager.py::test_start_vnc_log_read_failure_logs_error_type_without_raw_exception -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py -q
# 15 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸选择、viewer token issuance、profile 存储、VNC command args 或 launch fallback 行为。
- 不记录或公开 raw exception text、Xvnc log path、profile dir/path、headers、cookies、local storage、viewer token、runtime service token、automation payload 或页面内容。

## 2026-06-03 Proxy/launch API error detail redaction guardrail

背景：

- Proxy Manager、profile launch 和 runtime session create 都处在 release smoke / proxy-country triage / VNC viewer 入口上。
- 旧 API 分支会把底层 `ValueError` 原文作为 HTTP detail 返回；异常文本一旦包含 proxy URL、host、credentials、token 或 profile/runtime 上下文，就会被客户端、测试输出或上游服务固化。

已覆盖：

- `/api/proxies` create/update 的 proxy storage `ValueError` 只返回低敏 proxy 错误类别。
- `/api/profiles/{profile_id}/proxy-asset` 保存当前 profile proxy 为资产时，底层 create failure 只返回低敏 proxy 错误类别。
- `/api/profiles/{profile_id}/launch` 的 proxy validation `ValueError` 只返回低敏 proxy 错误类别。
- `/api/runtime/sessions` 创建时由 launch 抛出的 proxy validation `ValueError` 只返回低敏 proxy 错误类别。
- 已知低敏类别保留为固定文本：`Invalid proxy scheme`、`Invalid proxy URL`、`Proxy URL missing hostname`、`Proxy URL invalid port`、`Proxy URL missing port`；未知 `ValueError` 回落到 `Invalid proxy URL`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "redacts_sensitive_storage_error_detail"
# RED: 3 failed；HTTP detail 原样包含 proxy URL、credentials、host 和 token 文本

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "redacts_sensitive_storage_error_detail"
# 3 passed, 25 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q
# 28 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_invalid_proxy_400 backend/tests/test_api.py::test_launch_invalid_proxy_real_validation_400 backend/tests/test_session_broker.py::test_runtime_session_create_redacts_sensitive_launch_value_error_detail -q
# RED: 3 failed；profile launch/runtime session create HTTP detail 原样包含底层 ValueError 文本

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_invalid_proxy_400 backend/tests/test_api.py::test_launch_invalid_proxy_real_validation_400 backend/tests/test_session_broker.py::test_runtime_session_create_redacts_sensitive_launch_value_error_detail -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py -q -k "runtime_session_create or launch"
# 21 passed, 223 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 546 passed in 33.12s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.78s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy normalization、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、runtime session persistence 或 launch fallback 行为。
- 不记录或公开 raw exception text、proxy URL/host/username/password、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 CSV profile import template reference redaction guardrail

背景：

- CSV profile import preview/import 是批量 profile 创建入口，会处理用户上传的 template、proxy、notes、locale、timezone 等自由文本。
- 旧缺失模板错误会返回 `Template not found: <template_ref>`；当 template_ref 是 URL、token、path 或 credential 样式文本时，会进入 preview/import 的 row errors 和 source payload。

已覆盖：

- 缺失模板错误固定为 `Template not found`，不再拼接原始 template 引用。
- `source.template` 对 URL、userinfo、query、fragment、path、token/secret/password/cookie/authorization 样式文本返回 `[redacted]`。
- 普通模板名/ID lookup、模板字段复制、显式字段覆盖、CSV import preview/import 成功路径和行级错误结构保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q -k "csv_import"
# RED: 4 failed；缺失模板错误仍包含 raw template ref，敏感 URL host 出现在响应中

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q -k "csv_import"
# 10 passed, 5 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 15 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_api.py -q -k "profile_config or profile_bundle or csv_import or import_profile_configs or import_profile_bundle"
# 37 passed, 193 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 548 passed in 32.28s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.66s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy normalization、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、profile config import、profile bundle import 或 CSV parser 支持字段。
- 不记录或公开 raw missing template URL/host/username/password/query token/path、headers、cookies、local storage、viewer token、runtime service token、automation payload 或 profile dir 内容。

## 2026-06-03 CSV profile import source/header redaction guardrail

背景：

- CSV profile import preview/import 会返回 row `source` 和行级 errors，帮助用户定位批量导入问题。
- 旧 `source` 会复制整行输入；unsupported column 错误会拼接原始 header。上传的 header/value 如果包含 URL、credential、token、authorization、path 或 secret，会进入响应体。

已覆盖：

- Unsupported column 错误固定为 `Unsupported column`，不再拼接原始 header。
- `source` 只保留支持字段；unsupported/extra columns 只暴露低敏 `unsupported_column_count`。
- 支持字段的 source value 如果像 URL/userinfo/query/fragment/path/token/secret/password/cookie/authorization/bearer，则返回 `[redacted]`。
- 普通 CSV preview/import、proxy redaction、template lookup、profile config import 和 profile bundle import 相关路径保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_profile_csv_import_preview_redacts_sensitive_source_fields_and_headers backend/tests/test_bulk.py::test_profile_csv_import_redacts_sensitive_source_fields_and_headers -q
# RED: 2 failed；unsupported column error 包含 raw token header

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_profile_csv_import_preview_redacts_sensitive_source_fields_and_headers backend/tests/test_bulk.py::test_profile_csv_import_redacts_sensitive_source_fields_and_headers -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q -k "csv_import"
# 12 passed, 5 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 17 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_api.py -q -k "profile_config or profile_bundle or csv_import or import_profile_configs or import_profile_bundle"
# 39 passed, 193 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 550 passed in 33.26s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.90s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy normalization、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、profile config import、profile bundle import 或 CSV 支持字段。
- 不记录或公开 raw unsupported header/value、extra CSV values、URL/host/username/password/query token/path、authorization/bearer text、headers、cookies、local storage、viewer token、runtime service token、automation payload 或 profile dir 内容。

## 2026-06-03 Launch resource-limit API detail redaction guardrail

背景：

- Profile launch 和 runtime session create 都会把 `BrowserResourceLimitError` 映射为 409。
- 旧实现把 exception text 作为 HTTP detail 返回；如果底层资源限制异常带入 profile/proxy/token/path 文本，就会被客户端响应固化。

已覆盖：

- `/api/profiles/{profile_id}/launch` 的 resource-limit detail 固定为 `Maximum running profiles reached`。
- `/api/runtime/sessions` 创建时 launch resource-limit detail 固定为 `Maximum running profiles reached`。
- 现有 max running profile、proxy validation、runtime session create 和 launch 状态码语义保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_resource_limit_detail_does_not_echo_exception_text backend/tests/test_session_broker.py::test_runtime_session_create_resource_limit_detail_does_not_echo_exception_text -q
# RED: 2 failed；409 detail 原样包含 proxy URL、credentials 和 token 文本

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_resource_limit_detail_does_not_echo_exception_text backend/tests/test_session_broker.py::test_runtime_session_create_resource_limit_detail_does_not_echo_exception_text -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py -q -k "runtime_session_create or launch"
# 23 passed, 223 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 552 passed in 33.79s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.89s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 resource limit 判断、stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy normalization、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、runtime session persistence 或 launch fallback 行为。
- 不记录或公开 raw resource-limit exception text、proxy URL/host/username/password、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Proxy check API/DB error redaction guardrail

背景：

- Proxy check failure 会通过 `/api/proxies/{proxy_id}/check`、`/api/proxies/bulk/check` 和 persisted `last_check_error` 进入管理台与数据库。
- 旧实现只替换 raw proxy URL 和 parsed password；provider exception 中独立出现的 lookup URL、query token、Authorization/Bearer、provider host 或 proxy host 仍可能被固化。

已覆盖：

- Proxy check 失败统一写入固定低敏 `Proxy check failed`。
- Bulk proxy check 的 per-result `error` 与嵌套 proxy `last_check_error` 使用同一固定低敏文本。
- 成功 check、GeoIP field update、bulk partial success/missing proxy 语义保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "generic_failure_without_leaking_provider_details"
# RED: 2 failed；last_check_error / bulk error 原样包含 provider URL、token、Authorization/Bearer 和 proxy host

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "proxy_check"
# 3 passed, 27 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q
# 30 passed in 2.96s

. .venv/bin/activate && python -m pytest backend/tests -q
# 554 passed in 33.75s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.28s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 proxy storage URL、proxy validation、GeoIP lookup behavior、stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、VNC、viewer token、profile 存储或 runtime session 行为。
- 不记录或公开 raw proxy check exception text、provider URL/host/query token、Authorization/Bearer、proxy host/username/password、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 GeoIP source public-value guardrail

背景：

- GeoIP success metadata 会进入 proxy `last_check_source`、profile `last_geoip_source`、profile health response 和 health audit metadata。
- 当前真实 provider 返回固定 source label，但 API/DB 层原本直接信任 `GeoIPResult.source`；测试替身、未来 provider 或历史 DB 值若带入 URL、query token、Authorization/Bearer、host/path 文本，会被成功路径固化。

已覆盖：

- 新增共享 `public_geoip_source`，仅保留短的公开 source label（例如 `ip-api`、`ipapi.co`、`ipwho.is`、`qa`），非公开文本折叠为 `unknown`。
- Proxy check 成功路径写入 `last_check_source` 前会过滤 source。
- `GeoIPResult.as_dict()`、profile health 新 lookup response、persisted health cache response 和 health audit metadata 均使用低敏 source。
- 现有 GeoIP provider fallback、proxy check 成功字段、profile health stale/mismatch/audit 语义保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_check_redacts_sensitive_success_source backend/tests/test_health.py::test_health_check_redacts_sensitive_geoip_source backend/tests/test_health.py::test_health_get_redacts_persisted_sensitive_geoip_source -q
# RED: 3 failed；proxy/health source 原样包含 provider URL、token、Authorization/Bearer

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_check_redacts_sensitive_success_source backend/tests/test_health.py::test_health_check_redacts_sensitive_geoip_source backend/tests/test_health.py::test_health_get_redacts_persisted_sensitive_geoip_source -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py backend/tests/test_health.py backend/tests/test_proxies.py -q
# 65 passed in 4.66s

. .venv/bin/activate && python -m pytest backend/tests -q
# 557 passed in 33.19s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.87s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 GeoIP provider order、lookup URL、proxy normalization、IP/country/timezone/locale parsing、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、profile 存储 schema 或 runtime session 行为。
- 不记录或公开 raw GeoIP source URL/host/query token、Authorization/Bearer、proxy host/username/password、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Health proxy warning detail redaction guardrail

背景：

- Profile health warnings 会直接进入 `/api/profiles/{profile_id}/health`、`/api/profiles/{profile_id}/health/check` 和前端 summary/table UI。
- `_validate_proxy()` 已隐藏 credential，但 missing port / invalid port 等错误仍会把 redacted proxy host 拼进 message，例如 `Proxy URL missing port: http://proxy.example`；host 本身仍可能是敏感资产信息。

已覆盖：

- Health `proxy_invalid` warning message 现在映射为固定低敏分类：`Invalid proxy scheme`、`Invalid proxy URL`、`Proxy URL missing hostname`、`Proxy URL invalid port`、`Proxy URL missing port`。
- `compute_profile_health()` 直接调用和 `/health/check` invalid proxy API 路径都不再回显 scheme detail、proxy host、userinfo、password 或 raw proxy URL。
- Health audit 仍只记录 warning codes/count 和低敏 lookup/runtime metadata，不记录 warning message。
- Frontend 现有 health summary/table message handling 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_invalid_proxy_returns_error backend/tests/test_health.py::test_health_invalid_proxy_warning_uses_low_sensitive_detail backend/tests/test_health.py::test_health_check_invalid_proxy_warning_does_not_echo_proxy_host -q
# RED: 3 failed；warning message 原样包含 scheme detail 或 proxy host

. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_invalid_proxy_returns_error backend/tests/test_health.py::test_health_invalid_proxy_warning_uses_low_sensitive_detail backend/tests/test_health.py::test_health_check_invalid_proxy_warning_does_not_echo_proxy_host -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q
# 21 passed in 1.81s

npm --prefix frontend test -- --run ProfileSummaryPanel ProfileTable
# Test Files 2 passed；Tests 39 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 558 passed in 32.65s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.36s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 proxy validation semantics、profile proxy 存储、GeoIP lookup、health status/warning code、audit event shape、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token 或 runtime session 行为。
- 不记录或公开 raw proxy validation exception text、proxy host/username/password、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Health manual mismatch warning redaction guardrail

背景：

- Profile health 的 manual timezone/locale mismatch warning 会进入 API response 和前端 health badge/list/table。
- 旧文案直接拼接 profile 手动 timezone/locale 与 GeoIP 建议值；profile timezone/locale 可以来自用户输入、CSV/import 或历史 DB，若包含 URL、token、Authorization/Bearer 等文本，会被 warning message 固化。

已覆盖：

- `manual_timezone_mismatch` message 固定为 `手动 timezone 与当前出口建议不一致。`。
- `manual_locale_mismatch` message 固定为 `手动 locale 与当前出口建议不一致。`。
- mismatch 判断、manual override flags、GeoIP response fields、warning code/severity/action、audit metadata 和前端 rendering 语义保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_manual_mismatch_warning_does_not_echo_manual_values -q
# RED: 1 failed；warning message 原样包含 URL、token、Authorization/Bearer

. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_manual_mismatch_warning_does_not_echo_manual_values -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q
# 22 passed in 1.74s

npm --prefix frontend test -- --run HealthBadge ProfileList
# Test Files 2 passed；Tests 16 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 559 passed in 33.22s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.21s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 profile timezone/locale 存储、GeoIP timezone/locale parsing、mismatch detection、health status/warning code、audit event shape、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token 或 runtime session 行为。
- 不记录或公开 raw health mismatch warning values、URL/query token、Authorization/Bearer、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Audit metadata string redaction guardrail

背景：

- `db.create_audit_event()` 会持久化 runtime/profile/proxy/automation/viewer/health/bulk 等多类审计 metadata。
- 旧通用 sanitizer 会删除敏感 key，并对 URL 中的 userinfo 做 proxy URL redaction，但普通 string value 里的 standalone `token=...` 或 `Authorization=Bearer ...` 不会被处理；这类文本可来自异常摘要、用户输入名称/provider、未来 audit helper 或历史调用方。

已覆盖：

- 通用 audit metadata string sanitizer 现在会 redacts:
  - `Authorization=Bearer ...` / `Authorization: Bearer ...`
  - standalone `Bearer ...`
  - `token=...`、`auth_token=...`、`password=...`、`secret=...`、`cookie=...`、`runtime_service_token=...`、`service_token=...`、`viewer_token=...`
- 保留现有 sensitive key 删除、nested metadata 递归、proxy URL userinfo redaction 和普通安全字符串行为。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields -q
# RED: 1 failed；message 中 token=message-secret 和 Authorization=Bearer bearer-secret 原样保留

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py backend/tests/test_proxies.py backend/tests/test_bulk.py backend/tests/test_health.py -q
# 316 passed in 25.76s

. .venv/bin/activate && python -m pytest backend/tests -q
# 559 passed in 32.99s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.05s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 audit event schema、event types、actor/profile/session ids、runtime viewer flow、automation task semantics、profile/proxy CRUD behavior、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token 或 runtime session 行为。
- 不记录或公开 audit metadata string value 中的 token/password/secret/cookie/Authorization/Bearer 文本；proxy URL host redaction 行为保持既有低敏 URL bucket。

## 2026-06-03 Proxy provider preset audit observability guardrail

背景：

- Proxy provider presets 会影响 random assign 与 CSV import 默认值，但 CRUD API 之前没有 audit event。
- Preset 的 name/provider/notes/tags 是自由文本，可能包含 provider URL、token、Authorization/Bearer 或内部命名；新增 audit 需要只记录低敏 metadata。

已覆盖：

- Provider preset create/update/delete 成功后写入 audit events：
  - `proxy.provider_preset.created`
  - `proxy.provider_preset.updated`
  - `proxy.provider_preset.deleted`
- Audit metadata 仅包含 `preset_id`、`tag_count`，update 时额外包含 `updated_fields`。
- 不记录 name、provider、country_code、notes、tag text、credential、provider host 或 token-like 文本。
- Provider preset CRUD API、proxy manager frontend API/page 行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py::test_proxy_provider_preset_crud_writes_low_sensitive_audit_events -q
# RED: 1 failed；provider preset CRUD 没有 audit events

. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py::test_proxy_provider_preset_crud_writes_low_sensitive_audit_events -q
# 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py backend/tests/test_proxies.py -q
# 40 passed in 3.64s

npm --prefix frontend test -- --run ProxyManagerPage api
# Test Files 2 passed；Tests 61 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 560 passed in 33.39s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.91s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 provider preset storage/response fields、random assign selection semantics、CSV import preset application、profile/proxy CRUD behavior、audit event schema、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token 或 runtime session 行为。
- 不记录或公开 provider preset name/provider/notes/tag text、provider URL/host/query token、Authorization/Bearer、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 GeoIP success field public-value guardrail

背景：

- GeoIP success fields 会进入 `GeoIPResult.as_dict()`、proxy `last_check_*`、profile `last_geoip_*`、profile health response、health audit metadata 和 profile launch 的 GeoIP 填充边界。
- 真实 provider 当前返回低敏 country/timezone/locale，但测试替身、未来 provider 或历史 DB 值若把 URL、query token、Authorization/Bearer、provider host/path 文本塞进 `country_code`、`timezone` 或 `locale`，成功路径会把这些字段持久化或回显。

已覆盖：

- 新增共享 `public_geoip_country_code`、`public_geoip_timezone`、`public_geoip_locale`：
  - `country_code` 只保留 2 字母 ISO 风格值并大写。
  - `timezone` 只保留可由 `zoneinfo` 解析的 IANA/UTC 风格值。
  - `locale` 只保留短 BCP47 风格值并规范化大小写。
- `GeoIPResult.as_dict()`、GeoIP provider parser、profile network fingerprint 填充、profile health 新 lookup、persisted health cache response、health audit metadata 和 proxy check success write/read paths 都使用低敏字段。
- 非公开字段降为 `None`，不以 `unknown` 字符串替代，因为 country/timezone/locale 是可选事实字段。
- IP、source 既有语义保持；source 继续使用 `public_geoip_source`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py backend/tests/test_health.py backend/tests/test_proxies.py -q
# RED: 4 failed；GeoIPResult.as_dict、health/check、health GET 和 proxy check success 原样暴露 sensitive country/timezone/locale

. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py backend/tests/test_health.py backend/tests/test_proxies.py -q
# 71 passed in 4.54s

. .venv/bin/activate && python -m pytest backend/tests -q
# 564 passed in 32.87s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.13s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、proxy lookup order、provider URLs、profile schema 或 audit event schema。
- 不记录或公开 raw GeoIP country/timezone/locale 中的 provider URL/host/path/query token、Authorization/Bearer、headers、cookies、local storage、proxy credentials、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 GeoIP success IP public-value guardrail

背景：

- GeoIP `ip` success field 会进入 `GeoIPResult.as_dict()`、proxy `last_check_ip`、profile `last_geoip_ip`、profile health response 和 profile launch 的 GeoIP 填充边界。
- Real provider parser 已用 IP parser 处理 `query`/`ip`，但 `GeoIPResult` test double、future provider 或历史 DB 值仍可能把 URL、query token、Authorization/Bearer 或 provider host/path 文本放进 `ip`，成功路径原本会信任这些值。

已覆盖：

- 新增共享 `public_geoip_ip`，只保留 `ipaddress` 可解析的 IP 字符串。
- `GeoIPResult.as_dict()`、provider parser、profile health new lookup、persisted health cache response 和 proxy check success write/read paths 都使用低敏 IP。
- 非公开 `ip` 降为 `None`；country/timezone/locale/source 既有 public-value guardrails 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py backend/tests/test_health.py backend/tests/test_proxies.py -q
# RED: 4 failed；GeoIPResult.as_dict、health/check、health GET 和 proxy check success 原样暴露 sensitive ip

. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py backend/tests/test_health.py backend/tests/test_proxies.py -q
# 71 passed in 4.60s

. .venv/bin/activate && python -m pytest backend/tests -q
# 564 passed in 32.38s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.16s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、proxy lookup order、provider URLs、profile schema 或 audit event schema。
- 不记录或公开 raw GeoIP IP field 中的 provider URL/host/path/query token、Authorization/Bearer、headers、cookies、local storage、proxy credentials、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 CSV import proxy error detail redaction guardrail

背景：

- CSV profile import preview/import 会解析用户上传的 `proxy` 列，并把 row-level errors 返回给管理台。
- `normalize_proxy_asset_url()` 的底层 proxy validation 已隐藏 credentials，但 missing-port/invalid-port 等异常仍会把 redacted proxy host 拼进 message，例如 `Proxy URL missing port: http://csv-proxy.example`。
- CSV `source.proxy` 保持既有 redacted proxy URL 行为；本次收敛的是 row `errors` 中不应包含 proxy host 或 raw URL detail。

已覆盖：

- CSV import proxy validation error 现在映射为固定低敏类别：
  - `Invalid proxy scheme`
  - `Invalid proxy URL`
  - `Proxy URL missing hostname`
  - `Proxy URL invalid port`
  - `Proxy URL missing port`
- `/api/profiles/import/preview` 与 `/api/profiles/import` invalid proxy rows 都使用该固定 detail。
- CSV source field redaction、valid proxy normalization、template lookup、bulk audit 和 profile create behavior 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_profile_csv_import_preview_redacts_sensitive_proxy_error_detail backend/tests/test_bulk.py::test_profile_csv_import_redacts_sensitive_proxy_error_detail -q
# RED: 2 failed；row errors 原样包含 `Proxy URL missing port: http://...example`

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_profile_csv_import_preview_redacts_sensitive_proxy_error_detail backend/tests/test_bulk.py::test_profile_csv_import_redacts_sensitive_proxy_error_detail -q
# 2 passed in 0.64s

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 19 passed in 1.70s

. .venv/bin/activate && python -m pytest backend/tests -q
# 566 passed in 31.98s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.14s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、proxy storage URL semantics、CSV supported columns、profile schema 或 audit event schema。
- 不在 CSV row errors 中公开 proxy URL/host/username/password/query token、Authorization/Bearer、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Automation pages summary redaction guardrail

背景：

- Automation console/network summary 已对 URL、query、fragment、token assignments 和 Bearer token 做低敏化。
- `/api/profiles/{profile_id}/automation/pages` 仍直接返回 `page.url` 与 `page.title()`，如果页面 URL 或标题包含 query token、URL userinfo、Authorization/Bearer 或 token-like 文本，会在管理台 runtime page summary 中回显。

已覆盖：

- Automation pages summary URL 现在使用现有 `_automation_safe_url()` 输出：保留 scheme/host/port/path，移除 userinfo、params、query 和 fragment。
- `about:*` 页面 URL 保持原样，避免把正常 `about:blank` 页显示成空字符串。
- Page title 现在复用 `_automation_redact_text()`，会 redacts URL query/fragment、`token=...` assignments 和 Bearer tokens。
- Automation page id、index、page ref lookup、goto/click/fill/evaluate/screenshot/console/network 行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_pages_redacts_sensitive_url_and_title -q
# RED: 1 failed；pages response 原样返回 `https://user:pass@...?...#frag`

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_pages_redacts_sensitive_url_and_title -q
# 1 passed in 1.47s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_pages or automation_console_logs or automation_network_summary or automation_goto"
# 11 passed, 206 deselected in 2.63s

. .venv/bin/activate && python -m pytest backend/tests -q
# 567 passed in 32.77s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.12s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、automation page actions、navigation target URL、console/network capture internals 或 audit event schema。
- 不在 Automation pages summary 中公开 page URL userinfo/query/fragment token、Authorization/Bearer、token assignments、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Automation text header credential redaction guardrail

背景：

- Automation pages summary 和 console logs 共享 `_automation_redact_text()` 来展示页面标题和浏览器 console 文本。
- 该 helper 已覆盖 URL query/fragment、`token=...` assignments 和 standalone Bearer token，但 header-style credentials 仍有缺口：`Authorization=Bearer ...` 会留下尾随 token，`Authorization: Basic ...` 与 `Cookie: sid=...` 会原样显示。

已覆盖：

- `_automation_redact_text()` 现在先 redacts Authorization header-style values，再处理 Cookie/Set-Cookie header-style values，随后保留既有 generic assignment 与 Bearer token fallback。
- `/api/profiles/{profile_id}/automation/pages` title 和 `/api/profiles/{profile_id}/automation/pages/{page_ref}/console-logs` text 都复用该修复。
- Page URL redaction、console location URL redaction、network summary、page action behavior、screenshot response 和 audit schema 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'automation_pages_redacts_sensitive_url_and_title or automation_console_logs_redacts_sensitive_text_and_location_urls'
# RED: 2 failed；响应文本仍包含 equals-secret/basic-secret/session-secret

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'automation_pages_redacts_sensitive_url_and_title or automation_console_logs_redacts_sensitive_text_and_location_urls'
# 2 passed, 215 deselected in 0.76s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'automation_pages or automation_console_logs or automation_network_summary or automation_goto or automation_page_id'
# 12 passed, 205 deselected in 1.65s

. .venv/bin/activate && python -m pytest backend/tests -q
# 567 passed in 33.33s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.97s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、automation navigation target URL、console/network capture internals 或 audit event schema。
- 不在 automation page titles 或 console log text 中公开 URL userinfo/query/fragment token、Authorization/Bearer/Basic credential、Cookie/Set-Cookie credential、token assignments、headers、local storage、viewer token、runtime service token、automation payload、profile dir 或截图内容。

## 2026-06-03 VNC proxy Xvnc log dump redaction guardrail

背景：

- `_proxy_running_vnc()` 在 VNC proxy disconnect 后会检查 `/tmp/xvnc-{display}.log` 并把最后 20 行原样写入 manager logger。
- Xvnc/KasmVNC log line 属于外部进程输出，可能包含 backend WebSocket URL、viewer token、Authorization/Bearer、profile path 或内部路径文本。此前 VNCManager start 阶段已避免输出 raw Xvnc log path/content，但 proxy disconnect dump 仍未覆盖。

已覆盖：

- VNC proxy disconnect 现在只记录固定低敏事件：`action=vnc.xvnc_log_available profile_id=... display=:...`。
- 不再读取或输出 Xvnc log raw lines。
- VNC backend connect、client/backend stream、runtime viewer audit、close_code audit、RFB filtering、clipboard bridge 和 WebSocket subprotocol behavior 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_proxy_disconnect_does_not_dump_raw_xvnc_log -q
# RED: 1 failed；caplog 原样包含 xvnc-viewer-secret、xvnc-bearer-secret、127.0.0.1:6100 和 /tmp/profile-secret

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_proxy_disconnect_does_not_dump_raw_xvnc_log -q
# 1 passed in 0.86s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'vnc_proxy or vnc_ws or ws_allows'
# 6 passed, 212 deselected in 1.21s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q -k 'runtime_vnc'
# 7 passed, 23 deselected in 1.59s

. .venv/bin/activate && python -m pytest backend/tests -q
# 568 passed in 32.37s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.12s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC viewer token validation、runtime session state machine、RFB filtering 或 audit event schema。
- 不在 VNC proxy disconnect logs 中公开 Xvnc raw log line、backend URL/port path、viewer token、Authorization/Bearer credential、profile dir、headers、cookies、local storage、automation payload 或页面内容。

## 2026-06-03 WebSocket origin log redaction guardrail

背景：

- `_check_websocket_origin()` 是普通 VNC 和 runtime viewer VNC 的共享 CSWSH 防护边界。
- Origin/Host header 属于外部输入；此前 malformed/mismatch 分支会把 raw `Origin` 和 `Host` 写入 manager warning log。恶意或非浏览器 client 可构造带 query token、path、fragment 或 token-like 文本的 Origin header。

已覆盖：

- WebSocket origin rejection logs 现在只记录低敏 host label：`origin=<host[:port]|missing|malformed>` 和 `host=<host[:port]|missing|malformed>`。
- Query、fragment、path、userinfo 和 token-like header text 不再进入 origin warning logs。
- 普通 VNC cross-origin rejection、same-origin/no-origin allow behavior、runtime viewer `origin_not_allowed` audit 语义保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_ws_origin_rejection_logs_low_sensitive_origin -q
# RED: 1 failed；caplog 原样包含 http://evil.com/path?viewer_token=origin-secret#frag

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_ws_origin_rejection_logs_low_sensitive_origin -q
# 1 passed in 0.71s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'vnc_ws or ws_allows or vnc_proxy'
# 7 passed, 212 deselected in 1.13s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_vnc_rejects_cross_origin_even_with_valid_viewer_token -q
# 1 passed in 0.71s

. .venv/bin/activate && python -m pytest backend/tests -q
# 569 passed in 33.95s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.20s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC viewer token validation、runtime session state machine、RFB filtering、proxy logic 或 audit event schema。
- 不在 WebSocket origin warning logs 中公开 raw Origin/Host header、query token、path、fragment、viewer token、Authorization/Bearer credential、headers、cookies、local storage、automation payload、profile dir 或页面内容。

## 2026-06-03 Automation network summary method/resource redaction guardrail

背景：

- Automation network summary 已对 request URL 移除 userinfo、query 和 fragment。
- 继续复查发现 `method` 与 `resource_type` 仍直接来自 Playwright request object。页面脚本、异常浏览器行为或测试 double 可构造 token/header-like 文本，进入 `/api/profiles/{profile_id}/automation/pages/{page_ref}/network-summary` 响应。

已覆盖：

- `method` 现在只保留公开 HTTP method whitelist：`GET`、`POST`、`PUT`、`PATCH`、`DELETE`、`HEAD`、`OPTIONS`、`CONNECT`、`TRACE`；其他值折叠为 `UNKNOWN`。
- `resource_type` 现在只保留 Playwright 公开 resource type whitelist：`document`、`stylesheet`、`image`、`media`、`font`、`script`、`texttrack`、`xhr`、`fetch`、`eventsource`、`websocket`、`manifest`、`other`；其他值折叠为 `unknown`。
- URL redaction、event type、status、failure reason、ring buffer、console capture、page actions 和 audit schema 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_network_summary_redacts_urls_and_returns_recent_events -q
# RED: 1 failed；response 原样包含 method-secret/method-bearer/resource-secret

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_network_summary_redacts_urls_and_returns_recent_events -q
# 1 passed in 0.75s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'automation_pages or automation_console_logs or automation_network_summary or automation_page_id'
# 10 passed, 209 deselected in 1.43s

. .venv/bin/activate && python -m pytest backend/tests -q
# 569 passed in 33.36s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 6.38s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC/runtime viewer、proxy logic、automation navigation target URL、actual browser request method/resource type、console capture internals 或 audit event schema。
- 不在 Automation network summary 中公开 URL userinfo/query/fragment token、method/header-like token、resource_type token、Authorization/Bearer credential、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Automation cached summary output redaction guardrail

背景：

- Automation console/network capture helper 已在写入时做 URL/text/method/resource redaction。
- 继续复查发现 endpoints 仍直接返回 `page.automation_console_logs` 与 `page.automation_network_events` 当前列表。若 running page 已存在历史版本写入的 raw entries，或内存条目被污染，输出端会绕过捕获时 guardrail；network summary 还可能因 raw non-integer `status` 触发 Pydantic validation error。

已覆盖：

- `/api/profiles/{profile_id}/automation/pages/{page_ref}/console-logs` 现在在响应前逐项归一化 existing entries。
- Console log `type` 只保留公开 console type whitelist，其他值折叠为 `unknown`；`text` 复用 automation text redaction；`location.url` 使用 safe URL；line/column 字段只保留非负整数。
- `/api/profiles/{profile_id}/automation/pages/{page_ref}/network-summary` 现在在响应前逐项归一化 existing entries。
- Network `event`、`method`、`resource_type`、`status` 和 `failure` 都按低敏 public rules 输出，URL 继续使用 safe URL。
- 正常捕获路径继续复用同一套输出 helper，ring buffer、page action behavior 和 audit schema 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_console_logs_redacts_existing_in_memory_entries backend/tests/test_api.py::test_automation_network_summary_redacts_existing_in_memory_events -q
# RED: 2 failed；console response 原样包含 cached secrets，network response 因 raw status-token-secret 触发 ValidationError

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_console_logs_redacts_existing_in_memory_entries backend/tests/test_api.py::test_automation_network_summary_redacts_existing_in_memory_events -q
# 2 passed in 0.79s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'automation_pages or automation_console_logs or automation_network_summary or automation_page_id'
# 12 passed, 209 deselected in 1.62s

. .venv/bin/activate && python -m pytest backend/tests -q
# 571 passed in 34.10s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.33s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC/runtime viewer、proxy logic、automation navigation target URL、actual browser request/console behavior、browser-side capture event subscription 或 audit event schema。
- 不在 Automation cached console/network summary responses 中公开 URL userinfo/query/fragment token、console text token、console type token、location token、method/header-like token、resource/status/failure token、Authorization/Bearer credential、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Automation task status/error response redaction guardrail

背景：

- Automation task create/run/cancel/retry 正常路径只写固定状态和固定错误文本。
- 继续复查历史数据防御时发现 `_automation_task_response()` 已清洗 `steps` 和 `result`，但仍直接返回 DB 中的 `status` 和 `error`。
- 如果旧版本任务、手工 DB 修复或损坏 row 含有 URL/query token、Authorization/Bearer/Cookie 文本，这些字段会通过 `GET /api/tasks/{task_id}` 和 `GET /api/tasks` 进入 response/UI。

已覆盖：

- Automation task response `status` 现在只保留 `queued`、`running`、`cancel_requested`、`cancelled`、`failed`、`succeeded`；其他值折叠为 `unknown`。
- Automation task response `error` 现在只保留当前执行器写入的固定低敏错误文本；其他字符串或非字符串折叠为 `Automation task failed`。
- Automation task audit metadata 中的 `status` 和 `previous_status` 复用同一 public status allowlist。
- 正常任务执行、worker lease、result summary、step redaction、retry/cancel/run 语义和 audit event schema 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_response_sanitizes_persisted_status_and_error_fields -q
# RED: 1 failed；response 原样返回 failed-token-super-secret Authorization=Bearer bearer-secret

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_response_sanitizes_persisted_status_and_error_fields -q
# 1 passed in 0.76s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_task or list_automation_tasks or get_automation_task or retry_automation_task or run_automation_worker"
# 38 passed, 184 deselected in 4.66s

. .venv/bin/activate && python -m pytest backend/tests -q
# 572 passed in 32.80s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.95s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC/runtime viewer、proxy logic、automation task execution、worker lease、browser page actions 或 audit event schema。
- 不在 Automation task responses 中公开历史/污染 status token、error URL query/fragment、Authorization/Bearer credential、Cookie header text、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Profile GeoIP response redaction guardrail

背景：

- GeoIP success/result 写入路径和 health response 已使用 `public_geoip_*` 过滤 IP、country、timezone、locale 和 source。
- 继续复查 profile API 输出时发现 `GET /api/profiles`、`GET /api/profiles/{profile_id}` 以及 create/import/update/bundle import 返回的 `ProfileResponse` 仍直接信任 DB 中的 `last_geoip_*` 字段。
- 如果旧版本、手工修复或损坏 DB row 含有 URL/query token、Authorization/Bearer 或 provider host/path 文本，这些字段会进入 profile list/detail response 和 UI。

已覆盖：

- 新增 `_profile_response()` 统一构造 profile API 输出。
- `last_geoip_ip`、`last_geoip_country_code`、`last_geoip_timezone`、`last_geoip_locale` 和 `last_geoip_source` 在输出前复用 `public_geoip_*` 规则。
- `last_geoip_source` 的非公开值折叠为 `unknown`；非公开 IP/country/timezone/locale 折叠为 `null`。
- profile create、list、get、update、CSV import、config import 和 bundle import 的 successful profile response 都走同一 helper。
- 正常 GeoIP success persistence、health warning logic、profile tags、runtime status、VNC port、automation URL 和 audit metadata 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_redact_persisted_sensitive_geoip_fields -q
# RED: 1 failed；last_geoip_ip 原样返回 https://geoip-secret.example/check?token=super-secret

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_redact_persisted_sensitive_geoip_fields -q
# 1 passed in 0.72s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile and (geoip or get_profile or list_profiles or create_profile or update_profile or import_profile_configs or import_profile_bundle or launch_persists_resolved_geoip)"
# 19 passed, 204 deselected in 1.83s

. .venv/bin/activate && python -m pytest backend/tests/test_health.py backend/tests/test_geoip.py backend/tests/test_proxies.py -q -k "geoip or health_check or profile_health or proxy_check"
# 38 passed, 33 deselected in 2.23s

. .venv/bin/activate && python -m pytest backend/tests -q
# 573 passed in 31.93s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.95s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、GeoIP provider order、proxy lookup、profile launch behavior、VNC/runtime viewer 或 audit event schema。
- 不在 profile responses 中公开历史/污染 GeoIP IP URL、country token、timezone token、locale token、source query token、Authorization/Bearer credential、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Proxy last-check response redaction guardrail

背景：

- Proxy check success/failure 写入路径已经使用 `public_geoip_*` 和固定错误文本。
- 继续复查历史数据防御时发现 `_proxy_response()` 仅清洗 proxy URL 和 tags；如果旧版本、手工修复或损坏 row 写入非公开 `last_check_*` 字段，`GET /api/proxies` 与 `GET /api/proxies/{proxy_id}` 会直接回显这些历史值。

已覆盖：

- Proxy response `last_check_status` 只保留 `good`、`error`；其他非空值折叠为 `unknown`。
- `last_check_ip`、`last_check_country_code`、`last_check_timezone`、`last_check_locale` 和 `last_check_source` 输出前复用 `public_geoip_*` 规则。
- 非公开 source 折叠为 `unknown`，非公开 IP/country/timezone/locale 折叠为 `null`。
- `last_check_error` 只保留固定低敏错误 `Proxy check failed`；其他非空历史错误折叠为同一固定文本。
- 正常 proxy check persistence、bulk check result、proxy URL redaction、tags 和 audit metadata 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_api_responses_redact_persisted_sensitive_last_check_fields -q
# RED: 1 failed；last_check_status 原样返回人工 leak marker

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_api_responses_redact_persisted_sensitive_last_check_fields -q
# 1 passed in 0.70s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "proxy_crud or proxy_check or bulk_check or persisted_sensitive_last_check"
# 13 passed, 20 deselected in 1.63s

. .venv/bin/activate && python -m pytest backend/tests -q
# 574 passed in 34.34s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.00s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、GeoIP provider order、proxy lookup behavior、proxy check resolver、profile launch behavior、VNC/runtime viewer 或 audit event schema。
- 不在 proxy responses 中公开历史/污染 last-check URL/path marker、country marker、timezone marker、locale marker、source marker、Bearer-like credential text、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Runtime session status response redaction guardrail

背景：

- Runtime session diagnostics aggregate 已将非公开 status 折叠为 `unknown`。
- 继续复查 runtime service API 时发现 `RuntimeSessionResponse` 仍直接信任 DB row 中的 `status`。
- 如果旧版本、手工修复或损坏 row 写入 URL/header/token-like 文本，`GET /api/runtime/sessions/{session_id}` 会把它作为可见 session status 返回。

已覆盖：

- Runtime session response `status` 只保留 `active`、`terminated`；其他值折叠为 `unknown`。
- create/get/renew/terminate 正常路径、viewer token creation、runtime/VNC audit、lease logic、viewer token hash storage 和 diagnostics aggregate 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_status -q
# RED: 1 failed；status 原样返回人工 leak marker

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_status -q
# 1 passed in 0.69s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 31 passed in 3.48s

. .venv/bin/activate && python -m pytest backend/tests -q
# 575 passed in 35.78s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.05s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、viewer token validation、VNC proxying、profile launch behavior 或 audit event schema。
- 不在 runtime session responses 中公开历史/污染 status marker、headers、cookies、local storage、viewer token、viewer token hash、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Profile template apply public-value guardrail

背景：

- Profile template 正常 API 请求已有 Pydantic 校验，但历史/手工 DB row 可以绕过校验。
- `apply_profile_template_fields()` 之前直接复制 template fields 到 profile create/import 数据；污染的 screen/hardware 类型会导致 `ProfileResponse` validation error，污染的 GPU/launch args 也会进入 profile lifecycle。

已覆盖：

- Template apply 边界现在过滤 platform、screen_width、screen_height、gpu_vendor、gpu_renderer、hardware_concurrency、color_scheme、human_preset、humanize、geoip 和 launch_args。
- screen/hardware/GPU 复用浏览器启动侧 public-value 规则；无效值不覆盖 profile 默认值。
- launch_args 会丢弃 URL/query/header/token-like 文本，并复用 Firefox launch arg 冲突过滤。
- 正常 template CRUD、template create profile、CSV import preview/import、profile config import/export 行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py::test_create_profile_from_template_sanitizes_persisted_identity_fields -q
# RED: 1 failed；污染 screen/hardware template 字段导致 ProfileResponse ValidationError

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py::test_create_profile_from_template_sanitizes_persisted_identity_fields -q
# 1 passed in 0.64s

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 10 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q -k "template or csv_import or config_import"
# 16 passed, 3 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_config or profile_launch_args or create_profile"
# 11 passed, 212 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 576 passed in 33.90s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.13s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager 或 audit event schema。
- 不在 profile/template apply responses 中公开历史/污染 template identity marker、Authorization/Bearer-like text、URL/query token、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Profile template response redaction guardrail

背景：

- Template apply 边界已过滤历史/手工 template fingerprint 字段，但 template list/detail response 仍直接构造 `ProfileTemplateResponse`。
- 旧版本或损坏 row 中的非类型匹配 screen/hardware 字段会触发 response validation error，GPU/launch args 中的非公开文本也可能进入 UI/API。

已覆盖：

- Profile template list/detail response 现在复用 template public-value 过滤。
- 非公开 platform、screen_width、screen_height、gpu_vendor、gpu_renderer、hardware_concurrency、color_scheme、human_preset 和 launch_args 会折叠为安全默认值或过滤结果。
- 正常 template CRUD、template create profile、CSV import preview/import、profile config import/export 行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_identity_fields -q
# RED: 1 failed；template detail response 因污染 screen/hardware 字段触发 ProfileTemplateResponse ValidationError

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_identity_fields -q
# 1 passed in 0.65s

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 11 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q -k "template or csv_import or config_import"
# 16 passed, 3 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_config or profile_launch_args or create_profile"
# 11 passed, 212 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 577 passed in 34.81s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.53s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager 或 audit event schema。
- 不在 profile template responses 中公开历史/污染 identity marker、Authorization/Bearer-like text、URL/query token、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Profile config export and bundle export identity guardrail

背景：

- Profile response 与 template response/apply 边界已经过滤历史/污染 identity fields，但 profile config export 和 profile bundle export 仍直接用 DB profile row 构造 `ProfileConfigExport`。
- 旧版本或手工写入的 profile row 中，如果 screen/hardware 字段包含非整数文本，会触发 response validation error；GPU/timezone/locale/enum/launch args 中的 token/header/URL-like 文本也可能进入导出的 config/bundle manifest。

已覆盖：

- 新增共享 profile config export sanitizer，并用于 `/api/profiles/export` 与 `/api/profiles/{profile_id}/bundle/export`。
- 非公开 platform、screen_width、screen_height、gpu_vendor、gpu_renderer、hardware_concurrency、timezone、locale、color_scheme、human_preset 和 launch_args 会折叠为安全默认值、`null` 或过滤后的公开参数。
- 保留显式导出的 profile name/notes/tags 语义；proxy credential redaction 与 sensitive proxy confirmation 行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_bulk_export_profile_configs_sanitizes_persisted_identity_fields -q
# RED: 1 failed；profile config export 因污染 screen/hardware 字段触发 ProfileConfigExport ValidationError

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_sanitizes_persisted_identity_fields -q
# RED: 1 failed；profile bundle export 因污染 screen/hardware 字段触发 ProfileConfigExport ValidationError

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_bulk_export_profile_configs_sanitizes_persisted_identity_fields backend/tests/test_api.py::test_export_profile_bundle_sanitizes_persisted_identity_fields -q
# 2 passed in 1.25s

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -k "export_profile_configs or config_import or round_trip" -q
# 6 passed, 14 deselected in 1.19s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "export_profiles or profile_bundle or config_import" -q
# 23 passed, 201 deselected in 2.30s

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py -q
# 4 passed in 0.23s

. .venv/bin/activate && python -m pytest backend/tests -q
# 579 passed in 32.27s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.45s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager 或 audit event schema。
- 不在 profile config export 或 bundle manifest 中公开历史/污染 identity marker、Authorization/Bearer-like text、URL/query token、headers、cookies、local storage、viewer token、runtime service token、automation payload、profile dir 或页面内容。

## 2026-06-03 Malformed tag response stability guardrail

背景：

- DB tag decode 只保证 JSON tag item 是 dict，历史/手工 DB row 仍可能缺少 `tag`，或包含非字符串 `tag`/`color`。
- Profile、proxy asset 和 proxy provider preset 响应此前直接执行 `TagResponse(**tag)`；这会让 list/detail、proxy random assignment result、profile config export 等 release-smoke 路径在响应构造时抛 validation error。

已覆盖：

- 新增共享 tag response normalizer，用于 profile response、proxy response、proxy provider preset response 和 profile config export。
- 非 dict tag item、缺少字符串 `tag` 的 item 会被丢弃；非字符串或不可解码的 `color` 会变为 `null`。
- 正常 profile/proxy/provider preset tag 行为、proxy random assignment 和 config export 语义保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_response_sanitizes_persisted_malformed_tags backend/tests/test_proxies.py::test_proxy_response_sanitizes_persisted_malformed_tags backend/tests/test_proxy_provider_presets.py::test_proxy_provider_preset_api_sanitizes_persisted_malformed_tags -q
# RED: 3 failed；profile/proxy/preset responses 分别在 TagResponse 构造处失败

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_response_sanitizes_persisted_malformed_tags backend/tests/test_proxies.py::test_proxy_response_sanitizes_persisted_malformed_tags backend/tests/test_proxy_provider_presets.py::test_proxy_provider_preset_api_sanitizes_persisted_malformed_tags -q
# 3 passed in 1.76s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "profile_response or create_profile_with_all_fields or tags or export_profiles" -q
# 11 passed, 214 deselected in 1.76s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -k "proxy_crud_api or malformed_tags or random_proxy_assignment or assign_proxy" -q
# 7 passed, 27 deselected in 1.69s

. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py -q
# 10 passed in 1.50s

. .venv/bin/activate && python -m pytest backend/tests -q
# 582 passed in 32.13s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.44s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager 或 audit event schema。
- 不在 response tag normalizer 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates 或 audit metadata。

## 2026-06-03 Proxy selection metadata public-value guardrail

背景：

- Proxy asset 与 proxy provider preset 的 `provider`/`country_code` 会影响 random assignment 选择、release proxy-country smoke 过滤、API/UI 响应和 bulk audit metadata。
- 历史/手工 DB row 可以绕过输入路径，把 URL/query token、Authorization/Bearer、cookie 或非公开 country/provider 文本写入这些 selection metadata 字段。
- 此前 `_proxy_response` 只过滤 proxy URL、last_check 和 tags，provider preset response 只过滤 tags，random assignment 会直接把污染 preset metadata 用作候选过滤并写回 response/audit。

已覆盖：

- 新增 proxy provider public-value filter：保留短公共 provider 标签，丢弃 URL、proxy scheme、userinfo、query/fragment、Authorization/Bearer、token/secret/password/cookie/auth 以及控制/路径式文本。
- Proxy asset response、proxy provider preset response、proxy CRUD audit metadata、random assignment provider selection、proxy candidate matching 和 random assignment audit metadata 均复用 public provider/country 过滤。
- `country_code` 统一复用已有 2 字母 public GeoIP country normalizer；污染 country 值折叠为 `null`，正常 `JP`/`US` 等保持大写。
- 当 provider preset 的 provider/country 历史值污染但 tag 仍有效时，random assignment 会继续按有效 tag 选择候选，不再泄露或用污染 metadata 造成 400。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_api_responses_redact_persisted_sensitive_selection_fields backend/tests/test_proxy_provider_presets.py::test_proxy_provider_preset_api_redacts_persisted_sensitive_selection_fields backend/tests/test_proxies.py::test_random_proxy_assignment_redacts_persisted_sensitive_preset_selection_metadata -q
# RED: 3 failed；proxy/preset 响应直接回显敏感 provider，random assignment 使用污染 preset selection metadata 后返回 400

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_api_responses_redact_persisted_sensitive_selection_fields backend/tests/test_proxy_provider_presets.py::test_proxy_provider_preset_api_redacts_persisted_sensitive_selection_fields backend/tests/test_proxies.py::test_random_proxy_assignment_redacts_persisted_sensitive_preset_selection_metadata -q
# 3 passed in 1.00s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py backend/tests/test_proxy_provider_presets.py -q
# 47 passed in 4.40s

. .venv/bin/activate && python -m pytest backend/tests -q
# 585 passed in 33.87s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.14s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager 或 external proxy checking。
- 不在 provider/country guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw audit payloads。

## 2026-06-03 Profile/proxy audit name public-value guardrail

背景：

- Profile 与 proxy CRUD audit metadata 仍会记录普通 `name`，用于本地审计时识别对象。
- DB audit sanitizer 会清理 token assignment、Bearer 和 proxy URL userinfo，但如果 `name` 自身是 URL/header/token 风格文本，sanitizer 仍可能留下低敏性不足的 host/path 上下文，例如 `https://profile-audit-name.example`。
- Provider preset audit 已经不记录 name；profile/proxy audit 需要在保留普通短名称的同时，避免把敏感 name 放入持久 audit metadata。

已覆盖：

- 新增 audit name public-value filter：普通短 ASCII 名称继续写入 audit；URL、proxy scheme、userinfo、query/fragment、Authorization/Bearer、token/secret/password/cookie/auth、path/header/control 风格名称会从 audit metadata 中省略。
- Profile create/delete 与 proxy create/delete 的敏感 name 均不进入 audit metadata；API response 与 DB 中的用户可见 name 语义不变。
- 既有 profile/proxy CRUD audit 测试继续证明普通名称、platform/provider/country/tag_count/updated_fields 行为保持。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_crud_audit_omits_sensitive_name_metadata backend/tests/test_api.py::test_profile_crud_audit_omits_sensitive_name_metadata -q
# RED: 2 failed；audit metadata name 经 sanitizer 后仍包含 profile/proxy audit-name host

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_crud_audit_omits_sensitive_name_metadata backend/tests/test_api.py::test_profile_crud_audit_omits_sensitive_name_metadata -q
# 2 passed in 1.00s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -k "audit or proxy_crud_api" -q
# 6 passed, 31 deselected in 1.35s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "profile_crud_api_writes_redacted_audit_events or profile_crud_audit_omits_sensitive_name_metadata or delete_profile_stops_running" -q
# 3 passed, 223 deselected in 0.97s

. .venv/bin/activate && python -m pytest backend/tests -q
# 587 passed in 33.60s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.02s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager、profile/proxy response shape 或 persisted user-facing name values。
- 不在 audit name guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Profile response identity public-value guardrail

背景：

- Profile list/detail/create/update response 是 release smoke、profile lifecycle 和后续 launch/VNC/automation 操作的主要 API 面。
- Template apply、template response、config export 和 bundle export 已经过滤历史/手工 DB identity 字段，但 `_profile_response` 此前只过滤 last_geoip 和 tags。
- 历史 profile row 中的污染 `screen_width`、`hardware_concurrency`、boolean identity flags 等字段会在 `ProfileResponse` 构造时触发 validation error；GPU/timezone/locale/color/launch arg 污染值也可能进入 API/UI response。

已覆盖：

- 新增 profile response sanitizer，复用 profile template/export 的 public-value identity 规则，覆盖 platform、screen dimensions、GPU text、hardware concurrency、timezone、locale、humanize、human_preset、headless、geoip、clipboard_sync、auto_launch、color_scheme 和 launch_args。
- Profile response 的 `launch_args` 只做低敏过滤，保留普通既有 API 参数如 `--profile`，但丢弃 URL、query/fragment、Authorization/Bearer、token/password/secret/cookie 风格参数。
- Profile response 仍保留既有 name、proxy、notes、user_data_dir 等 API 语义；本轮不改变 profile storage、launch manager 或 config export 行为。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_identity_fields -q
# RED: 1 failed；ProfileResponse 构造在 screen_width/hardware_concurrency/boolean identity flags 上触发 validation errors

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_identity_fields -q
# 1 passed in 0.70s

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 11 passed in 1.22s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "profile_responses or profile_response or create_profile_with_all_fields or get_profile or update_profile or profile_config or export_profiles" -q
# 22 passed, 205 deselected in 2.47s

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -k "export_profile_configs or config_import or round_trip or csv_import" -q
# 20 passed in 2.25s

. .venv/bin/activate && python -m pytest backend/tests -q
# 588 passed in 33.33s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.14s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager、external smoke scripts 或 stored profile fields。
- 不在 profile response sanitizer 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Runtime external session id public-value guardrail

背景：

- Runtime service API 与 runtime viewer VNC audit 使用 `external_session_id` 作为跨系统关联字段。
- Runtime session `status` 已做 response sanitizer，但 `external_session_id` 仍是 runtime service caller 控制的字符串；response 与 audit event 顶层字段都会直接使用它。
- DB audit metadata sanitizer 不处理顶层 `external_session_id`，因此 URL/query token、Authorization/Bearer 或 viewer-token 风格 external id 会进入 release smoke audit evidence。

已覆盖：

- 新增 runtime external session id public-value filter：保留普通短 id，如 `pm-session-token`、`pm-session-auth-enabled` 和 `external-1`；丢弃 URL、proxy scheme、userinfo、query/fragment、Authorization/Bearer 和 token/password/cookie/secret assignment 风格字符串。
- RuntimeSessionResponse 中非公开 external id 折叠为 `unknown`。
- Runtime service audit、runtime viewer connected/disconnected audit 和 runtime viewer failure audit 的顶层 `external_session_id` 均复用该 filter；非公开值省略为 `null`。
- DB 原始 session row、viewer token flow、runtime service token flow 和正常 external id 行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_external_session_id backend/tests/test_session_broker.py::test_runtime_viewer_failure_audit_omits_sensitive_external_session_id -q
# RED: 2 failed；response 和 audit 顶层 external_session_id 直接保留 URL/query token/Authorization/Bearer 文本

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_external_session_id backend/tests/test_session_broker.py::test_runtime_viewer_failure_audit_omits_sensitive_external_session_id -q
# 2 passed in 0.75s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 33 passed in 3.59s

. .venv/bin/activate && python -m pytest backend/tests -q
# 590 passed in 34.51s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.87s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage, viewer token generation, VNC proxying, or external smoke scripts。
- 不在 runtime external id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Runtime profile id public-value guardrail

背景：

- Runtime service API response 与 runtime service/viewer audit 顶层字段都会暴露 `profile_id`，用于关联 runtime session 与本地 profile。
- 正常 profile id 应为 UUID；但旧版本、手工修复或损坏 DB row 可能让 runtime session 关联到非 UUID profile id。
- DB audit metadata sanitizer 不处理顶层 `profile_id`，因此 URL/query token、Authorization/Bearer 或 header-like profile id 会进入 release smoke response/audit evidence。

已覆盖：

- 新增 UUID-only public identifier helper；只保留 canonical UUID 字符串。
- RuntimeSessionResponse 中非 UUID `profile_id` 折叠为 `unknown`。
- Runtime service audit、runtime viewer connected/disconnected audit 和 runtime viewer failure audit 的顶层 `profile_id` 复用 UUID-only filter；非公开值省略为 `null`。
- DB 原始 row、runtime session lease、viewer credential、runtime service token、external session id guardrail 和正常 UUID profile id 行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_profile_id backend/tests/test_session_broker.py::test_runtime_viewer_failure_audit_omits_sensitive_profile_id -q
# RED: 2 failed；response 和 audit 顶层 profile_id 直接保留非 UUID URL/header/token-like 文本

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_profile_id backend/tests/test_session_broker.py::test_runtime_viewer_failure_audit_omits_sensitive_profile_id -q
# 2 passed in 0.80s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 35 passed in 3.73s

. .venv/bin/activate && python -m pytest backend/tests -q
# 592 passed in 34.53s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.33s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 runtime profile id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Runtime session id public-value guardrail

背景：

- Runtime session `id` 是 RuntimeSessionResponse、runtime service audit、runtime viewer audit 和 viewer-token URL 的顶层关联字段。
- 正常 runtime session id 应为 UUID；但旧版本、手工修复或损坏 DB row 可能写入非 UUID 字符串。
- Runtime viewer origin rejection 在读取 session 前就会写 failure audit；此前会直接使用 URL path 中的 `session_id`。

已覆盖：

- RuntimeSessionResponse 中非 UUID `id` 折叠为 `unknown`。
- Runtime service audit、runtime viewer connected/disconnected audit 和 runtime viewer failure audit 的顶层 `runtime_session_id` 复用 UUID-only filter；非公开值省略为 `null`。
- Runtime viewer-token response 的 `viewer_url` session path 只使用 canonical UUID；非公开 session id 折叠为 `unknown`，避免历史/污染 id 进入 response URL。
- DB 原始 row、runtime lookup、lease、viewer credential、runtime service token、external/profile id guardrails 和正常 UUID session id 行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_session_id backend/tests/test_session_broker.py::test_runtime_viewer_token_response_sanitizes_persisted_session_id backend/tests/test_session_broker.py::test_runtime_viewer_origin_failure_audit_omits_sensitive_session_id -q
# RED: 3 failed；response id、viewer_url 和 audit 顶层 runtime_session_id 直接保留非 UUID URL/header/token-like 文本

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_session_id backend/tests/test_session_broker.py::test_runtime_viewer_token_response_sanitizes_persisted_session_id backend/tests/test_session_broker.py::test_runtime_viewer_origin_failure_audit_omits_sensitive_session_id -q
# 3 passed in 0.97s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 38 passed in 3.91s

. .venv/bin/activate && python -m pytest backend/tests -q
# 595 passed in 34.00s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.10s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 runtime session id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Runtime template profile name public-value guardrail

背景：

- Runtime session 使用 `template_id` 创建临时 profile 时，会自动生成 profile name。
- 旧实现直接拼接 caller-controlled `external_session_id`，即使 runtime response/audit 顶层 external id 已过滤，profile list/detail 仍会保留 name 语义并可能回显 URL/query token/header-like external id。

已覆盖：

- Template-created runtime profile name 现在只拼接 public external session id。
- 非公开 external id 不进入 profile name；生成名称固定为 `Runtime session`。
- 正常 public external id 仍生成 `Runtime <external_session_id>`，template platform/screen/geoip 应用、launch、runtime session persistence 和 existing profile_id flow 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_generated_profile_name -q
# RED: 1 failed；template-created profile name 直接保留 URL/header/token-like external id

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_generated_profile_name -q
# 1 passed in 0.70s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_creates_profile_then_launches backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_generated_profile_name backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_external_session_id -q
# 3 passed in 3.14s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 39 passed in 4.48s

. .venv/bin/activate && python -m pytest backend/tests -q
# 596 passed in 34.65s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.06s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 runtime template profile name guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Runtime template identity field guardrail

背景：

- Profile create/import template apply 和 template response 已复用 public-value sanitizer。
- Runtime session `template_id` 创建 profile 的路径仍直接复制 template platform、screen、GPU、hardware、color、human preset 和 launch_args 字段，并把新 profile 传给 `browser_mgr.launch()`。
- 历史/手工污染 template row 可绕过既有 template apply guardrail，把 URL/query token/header-like identity 字段写入 runtime-created profile 并进入 launch lifecycle。

已覆盖：

- Runtime template create path 现在先复用 `sanitize_profile_template_response_data()`。
- 进入 `db.create_profile()` 和 `browser_mgr.launch()` 的 template identity fields 与 profile/template API sanitizer 保持一致：无效 platform/screen/hardware/color/human preset 回落到 defaults，非公开 GPU 文本删除，非公开 launch args 删除。
- 正常 template field copy、runtime generated profile name、launch、runtime session persistence、existing profile_id flow 和 response/audit id guardrails 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_template_identity_before_launch -q
# RED: 1 failed；runtime template path 直接把污染 platform/GPU/screen/launch_args 送入 launch profile

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_template_identity_before_launch -q
# 1 passed in 0.72s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_creates_profile_then_launches backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_generated_profile_name backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_template_identity_before_launch backend/tests/test_templates.py::test_create_profile_from_template_sanitizes_persisted_identity_fields backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_identity_fields -q
# 5 passed in 1.00s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_templates.py -q
# 51 passed in 4.85s

. .venv/bin/activate && python -m pytest backend/tests -q
# 597 passed in 34.10s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.16s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 runtime template identity field guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Launch failure profile id log guardrail

背景：

- Profile launch 和 runtime session launch 的 generic failure 日志已只记录固定 `error_type`，不记录 raw exception text。
- 继续复查发现这两个 endpoint 的 failure log 仍直接写 `profile_id`。
- 如果旧版本、手工修复或损坏 DB row 让 profile id 变成 URL/query token/header-like 字符串，launch failure 日志会保留该文本。

已覆盖：

- 普通 `POST /api/profiles/{profile_id}/launch` generic failure log 中的 profile id 只保留 canonical UUID；非 UUID 折叠为 `unknown`。
- Runtime `POST /api/runtime/sessions` profile launch generic failure log 使用同一 UUID-only public identifier。
- 既有 HTTP 500 response、fixed `error_type`、ValueError proxy detail redaction、resource-limit handling、diagnostics launch failure summary 和正常 UUID profile id 语义保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_failure_log_omits_sensitive_profile_id backend/tests/test_session_broker.py::test_runtime_session_create_launch_failure_log_omits_sensitive_profile_id -q
# RED: 2 failed；普通 launch 和 runtime session launch failure log 直接保留非 UUID URL/header/token-like profile id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_failure_log_omits_sensitive_profile_id backend/tests/test_session_broker.py::test_runtime_session_create_launch_failure_log_omits_sensitive_profile_id -q
# 2 passed in 0.85s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_failure_500 backend/tests/test_api.py::test_launch_failure_log_omits_sensitive_profile_id backend/tests/test_api.py::test_system_diagnostics_reports_low_sensitive_launch_failure_summary backend/tests/test_session_broker.py::test_runtime_session_create_launch_failure_log_omits_sensitive_profile_id backend/tests/test_session_broker.py::test_runtime_session_create_redacts_sensitive_launch_value_error_detail -q
# 5 passed in 1.02s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py -q -k "runtime_session_create or launch_failure or launch_invalid_proxy or max_running_profiles"
# 16 passed, 253 deselected in 1.84s

. .venv/bin/activate && python -m pytest backend/tests -q
# 599 passed in 34.47s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.13s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 launch failure profile id log guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Profile response id / automation URL guardrail

背景：

- Profile list/detail response 已清洗 persisted identity fields、GeoIP 和 tags。
- 继续复查发现 response 顶层 `id` 仍直接使用 DB row id，running status 的 `automation_url` 也由该 id 拼接。
- 如果历史/手工 DB row 含有非 UUID profile id，profile list/detail 和 UI-facing automation URL 会保留该文本。

已覆盖：

- `ProfileResponse.id` 现在只保留 canonical UUID；非 UUID 折叠为 `unknown`。
- Running profile response 的 `automation_url` 使用同一 public profile id 重建；非 UUID id 返回 `/api/profiles/unknown/automation`。
- 正常 UUID profile list/detail、profile identity field sanitizer、status 和 running automation URL 语义保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_response_sanitizes_persisted_profile_id_and_automation_url -q
# RED: 1 failed；profile response 顶层 id 直接保留非 UUID DB row id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_response_sanitizes_persisted_profile_id_and_automation_url -q
# 1 passed in 0.78s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_response or get_profile or list_profiles"
# 13 passed, 216 deselected in 1.46s

. .venv/bin/activate && python -m pytest backend/tests -q
# 600 passed in 34.05s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.98s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 profile response id / automation URL guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Profile launch/status automation URL guardrail

背景：

- Profile list/detail response 已经对顶层 id 和 running automation URL 使用 public UUID guardrail。
- 继续复查相邻 API 后发现 launch success response、profile status response 和 automation info response 仍直接使用 raw path/DB profile id 拼接 response `profile_id`、`automation_url` 和 `pages_url`。
- 历史/手工非 UUID profile id 不应进入 release smoke response、UI-facing automation URL 或低敏交接证据。

已覆盖：

- `POST /api/profiles/{profile_id}/launch` 成功响应的 `profile_id` 现在只保留 canonical UUID；非 UUID 折叠为 `unknown`。
- Launch success 和 `GET /api/profiles/{profile_id}/status` 的 `automation_url` 现在由 public profile id 重建。
- `GET /api/profiles/{profile_id}/automation` 的 `profile_id` 和 `pages_url` 现在由 public profile id 重建。
- 正常 UUID launch/status/automation info 路径保持通过；内部 running profile lookup 和 route path 语义不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_success_response_sanitizes_persisted_profile_id_and_automation_url backend/tests/test_api.py::test_status_and_automation_info_sanitize_persisted_profile_id_urls -q
# RED: 2 failed；launch success profile_id 与 status automation_url 直接保留非 UUID profile id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_success_response_sanitizes_persisted_profile_id_and_automation_url backend/tests/test_api.py::test_status_and_automation_info_sanitize_persisted_profile_id_urls -q
# 2 passed in 1.06s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "launch_success_response or automation_info or running_profile_exposes_automation_url_only or profile_response_sanitizes_persisted_profile_id"
# 7 passed, 224 deselected in 1.12s

. .venv/bin/activate && python -m pytest backend/tests -q
# 602 passed in 34.37s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.94s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 profile launch/status automation URL guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Automation task profile id guardrail

背景：

- Automation Task response 已清洗 steps、result、error、status 和 lease metadata。
- 继续复查发现 task response 顶层 `profile_id` 和 `automation.task.*` audit event 顶层 `profile_id` 仍直接使用 task 中的 profile id。
- 如果历史/手工 DB row 含有非 UUID profile id，task create/get/list/cancel/retry/run response 和 audit evidence 会保留该文本。

已覆盖：

- AutomationTaskResponse 的 `profile_id` 现在只保留 canonical UUID；非 UUID 折叠为 `unknown`。
- `automation.task.*` audit event 顶层 `profile_id` 现在只保留 canonical UUID；非 UUID 省略。
- Task create/list/get/cancel/retry/run response 和 created/cancelled/retried/succeeded audit flow 均覆盖。
- 正常 UUID Automation Task response/audit 行为保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_sanitize_persisted_profile_id -q
# RED: 1 failed；Automation Task responses 直接保留非 UUID profile id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_sanitize_persisted_profile_id -q
# 1 passed in 0.86s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_task"
# 39 passed, 193 deselected in 5.16s

. .venv/bin/activate && python -m pytest backend/tests -q
# 603 passed in 36.54s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.05s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 automation task profile id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Cookie import/export profile id guardrail

背景：

- Cookie import/export API 已要求显式确认，并清洗 cookie values、names、domains、URL query/fragment 和 audit summary。
- 继续复查发现 JSON/Netscape cookie import/export response 顶层 `profile_id`、cookie export document metadata `profile_id`、以及 `cookie.exported` audit 顶层 `profile_id` 仍直接使用 route/profile id。
- 历史/手工非 UUID profile id 不应进入 cookie API response、export metadata 或 release smoke audit evidence。

已覆盖：

- JSON cookie import 和 Netscape cookie import response 的 `profile_id` 现在只保留 canonical UUID；非 UUID 折叠为 `unknown`。
- JSON cookie export 和 Netscape cookie export response 的 `profile_id` 现在使用同一 public profile id。
- JSON cookie export document metadata `profile_id` 使用 public profile id；正常 UUID artifact 不变，非 UUID 返回 `unknown`。
- `cookie.exported` audit event 顶层 `profile_id` 现在只保留 canonical UUID；非 UUID 省略。
- 正常 UUID cookie import/export response、document、text 和 audit summary 行为保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_cookie_import_export_sanitizes_persisted_profile_id_response_and_audit -q
# RED: 1 failed；cookie import/export responses 直接保留非 UUID profile id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_cookie_import_export_sanitizes_persisted_profile_id_response_and_audit -q
# 1 passed in 0.78s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "cookie"
# 28 passed, 205 deselected in 2.63s

. .venv/bin/activate && python -m pytest backend/tests -q
# 604 passed in 36.83s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.25s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 cookie import/export profile id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Profile bundle export profile id guardrail

背景：

- Profile bundle export 会组合 profile config、cookie document、local storage entries 和 bundle audit events。
- 继续复查发现 bundle response 顶层 `profile_id`、bundle metadata `source_profile_id`、embedded cookie document `profile_id`、以及 `profile_bundle.cookie_exported` / `profile_bundle.local_storage_exported` audit 顶层 `profile_id` 仍直接使用 route/profile id。
- 历史/手工非 UUID profile id 不应进入 bundle API response、bundle metadata、embedded cookie metadata 或 release smoke audit evidence。

已覆盖：

- ProfileBundleExportResponse 的 `profile_id` 现在只保留 canonical UUID；非 UUID 折叠为 `unknown`。
- Bundle metadata `source_profile_id` 使用同一 public profile id。
- Bundle cookie document metadata `profile_id` 使用 public profile id。
- Bundle cookie/local-storage export audit 顶层 `profile_id` 现在只保留 canonical UUID；非 UUID 省略。
- 正常 UUID bundle config/cookie/local-storage export 和 bundle import behavior 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_sanitizes_persisted_profile_id_response_and_audit -q
# RED: 1 failed；bundle export response 顶层 profile_id 直接保留非 UUID profile id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_sanitizes_persisted_profile_id_response_and_audit -q
# 1 passed in 0.80s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_bundle"
# 20 passed, 214 deselected in 2.05s

. .venv/bin/activate && python -m pytest backend/tests -q
# 605 passed in 35.56s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.17s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 profile bundle export profile id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Proxy assignment profile id guardrail

背景：

- Proxy assign/random-assign API 是 proxy-country release gate 的准备路径。
- 继续复查发现 fixed proxy assignment 和 random proxy assignment response 的 per-profile result `profile_id` 直接使用 request/profile id。
- 如果历史/手工 DB row 含有非 UUID profile id，成功 assignment response 会把该文本带入 release smoke evidence。

已覆盖：

- Fixed proxy assignment 成功 result 的 `profile_id` 现在只保留 canonical UUID；命中的非 UUID profile id 折叠为 `unknown`。
- Random proxy assignment 成功 result 使用同一 public profile id guardrail。
- Missing profile 的普通低敏 id 仍按既有 API 语义返回；missing 的敏感/非公开 id 会折叠为 `unknown`。
- 正常 UUID proxy assign/random-assign behavior、proxy redaction、provider/country/tag filtering 和 audit metadata 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_proxy_assignment_responses_sanitize_persisted_profile_id -q
# RED: 1 failed；fixed proxy assignment response 直接保留非 UUID profile id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_proxy_assignment_responses_sanitize_persisted_profile_id backend/tests/test_proxies.py::test_proxy_assigns_raw_url_to_profiles_without_leaking_credentials backend/tests/test_proxies.py::test_random_proxy_assignment_filters_by_country_tag_and_preset_without_leaking_credentials -q
# 3 passed in 1.13s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py backend/tests/test_proxies.py -q -k "proxy_assignment or proxy_assign or random_proxy_assignment or random_assign or proxy"
# 47 passed, 225 deselected in 4.44s

. .venv/bin/activate && python -m pytest backend/tests -q
# 606 passed in 36.81s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.32s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 proxy assignment profile id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Profile config export profile id guardrail

背景：

- Profile config export 是 release artifact flow 的基础接口，常用于 bundle import/export 前后校验 profile config。
- 继续复查发现 `/api/profiles/export` 每个 result 的 `profile_id` 直接使用 request/profile id。
- 如果历史/手工 DB row 含有非 UUID profile id，成功 export result 会把该文本带入 API response 和 release smoke evidence。

已覆盖：

- 成功 export result 的 `profile_id` 现在只保留 canonical UUID；命中的非 UUID profile id 折叠为 `unknown`。
- Missing profile 的普通低敏 id 仍按既有 API 语义返回；missing 的敏感/非公开 id 会折叠为 `unknown`。
- Profile config payload 继续复用既有 sanitizer；正常 UUID export、missing profile result、sensitive proxy confirmation 和 bulk audit behavior 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profiles_sanitizes_persisted_profile_id_response -q
# RED: 1 failed；profile export success result 直接保留非 UUID profile id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profiles_sanitizes_persisted_profile_id_response -q
# 1 passed in 0.80s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py backend/tests/test_bulk.py -q -k "export_profiles or profiles/export or profile_config_export"
# 6 passed, 250 deselected in 1.11s

. .venv/bin/activate && python -m pytest backend/tests -q
# 607 passed in 35.15s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.26s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 profile config export profile id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Profile/health audit profile id guardrail

背景：

- Release smoke 会抽查 profile CRUD audit、profile health audit 和 health lookup failure logs。
- 继续复查发现 profile CRUD audit 和 health audit 的顶层 `profile_id` 仍直接使用 DB/path profile id；health GeoIP lookup failure log 也直接打印 path profile id。
- 如果历史/手工 DB row 含有非 UUID profile id，这些 audit/log 边界会把 URL/header/token 风格文本带入低敏 evidence。

已覆盖：

- Profile CRUD audit 顶层 `profile_id` 现在只保留 canonical UUID；非 UUID 历史/手工 id 会省略。
- Profile audit metadata 的 `platform` 现在只保留 `windows`、`macos`、`linux`；非公开/污染 platform 会省略。
- Profile health audit 顶层 `profile_id` 现在只保留 canonical UUID；非 UUID id 会省略。
- Health GeoIP lookup failure log 的 profile id 现在使用 UUID-only 值，非 UUID 记录为固定 `unknown`。
- 正常 UUID profile CRUD audit、health audit metadata、GeoIP lookup failure log、response redaction 和 existing health behavior 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_crud_audit_sanitizes_persisted_profile_id_and_platform -q
# RED: 1 failed；profile.updated/profile.deleted audit 顶层 profile_id 直接保留非 UUID profile id

. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_check_audit_and_logs_sanitize_persisted_profile_id -q
# RED: 1 failed；profile.health_checked audit 和 health lookup failure log 直接保留非 UUID profile id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_crud_audit_sanitizes_persisted_profile_id_and_platform -q
# 1 passed in 0.79s

. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_check_audit_and_logs_sanitize_persisted_profile_id -q
# 1 passed in 0.70s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_crud_audit or profile.created or profile.updated or profile.deleted"
# 2 passed, 235 deselected in 0.89s

. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q -k "health_check_success_writes_redacted_audit_event or health_check_invalid_proxy_writes_redacted_audit_without_lookup or health_check_lookup_failure_writes_redacted_audit_event or health_check_lookup_failure_logs_error_type_without_raw_exception or health_check_audit_and_logs_sanitize_persisted_profile_id"
# 5 passed, 20 deselected in 1.06s

. .venv/bin/activate && python -m pytest backend/tests -q
# 609 passed in 38.42s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.05s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 profile/health audit profile id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Proxy asset id guardrail

背景：

- Proxy Manager、proxy assignment、random assignment 和 bulk check 都是 proxy-country release gate 的准备与证据路径。
- 继续复查发现 proxy asset response、fixed/random assignment result、bulk check result 和 proxy CRUD/assignment audit metadata 仍直接使用 proxy asset id。
- 如果历史/手工 DB row 含有非 UUID proxy id，这些 API/audit 边界会把 URL/header/token 风格 id 文本带入低敏 release evidence。

已覆盖：

- Proxy list/detail/update response 的 `id` 现在只保留 canonical UUID；非 UUID 历史/手工 id 折叠为 `unknown`。
- Fixed proxy assignment response 顶层 `proxy_id` 和 nested proxy response id 使用同一 public proxy id。
- Random proxy assignment per-result `proxy_id` 和 nested proxy response id 使用同一 public proxy id。
- Proxy bulk check existing-result `proxy_id` 和 nested proxy response id 使用同一 public proxy id；missing proxy 的普通低敏 id 仍保持既有语义，敏感/非公开 missing id 折叠为 `unknown`。
- Proxy CRUD audit 和 fixed assignment audit metadata 只保留 canonical UUID proxy id；非 UUID proxy id 会省略。
- 正常 UUID proxy CRUD、audit、bulk check、fixed assignment、random assignment、provider/country/tag filtering 和 credential redaction 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_asset_responses_and_audits_sanitize_persisted_proxy_id -q
# RED: 1 failed；proxy detail response id 直接保留非 UUID proxy id

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_asset_responses_and_audits_sanitize_persisted_proxy_id -q
# 1 passed in 0.99s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py backend/tests/test_api.py -q -k "proxy_asset_responses_and_audits_sanitize_persisted_proxy_id or proxy_crud_api or proxy_crud_audit or proxy_assign or random_proxy_assignment or proxy_bulk_check or proxy_assignment_responses"
# 19 passed, 256 deselected in 2.75s

. .venv/bin/activate && python -m pytest backend/tests -q
# 610 passed in 36.73s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.03s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 proxy asset id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Proxy provider preset id guardrail

背景：

- Provider preset 是 random proxy assignment 和 proxy-country release preparation 的输入边界。
- 继续复查发现 provider preset list/detail/update response、provider preset audit metadata、random assignment response 和 random assignment audit metadata 仍直接使用 provider preset id。
- 如果历史/手工 DB row 含有非 UUID provider preset id，这些 API/audit 边界会把 URL/header/token 风格 id 文本带入低敏 evidence。

已覆盖：

- Provider preset list/detail/update response 的 `id` 现在只保留 canonical UUID；非 UUID 历史/手工 id 折叠为 `unknown`。
- Provider preset CRUD audit metadata 的 `preset_id` 现在只保留 canonical UUID；非 UUID id 会省略。
- Random proxy assignment response 的 `provider_preset_id` 现在来自命中 preset row 的 public id；非 UUID preset id 折叠为 `unknown`。
- Random assignment audit metadata 的 `provider_preset_id` 现在只保留 canonical UUID；非 UUID id 会省略。
- 正常 UUID provider preset flow、random assignment selection、provider/country/tag filtering、proxy credential redaction 和 frontend gates 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_provider_preset_responses_and_audits_sanitize_persisted_preset_id -q
# RED: 1 failed；provider preset detail response id 直接保留非 UUID preset id

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_provider_preset_responses_and_audits_sanitize_persisted_preset_id -q
# 1 passed in 0.88s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "provider_preset or random_proxy_assignment or provider_preset_id"
# 6 passed, 33 deselected in 1.43s

. .venv/bin/activate && python -m pytest backend/tests -q
# 611 passed in 39.19s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.32s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 proxy provider preset id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、proxy credentials 或 raw browser artifacts。

## 2026-06-03 Automation task id guardrail

背景：

- Automation task list/detail/cancel/retry/run response 和 automation.task audit event 是 release smoke 常用证据面。
- 继续复查发现 response `id`、audit metadata `task_id`、retry `source_task_id/new_task_id` 仍信任历史/手工 DB task id。
- 如果历史/手工 DB row 含有非 UUID task id，这些 API/audit 边界会把 URL/header/token 风格 id 文本带入低敏 release evidence。

已覆盖：

- AutomationTaskResponse `id` 现在只保留 canonical UUID；非 UUID 历史/手工 id 折叠为 `unknown`。
- automation.task audit metadata `task_id`、`source_task_id` 和 `new_task_id` 现在只保留 canonical UUID；非 UUID id 会省略。
- 内部 get/list/cancel/retry/run 仍使用原始 task id 做 DB lookup，不改变既有路由语义。
- 正常 UUID task create/list/detail/cancel/retry/run、profile id redaction、step/result redaction 和 worker lease metadata 边界保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_sanitize_persisted_task_id -q
# RED: 1 failed；task detail response id 直接保留非 UUID task id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_sanitize_persisted_task_id -q
# 1 passed in 0.89s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_task"
# 40 passed, 198 deselected in 5.26s

. .venv/bin/activate && python -m pytest backend/tests -q
# 612 passed in 38.90s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.84s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 automation task id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation payloads 或 raw browser artifacts。

## 2026-06-03 Profile template id guardrail

背景：

- Profile template list/detail/update response 和 CSV import preview 是模板/批量创建 release smoke 的常用证据面。
- 继续复查发现 template identity field 已经清洗，但模板 `id` 本身以及 CSV preview `profile.template_id` 仍信任历史/手工 DB id。
- 如果历史/手工 DB row 含有非 UUID template id，这些 API/preview 边界会把 URL/header/token 风格 id 文本带入低敏 release evidence。

已覆盖：

- ProfileTemplateResponse `id` 现在只保留 canonical UUID；非 UUID 历史/手工 id 折叠为 `unknown`。
- CSV import preview `profile.template_id` 现在只保留 canonical UUID；非 UUID 历史/手工 id 折叠为 `unknown`。
- 内部 template lookup、template field application、profile create/import data 仍使用原始 template id，不改变既有模板匹配和创建语义。
- 正常 UUID template CRUD、template field copy、CSV preview/import、template identity field redaction 和 bulk tests 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py::test_profile_template_api_and_import_preview_sanitize_persisted_template_id -q
# RED: 1 failed；template detail response id 直接保留非 UUID template id

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py::test_profile_template_api_and_import_preview_sanitize_persisted_template_id -q
# 1 passed in 0.65s

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py backend/tests/test_bulk.py -q
# 32 passed in 2.63s

. .venv/bin/activate && python -m pytest backend/tests -q
# 613 passed in 39.91s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.98s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 profile template id guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation payloads 或 raw browser artifacts。

## 2026-06-03 Audit event reader guardrail

背景：

- Release smoke 和 regression tests 会直接读取 audit event 列表作为低敏 evidence。
- `create_audit_event()` 已经清洗 metadata，但历史/手工 DB row 通过 `get_audit_event()` / `list_audit_events()` 读出时仍可能回显污染的顶层字段和原始 metadata。
- 如果 audit row 含有 URL/header/token 风格 `id`、`runtime_session_id`、`profile_id`、`external_session_id`、`event_type`、`actor_type` 或 `created_at`，这些字段会进入 release evidence。

已覆盖：

- Audit reader 现在对 event `id` 使用 UUID-only 输出；非 UUID 折叠为 `unknown`。
- `runtime_session_id` 和 `profile_id` 现在只保留 canonical UUID；非 UUID 输出为 `null`。
- `external_session_id` 只保留普通低敏 external id；URL/query/header/token 风格值输出为 `null`。
- `event_type` 只保留 dotted lowercase audit labels；`actor_type` 只保留 `local_admin`、`runtime_service`、`runtime_viewer`；非公开值折叠为 `unknown`。
- `created_at` 只保留可解析 ISO timestamp；污染值折叠为 `unknown`。
- 历史 metadata 读出时会再次经过既有 audit metadata sanitizer，去掉 token/hash/cookie/password/secret 类 key 并 redacts token/Bearer/proxy credential text。
- 正常 runtime session/viewer audit、profile/proxy/cookie/bundle audit、automation task audit 和 diagnostics 读数保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_audit_event_reader_sanitizes_historical_top_level_fields_and_metadata -q
# RED: 1 failed；audit event id 直接保留非 UUID token/header-like text

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_audit_event_reader_sanitizes_historical_top_level_fields_and_metadata -q
# 1 passed in 0.77s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 42 passed in 5.90s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "audit or automation_task"
# 53 passed, 185 deselected in 7.89s

. .venv/bin/activate && python -m pytest backend/tests -q
# 614 passed in 39.49s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.85s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 audit event reader guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation payloads 或 raw browser artifacts。

## 2026-06-03 Automation task timestamp guardrail

背景：

- Automation task list/detail/cancel/retry/run response 是 release smoke 和 worker observability 的常用证据面。
- 之前已经清洗 task id、profile id、status、error、steps 和 result，但历史/手工 DB row 的 `created_at`、`started_at`、`finished_at` 仍直接进入 response。
- 如果 automation task timestamp 字段被污染为 URL/header/token 风格文本，会进入低敏 release evidence。

已覆盖：

- AutomationTaskResponse `created_at` 现在只保留可解析 ISO timestamp；非公开/污染值折叠为 `unknown`。
- `started_at` 和 `finished_at` 现在只保留可解析 ISO timestamp；非公开/污染值折叠为 `null`。
- DB 内部 task ordering、lease handling、worker/run/cancel/retry 状态更新不变，只在 response 输出侧过滤。
- 正常 automation task create/list/detail/cancel/retry/run、worker terminal audit、task id/profile/status/error/step/result redaction 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_response_sanitizes_persisted_timestamp_fields -q
# RED: 1 failed；created_at 直接保留 token-like timestamp text

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_response_sanitizes_persisted_timestamp_fields -q
# 1 passed in 0.87s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_task"
# 41 passed, 198 deselected in 5.05s

. .venv/bin/activate && python -m pytest backend/tests -q
# 615 passed in 40.58s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.86s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 automation task timestamp guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation payloads 或 raw browser artifacts。

## 2026-06-03 Runtime session timestamp guardrail

背景：

- Runtime session detail/create/renew/terminate response 是 Project Mileage session broker、VNC viewer token flow 和 release smoke 的常用低敏证据面。
- 之前已经清洗 runtime session id、profile id、external_session_id 和 status，但历史/手工 DB row 的 `lease_expires_at`、`created_at`、`updated_at` 仍直接进入 response。
- 如果 runtime session timestamp 字段被污染为 URL/header/token 风格文本，会进入低敏 release evidence。

已覆盖：

- RuntimeSessionResponse `lease_expires_at`、`created_at`、`updated_at` 现在只保留可解析 ISO timestamp。
- 非公开/污染 timestamp 文本折叠为 `unknown`，不会回显 token、Authorization/Bearer 或 URL host/path context。
- DB 内部 lease/live 判断、runtime session create/get/renew/terminate、viewer token、runtime service token 和 audit 语义不变，只在 response 输出侧过滤。
- 正常 runtime session broker 相邻路径和既有 runtime id/profile id/external id/status guardrails 保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_timestamp_fields -q
# RED: 1 failed；lease_expires_at 直接保留 token-like timestamp text

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_timestamp_fields -q
# 1 passed in 0.78s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 43 passed in 4.49s

. .venv/bin/activate && python -m pytest backend/tests -q
# 616 passed in 38.24s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.43s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 runtime session timestamp guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation payloads 或 raw browser artifacts。

## 2026-06-03 Management response timestamp guardrail

背景：

- Profile、Proxy、Profile Template 和 Proxy Provider Preset list/detail responses 是运营台、Proxy Manager、template import preview 和 release smoke 的常用低敏证据面。
- 这些响应已清洗 id、provider/country、GeoIP、tags 和若干 identity 字段，但历史/手工 DB row 的 `created_at`、`updated_at`、`last_check_at`、`last_geoip_resolved_at` 仍可能直接进入 response。
- 如果这些 timestamp 字段被污染为 URL/header/token 风格文本，会进入低敏 release evidence。

已覆盖：

- ProfileResponse `created_at`、`updated_at` 现在只保留可解析 ISO timestamp；污染值折叠为 `unknown`。
- ProfileResponse `last_geoip_resolved_at`、ProxyResponse `last_check_at` 现在只保留可解析 ISO timestamp；污染值折叠为 `null`。
- ProxyResponse、ProfileTemplateResponse、ProxyProviderPresetResponse `created_at`、`updated_at` 现在只保留可解析 ISO timestamp；污染值折叠为 `unknown`。
- DB 内部 ordering、update timestamps、GeoIP/proxy check persistence、template/preset CRUD 和 random assignment selection 不变，只在 response 输出侧过滤。
- 正常 profile/proxy/template/preset CRUD、existing response id/identity/GeoIP/provider/tag redaction 和相关管理 API 行为保持通过。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_timestamp_fields backend/tests/test_proxies.py::test_proxy_api_responses_sanitize_persisted_timestamp_fields backend/tests/test_proxies.py::test_proxy_provider_preset_responses_sanitize_persisted_timestamp_fields backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_timestamp_fields -q
# RED: 4 failed；created_at 直接保留 token/header-like timestamp text

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_timestamp_fields backend/tests/test_proxies.py::test_proxy_api_responses_sanitize_persisted_timestamp_fields backend/tests/test_proxies.py::test_proxy_provider_preset_responses_sanitize_persisted_timestamp_fields backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_timestamp_fields -q
# 4 passed in 1.18s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py backend/tests/test_proxies.py backend/tests/test_templates.py -q
# 294 passed in 25.61s

. .venv/bin/activate && python -m pytest backend/tests -q
# 620 passed in 39.13s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.96s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 management response timestamp guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation payloads 或 raw browser artifacts。

## 2026-06-03 Launch failure stage diagnostics guardrail

背景：

- `/api/diagnostics` 会展示 BrowserManager in-memory launch failure summary，帮助 release smoke triage profile/VNC/runtime launch failures。
- `_record_launch_failure()` 已经把运行时 stage 规范到固定白名单，但 `launch_failure_summary()` 仍直接信任当前 `_launch_failure_stage_counts` dict。
- 如果未来代码路径、测试注入或异常状态把 URL/header/token 风格 stage key 或非整数 count 写入该 dict，diagnostics 可能暴露 raw key 或抛出 TypeError。

已覆盖：

- `launch_failure_summary()` 现在只累计正整数计数；bool、非整数、0 和负数都会忽略。
- stage key 只保留 `LAUNCH_FAILURE_STAGES` 白名单；非白名单 stage 统一归并到 `unknown`。
- summary 输出继续按 stage 排序，`launch_failure_count` 来自过滤后的 public counts。
- 正常 launch failure 记录、VNC allocation failure、startup cleanup failure 和 diagnostics 渲染语义保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_failure_summary_sanitizes_existing_stage_counts -q
# RED: 1 failed；polluted count caused TypeError and raw stage key was not normalized

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_failure_summary_sanitizes_existing_stage_counts -q
# 1 passed in 0.15s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 69 passed in 0.90s

. .venv/bin/activate && python -m pytest backend/tests -q
# 621 passed in 38.84s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.30s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager, runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 launch failure stage diagnostics guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation payloads 或 raw browser artifacts。

## 2026-06-03 BrowserManager lifecycle profile-id log guardrail

背景：

- BrowserManager lifecycle logs 是 release smoke 和 runtime/VNC triage 的主要低敏证据面。
- API 层已经对 profile id response/audit 做 UUID-only 或 public-value 过滤，但 BrowserManager 内部 lifecycle logs 仍直接记录传入的 `profile_id`。
- 如果历史/手工 profile id 被污染为 URL/header/token 风格文本，launch failure、stop、browser_closed、auto_launch 等日志会保留 raw id。

已覆盖：

- BrowserManager 新增 public profile log id 过滤；普通低敏 id 如 `profile-log`、`auto-ok` 继续保留。
- URL/query/header/token/password/secret/cookie 风格 id 在 lifecycle logs 中统一折叠为 `unknown`。
- 已接入 launch success/failure、existing page init debug、bootstrap debug、launch teardown debug、browser_closed、stop requested/finished、stop close failures、auto_launch success/failure。
- 内部 running map、profile lookup、automation_url construction 和 API response 语义不变；只过滤日志输出参数。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_lifecycle_logs_sanitize_sensitive_profile_ids -q
# RED: 1 failed；BrowserManager lifecycle logs included raw URL/header/token-like profile_id

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_lifecycle_logs_sanitize_sensitive_profile_ids -q
# 1 passed in 0.04s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 70 passed in 0.89s

. .venv/bin/activate && python -m pytest backend/tests -q
# 622 passed in 39.92s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.20s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、profile launch manager、runtime session storage、viewer token generation、VNC proxying 或 external smoke scripts。
- 不在 BrowserManager lifecycle profile-id log guardrail 中读取或公开 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation payloads 或 raw browser artifacts。

## 2026-06-03 VNC/clipboard profile-id log guardrail

背景：

- VNC proxy 和 clipboard relay 是 release smoke、runtime viewer、远程工作台排障时最常看的日志入口。
- BrowserManager lifecycle 日志已经过滤 profile id，但 `backend/main.py` 的 VNC/clipboard route 日志仍直接使用 path profile id。
- 如果历史/手工 DB 或调用路径里出现 URL/query/header/token 风格 profile id，排障日志会保留该文本。

已覆盖：

- clipboard page/context read failure 日志现在只记录公开 profile id；非 UUID profile id 折叠为 `unknown`。
- VNC proxy connect、client/backend stream failure、Xvnc log available、websocket close failure，以及 connected/finished lifecycle 日志现在使用同一公开 profile id。
- 内部 running profile lookup、WebSocket path、clipboard 行为和 runtime viewer audit 回调不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_get_clipboard_page_failure_logs_public_profile_id backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_public_profile_id -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.80s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "vnc or clipboard"
# 16 passed, 226 deselected in 1.68s

. .venv/bin/activate && python -m pytest backend/tests -q
# 624 passed in 39.45s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.23s
```

边界：

- 这是 VNC/clipboard 运行日志和 release evidence 脱敏硬化，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation payloads 或 raw audit metadata。

## 2026-06-03 Automation page/action profile-id log guardrail

背景：

- Direct Automation API 是 release smoke 和脚本侧排障的主要证据面。
- Automation response/audit 已经做过 profile id 脱敏，但 page title failure 和 page action failure 日志仍直接记录 `running.profile_id` 或 path `profile_id`。
- 如果历史/手工 running map 或调用路径里出现 URL/query/header/token 风格 profile id，automation failure logs 会保留该文本。

已覆盖：

- automation pages 读取 title 失败时，`action=automation.page_title_failed` 日志只记录公开 profile id；非 UUID 折叠为 `unknown`。
- automation page action failure helper 现在统一过滤 profile id，覆盖 `new_page`、`goto`、`evaluate`、`wait_for_selector`、`click`、`fill`、`keyboard_type`、`scroll`、`screenshot` 和 `close_page` failure logs。
- API response、running profile lookup、page lookup、page action 执行和错误响应语义不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_page_title_failure_logs_public_profile_id backend/tests/test_api.py::test_automation_action_failure_logs_public_profile_id -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.78s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation and not task"
# 46 passed, 198 deselected in 4.03s

. .venv/bin/activate && python -m pytest backend/tests -q
# 626 passed in 37.92s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.18s
```

边界：

- 这是 Automation API failure log 和 release evidence 脱敏硬化，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation expressions/results/payloads 或 raw audit metadata。

## 2026-06-03 Cookie/profile bundle profile-id log guardrail

背景：

- Cookie import/export 和 profile bundle export 是 release smoke 中验证数据边界、备份/迁移边界和敏感材料不外泄的重要路径。
- 这些 response/audit 已经做过 profile id 脱敏，但 cookie import failure、cookie document validation failure、profile bundle request validation failure、local storage export failure 的 warning logs 仍直接记录 path `profile_id`。
- 如果历史/手工 running map 或调用路径里出现 URL/query/header/token 风格 profile id，cookie/bundle failure logs 会保留该文本。

已覆盖：

- Cookie JSON import validation failure 和 add_cookies failure logs 现在使用公开 profile id；非 UUID 折叠为 `unknown`。
- Netscape cookie import validation failure 和 add_cookies failure logs 使用同一公开 profile id。
- Profile bundle export request validation failure 和 local storage export failure logs 使用公开 profile id。
- Cookie/bundle response、audit、running profile lookup、cookie 写入、bundle 构造和 local storage 读取语义不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_cookie_json_failure_logs_public_profile_id backend/tests/test_api.py::test_export_profile_bundle_validation_logs_public_profile_id -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.79s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "cookie or bundle"
# 45 passed, 201 deselected in 3.88s

. .venv/bin/activate && python -m pytest backend/tests -q
# 628 passed in 38.03s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.29s
```

边界：

- 这是 cookie/profile bundle failure log 和 release evidence 脱敏硬化，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、automation expressions/results/payloads 或 raw audit metadata。

## 2026-06-03 VNC/RFB raw frame log guardrail

背景：

- VNC proxy 会解析 noVNC client -> KasmVNC 的 RFB frame，并在 release smoke 或 VNC 排障时输出 debug/info 日志。
- 旧日志在 handshake、filtered send、安全拒绝和 unknown message drop 路径中记录 raw frame hex。
- RFB ClientCutText 或异常 client frame 可能包含 clipboard/token-like 文本；即使以 hex 形式记录，也仍会把敏感 payload 留在 release evidence/logs 中。

已覆盖：

- `_filter_rfb_client_messages()` 对 unknown message 只记录 type、offset、总长度和 skipped byte count，不再记录 frame hex。
- VNC handshake debug 只记录序号和 byte length。
- RFB safety refusal 只记录 first byte 和 filtered length。
- VNC send debug 只记录 byte length 和 first_type。
- RFB filtering、extension skip、SetEncodings rewrite、PointerEvent rewrite 和 VNC forwarding 语义不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_rfb_filter_unknown_message_does_not_log_raw_frame_hex -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.77s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "vnc or clipboard or rfb"
# 17 passed, 230 deselected in 1.75s

. .venv/bin/activate && python -m pytest backend/tests -q
# 629 passed in 40.11s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.33s
```

边界：

- 这是 VNC/RFB runtime log 和 release evidence 脱敏硬化，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw VNC/RFB frames、automation payloads 或 raw audit metadata。

## 2026-06-03 Firefox identity major-version diagnostics guardrail

背景：

- Pixelscan no-proxy diagnostic 已经显示底层 managed UA major 与 bundled Firefox binary major 存在版本差异风险。
- 旧的 System diagnostics 分开展示 Managed UA、Firefox binary 和 Firefox BuildID，但没有直接给出 major 是否一致的低敏判断。
- Release triage 需要一个无需进入容器、无需记录 full UA/path/profile data 的快速信号。

已覆盖：

- `GET /api/diagnostics` 的 runtime payload 新增 `firefox_identity_major_version_match`。
- 该字段只比较 managed UA version 与 Firefox binary version 的 major number：
  - 一致返回 `true`。
  - 不一致返回 `false`。
  - 任一侧不是公开数字版本时返回 `null`。
- 前端 System diagnostics 新增 `Firefox major match` 行，显示 `match`、`mismatch` 或 `unknown`。
- 现有 Managed UA、Firefox binary、Firefox BuildID、stealth prefs 等低敏诊断语义不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 2 passed in 0.86s

npm --prefix frontend test -- --run src/components/SystemDiagnosticsPage.test.tsx src/lib/api.test.ts
# Test Files 2 passed；Tests 42 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 629 passed in 39.55s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.59s

git diff --check
# passed
```

边界：

- 这是 Firefox identity observability guardrail，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录 full UA、package path、Firefox binary path、screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 Fingerprint seed launch guardrail

背景：

- `fingerprint_seed` 决定底层 `invisible_playwright` profile generation，是 Pixelscan/seed stability 排障的关键输入。
- 正常 API 输入会被 Pydantic 解析为整数，但历史/手工 DB row 或内部 runtime profile dict 仍可能绕过请求校验。
- 旧 `_build_invisible_kwargs()` 直接把 `profile["fingerprint_seed"]` 传给 `InvisiblePlaywright(seed=...)`，非整数 URL/token/path 风格文本可能进入底层 runtime。

已覆盖：

- 新增 `_public_fingerprint_seed()`，在构造 invisible kwargs 前复用 public int 过滤。
- 正常整数 seed 保持不变。
- URL/query token 风格 seed、bool seed 等非公开值在 launch kwargs 中折叠为 `None`。
- locale、timezone、screen/GPU/hardware、proxy 和 launch args 既有 guardrails 保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_fingerprint_seed_values -q
# RED: kwargs["seed"] 原样返回 URL/token 风格文本；GREEN: 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_maps_manager_profile backend/tests/test_browser_manager.py::test_build_invisible_kwargs_omits_empty_optional_values backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_fingerprint_seed_values backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_timezone_text backend/tests/test_browser_manager.py::test_build_invisible_kwargs_pins_managed_firefox_identity -q
# 6 passed in 0.05s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 71 passed in 0.88s

. .venv/bin/activate && python -m pytest backend/tests -q
# 630 passed in 40.55s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.70s

git diff --check
# passed
```

边界：

- 这是 fingerprint launch input 和 release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 GeoIP WebRTC env IP guardrail

背景：

- Browser launch 会把 GeoIP 解析出的 exit IP 临时写入 `STEALTHFOX_WEBRTC_PUBLIC_IP`，让底层 Firefox WebRTC 行为与出口 IP 对齐。
- GeoIP 模块已经对 provider response 和 persisted result 做 `public_geoip_ip()` 过滤，但 BrowserManager launch path 仍直接信任 `_geoip_result["ip"]`。
- 如果历史/损坏 profile dict 或异常 resolver 返回 URL/query token 风格 IP 文本，旧实现会把该文本放入进程环境并让 `InvisiblePlaywright.__aenter__()` 继承。

已覆盖：

- `_geoip_exit_ip()` 现在复用 `public_geoip_ip()`。
- 正常 IP 仍会在 launch 期间临时写入 `STEALTHFOX_WEBRTC_PUBLIC_IP`，并在 launch 后恢复原环境。
- URL/query token 风格 IP 不再写入 launch env。
- GeoIP timezone/locale、Accept-Language、managed Firefox identity 和 WebRTC local IP suppression prefs 既有行为保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_drops_non_public_geoip_exit_ip_for_webrtc_env -q
# RED: 污染 URL/token IP 进入 STEALTHFOX_WEBRTC_PUBLIC_IP；GREEN: 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_passes_geoip_exit_ip_to_invisible_webrtc_env backend/tests/test_browser_manager.py::test_launch_drops_non_public_geoip_exit_ip_for_webrtc_env backend/tests/test_browser_manager.py::test_launch_resolves_missing_timezone_and_locale_before_invisible_launch -q
# 3 passed in 0.06s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 72 passed in 0.92s

. .venv/bin/activate && python -m pytest backend/tests -q
# 631 passed in 40.83s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.71s

git diff --check
# passed
```

边界：

- 这是 GeoIP/WebRTC launch env 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 VNC start failure exception redaction guardrail

背景：

- KasmVNC/Xvnc 启动失败时，`VNCManager.start_vnc()` 会读取 `/tmp/xvnc-<display>.log` 辅助排障。
- 旧实现把整个 Xvnc log 内容拼进 `RuntimeError`。
- 即使上层 API/log 多数只记录 `error_type`，异常对象本身仍可能携带 viewer token、URL、websockify path 或其它原始 VNC/Xvnc 文本，进入测试输出、调试终端或 release evidence。

已覆盖：

- Xvnc 退出时仍尝试读取 log，以保留 log-read failure 的低敏 `error_type` 调试行为。
- 抛出的 `RuntimeError` 只保留固定 `Xvnc failed to start on :<display>`。
- raw Xvnc log 内容不再进入异常 message。
- VNC start request 低敏日志、allocation、cleanup_stale 和 active display 行为不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py::test_start_vnc_failure_exception_omits_raw_xvnc_log -q
# RED: RuntimeError 包含 viewer_token/xvnc log；GREEN: 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py -q
# 16 passed in 0.05s

. .venv/bin/activate && python -m pytest backend/tests -q
# 632 passed in 39.66s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.79s

git diff --check
# passed
```

边界：

- 这是 VNC startup failure exception 和 release evidence 脱敏硬化，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw VNC/Xvnc logs、raw audit metadata 或外站页面原文。

## 2026-06-03 Profile directory launch guardrail

背景：

- 正常 profile `user_data_dir` 由数据库生成在 `/data/profiles/<uuid>`。
- BrowserManager launch 旧实现直接信任 profile dict 中的 `user_data_dir`，在 VNC allocation 后用于 Firefox startup-state cleanup，并传给 `InvisiblePlaywright(profile_dir=...)`。
- 如果历史/手工 DB row 或内部 runtime profile dict 被污染为 URL/query token/header 风格路径，启动流程可能触碰该 raw path 或把它传入底层 runtime。

已覆盖：

- 新增 profile directory public boundary，拒绝空值、非字符串/path-like、URL/query token/header 风格文本和控制字符。
- `BrowserManager.launch()` 现在在 VNC allocation 前验证 profile dir。
- `_build_invisible_kwargs()` 复用同一边界后再构造 `profile_dir`。
- 正常本地 profile path、startup-state cleanup、VNC allocation、launch kwargs 和 GeoIP/locale/timezone 流程保持不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_rejects_non_public_user_data_dir_before_vnc_allocation -q
# RED: 污染 user_data_dir 进入 VNC allocation；GREEN: 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_maps_manager_profile backend/tests/test_browser_manager.py::test_build_invisible_kwargs_omits_empty_optional_values backend/tests/test_browser_manager.py::test_launch_rejects_non_public_user_data_dir_before_vnc_allocation backend/tests/test_browser_manager.py::test_launch_clears_launching_state_when_vnc_allocation_fails backend/tests/test_browser_manager.py::test_launch_resolves_missing_timezone_and_locale_before_invisible_launch -q
# 5 passed in 0.06s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 73 passed in 0.95s

. .venv/bin/activate && python -m pytest backend/tests -q
# 633 passed in 42.95s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 6.59s

git diff --check
# passed
```

边界：

- 这是 profile lifecycle launch input 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 Launch args runtime input guardrail

背景：

- Profile `launch_args` 是用户/历史 DB 可控的 Firefox 启动输入，最终会进入 `InvisiblePlaywright(extra_args=...)`。
- 既有 `_filter_firefox_launch_args()` 已屏蔽 remote-debugging、user-agent、profile、window-size 等冲突 flag，但仍保留其它非冲突字符串。
- 如果历史/手工 row 或内部 runtime profile dict 把 URL/query token/header 风格文本放进 launch args，这些文本可能进入底层 runtime 启动参数或失败证据。

已覆盖：

- 新增 launch arg public boundary，只保留字符串、非空、无控制字符、无 URL/query/token/password/secret/cookie/Authorization/Bearer 风格文本的参数。
- `_filter_firefox_launch_args()` 现在先做 public boundary，再复用既有冲突 flag 过滤。
- 非 list `launch_args` 退化为空；list 内非字符串项会被丢弃。
- 正常 `--private-window`、`--lang=en-US` 等普通低敏 Firefox 参数继续保留。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_launch_args -q
# RED: 敏感 launch args 仍进入 extra_args；GREEN: 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_launch_args backend/tests/test_browser_manager.py::test_build_invisible_kwargs_filters_chromium_only_launch_args -q
# 2 passed in 0.19s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 74 passed in 0.96s

. .venv/bin/activate && python -m pytest backend/tests -q
# 634 passed in 38.92s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.43s

git diff --check
# passed
```

边界：

- 这是 profile lifecycle launch input 和 release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 Fingerprint seed response/export guardrail

背景：

- `fingerprint_seed` 是 profile list/detail、profile config export 和 profile bundle config manifest 的必填整数。
- runtime launch 已在 `_build_invisible_kwargs()` 中过滤非公开 seed，但 response/export sanitizer 仍直接信任历史/手工 DB row。
- 如果 `fingerprint_seed` 被污染为 URL/query token/header 风格文本，profile response 或 export 会触发 Pydantic validation failure，并可能把污染文本带入测试/调试输出。

已覆盖：

- `sanitize_profile_response_data()` 现在复用 fingerprint seed public boundary，非公开 seed 折叠为固定低敏 `0`。
- `sanitize_profile_config_export_data()` 使用同一边界，覆盖 `/api/profiles/export` 和 profile bundle config manifest。
- 正常整数 seed 继续保留；runtime launch seed filtering 语义不变。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_identity_fields backend/tests/test_bulk.py::test_bulk_export_profile_configs_sanitizes_persisted_identity_fields backend/tests/test_profile_bundle.py::test_build_profile_config_bundle_sanitizes_non_public_fingerprint_seed -q
# RED: 3 failed due ProfileResponse/ProfileConfigExport fingerprint_seed validation；GREEN: 3 passed in 0.95s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_identity_fields backend/tests/test_api.py::test_profile_response_sanitizes_persisted_profile_id_and_automation_url backend/tests/test_bulk.py::test_bulk_export_profile_configs_sanitizes_persisted_identity_fields backend/tests/test_profile_bundle.py -q
# 8 passed in 0.95s

. .venv/bin/activate && python -m pytest backend/tests -q
# 635 passed in 39.14s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.58s

git diff --check
# passed
```

边界：

- 这是 profile response/config export/bundle manifest 稳定性和 release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变底层 `invisible_playwright` seed generation、same-seed stability、different-seed variation、stealth prefs、WebGL、WebRTC、UA、locale/timezone、proxy 或 profile launch 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 Profile delete directory guardrail

背景：

- BrowserManager launch 已经在 VNC 分配和 invisible_playwright kwargs 前校验 `user_data_dir`。
- Profile delete 路径仍直接把 DB 中的 `user_data_dir` 转成 `Path`，再删除 DB 和清理磁盘。
- 如果历史/手工 DB row 被污染为 URL/query token/header 风格目录文本，delete 可能在可信边界外尝试 stop/cleanup，并把 profile lifecycle evidence 带入不可预测状态。

已覆盖：

- `DELETE /api/profiles/{id}` 现在复用 `_public_profile_dir()` 校验持久化 `user_data_dir`。
- 非公开 profile dir 返回固定低敏 `400 Invalid profile directory`。
- 校验失败时不会 stop running profile、不会删除 DB row、不会调用 `shutil.rmtree()`、不会写 `profile.deleted` audit。
- 正常删除、缺少显式确认、not found、running profile stop 和 profile CRUD audit 行为保持通过。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_delete_profile_rejects_non_public_user_data_dir_without_side_effects -q
# RED: 旧实现返回 200；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k "delete_profile or profile_crud" -q
# 8 passed, 240 deselected

.venv/bin/python -m pytest backend/tests -q
# 636 passed in 38.89s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.74s

git diff --check
# passed
```

边界：

- 这是 profile lifecycle delete path 和 release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone、proxy 或 profile launch 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 Profile response directory guardrail

背景：

- Profile list/detail/create/update 响应仍保留既有 `user_data_dir` API 字段。
- 正常 profile 目录可继续作为本地管理台语义返回，但历史/手工 DB row 可能把 URL/query token/header 风格文本写进 `user_data_dir`。
- Release evidence 禁止记录 profile dir 和 token/header 文本，因此响应层需要和 launch/delete 路径使用同一条 public profile-dir 边界。

已覆盖：

- `_profile_response()` 现在用 `_public_profile_dir()` 过滤 persisted `user_data_dir`。
- 普通本地 profile dir 仍返回原字符串，保持既有 API 语义。
- 非公开 URL/query token/header 风格 `user_data_dir` 折叠为固定低敏 `unknown`。
- Profile get/list 响应不再回显污染 host、`token=`、Authorization/Bearer 或 secret marker。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_profile_response_sanitizes_persisted_user_data_dir -q
# RED: 旧实现原样回显污染 user_data_dir；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k "profile_response or profile_responses or profile_crud or delete_profile or create_profile or get_profile" -q
# 25 passed, 224 deselected

.venv/bin/python -m pytest backend/tests -q
# 637 passed in 39.23s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.61s

git diff --check
# passed
```

边界：

- 这是 profile response release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变 DB 存储、profile launch/delete 内部路径、底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 Runtime viewer close-code audit guardrail

背景：

- Runtime VNC viewer connected/disconnected audit 是 Project Mileage remote workspace 和 release VNC smoke 的交接证据面。
- `runtime.viewer.disconnected` metadata 中的 `close_code` 语义上只应是 WebSocket close code 数字或 null。
- 如果测试 double、框架边界或未来调用方把 URL/query token/header 风格文本放进 close_code，通用 audit sanitizer 会留下 `token=[redacted]`、`Authorization=[redacted]` 这类非低敏语义。

已覆盖：

- Runtime viewer audit metadata 现在对 `close_code` 做 public boundary。
- 非 bool 整数 `0..65535` 保留；其他值折叠为 null。
- 既有成功 VNC audit 仍记录 `close_code=1000`。
- 污染 close_code 不再把 secret、`token=`、Authorization 或 Bearer 文本写入 audit evidence。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_viewer_disconnect_audit_sanitizes_non_integer_close_code -q
# RED: 旧实现保存 token/header 风格 close_code；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 44 passed in 4.65s

.venv/bin/python -m pytest backend/tests -q
# 638 passed in 39.53s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.19s

git diff --check
# passed
```

边界：

- 这是 runtime viewer audit/release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变 viewer token 签发、VNC proxy、WebSocket close 行为、runtime session 状态、底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 Runtime viewer metadata allowlist audit guardrail

背景：

- Runtime viewer audit helper 是 VNC smoke 和 Project Mileage remote workspace 的低敏证据边界。
- 正常 `runtime.viewer.connected` 只需要记录 negotiated subprotocol；正常 `runtime.viewer.disconnected` 只需要记录 close code。
- helper 之前会复制未知 metadata key；如果未来调用方传入 origin、viewer URL、header/token 风格文本，通用 sanitizer 仍可能留下 host 或 `token=[redacted]` 这类非低敏证据。

已覆盖：

- `_runtime_viewer_audit_metadata()` 现在按 event type 输出固定白名单。
- `runtime.viewer.connected` 只保留 public subprotocol：`binary` 或 null。
- `runtime.viewer.disconnected` 只保留 public WebSocket close code：非 bool 整数 `0..65535` 或 null。
- 其他 viewer event metadata 折叠为空对象，防止未知调试字段进入 release evidence。
- 污染 subprotocol、origin 和 viewer URL 不再写入 audit evidence；正常 VNC success audit 仍记录 `subprotocol=binary` 和 `close_code=1000`。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_viewer_connected_audit_allows_only_public_subprotocol_metadata -q
# RED: 旧实现保存污染 subprotocol 和 origin；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_viewer_connected_audit_allows_only_public_subprotocol_metadata backend/tests/test_session_broker.py::test_runtime_viewer_disconnect_audit_sanitizes_non_integer_close_code backend/tests/test_session_broker.py::test_runtime_vnc_success_writes_redacted_connect_and_disconnect_audit -q
# 3 passed in 0.95s

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 45 passed in 4.84s

.venv/bin/python -m pytest backend/tests -q
# 639 passed in 38.09s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.96s

git diff --check
# passed
```

边界：

- 这是 runtime viewer audit/release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变 viewer token 签发、WebSocket accept/subprotocol negotiation、VNC proxy、runtime session 状态、底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 Runtime service metadata allowlist audit guardrail

背景：

- Runtime service audit 是 Project Mileage server-to-server session broker 的 release evidence 面。
- 正常 runtime service events 只需要固定 metadata：session create 的 profile source/lease、viewer token create 的 TTL/expiry、renew 的 lease/expiry，read/terminate 不需要 metadata。
- helper 之前直接依赖通用 audit sanitizer；如果未来调用方传入 wallet/order/billing、viewer URL、header/token 风格字段，仍可能留下 redacted 但非低敏的 evidence。

已覆盖：

- `_audit_runtime_event()` 现在通过 `_runtime_service_audit_metadata()` 按 event type 输出固定白名单。
- `runtime.session.created` 只保留 public profile source 和 `1..86400` lease seconds。
- `runtime.viewer_token.created` 只保留 `1..300` TTL seconds 和 parseable expiry timestamp。
- `runtime.session.renewed` 只保留 `1..86400` lease seconds 和 parseable lease expiry timestamp。
- `runtime.session.read`、`runtime.session.terminated` 和未知 runtime service events metadata 折叠为空对象。
- 污染 profile source、seconds、timestamps、wallet/order/billing 和 viewer URL 不再写入 runtime service audit evidence；正常 runtime service audit flow 保持原 shape。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_service_audit_allows_only_public_metadata_shapes -q
# RED: 旧实现保存污染 metadata；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_service_audit_allows_only_public_metadata_shapes backend/tests/test_session_broker.py::test_runtime_service_actions_write_redacted_audit_events -q
# 2 passed in 1.04s

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 46 passed in 4.72s

.venv/bin/python -m pytest backend/tests -q
# 640 passed in 37.47s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.27s

git diff --check
# passed
```

边界：

- 这是 runtime service audit/release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变 runtime service token 校验、viewer token 签发、lease/renew/terminate 业务行为、VNC/WebSocket 行为、底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata、wallet/order/billing 数据或外站页面原文。

## 2026-06-03 Automation task runner/reason audit guardrail

背景：

- Automation task terminal audit 是 API runner、background worker 和 release automation smoke 的证据面。
- `runner_type` 语义上只应是 `api` 或 `worker`；`reason_code` 只应是固定失败分类。
- 旧 helper 已经清理 task id、profile id、step type、result summary 等字段，但 `runner_type` 和 `reason_code` 仍直接信任调用方；如果未来边界传入 token/header 风格文本，通用 sanitizer 会留下 redacted 但非低敏的 metadata。

已覆盖：

- `_automation_task_audit_metadata()` 现在对 `runner_type` 和 `reason_code` 做 public enum boundary。
- runner type 只保留 `api`/`worker`；其他值折叠为 `unknown`。
- reason code 只保留 `automation_step_failed`、`invalid_step`、`unsupported_step_type`；其他值折叠为 `unknown`。
- 正常 API runner、worker runner 和 unsupported step failure audit 保持原 shape。
- 污染 runner/reason 不再把 secret、`token=`、Authorization 或 Bearer 文本写入 automation task audit evidence。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_audit_sanitizes_runner_type_and_reason_code -q
# RED: 旧实现保存污染 runner_type/reason_code；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_audit_sanitizes_runner_type_and_reason_code backend/tests/test_api.py::test_automation_task_create_cancel_retry_and_run_write_redacted_audit_events backend/tests/test_api.py::test_automation_worker_run_once_writes_redacted_terminal_audit_event -q
# 3 passed in 1.18s

.venv/bin/python -m pytest backend/tests/test_api.py -k "automation_task or automation_worker" -q
# 55 passed, 195 deselected in 6.61s

.venv/bin/python -m pytest backend/tests -q
# 641 passed in 38.07s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.07s

git diff --check
# passed
```

边界：

- 这是 automation task audit/release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变 automation task execution、worker lease、runner selection、task retry/cancel/run、VNC/WebSocket 行为、底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata、automation payload 或外站页面原文。

## 2026-06-03 Automation task persisted-step shape guardrail

背景：

- Automation task DB reader 会保证 `steps` 顶层是 list，但历史/手工 row 仍可能包含非 dict list item。
- Response redaction 旧实现直接对每个 item 调用 `.get()`；如果 persisted step item 是 URL/query token/header 风格字符串，task get/list/cancel 等 release smoke 路径会 500。
- Audit `step_count` 也不应把非 step item 计入低敏证据。

已覆盖：

- 新增 `_automation_task_public_steps()`，只允许 dict step item 进入 response/audit step processing。
- `_automation_task_redacted_steps()`、`_automation_task_step_types()` 和 audit `step_count` 现在共用这个边界。
- 非 dict persisted step 被跳过；污染 dict step type 仍按既有规则折叠为 `unknown`。
- Task get/list/cancel 不再因 polluted non-dict persisted steps 崩溃，也不回显 secret、host、`token=`、Authorization 或 Bearer 文本。
- Automation task audit step_count 只统计 public dict steps，step_types 只输出 public step type labels。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_skip_non_dict_persisted_steps -q
# RED: 旧实现对 string step 调用 .get() 并 500；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_skip_non_dict_persisted_steps backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_unknown_step_type_before_persisting_responding_or_audit backend/tests/test_api.py::test_automation_task_create_cancel_retry_and_run_write_redacted_audit_events -q
# 3 passed in 1.20s

.venv/bin/python -m pytest backend/tests/test_api.py -k "automation_task or automation_worker" -q
# 56 passed, 195 deselected in 6.45s

.venv/bin/python -m pytest backend/tests -q
# 642 passed in 38.23s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.21s

git diff --check
# passed
```

边界：

- 这是 automation task response/audit stability and release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变 normal automation task create/run/cancel/retry semantics、worker lease、runner selection、VNC/WebSocket 行为、底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata、automation payload 或外站页面原文。

## 2026-06-03 Automation wait-step ms response guardrail

背景：

- Automation wait step execution 已要求 `ms` 是非 bool 整数且范围为 `1..300000`。
- Response redaction 旧实现只检查 `ms` 是非 bool 整数，历史/手工 DB row 中的负数或超大值会进入 task get/list/cancel release evidence。
- Release evidence 应和执行边界一致，只保留 public wait duration。

已覆盖：

- `_automation_task_redacted_steps()` 的 `wait.ms` 输出边界现在和执行边界一致。
- 正常 `ms=1` 保留；负数、bool、超大值不再出现在 response evidence 中。
- Task get/list/cancel 继续返回低敏 step shape；audit step_count/step_types 保持既有语义。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_response_filters_persisted_wait_ms_boundary -q
# RED: 旧实现回显 invalid wait ms；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_response_filters_persisted_wait_ms_boundary backend/tests/test_api.py::test_automation_task_responses_redact_open_url_steps backend/tests/test_api.py::test_run_automation_task_marks_failed_for_invalid_wait_ms -q
# 3 passed in 2.13s

.venv/bin/python -m pytest backend/tests/test_api.py -k "automation_task or automation_worker" -q
# 57 passed, 195 deselected in 10.19s

.venv/bin/python -m pytest backend/tests -q
# 643 passed in 39.59s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.53s

git diff --check
# passed
```

边界：

- 这是 automation task response/release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变 normal automation wait execution、worker lease、runner selection、task retry/cancel/run、VNC/WebSocket 行为、底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata、automation payload 或外站页面原文。

## 2026-06-03 Automation retry persisted-step shape guardrail

背景：

- Automation retry 会基于原 task 的 persisted `steps` 创建新 queued task。
- Response/audit 已经过滤非 dict persisted step item，但 retry builder 仍直接对每个 item 调用 `.get()`。
- 历史/手工 DB row 如果包含 URL/query token/header 风格 string step，retry 会 500，也可能阻断 release automation smoke。

已覆盖：

- `_automation_task_persisted_steps()` 现在复用 `_automation_task_public_steps()`。
- 非 dict persisted step 在 retry 时被跳过；污染 dict step type 仍折叠为 `unknown`。
- Retry response 和 retried audit 不再回显 polluted step host、`token=`、Authorization 或 Bearer 文本。
- 正常 failed-task retry 和 retry redaction 行为保持通过。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_retry_automation_task_skips_non_dict_persisted_steps -q
# RED: 旧实现对 string step 调用 .get() 并 500；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py::test_retry_automation_task_skips_non_dict_persisted_steps backend/tests/test_api.py::test_retry_automation_task_keeps_steps_redacted backend/tests/test_api.py::test_retry_failed_automation_task_creates_new_queued_task_without_running_script -q
# 3 passed in 1.08s

.venv/bin/python -m pytest backend/tests/test_api.py -k "automation_task or automation_worker" -q
# 58 passed, 195 deselected in 7.17s

.venv/bin/python -m pytest backend/tests -q
# 644 passed in 38.43s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.31s

git diff --check
# passed
```

边界：

- 这是 automation retry stability/release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变 normal retry semantics、worker lease、runner selection、task run/cancel、VNC/WebSocket 行为、底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- 不记录真实 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata、automation payload 或外站页面原文。

## 2026-06-03 VNC proxy close-code log guardrail

背景：

- Runtime viewer audit metadata 已经把 WebSocket `close_code` 过滤为 public integer 或 `null`。
- VNC proxy 日志仍直接打印 client/backend disconnect close code；正常 close code 是整数，但 transport dict 不应被信任为 release evidence。
- 如果测试/异常 transport 给 `code` 填入 URL/query token/header 风格文本，日志会保留这些文本。

已覆盖：

- `_proxy_running_vnc()` 现在在写 disconnect metadata 和日志前统一调用 `_public_ws_close_code()`。
- Client-to-VNC disconnect、client WebSocketDisconnect、KasmVNC stream ended、backend-to-client WebSocketDisconnect 四条 close-code 路径都只记录 public close code 或 `None`。
- 正常 integer close code 语义保留；VNC/RFB proxy 行为、frame filtering、viewer token 校验和 runtime session 状态机不变。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_vnc_proxy_disconnect_close_code_is_public_in_logs_and_metadata -q
# RED: 旧实现在 VNC proxy client disconnect 日志中写入 Authorization/Bearer/token 风格 close code；GREEN: 1 passed

.venv/bin/python -m pytest \
  backend/tests/test_api.py::test_vnc_proxy_connects_websockify_path \
  backend/tests/test_api.py::test_vnc_proxy_disconnect_close_code_is_public_in_logs_and_metadata \
  backend/tests/test_api.py::test_vnc_proxy_disconnect_does_not_dump_raw_xvnc_log \
  backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_error_type_without_raw_exception \
  backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_public_profile_id \
  backend/tests/test_session_broker.py::test_runtime_viewer_disconnect_audit_sanitizes_non_integer_close_code \
  -q
# 6 passed in 1.07s
```

边界：

- 这是 VNC/runtime viewer release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变底层 `invisible_playwright`、stealth prefs、Firefox identity、WebGL、WebRTC、UA、locale/timezone、proxy、profile launch 或 Docker runtime 行为。
- 不记录 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。

## 2026-06-03 VNC proxy unhandled-message log guardrail

背景：

- VNC proxy client-to-backend loop 会在遇到未识别 websocket message shape 时记录 `keys` 和 `type`。
- 正常 Starlette transport 只会产生固定低敏 key/type，但异常测试 transport 或未来 adapter 不应被信任。
- 原实现会把 raw message key 和 raw type 写入日志；如果其中包含 URL/query token/header 文本，会进入 release evidence。

已覆盖：

- 新增 `_public_ws_message_type()`，只保留 `websocket.receive` / `websocket.disconnect`，其它值折叠为 `unknown`。
- 新增 `_public_ws_message_keys()`，只保留 `type`、`bytes`、`text`、`code`、`reason`，其它 key 合并为 `unknown`。
- VNC proxy unhandled message 日志现在只记录 public keys/type。

验证记录：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_vnc_proxy_unhandled_message_log_uses_public_keys_and_type -q
# RED: 旧实现泄露 Authorization/Bearer/token 风格 raw key/type；GREEN: 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k "vnc or runtime_viewer" -q
# 9 passed, 246 deselected in 1.09s

.venv/bin/python -m pytest backend/tests -q
# 646 passed in 37.66s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.67s

git diff --check
# passed
```

边界：

- 这是 VNC proxy log/release evidence 防御，不是 Pixelscan `PXLSCN-FINGERPRINT-MASKING` 修复。
- 不改变 WebSocket accept、VNC forwarding、RFB filtering、clipboard bridge、viewer token、runtime session、profile launch 或 browser fingerprint 行为。
- 不记录 screenshots、cookies、local storage、headers、tokens、IP values、profile dirs、full page text、full URL params、font lists、WebRTC candidates、raw audit metadata 或外站页面原文。
