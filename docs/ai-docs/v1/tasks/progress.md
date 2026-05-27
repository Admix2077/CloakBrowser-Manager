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

- 本轮继续 08 Cookie、Profile 导入导出，完成前端 Cookie 管理入口小闭环：
  - `frontend/src/lib/api.ts` 新增 Cookie JSON v1 类型、`api.importProfileCookies(profileId, document)` 和 `api.exportProfileCookies(profileId)`。
  - `api.importProfileCookies()` 调用既有 `POST /api/profiles/{profile_id}/cookies/import`。
  - `api.exportProfileCookies()` 调用既有 `POST /api/profiles/{profile_id}/cookies/export`，请求体固定 `{ confirm_export: true }`。
  - 新增 `frontend/src/components/ProfileCookieManager.tsx`，并接入 `ProfileSummaryPanel` 的单 profile `Cookies` 区域。
  - Cookie 管理入口只对 running profile 启用 import/export；stopped profile 显示固定提示并禁用按钮，不调用 cookie API。
  - Import 粘贴 Cookie JSON v1 后调用后端，成功或失败后清空 textarea；成功只显示导入数量和低敏 summary 计数。
  - Export 必须勾选显式确认；后端响应里的 Cookie JSON document 只用于下载文件，不渲染到页面文本。
  - 页面与组件测试覆盖不渲染 cookie value、cookie name、domain、URL query、fragment 或 token。
  - 浏览器验收使用临时后端和临时 SQLite 数据目录，确认 Cookie 管理区可见、非法 JSON 固定错误、textarea 清空、页面文本无敏感 cookie 字段，console warning/error 为 0。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 Netscape cookie 格式层小闭环：
  - `backend/cookie_formats.py` 新增 `parse_netscape_cookies()`、`build_netscape_cookie_export()` 和 `netscape_cookie_audit_summary()`。
  - parser 支持标准 7 列 Netscape cookie 行、普通注释/空行跳过和 `#HttpOnly_` 前缀，并转换为 `CookieJsonDocument`。
  - parser 非法行只返回固定 `Invalid Netscape cookie line <line_number>`，不回显 cookie value、cookie name、domain、URL 或原始行内容。
  - exporter 从 Cookie JSON v1 生成 Netscape cookie 文本；对只有 `url` 的 cookie 只提取 hostname，不把 query/fragment/token 写入 Netscape domain 字段。
  - Netscape audit summary 只输出低敏计数，不包含 cookie value、cookie name、domain、URL、query 或 fragment。
  - 本小闭环只实现格式层，不新增 REST API，不读写运行中 browser context，不写 `audit_events`，不新增前端入口，不接 Project Mileage DTO。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 profile config import JSON 小闭环：
  - 新增 `POST /api/profiles/config/import`，独立于既有 CSV `POST /api/profiles/import`，避免破坏 CSV 粘贴导入契约。
  - 请求体固定 `schema_version=1`，`configs[]` 为 profile config JSON 数组。
  - 每条 config 只从白名单字段创建 profile：`name/fingerprint_seed/proxy/timezone/locale/platform/user_agent/screen_width/screen_height/gpu_vendor/gpu_renderer/hardware_concurrency/humanize/human_preset/headless/geoip/clipboard_sync/auto_launch/color_scheme/launch_args/notes/tags`。
  - 调用方附带的 cookie、local storage、profile dir、`user_data_dir`、runtime session、viewer token、VNC token、automation task、wallet/order/payment/permission/Project Mileage 业务字段不会被导入、写库或回显。
  - 有效 config 创建新 profile；无效 config 返回行级 `ok=false` 和校验错误，不阻塞同批其他有效 config。
  - `schema_version` 非 `1` 时整体返回 `422`，不产生数据库副作用。
  - 支持从 `POST /api/profiles/export` 的 `config` 结果 round-trip 导入；若导出时 `include_sensitive: true`，proxy 凭证会按可信本地管理 API 语义随 config 导入。
  - 本小闭环不新增前端入口、不写 audit、不导入 cookie/local storage/profile dir、不接 Project Mileage DTO。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 profile config export 敏感字段默认脱敏小闭环：
  - 既有 `POST /api/profiles/export` 支持 `include_sensitive`，默认 `false`。
  - `include_sensitive` 必须是 JSON boolean，不接受字符串或数字宽松转换。
  - 默认导出的 `config.proxy` 会移除 `username:password@`，只保留 scheme、host、port。
  - 显式 `include_sensitive: true` 时，才返回完整 proxy URL，用于可信本地管理侧明确选择导出敏感配置。
  - profile config export 仍只导出 profile 配置字段，不包含 cookie、local storage、profile dir、viewer token、runtime session、automation task、钱包、订单、权限或 Project Mileage 业务事实源。
  - 本小闭环不新增前端入口、不新增 audit 事件、不实现 profile config import、不接 Project Mileage DTO。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 JSON cookie export 显式确认与审计小闭环：
  - 新增 `POST /api/profiles/{profile_id}/cookies/export`。
  - 请求体必须显式传入 JSON boolean `confirm_export: true`，不接受字符串或数字宽松转换；缺失或 `false` 返回固定 `422 Cookie export requires explicit confirmation`，且不读取 browser context、不写 audit。
  - 该 endpoint 只允许运行中 profile；profile 未运行返回 `404 Profile not running`，停止状态 profile 不读 Firefox profile dir。
  - 执行时调用运行中 Playwright browser context 的 `cookies()`，再构造成 Cookie JSON v1 导出文档。
  - 响应返回 `profile_id`、`exported`、低敏 `summary` 和 `document`；`document` 包含 cookie 明文，因此该 API 仅限可信本地管理侧并要求显式确认。
  - 成功导出会写 `audit_events`：`event_type=cookie.exported`、`actor_type=local_admin`、`profile_id` 和低敏 metadata。
  - audit metadata 使用 `total_count/session_count/persistent_count` 等不含 `cookie` 字样的 key，避免通用 audit sanitizer 删除统计字段。
  - audit metadata、固定错误和 logger warning 均不回显 cookie value、cookie name、domain、URL、query 或 Playwright 原始异常 message。
  - `cookies()` 执行失败返回固定 `400 Cookie export failed`，不写 audit。
  - 本小闭环不实现 Netscape 格式、不新增前端入口、不接 Project Mileage DTO。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 JSON cookie import 运行中 profile 小闭环：
  - 新增 `POST /api/profiles/{profile_id}/cookies/import`。
  - 请求体复用 Cookie JSON v1 格式，执行时调用运行中 Playwright browser context 的 `add_cookies()`。
  - profile 未运行返回 `404 Profile not running`；停止状态 profile 不写 Firefox profile dir，不尝试直接修改磁盘 cookie 存储。
  - 响应只返回 `profile_id`、`imported` 和低敏 `summary` 计数。
  - 非法文档返回固定 `422 Invalid cookie JSON document`；`add_cookies()` 失败返回固定 `400 Cookie import failed`。
  - 响应、固定错误和 logger warning 均不回显 cookie value、cookie name、domain、URL、query 或 Playwright 原始异常 message。
  - 本小闭环不实现 cookie export、不写 `audit_events`、不新增前端入口、不接 Project Mileage DTO。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮进入 08 Cookie、Profile 导入导出，完成 Cookie JSON v1 格式层小闭环：
  - 新增 `backend/cookie_formats.py`，定义 `cloakbrowser.cookie-json.v1` / `schema_version=1`。
  - 单条 cookie 支持 `name/value/domain/url/path/expires/secure/httpOnly/sameSite`，并要求至少提供 `domain` 或 `url`。
  - `CookieJsonDocument` 用作导入格式校验；`build_cookie_json_export()` 可生成导出文档；`cookies_for_playwright()` 可转换为 Playwright `context.add_cookies()` 可用字段。
  - 新增 `cookie_json_audit_summary()`，只输出低敏计数，不包含 cookie value、cookie name、domain、URL 或 query。
  - Cookie 模型 repr 不显示 `value`，降低测试失败、日志或调试输出泄露 cookie 明文的风险。
  - 本小闭环只定义格式层，不新增公开 REST API、不读写浏览器 context、不写 `audit_events`、不新增前端入口、不接 Project Mileage DTO。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation worker lifecycle 配置无效值防护小闭环：
  - `_env_float()` 现在会把 `NaN`、`Infinity`、`-Infinity` 这类非有限浮点配置视为无效值。
  - `AUTOMATION_WORKER_LEASE_SECONDS` 低于最小值、`AUTOMATION_WORKER_IDLE_SLEEP_SECONDS` 非有限、`AUTOMATION_WORKER_SHUTDOWN_TIMEOUT_SECONDS` 非法字符串时，lifespan 回退默认值。
  - worker 启动配置回退只写固定配置名告警，不记录原始 env 值、task payload、URL、selector、表单值或 secret。
  - 默认关闭和显式启用 worker 的既有行为保持不变；该小闭环不新增公开 REST API、不新增前端入口、不自动启动 profile、不接 Project Mileage DTO。
  - 本小闭环不实现 worker 池、跨进程 supervisor、跨系统补偿、钱包/订单/权限/扣费/续期/viewer token/屏幕流逻辑。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation worker lost lease summary 小闭环：
  - `run_automation_worker_loop()` 会识别内部固定 `409 Automation task lease no longer owned by worker`。
  - 如果单次 worker 因租约不再归当前 owner 而抛出该固定异常，loop 不再崩退出。
  - loop 会把该情况低敏计入 summary：`claimed += 1`、`failed += 1`。
  - task 本身保持 DB 当前状态，不尝试覆盖为 `failed`，避免覆盖其他 worker 已接管或已收束的状态。
  - summary 仍只包含 `claimed/succeeded/failed/cancelled/idle_cycles`，不包含 task id、profile id、URL、selector、表单值、异常原文或 lease owner。
  - 其他未知 `HTTPException` 仍继续抛出，不被吞掉。
  - 该能力只属于内部 worker loop，不新增公开 REST API、不新增前端入口、不自动启动 profile、不接 Project Mileage DTO。
  - 本小闭环不实现 worker 池、跨进程 supervisor、跨系统补偿、钱包/订单/权限/扣费/续期/viewer token/屏幕流逻辑。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation worker lease heartbeat 小闭环：
  - `run_automation_worker_once()` 执行已领取 task 时，会启动内部 lease heartbeat。
  - heartbeat 按 `lease_seconds` 的半周期续租，间隔下限 `0.1s`、上限 `30s`，通过 `renew_automation_task_lease()` 校验当前 `lease_owner`。
  - heartbeat 覆盖长 `wait` 或长 Playwright await 期间的租约续期，降低 lease 过期后被其他 worker 重领的风险。
  - task 成功、失败、取消或异常收束后，heartbeat 会停止；最终 task 仍通过 `finish_claimed_automation_task()` 清空 `lease_owner` / `lease_expires_at`。
  - heartbeat 失败说明 worker 不再拥有 lease，会以 `409 Automation task lease no longer owned by worker` 收束调用路径，不覆盖其他 worker 已接管的状态。
  - 该能力只属于内部 worker，不新增公开 REST API、不新增前端入口、不自动启动 profile、不接 Project Mileage DTO。
  - heartbeat 不写公开响应、不写 task result、不记录 step payload、URL、selector、表单值或异常原文，不承诺强制打断正在 await 的 Playwright 操作。
  - 本小闭环不实现 worker 池、跨进程 supervisor、跨系统补偿、钱包/订单/权限/扣费/续期/viewer token/屏幕流逻辑。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation worker lifespan 可选启动小闭环：
  - FastAPI lifespan 已支持可选启动一个内部 automation worker loop。
  - 默认关闭：未设置 `AUTOMATION_WORKER_ENABLED=true` 时，不启动 worker，不自动领取或执行 queued task。
  - 显式启用时，lifespan 会创建一个随机低敏 `lease_owner`，启动 `run_automation_worker_loop(max_runs=None, max_idle_cycles=None)`。
  - 支持内部运行配置：`AUTOMATION_WORKER_LEASE_SECONDS`、`AUTOMATION_WORKER_IDLE_SLEEP_SECONDS`、`AUTOMATION_WORKER_SHUTDOWN_TIMEOUT_SECONDS`。
  - 配置值无效或低于最小值时回退默认值，只写固定配置名告警，不写 task payload、URL、selector、表单值或 secret。
  - shutdown 时先设置内部 `stop_event`，让 worker 在下一轮 claim 前自然退出；超时后取消内部 task。
  - 该能力不新增公开 REST API、不新增前端入口、不自动启动 profile、不接 Project Mileage DTO。
  - 本小闭环不实现 worker 池、自动续租循环、跨进程 supervisor、跨系统补偿、钱包/订单/权限/扣费/续期/viewer token/屏幕流逻辑。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation worker loop 内部骨架小闭环：
  - 新增内部 `run_automation_worker_loop(lease_owner, lease_seconds=60, max_runs=None, max_idle_cycles=1, idle_sleep_seconds=1.0, stop_event=None)`，为后续后台常驻 worker 提供可测试 loop 骨架。
  - loop 持续调用 `run_automation_worker_once()`，直到达到 `max_runs`、达到 `max_idle_cycles` 或 `stop_event` 已设置。
  - loop 返回低敏 summary：`claimed/succeeded/failed/cancelled/idle_cycles`，不包含 task id、profile id、step payload、URL、selector、表单值、异常原文或 lease owner。
  - 空队列时会增加 `idle_cycles`；如果还未达到上限且 `idle_sleep_seconds > 0`，才进行 sleep；达到最后一次允许空闲周期后直接退出，避免额外等待。
  - `stop_event` 在每轮 claim 前检查；如果已设置，不领取 queued task，不修改 task 状态。
  - 当前已在后续小闭环中接入 FastAPI lifespan 可选启动；默认仍不启动后台 worker。
  - 本小闭环不实现 worker 池、自动续租循环、跨进程 supervisor、跨系统补偿、钱包/订单/权限/扣费/续期/viewer token/屏幕流逻辑。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation worker run-once 内部骨架小闭环：
  - 新增内部 `run_automation_worker_once(lease_owner, lease_seconds=60)`，作为后续后台 worker loop 的单次执行骨架。
  - worker 通过 `claim_next_automation_task()` 原子领取可执行 task；无可领取 task 时返回 `None`，不修改数据库。
  - 同步 `POST /api/tasks/{id}/run` 的 step 执行逻辑已抽为内部 `_execute_running_automation_task()`，worker 和同步 run 复用同一套 step 校验、执行、低敏 result 和协作式取消边界。
  - worker 领取 task 后只复用已运行 profile 执行脚本；profile 不存在或未运行时使用匹配 `lease_owner` 将 task 收束为 `failed`，并清空 `lease_owner` / `lease_expires_at`。
  - worker 执行中遇到 page not found 等内部 HTTP step 错误时，收束为 `failed`，错误固定为 `Automation step failed`，不透传 selector、URL、异常原文或内部路径。
  - worker 成功、失败或取消收束均走 `finish_claimed_automation_task()` owner 校验；owner 不匹配时不会覆盖 task 状态。
  - 公开 task API 响应仍不暴露 `lease_owner`、`lease_expires_at`；`steps` 和 `result` 继续统一白名单脱敏。
  - 当前仍未实现后台常驻 loop、调度器、worker 池、自动续租循环、自动启动 profile、跨系统补偿或 Project Mileage DTO。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation task lease renew/finish 数据层小闭环：
  - 新增 DB 层 `renew_automation_task_lease()`，只允许匹配当前 `lease_owner` 且状态允许的 task 续租。
  - 续租时间按当前服务器时间或传入 `now` 重新计算为 `now + lease_seconds`，不在旧 lease 上累加。
  - 新增 DB 层 `finish_claimed_automation_task()`，只允许匹配当前 `lease_owner` 的 `running` task 收束为 `succeeded | failed | cancelled`。
  - 收束成功后写入 `status/result/error/finished_at`，并清空 `lease_owner`、`lease_expires_at`。
  - owner 不匹配、状态不匹配、task 已收束或非终态 status 时返回 `None`，不覆盖既有 task 状态。
  - `finish_claimed_automation_task()` 支持显式 `allowed_statuses`；后台 worker 处理取消请求时可允许同 owner 的 `cancel_requested -> cancelled`，用于后续 worker 池安全收束取消任务。
  - 公开 task API 响应仍不暴露 `lease_owner`、`lease_expires_at`；该能力仍只服务后续内部 worker 池。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation task claim/lease 数据层小闭环：
  - `automation_tasks` 表新增内部 worker lease 字段 `lease_owner`、`lease_expires_at`，并在 `init_db()` 中补齐既有数据库迁移。
  - 新增 DB 层 `claim_next_automation_task(lease_owner, lease_seconds, now=None)`，用于后续后台 worker 池领取 task。
  - claim 使用 `BEGIN IMMEDIATE`，优先重领 lease 已过期的 `running` task，否则领取最早 `queued` task。
  - 同一 `profile_id` 若已有有效 `running` 或 `cancel_requested` task，则跳过该 profile 的 queued task，延续 profile 级并发边界。
  - claim 成功后只更新 DB 内部调度字段和 `status=running/started_at`，不开放新的公开 REST API，不启动后台 worker，不自动执行脚本，不自动启动 profile。
  - `lease_owner`、`lease_expires_at` 不属于 `AutomationTaskResponse`；`create/get/list/cancel/retry/run` 对外响应不暴露这些内部 worker 字段。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成前端 Automation task log task/profile search 小闭环：
  - `frontend/src/components/AutomationTaskLogViewer.tsx` 在 status filter 旁新增只读本地搜索框。
  - 搜索只匹配 `task.id` 和 `profile_id`，并与 status filter 组合生效。
  - 搜索只作用于前端当前已加载的最近 50 条 task，不新增后端 API query，不调用新的后端接口，不修改 task 状态。
  - 搜索不匹配 `steps`、`result`、`error`，不读取或渲染自动化 payload 里的 URL、query、fragment、token、selector、表单值、keyboard text、evaluate expression/result、screenshot 内容、console/network 内容或未知字段。
  - 搜索控件不提供 `run`、`cancel`、`retry` 能力；原 task log、status filter 和 detail drawer 的脱敏边界保持不变。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成前端 Automation task log status filter 小闭环：
  - `frontend/src/components/AutomationTaskLogViewer.tsx` 新增只读 status filter segmented control。
  - `All` 展示当前加载的最近 50 条；`Running` 展示 `running | cancel_requested`；`Failed` 展示 `failed`；`Finished` 展示 `succeeded | cancelled`。
  - 该过滤只作用于前端当前内存列表，不新增后端 API query，不调用新的后端接口，不修改 task 状态。
  - 过滤控件不提供 `run`、`cancel`、`retry` 能力；原 task log 和 detail drawer 的脱敏边界保持不变。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成前端 Automation task detail drawer 小闭环：
  - `frontend/src/components/AutomationTaskLogViewer.tsx` 的 task log table 每行新增只读 `Details` 入口。
  - detail drawer 展示 task 短 ID、profile 短 ID、status、created/started/finished、固定错误文案、完整低敏 steps 和完整低敏 result steps。
  - 表格仍保留最多 4 条 step/result 摘要，drawer 不使用该截断上限，便于本地管理台排查完整脚本轨迹。
  - drawer 复用 task log viewer 的低敏渲染边界，只显示 step 白名单字段 `type/page_ref/ms/wait_until/state/timeout_ms/delay_ms/delta_x/delta_y/full_page` 和 `result.steps[].index/type/status`。
  - drawer 不渲染 `open_url.url`、URL query、fragment、token、selector、fill value、keyboard text、evaluate expression/result、screenshot bytes/base64/path、clipboard、console/network URL、headers、body 或未知字段。
  - drawer 不提供 `run`、`cancel`、`retry` 按钮，不调用新的后端接口，不启动/停止 profile，不修改 task 状态。
  - `cancel_requested` 在前端状态 pill 中按进行中/待收束口径展示，并计入 Running 统计。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation running task 协作式取消小闭环：
  - queued task 取消仍为 `queued -> cancelled`，并写入 `finished_at`。
  - running task 取消改为 `running -> cancel_requested`，`finished_at` 保持 `null`，不伪造已停止。
  - `cancel_requested` task 重复取消会幂等返回当前 task。
  - 已结束 task 取消返回 `409 Only queued or running automation tasks can be cancelled`。
  - `cancel_requested` 会继续占用同一 `profile_id` 的执行槽；同 profile 新 queued task run 返回 `409 Automation profile already has a running task`，直到原 task 被 runner 收束。
  - runner 在 step 边界检查 `cancel_requested`，把当前未执行 step 或 wait 后的下一步记录为低敏 `cancelled` 结果，并将 task 收束为 `cancelled`。
  - 该取消是协作式边界检查，不承诺打断正在 await 的 Playwright 操作，不终止浏览器，不停止 profile。
  - cancel/get/list/run 的对外响应继续统一脱敏；`open_url.url`、query、fragment、token、selector、表单值、keyboard text、evaluate expression/result、screenshot 内容不会回显。
  - 本小闭环不实现后台队列、全局 worker 池、强杀 Playwright 操作、跨系统补偿，不修改 Project Mileage app/payload，不写钱包、订单、权限、扣费、续期、viewer token 或审计事实源。
