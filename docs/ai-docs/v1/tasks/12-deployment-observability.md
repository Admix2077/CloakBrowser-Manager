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