- 本轮继续 07 Automation API 与脚本运行器，完成前端 Automation task log viewer 小闭环：
  - 前端新增 `Automation` 顶部分段入口，与 `Profiles`、`Proxy Manager` 同级。
  - 新增 `frontend/src/components/AutomationTaskLogViewer.tsx`，只读展示最近 50 条 Automation task。
  - 新增 `api.listAutomationTasks({ profileId?, limit?, offset? })`，通过统一 API adapter 请求 `/api/tasks`，支持 `profile_id`、`limit`、`offset` query。
  - viewer 展示 task 短 ID、profile 短 ID、status、低敏 step 摘要、低敏 result step 摘要、固定错误文案和 created/finished 时间。
  - viewer 不提供 `run`、`cancel`、`retry` 按钮，不新增脚本执行入口，不启动 profile，不终止浏览器，不修改 task 状态。
  - viewer 只渲染白名单字段：`type/page_ref/ms/wait_until/state/timeout_ms/delay_ms/delta_x/delta_y/full_page` 和 `result.steps[].index/type/status`。
  - 即使 API mock 或历史数据带有 `open_url.url`、query、fragment、token、selector、value、keyboard text、evaluate expression、screenshot base64/path、result raw URL 或表单值，前端组件也不会渲染这些字段。
  - 该页面仍然只面向 CloakBrowser 本地可信管理台；`GET /api/tasks` 当前没有 Project Mileage 账号归属、订单、权限或审计隔离，不能直接暴露给 Project Mileage App。
  - 本小闭环不修改 Project Mileage app/payload，不写钱包、订单、权限、扣费、续期、viewer token、VNC token 或屏幕流逻辑。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation task 列表分页小闭环：
  - `GET /api/tasks` 支持可选 `limit` 和 `offset` query。
  - `limit` 范围为 `1..500`；超过范围返回 FastAPI `422`。
  - `offset` 默认 `0`，范围为非负整数；负数返回 FastAPI `422`。
  - 未传 `limit` 时保持兼容行为：返回匹配条件下的全部 task。
  - 分页在 `profile_id` 过滤后应用，排序仍为 `created_at desc`，最新 task 在前。
  - DB 层 `list_automation_tasks(profile_id=None, limit=None, offset=0)` 支持同样的分页语义，避免 API 事后切片。
  - 分页后的对外响应继续复用统一 `AutomationTaskResponse` 脱敏。
  - 当前仍未提供权限隔离；该接口仍只能视为 CloakBrowser 本地可信管理 API，不能直接暴露给 Project Mileage App。
  - 本小闭环为后续前端 Automation 页面 / task log viewer 提供基础，不修改 Project Mileage app/payload，不写钱包、订单、权限、扣费、续期或 viewer token 逻辑。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation task 显式重试小闭环：
  - 新增 `POST /api/tasks/{id}/retry`。
  - retry 只允许对已结束 task 创建新 queued task，允许 `failed | cancelled | succeeded`。
  - `queued` 或 `running` task retry 返回 `409 Only finished automation tasks can be retried`。
  - task 不存在时返回 `404 Automation task not found`；profile 不存在时返回 `404 Profile not found`。
  - retry 成功后返回新创建的 queued task，状态码 `201`。
  - 原 task 的 `status/result/error/started_at/finished_at` 保持不变，不伪造恢复状态。
  - retry 不自动执行脚本，不启动 profile，不绕过 `run` 的 profile running 检查或 profile 级并发限制。
  - retry 复制已持久化并裁剪过的内部 `steps`；对外响应继续统一脱敏，`open_url.url`、query、fragment、selector、表单值、evaluate expression、screenshot 内容、token 和未知字段不会回显。
  - retry 只是显式再排队一次，不判断 step 是否有副作用；涉及点击、填写、跳转等副作用脚本时，调用方必须在可信管理侧确认可重复执行。
  - 本小闭环不修改 Project Mileage app/payload，不写钱包、订单、权限、扣费、续期、viewer token 或审计事实源。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation task profile 过滤小闭环：
  - `GET /api/tasks` 支持可选 `profile_id` query。
  - 未传 `profile_id` 时保持原行为：返回所有已持久化 task，并按 `created_at desc` 排序。
  - 传入 `profile_id` 时只返回该 profile 的 task，并继续按 `created_at desc` 排序。
  - profile 不存在时返回 `404 Profile not found`，避免把无效 profile 误读为空任务列表。
  - 过滤后的对外响应继续复用统一 `AutomationTaskResponse` 脱敏；`open_url.url`、query、fragment、token 和未知字段不会回显。
  - 当前仍未提供权限隔离；`GET /api/tasks` 仍只能视为 CloakBrowser 本地可信管理 API，不能直接暴露给 Project Mileage App。
  - 本小闭环不修改 Project Mileage app/payload，不写钱包、订单、权限、扣费、续期或 viewer token 逻辑。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation task profile 并发限制小闭环：
  - `POST /api/tasks/{id}/run` 已增加 profile 级并发限制。
  - 同一个 `profile_id` 已存在其他 `running` 或 `cancel_requested` task 时，新的 queued task run 返回 `409`。
  - 不同 profile 的 running task 不阻塞当前 profile 的 queued task。
  - 被拒绝的 queued task 保持 `queued`，不写 `started_at`、`finished_at` 或 `result`，便于稍后重试。
  - 错误 detail 固定为 `Automation profile already has a running task`，不回显 step payload、URL query、token、selector、表单值或未知字段。
  - 当前仍未实现后台队列。
- 本轮继续 07 Automation API 与脚本运行器，完成 Script Runner screenshot step 小闭环：
  - `POST /api/tasks/{id}/run` 已支持 `screenshot` step。
  - `screenshot` 支持可选 `page_ref`，默认 `"0"`；可选 `full_page`，默认 `false`，且严格要求布尔值。
  - 执行时复用已运行 profile 的既有 page 和 `page.screenshot(type="png", full_page=full_page)`，不自动启动 profile，不创建新 page，不开放 `path`、`clip`、`quality` 或下载 URL。
  - 非法 `full_page` 进入 `failed` 并返回固定低敏错误 `Invalid screenshot step`；执行异常进入 `failed` 并返回固定低敏错误 `Screenshot step failed`。
  - 创建 task 时会先按 step 类型做执行字段白名单裁剪；`screenshot` 入库仅保留 `type/page_ref/full_page`，不持久化调用方附带的 `path`、`filename`、`base64`、`note` 等未知字段。
  - task 对外响应对 `screenshot` step 做白名单脱敏，只回显 `type/page_ref/full_page`，不回显 PNG bytes、base64、路径、下载 URL 或未知字段。
  - `result.steps[]` 只记录 `index/type/status`，runner 会丢弃 `page.screenshot()` 返回的 PNG bytes，不复制 screenshot 内容、完整 step payload 或异常原文。
  - 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。
- 本轮继续 07 Automation API 与脚本运行器，完成 Script Runner evaluate step 小闭环：
  - `POST /api/tasks/{id}/run` 已支持 `evaluate` step。
  - `evaluate` 支持必填 `expression`，长度 `1..200000`；可选 `page_ref`，默认 `"0"`。
  - 执行时复用已运行 profile 的既有 page 和 `page.evaluate(expression)`，不自动启动 profile，不创建新 page。
  - 非法 expression 进入 `failed` 并返回固定低敏错误 `Invalid evaluate step`；执行异常进入 `failed` 并返回固定低敏错误 `Evaluate step failed`。
  - task 对外响应对 `evaluate` step 做白名单脱敏，只回显 `type/page_ref`，不回显 expression。
  - `result.steps[]` 只记录 `index/type/status`，不复制 expression、evaluate 返回值、完整 step payload 或异常原文。
  - 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。
- 本轮继续 07 Automation API 与脚本运行器，完成 Script Runner wait_for_selector step 小闭环：
  - `POST /api/tasks/{id}/run` 已支持 `wait_for_selector` step。
  - `wait_for_selector` 支持必填 `selector`，长度 `1..10000`；可选 `page_ref`，默认 `"0"`；可选 `state`，默认 `visible`，允许 `attached | detached | visible | hidden`；可选 `timeout_ms`，默认 `30000`，范围 `1..300000`，且拒绝 `bool`。
  - 执行时复用已运行 profile 的既有 page 和 `page.wait_for_selector(selector, state=state, timeout=timeout_ms)`，不自动启动 profile，不创建新 page。
  - 非法 selector、state 或 timeout 进入 `failed` 并返回固定低敏错误 `Invalid wait_for_selector step`；执行异常进入 `failed` 并返回固定低敏错误 `Wait for selector step failed`。
  - task 对外响应对 `wait_for_selector` step 做白名单脱敏，只回显 `type/page_ref/state/timeout_ms`，不回显 selector。
  - `result.steps[]` 只记录 `index/type/status`，不复制 selector、完整 step payload 或异常原文。
  - 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。
- 本轮继续 07 Automation API 与脚本运行器，完成 Script Runner keyboard_type step 小闭环：
  - `POST /api/tasks/{id}/run` 已支持 `keyboard_type` step。
  - `keyboard_type` 支持必填 `text`，长度 `1..1048576`；可选 `page_ref`，默认 `"0"`；可选 `delay_ms`，默认 `0`，范围 `0..10000`，且拒绝 `bool`。
  - 执行时复用已运行 profile 的既有 page 和 `page.keyboard.type(text, delay=delay_ms)`，不自动启动 profile，不创建新 page。
  - 非法 text 或 delay 进入 `failed` 并返回固定低敏错误 `Invalid keyboard_type step`；执行异常进入 `failed` 并返回固定低敏错误 `Keyboard type step failed`。
  - task 对外响应对 `keyboard_type` step 做白名单脱敏，只回显 `type/page_ref/delay_ms`，不回显 text。
  - `result.steps[]` 只记录 `index/type/status`，不复制 text、完整 step payload 或异常原文。
  - 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。
- 本轮继续 07 Automation API 与脚本运行器，完成 Script Runner fill step 小闭环：
  - `POST /api/tasks/{id}/run` 已支持 `fill` step。
  - `fill` 支持必填 `selector`，长度 `1..10000`；必填 `value`，长度 `0..1048576`，允许空字符串用于清空输入；可选 `page_ref`，默认 `"0"`；可选 `timeout_ms`，默认 `30000`，范围 `1..300000`，且拒绝 `bool`。
  - 执行时复用已运行 profile 的既有 page 和 `page.fill(selector, value, timeout=timeout_ms)`，不自动启动 profile，不创建新 page。
  - 非法 selector、value 或 timeout 进入 `failed` 并返回固定低敏错误 `Invalid fill step`；执行异常进入 `failed` 并返回固定低敏错误 `Fill step failed`。
  - task 对外响应对 `fill` step 做白名单脱敏，只回显 `type/page_ref/timeout_ms`，不回显 selector 或 value。
  - `result.steps[]` 只记录 `index/type/status`，不复制 selector、value、完整 step payload 或异常原文。
  - 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。
- 本轮继续 07 Automation API 与脚本运行器，完成 Script Runner click step 小闭环：
  - `POST /api/tasks/{id}/run` 已支持 `click` step。
  - `click` 支持必填 `selector`，长度 `1..10000`；可选 `page_ref`，默认 `"0"`；可选 `timeout_ms`，默认 `30000`，范围 `1..300000`，且拒绝 `bool`。
  - 执行时复用已运行 profile 的既有 page 和 `page.click(selector, timeout=timeout_ms)`，不自动启动 profile，不创建新 page。
  - 非法 selector 或 timeout 进入 `failed` 并返回固定低敏错误 `Invalid click step`；执行异常进入 `failed` 并返回固定低敏错误 `Click step failed`。
  - task 对外响应对 `click` step 做白名单脱敏，只回显 `type/page_ref/timeout_ms`，不回显 selector。
  - `result.steps[]` 只记录 `index/type/status`，不复制 selector、完整 step payload 或异常原文。
  - 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation task result 响应脱敏加固小闭环：
  - create/get/list/cancel/run 的所有对外 `AutomationTaskResponse.result` 统一走白名单脱敏。
  - 对外只保留 `result.steps[]` 的 `index/type/status`。
  - 即使历史持久化数据或后续 runner 误写入 `raw_url`、完整 step payload、URL query、fragment 或 token 字段，对外响应也不会回显。
  - 该加固不修改数据库内部结构，不扩大 task runner 能力，不修改 Project Mileage app/payload。
- 本轮继续 07 Automation API 与脚本运行器，完成 Script Runner scroll step 小闭环：
  - `POST /api/tasks/{id}/run` 已支持 `scroll` step。
  - `scroll` 支持可选 `page_ref`，默认 `"0"`。
  - `delta_x` 和 `delta_y` 必须是整数，范围 `-100000..100000`，默认 `0`。
  - 执行时复用已运行 profile 的既有 page 和 `window.scrollBy(deltaX, deltaY)`，不自动启动 profile，不创建新 page。
  - 非法 delta 进入 `failed` 并返回 `400`。
  - task 对外响应对 `scroll` step 做白名单脱敏，只回显 `type/page_ref/delta_x/delta_y`。
  - `result.steps[]` 只记录 `index/type/status`，不复制完整 step payload。
  - 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。
- 本轮继续 07 Automation API 与脚本运行器，完成 Automation task 响应脱敏收口小闭环：
  - create/get/list/cancel/run 的所有对外 `AutomationTaskResponse.steps` 统一走白名单脱敏。
  - `wait` step 仅回显 `type/ms`。
  - `open_url` step 仅回显 `type/page_ref/wait_until/timeout_ms`。
  - `open_url.url`、query、fragment、未知 step 字段、表单值、token、cookie、secret 不会在 task 响应中回显。
  - `result` 对外响应也统一做白名单脱敏；即使历史持久化数据或后续 runner 误写入 `raw_url`、完整 step payload、URL query、fragment 或 token 字段，对外也只返回 `result.steps[]` 的 `index/type/status`。
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
  - 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。
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
  - 该小闭环完成时，后台队列和其他后续 runner 能力留待后续小闭环。
- 本轮继续 07 Automation API 与脚本运行器，完成 task 列表与取消小闭环：
  - 新增 `AutomationTasksResponse`。
  - 新增 `GET /api/tasks`：返回所有已持久化 task，并按 `created_at desc` 让最新 task 在前；当前已支持可选 `profile_id` query 过滤。
  - 新增 `POST /api/tasks/{id}/cancel`：只允许取消 `queued` task。
  - 取消成功后 task 状态更新为 `cancelled`，并写入 `finished_at`。
  - task 不存在时返回 `404`；非 `queued` task 返回 `409`，避免把运行中、已完成或失败 task 伪装成可取消成功。
  - `GET /api/tasks` 当前未提供分页或权限隔离，只能视为 CloakBrowser 本地管理 API，不能直接暴露给 Project Mileage App。
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

1. 继续 CloakBrowser 独立侧 07 Automation API，进入后台队列、全局 worker 池、task detail drawer 或更完整任务过滤等后续小闭环；所有 task 对外响应继续保持步骤和结果白名单脱敏。
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
