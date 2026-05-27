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

- 本轮继续 12 部署、观测与资源治理，完成 `VITE_BULK_LAUNCH_CONCURRENCY` 前端批量启动并发小闭环：
  - 前端 `launchProfiles()` 不再硬编码批量启动并发 2，而是读取构建时环境变量 `VITE_BULK_LAUNCH_CONCURRENCY`。
  - 默认仍为 2；缺失或非法值回退默认，合法值钳制在 `1..8`。
  - 新增前端测试覆盖配置为 1 时，3 个待启动 profile 最大实际并发为 1。
  - 该配置只影响 CloakBrowser 前端批量按钮的请求并发，不改变单 profile launch 确认、不绕过后端 `MAX_RUNNING_PROFILES`，也不作为 Project Mileage 套餐/订单/权限事实源。
  - 本小闭环不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 12 部署、观测与资源治理，完成 `MAX_RUNNING_PROFILES` 运行资源限制小闭环：
  - 新增可选环境变量 `MAX_RUNNING_PROFILES`；默认未设置时不限制，合法正整数会限制 `running + launching` 的 profile 总数。
  - 限制判断放在 `BrowserManager.launch()` 内部锁里，普通 profile launch 和 runtime session broker 共享同一资源闸门。
  - 达到限制时在 VNC allocate 前返回固定 `409 Maximum running profiles reached`，不自动停止已有 profile，不创建 runtime session audit，不泄露 profile id、display、ws port、proxy、路径、env 原文或 token。
  - `/api/diagnostics.runtime.max_running_profiles` 只返回解析后的正整数或 `null`，不回显原始环境变量。
  - 该限制只是 CloakBrowser runtime 资源保护；Project Mileage 业务套餐/订单/并发权限仍必须由 Payload 作为事实源实现，App 不能直连 CloakBrowser API 判断权限。
  - 本小闭环不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 12 部署、观测与资源治理，完成 `/api/diagnostics` 低敏诊断小闭环：
  - 新增受保护的 `GET /api/diagnostics`；该接口不加入 healthcheck/auth exempt，`AUTH_TOKEN` 开启时未认证返回 401。
  - 响应只返回低敏诊断快照：`status`、`binary_version`、`data_dir_exists`、`db_exists`、运行/启动中/profile/proxy/task 计数、active display/ws port 数值列表，以及 automation worker 的解析后配置。
  - diagnostics 计数继续只使用 `count_profiles()`、`count_proxies()` 和 `count_automation_tasks_by_status()`，不读取完整 profile/proxy/automation task rows。
  - 响应不回显真实 `DATA_DIR`/`DB_PATH` 路径、profile id、profile notes、proxy URL/host/username/password、automation steps/result/error、URL/query/fragment、selector、fill value、env 原文、token、cookie/local storage、viewer/runtime service token 或 Project Mileage 钱包/订单/权限/审计事实。
  - 该接口仍是 CloakBrowser 本地可信管理 API；未来 Project Mileage 远程工作台如需诊断能力，必须由 Payload 通过安全 DTO 重新定义，App 不能直连 CloakBrowser diagnostics/runtime API。
  - 本小闭环不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 12 部署、观测与资源治理，完成 `/api/status` 低敏运行计数小闭环：
  - `StatusResponse` 增加 `launching_count`、`failed_count`、`proxy_count`、`task_queue_count` 和 `automation_task_counts`。
  - `/api/status` 仍作为 Docker healthcheck 免登录接口，只返回低敏计数，不返回明细。
  - 新增 `count_profiles()`、`count_proxies()` 和 `count_automation_tasks_by_status()`，status 计算只使用 `COUNT(*)` / `GROUP BY status`，不读取完整 profile、proxy 或 automation task rows。
  - `running_count` 来自 browser manager running map；`launching_count` 来自 browser manager 内部启动中集合计数；`failed_count`、`task_queue_count` 和 `automation_task_counts` 来自 automation task status 聚合。
  - 前端 `SystemStatus` 类型已同步新增字段。
  - 测试覆盖 status 响应包含新增计数，且响应和实现都不泄露 proxy password/host、automation URL token、selector、fill value、evaluate expression 或 steps 明细。
  - 本小闭环不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 profile 创建类导入后端强制确认小闭环：
  - `POST /api/profiles/import`、`POST /api/profiles/config/import` 和 `POST /api/profiles/bundle/import` 都会创建新 profile，必须显式传入 JSON boolean `confirm_import: true`。
  - 缺失请求体、空 JSON、非 object、缺失确认、`false` 或字符串 `"true"` 均返回固定 422；CSV import 返回 `Profile import requires explicit confirmation`，config import 返回 `Profile config import requires explicit confirmation`，bundle import 返回 `Profile bundle import requires explicit confirmation`。
  - 未确认导入不会解析并创建 profile，不会写 `profile.imported` / `profile.config_imported` bulk audit；bundle import 仍不写 audit。
  - 确认通过后继续保留既有语义：CSV import 支持部分成功并写 `profile.imported`，config import 支持行级结果并写 `profile.config_imported`，bundle import 只读取 `bundle.profile.config` 白名单字段并创建新 profile。
  - 前端 `api.importProfiles()` 固定发送 `{ confirm_import: true }`，既有 CSV preview/import UI 复用该安全确认。
  - 本小闭环只修改 CloakBrowser 本仓 profile 导入安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 cookie import 后端强制确认小闭环：
  - `POST /api/profiles/{profile_id}/cookies/import` 和 `POST /api/profiles/{profile_id}/cookies/import/netscape` 必须显式传入 JSON boolean `confirm_import: true`。
  - 缺失请求体、空 JSON、缺失确认、`false` 或字符串 `"true"` 均返回固定 `422 Cookie import requires explicit confirmation`。
  - JSON Cookie import 会先校验确认，通过后再把 `confirm_import` 从 Cookie JSON document 中剥离并交给格式模型校验。
  - 未确认 import 不会调用运行中 browser context 的 `add_cookies()`，不会写入 cookie。
  - 前端 `api.importProfileCookies()` 与 `api.importProfileCookiesNetscape()` 固定发送 `{ confirm_import: true }`，既有 Cookie 管理 UI 复用该安全确认。
  - 本小闭环只修改 CloakBrowser 本仓 cookie import 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 profile launch 后端强制确认小闭环：
  - `POST /api/profiles/{profile_id}/launch` 新增请求体确认模型，必须显式传入 JSON boolean `confirm_launch: true`。
  - 缺失请求体、空 JSON、`false` 或字符串 `"true"` 均返回固定 `422 Profile launch requires explicit confirmation`。
  - 未确认启动不会调用 `browser_mgr.launch()`，不会启动浏览器/VNC 运行环境，不会更新运行状态或 GeoIP 结果。
  - 确认启动后继续保留既有语义：profile 不存在返回 404，已运行返回 409，成功返回 `LaunchResponse` 并保留 automation URL。
  - 前端 `api.launchProfile()` 固定发送 `{ confirm_launch: true }`，既有单 profile launch 和批量 launch hook 复用该安全确认。
  - 本小闭环只修改 CloakBrowser 本仓 profile launch 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 proxy bulk check 后端强制确认小闭环：
  - `POST /api/proxies/bulk/check` 新增请求体确认字段，必须显式传入 JSON boolean `confirm_bulk_check: true`。
  - 缺失请求体、空 JSON、非 object、缺失确认、`false` 或字符串 `"true"` 均返回固定 `422 Proxy bulk check requires explicit confirmation`。
  - 确认检查发生在 `proxy_ids` 列表校验之前；未确认时即使 `proxy_ids=[]` 也只返回固定确认错误。
  - 未确认批量检测不会调用 `resolve_network_geo()`，不会更新 proxy `last_check_*`，也不会写 `proxy.bulk_checked` audit。
  - 确认批量检测后继续保留既有语义：同批成功、检测失败和 missing proxy 可共存；响应和 audit 继续保持 proxy URL/密码脱敏边界。
  - 前端 `api.bulkCheckProxies()` 固定发送 `{ confirm_bulk_check: true }`，既有 Proxy Manager 批量检测流程复用该确认。
  - 本小闭环只修改 CloakBrowser 本仓 proxy bulk check 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 automation page close 后端强制确认小闭环：
  - `DELETE /api/profiles/{profile_id}/automation/pages/{page_ref}` 新增请求体确认模型，必须显式传入 JSON boolean `confirm_close_page: true`。
  - 缺失请求体、空 JSON、`false` 或字符串 `"true"` 均返回固定 `422 Automation page close requires explicit confirmation`。
  - 未确认 close 不会调用 `page.close()`，不会关闭运行中的 automation page。
  - 确认 close 后继续保留既有语义：按 index 或 `page_id` 找到运行中 page，调用 Playwright `page.close()` 并返回 `{ ok: true }`。
  - 本小闭环只修改 CloakBrowser 本仓 automation page close 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 runtime session terminate 后端强制确认小闭环：
  - `POST /api/runtime/sessions/{session_id}/terminate` 新增请求体确认模型，必须显式传入 JSON boolean `confirm_terminate: true`。
  - 缺失请求体、空 JSON、`false` 或字符串 `"true"` 均返回固定 `422 Runtime session terminate requires explicit confirmation`。
  - 未确认 terminate 不会把 session 标记为 `terminated`，不会撤销 viewer token hash / 过期时间，也不会写 `runtime.session.terminated` audit。
  - 确认 terminate 后继续保留既有语义：session 标记为 `terminated`，清空 viewer token hash 和过期时间，使原 viewer token 无法继续连接 runtime VNC；仍不自动 stop profile。
  - 本小闭环只修改 CloakBrowser 本仓 runtime terminate 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 proxy assign / random assign 后端强制确认小闭环：
  - `POST /api/proxies/{proxy_id}/assign` 与 `POST /api/proxies/assign/random` 均新增请求体确认字段，必须显式传入 JSON boolean `confirm_assign: true`。
  - 缺失确认、`false` 或字符串 `"true"` 均返回固定 422；普通指定分配返回 `Proxy assignment requires explicit confirmation`，随机分配返回 `Random proxy assignment requires explicit confirmation`。
  - 未确认分配不会改写 profile 的 `proxy` 字段，不会写 `proxy.assigned` / `proxy.random_assigned` audit。
  - 确认分配后继续保留既有语义：指定 proxy 分配写入该 proxy raw URL；随机分配按 provider/country/tag/preset 筛选候选 proxy 后为每个 profile 随机选择；响应和 audit 继续保持 proxy URL/密码脱敏边界。
  - 前端 `api.assignProxyToProfiles()` 与 `api.assignRandomProxyToProfiles()` 固定发送 `{ confirm_assign: true }`，既有 Proxy Manager 分配弹窗和随机分配弹窗复用该确认。
  - 本小闭环只修改 CloakBrowser 本仓 proxy 分配安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 profile stop 后端强制确认小闭环：
  - `POST /api/profiles/{profile_id}/stop` 新增请求体确认模型，必须显式传入 JSON boolean `confirm_stop: true`。
  - 缺失请求体、空 JSON、`false` 或字符串 `"true"` 均返回固定 `422 Profile stop requires explicit confirmation`。
  - 未确认停止不会调用 `browser_mgr.stop()`，不会停止运行中的 profile。
  - 确认停止后继续保留既有语义：未运行返回 `404 Profile is not running`，运行中调用 `browser_mgr.stop(profile_id)` 并返回 `{ ok: true }`。
  - 前端 `api.stopProfile()` 固定发送 `{ confirm_stop: true }`，既有单 profile stop 和批量 stop 流程复用该安全确认。
  - 本小闭环只修改 CloakBrowser 本仓 profile stop 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 automation task cancel 后端强制确认小闭环：
  - `POST /api/tasks/{task_id}/cancel` 新增请求体确认模型，必须显式传入 JSON boolean `confirm_cancel: true`。
  - 缺失确认、`false` 或字符串 `"true"` 均返回固定 `422 Automation task cancel requires explicit confirmation`。
  - 未确认取消不会把 queued task 改为 `cancelled`，不会把 running task 改为 `cancel_requested`，也不会写 `automation.task.cancelled` / `automation.task.cancel_requested` audit。
  - 确认取消后继续保留 queued 直接 cancelled、running 协作式 cancel_requested、cancel_requested 幂等返回当前 task 的既有语义；对外响应继续统一脱敏。
  - 本小闭环只修改 CloakBrowser 本仓 automation task cancel 安全边界，不新增前端取消入口，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 profile template delete 后端强制确认小闭环：
  - `DELETE /api/profile-templates/{template_id}` 新增请求体确认模型，必须显式传入 JSON boolean `confirm_delete: true`。
  - 缺失确认、`false` 或字符串 `"true"` 均返回固定 `422 Profile template delete requires explicit confirmation`。
  - 未确认删除不会删除 profile template；确认删除继续保持“模板更新/删除不改写已有 profile”的既有事实源边界。
  - 前端 `api.deleteProfileTemplate()` 固定发送 `{ confirm_delete: true }`。
  - 本小闭环只修改 CloakBrowser 本仓 template delete 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 proxy provider preset delete 后端强制确认小闭环：
  - `DELETE /api/proxy-provider-presets/{preset_id}` 新增请求体确认模型，必须显式传入 JSON boolean `confirm_delete: true`。
  - 缺失确认、`false` 或字符串 `"true"` 均返回固定 `422 Proxy provider preset delete requires explicit confirmation`。
  - 未确认删除不会删除 provider preset；确认删除继续保持“不级联删除 proxy assets”的既有契约。
  - 前端 `api.deleteProxyProviderPreset()` 固定发送 `{ confirm_delete: true }`，既有 provider preset 管理弹窗删除确认流程继续保留。
  - 本小闭环只修改 CloakBrowser 本仓 provider preset delete 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 proxy delete 后端强制确认小闭环：
  - `DELETE /api/proxies/{proxy_id}` 新增请求体确认模型，必须显式传入 JSON boolean `confirm_delete: true`。
  - 缺失确认、`false` 或字符串 `"true"` 均返回固定 `422 Proxy delete requires explicit confirmation`。
  - 未确认删除不会删除 proxy asset，也不会写 `proxy.deleted` audit；确认删除继续写既有低敏 `proxy.deleted` audit。
  - 前端 `api.deleteProxy()` 固定发送 `{ confirm_delete: true }`。
  - 本小闭环只修改 CloakBrowser 本仓 proxy delete 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 sensitive proxy export 双确认小闭环：
  - `POST /api/profiles/export` 只有同时传入 JSON boolean `include_sensitive: true` 和 `confirm_sensitive_export: true` 时，才返回完整 proxy URL；只传 `include_sensitive: true` 会返回固定 `422 Profile export sensitive proxy requires explicit confirmation`。
  - `POST /api/profiles/{profile_id}/bundle/export` 只有同时传入 JSON boolean `include_sensitive_proxy: true` 和 `confirm_sensitive_proxy_export: true` 时，才在 bundle config 中包含完整 proxy；只传 `include_sensitive_proxy: true` 会返回固定 `422 Profile bundle sensitive proxy export requires explicit confirmation`。
  - 缺失敏感导出确认时不导出 proxy password、不写 export audit；字符串或数字类型仍不被宽松转换。
  - 前端 `api.exportProfiles(profileIds, { includeSensitive: true })` 会同时发送 `include_sensitive` 与 `confirm_sensitive_export`，默认导出继续只发送 profile ids 并保持 proxy 脱敏。
  - 本小闭环只修改 CloakBrowser 本仓敏感 proxy 导出确认边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 profile delete 后端强制确认小闭环：
  - `DELETE /api/profiles/{profile_id}` 新增请求体确认模型，必须显式传入 JSON boolean `confirm_delete: true`。
  - 缺失确认、`false` 或字符串 `"true"` 均返回固定 `422 Profile delete requires explicit confirmation`。
  - 未确认删除不会调用 `browser_mgr.stop()`，不会删除 DB 记录，不会删除 `user_data_dir`，也不会写 `profile.deleted` audit。
  - 确认删除继续先停止运行 profile，再删除 DB，再清理磁盘，并写既有低敏 `profile.deleted` audit。
  - 前端 `api.deleteProfile()` 固定发送 `{ confirm_delete: true }`，既有单 profile UI dialog 和 bulk delete 确认流程继续保留。
  - 本小闭环只修改 CloakBrowser 本仓 profile delete 安全边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 cookie export 不写日志小闭环：
  - `POST /api/profiles/{profile_id}/cookies/export`、`POST /api/profiles/{profile_id}/cookies/export/netscape` 和 `POST /api/profiles/{profile_id}/bundle/export` 的 cookie export 分支成功路径不写 logger。
  - 以上 cookie export 失败路径只返回固定错误，不写 manager logger，不写失败 audit，不记录异常类型、profile id、cookie value、cookie name、domain、URL、query 或 fragment。
  - 成功路径继续按既有 `cookie.exported` / `profile_bundle.cookie_exported` 写低敏 audit metadata，只包含格式、schema、计数等摘要。
  - 新增失败路径测试覆盖 JSON cookie export、Netscape cookie export 和 profile bundle cookie export，不泄露响应、不写失败 audit、`caplog.text == ""`。
  - 本小闭环只修改 CloakBrowser 本仓 cookie export 日志边界，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 runtime service token 隔离测试与文档收口小闭环：
  - `RUNTIME_SERVICE_TOKEN` / `X-Runtime-Service-Token` 明确作为 runtime service API 专用凭证，用于未来由 Payload 调用 CloakBrowser runtime API。
  - runtime service API 只接受 `X-Runtime-Service-Token`，不接受普通 `AUTH_TOKEN` bearer 或 `auth_token` cookie。
  - 普通受保护 `/api/*` local admin API 只接受 `AUTH_TOKEN` bearer 或 `auth_token` cookie，不接受 `X-Runtime-Service-Token`。
  - `/api/auth/status` 会忽略 runtime service token，不把它当作登录态。
  - 新增测试覆盖 service token 不能访问普通 protected API、auth status 不接受 service token、普通 auth token/cookie 不能创建 runtime session。
  - 当前只完成 local admin API 与 runtime service API 的 token 隔离；viewer/operator/admin 多角色 RBAC 仍是远期，Project Mileage 业务权限仍必须以 Payload roles/DTO 为准。
  - 本小闭环只修改 CloakBrowser 本仓测试和文档，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 bulk action audit 小闭环：
  - `POST /api/profiles/import` 至少成功创建 1 个 profile 后写 `profile.imported` 汇总 audit。
  - `POST /api/profiles/export` 至少成功导出 1 个 profile config 后写 `profile.config_exported` 汇总 audit。
  - `POST /api/profiles/config/import` 至少成功创建 1 个 profile 后写 `profile.config_imported` 汇总 audit。
  - `POST /api/proxies/bulk/check` 至少检查到 1 个真实 proxy 后写 `proxy.bulk_checked` 汇总 audit。
  - `POST /api/proxies/{proxy_id}/assign` 至少成功分配 1 个 profile 后写 `proxy.assigned` 汇总 audit。
  - `POST /api/proxies/assign/random` 至少成功分配 1 个 profile 后写 `proxy.random_assigned` 汇总 audit。
  - preview、列表读取、逐项 missing 失败、没有真实成功/检查动作的请求不写 bulk audit，避免扫描噪声。
  - metadata 只记录 source format、schema version、include_sensitive boolean、total/requested/counts、proxy/profile/candidate/tag 计数、provider/country_code 和 proxy/preset id 等低敏汇总字段。
  - metadata 不记录 CSV 原文、导出 config 内容、proxy URL/host/username/password、notes、last_check_error、IP、timezone/locale 原文、cookie/local storage、token、headers、路径或 Project Mileage 钱包/订单/权限/审计事实。
  - 新增 profile/proxy bulk audit 测试覆盖 CSV import、config export/import、import preview 不写、proxy bulk check、proxy assign、random assign，并断言 proxy password/host、notes、IP、CSV/config 原文等敏感内容不泄露。
  - 本小闭环只修改 CloakBrowser 本仓 bulk action 审计，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 automation task audit 小闭环：
  - `POST /api/tasks` 成功创建 queued task 后写 `automation.task.created`。
  - `POST /api/tasks/{id}/cancel` 对 queued task 写 `automation.task.cancelled`，对 running task 写 `automation.task.cancel_requested`。
  - `POST /api/tasks/{id}/retry` 成功创建新 queued task 后写 `automation.task.retried`。
  - `POST /api/tasks/{id}/run` 和内部 `run_automation_worker_once()` 终态写 `automation.task.succeeded`、`automation.task.failed` 或 `automation.task.cancelled_by_runner`。
  - `GET /api/tasks`、`GET /api/tasks/{id}`、claim/lease renew/heartbeat/worker loop idle、逐 step 成功失败不写 audit，避免噪声和 payload 泄露。
  - audit actor 固定为 `local_admin`；顶层 `profile_id` 指向目标 profile；metadata 只记录 `task_id/status/previous_status/step_count/step_types/runner_type/source_task_id/new_task_id/succeeded_step_count/failed_step_count/cancelled_step_count/reason_code` 等低敏字段。
  - metadata 不记录原始 steps、完整 result、error 原文、URL/query/fragment/host/path、selector、fill value、keyboard text、evaluate expression/result、screenshot、clipboard、console/network、headers、body、lease owner、profile dir、cookie/local storage、token、proxy URL、notes 或 Project Mileage 钱包/订单/权限/审计事实。
  - 新增 automation task audit 测试覆盖 create/cancel/retry/API run success/API run failure/running cancel request/worker terminal audit，并断言敏感 step payload 和 worker owner 不泄露。
  - 本小闭环只修改 CloakBrowser 本仓 automation task 审计，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 health check audit 小闭环：
  - `POST /api/profiles/{profile_id}/health/check` 主动检测完成后写 `profile.health_checked` audit event。
  - `GET /api/profiles/{profile_id}/health` 不写 audit，避免前端只读刷新产生噪声；missing profile 不写 audit，避免扫描 path 或伪造 ID 落库。
  - audit actor 固定为 `local_admin`；顶层 `profile_id` 指向目标 profile。
  - metadata 只记录 `status/warning_codes/warning_count/lookup_attempted/lookup_result/geoip_source/geoip_country_code/manual_*_override/runtime_status` 等低敏字段。
  - metadata 不记录 proxy URL、proxy host、proxy username/password、IP、timezone/locale 原文、warning message/action、异常 message、请求体、headers、token、cookie、`user_data_dir`、viewer URL、VNC 地址、automation URL 或 Project Mileage 钱包/订单/权限/审计事实。
  - 新增 health audit 测试覆盖成功 GeoIP、invalid proxy 未查询、GeoIP provider 失败、GET 不写 audit、missing profile 不写 audit，并断言 proxy/IP/异常/token/runtime URL 不泄露。
  - 本小闭环只修改 CloakBrowser 本仓 health check 审计，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 profile mutation audit 小闭环：
  - `POST /api/profiles` 成功后写 `profile.created` audit event。
  - `PUT /api/profiles/{id}` 成功后写 `profile.updated` audit event。
  - `DELETE /api/profiles/{id}` 成功后写 `profile.deleted` audit event。
  - audit actor 固定为 `local_admin`；顶层 `profile_id` 指向目标 profile；metadata 只记录 `name/platform/tag_count/updated_fields` 等低敏字段。
  - metadata 不记录 proxy URL、proxy username/password、notes、`user_data_dir`、runtime/viewer、cookie/local storage、请求体、错误详情或 Project Mileage 钱包/订单/权限/审计事实。
  - 新增 `test_profile_crud_api_writes_redacted_audit_events` 覆盖 create/update/delete audit 顺序、metadata 内容和 proxy/notes/runtime/viewer/profile dir 不泄露。
  - 既有 cookie/profile bundle audit 测试已调整为过滤 setup 阶段的 `profile.created`，继续验证 cookie/bundle 失败路径不写对应 export audit。
  - 本小闭环只修改 CloakBrowser 本仓 profile CRUD 审计，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 proxy mutation audit 小闭环：
  - `POST /api/proxies` 成功后写 `proxy.created` audit event。
  - `PUT /api/proxies/{id}` 成功后写 `proxy.updated` audit event。
  - `DELETE /api/proxies/{id}` 成功后写 `proxy.deleted` audit event。
  - audit actor 固定为 `local_admin`；metadata 只记录 `proxy_id/name/provider/country_code/tag_count/updated_fields` 等低敏字段。
  - metadata 不记录 proxy URL、username/password、notes、请求体、错误详情或 Project Mileage 钱包/订单/权限/审计事实。
  - 新增 `test_proxy_crud_api_writes_redacted_audit_events` 覆盖 create/update/delete audit 顺序、metadata 内容和 proxy password/host 不泄露。
  - 本小闭环只修改 CloakBrowser 本仓 proxy API 审计，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 WebSocket viewer token / origin / VNC token hash 验收收口小闭环：
  - runtime VNC `WebSocket /api/runtime/sessions/{id}/vnc` 已要求有效、未过期 viewer token；missing/wrong/expired token 会拒绝连接。
  - viewer token 明文只在 `POST /api/runtime/sessions/{id}/viewer-token` 响应中返回一次；DB 只保存 `viewer_token_hash`，对外 `RuntimeSessionResponse` 不暴露 hash。
  - terminate 会撤销 viewer token，renew 不延长既有短生命周期 viewer token。
  - WebSocket Origin 检查仍拒绝跨源浏览器连接，允许同源和无 Origin 的非浏览器客户端。
  - runtime viewer failure audit 只写固定 reason code，不记录 viewer token、viewer URL、token hash、Origin 原文、请求头、URL query、后端 VNC 地址或异常 message。
  - 本小闭环只更新 CloakBrowser 本仓安全验收文档，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 proxy password 响应脱敏验收收口小闭环：
  - 复核 `GET /api/proxies`、`GET /api/proxies/{id}`、create/update/check/bulk-check/assign/random-assign/profile-proxy-asset 等返回 `ProxyResponse` 的路径均统一走 `_proxy_response()`。
  - `_proxy_response()` 会调用 `redact_proxy_asset_url()`，响应中的 `proxy.url` 只保留 scheme、host 和 port，不回显 username/password。
  - proxy check 失败路径使用 `_safe_proxy_check_error()`，会替换完整 raw proxy URL 和 password 明文，`last_check_error` 不保存 proxy password。
  - `backend/tests/test_proxies.py` 已覆盖列表、详情、创建、更新、单个检查、批量检查、分配、随机分配和从 profile 保存 proxy asset 的响应不泄露 `hiddenpass`。
  - DB 内部仍保存完整 proxy URL，用于真实启动、健康检查和批量分配；该能力仍限定为 CloakBrowser 本地可信管理侧，不对 Project Mileage App 直连暴露。
  - 本小闭环只更新 CloakBrowser 本仓安全验收文档，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 10 审计、安全与权限，完成 `AUTH_TOKEN` 登录响应脱敏小闭环：
  - 保留当前单机本地部署 `AUTH_TOKEN` 模式，`Authorization: Bearer <AUTH_TOKEN>` 仍可访问受保护 API。
  - `/api/auth/login` 仍要求用户提交 token，并与 `AUTH_TOKEN` 做常量时间比对。
  - 登录成功 JSON 响应继续只返回 `{ ok: true }`，不返回 token、hash 或 session 细节。
  - 登录成功写入的 `auth_token` cookie 改为由 `AUTH_TOKEN` 派生的 `v1.<hmac-sha256>` 值，避免 `Set-Cookie` 响应头回显环境变量明文。
  - 认证中间件暂时兼容读取旧明文 cookie，避免本地已登录页面立即失效；新登录不再签发旧明文 cookie。
  - 新增 `test_login_correct_does_not_return_auth_token_in_response` 覆盖响应体、响应头和 cookie 值均不包含 `AUTH_TOKEN` 明文，并确认登录后 `/api/auth/status` 仍为 authenticated。
  - 本小闭环只修改 CloakBrowser 本仓认证实现和文档，不新增 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 Cookie JSON Playwright payload 修正与验收小闭环：
  - 修正 `backend/cookie_formats.py:CookieJsonCookie.to_playwright_cookie()`，`url` scoped cookie 转换为 Playwright payload 时只输出 `url`，不再同时输出默认 `path`；`domain` scoped cookie 继续输出 `domain + path`。
  - 根因是 Playwright `context.add_cookies()` 要求 cookie shape 在 `url` 和 `domain + path` 之间二选一；旧转换会让真实 browser context 报 `Cookie should have either url or path`。
  - 新增 `test_cookies_for_playwright_uses_url_or_domain_path_shape`，并同步 API import 测试期望。
  - Cookie JSON export 字段保留继续由格式层和 API export 测试覆盖；audit 仍只写低敏计数。
  - 使用本机一次性 HTTP server 和系统 Chrome 的 Playwright smoke 验证修复后的 URL scoped payload 可被 browser 接受，页面 `document.cookie` 可读到非 httpOnly cookie，`context.cookies()` 可导出 visible/httpOnly 两条 cookie。
  - 标准 Playwright Firefox 未安装，`invisible_playwright` 一次性 Firefox 验收在当前环境挂起并已清理临时进程；本轮不标 Firefox/invisible_playwright 浏览器 PASS。
  - 本小闭环不新增 API，不修改前端，不读取真实 profile dir，不接 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 stopped profile cookie storage 只读评估小闭环：
  - 新增 `docs/ai-docs/v1/stopped-profile-cookie-storage-evaluation.md`。
  - 评估结论是当前阶段不实现停止态 Firefox profile dir 的 `cookies.sqlite` 直接写入。
  - 现有 Cookie JSON / Netscape import 继续只支持 running profile，并通过 Playwright browser context `add_cookies()` 完成。
  - 文档明确直接写 stopped profile cookie 存储风险高于 browser context import，必须先验证 SQLite/WAL/SHM 一致性、Firefox schema、字段语义、去重覆盖、partition/origin attributes、备份/事务/rollback 和日志脱敏。
  - 当前禁止新增 stopped cookie import REST API，禁止在 stopped profile 上打开或写入 `cookies.sqlite`，禁止通过 bundle/archive import 写入 cookie 明文，禁止自动启动 profile 作为隐式副作用。
  - 本小闭环只更新 CloakBrowser 文档，不新增 API，不读取 profile dir，不读取 cookie DB，不接 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 profile dir archive 只读评估小闭环：
  - 新增 `docs/ai-docs/v1/profile-dir-archive-evaluation.md`。
  - 评估结论是当前阶段不实现 profile dir archive export/import API。
  - 未来如实现 export，必须只允许 stopped profile，要求独立 JSON boolean `include_profile_dir_archive` 和 `confirm_profile_dir_archive_export`；未确认时不读取 profile dir、不统计文件、不写 audit。
  - 未来如实现 import，必须创建新 profile、新 UUID 和新 `user_data_dir`，不能覆盖既有 profile 或解压到调用方指定目录。
  - 文档明确 allowlist 优先、denylist 必备，并要求拒绝路径穿越、绝对路径、重复路径、symlink、hardlink、设备文件、socket、FIFO、特殊权限位和超限 archive。
  - 未来 audit 只允许记录低敏统计和 `archive_manifest_hash`，不记录文件名明细、原始路径、URL、cookie/local storage/IndexedDB 内容、token、secret、proxy password 或 Project Mileage 业务事实。
  - 本小闭环只更新 CloakBrowser 文档，不新增 API，不读取 profile dir，不生成 archive，不接 Project Mileage DTO，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 running profile 当前 origin local storage bundle export 小闭环：
  - `POST /api/profiles/{profile_id}/bundle/export` 新增 `include_local_storage`、`confirm_local_storage_export` 和 `local_storage_page_ref`。
  - `include_local_storage` / `confirm_local_storage_export` 必须是 JSON boolean，不接受字符串或数字宽松转换。
  - 只有 `include_local_storage=true` 且 `confirm_local_storage_export=true` 时才读取指定 page 的 `window.localStorage`；未确认时返回固定 422，不读取 page、不写 audit。
  - profile 未运行返回固定 `404 Profile not running`；无 http/https origin 的页面返回固定 `400 Local storage origin unavailable`，不回显完整 URL。
  - 成功响应只记录当前 origin 的 `cloakbrowser.local-storage.v1` entries，origin 只含 scheme/host/port，不含 path/query/fragment；config-only 默认响应不输出 local storage `entries=null`、`origin=null` 或格式字段。
  - 成功写 `profile_bundle.local_storage_exported` 低敏 audit，metadata 只含格式/schema/entry_count/total_value_bytes/origin_hash，不含 key/value/origin 原文/URL query/fragment。
  - 本小闭环不导入 local storage、不读取停止态 profile dir、不使用 `context.storage_state()`、不扫描所有 tabs、不新增前端入口、不接 Project Mileage DTO、不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 local storage 只读评估小闭环：
  - 新增 `docs/ai-docs/v1/local-storage-bundle-readonly-evaluation.md`。
  - 评估结论是不采用 `context.storage_state()` 作为默认实现，不实现停止态 profile dir 读取。
  - 推荐后续最小实现只读取 running profile 指定 `page_ref` 当前 origin 的 `window.localStorage`。
  - 推荐 `include_local_storage`、`confirm_local_storage_export` 和 `local_storage_page_ref` 字段，boolean 必须严格 JSON boolean。
  - 推荐 audit 只写低敏计数和可选 `origin_hash`，不写 origin 原文、key、value、URL query 或 fragment。
  - 本小闭环只更新 CloakBrowser 文档，不新增 API、不读取 local storage 明文、不读取 profile dir、不接 Project Mileage DTO、不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 running profile cookie bundle export 小闭环：
  - `POST /api/profiles/{profile_id}/bundle/export` 新增 `include_cookies` 和 `confirm_cookie_export`。
  - 两个 flag 都必须是 JSON boolean，不接受字符串或数字宽松转换。
  - 只有 `include_cookies=true` 且 `confirm_cookie_export=true` 时才读取 running browser context `cookies()`；未确认时返回固定 422，不读取 context、不写 audit。
  - profile 未运行时返回固定 `404 Profile not running`，不读取停止态 Firefox profile dir。
  - 成功响应把 Cookie JSON v1 document 嵌入 `bundle.cookies.document`，并设置低敏 summary 和 `metadata.cookies_included=true`；config-only 默认响应不输出 `cookies.document: null`。
  - 成功写 `profile_bundle.cookie_exported` 低敏 audit，metadata 只含格式/schema/计数，不含 cookie value/name/domain/URL/query/fragment。
  - 本小闭环不导入 cookie、不导出 local storage、不读取 profile dir、不新增前端入口、不接 Project Mileage DTO、不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 Profile Bundle config import API 小闭环：
  - 新增 `POST /api/profiles/bundle/import`。
  - 10 审计安全阶段已补导入确认：该接口必须显式传入 JSON boolean `confirm_import: true`；缺失确认、`false` 或字符串 `"true"` 返回固定 `422 Profile bundle import requires explicit confirmation`，不创建新 profile。
  - 请求体只接受 `cloakbrowser.profile-bundle.v1` / `schema_version=1` bundle。
  - import 只读取 `bundle.profile.config`，复用既有 `ProfileConfigExport` / `ProfileCreate` 校验和 profile config 白名单字段。
  - 成功导入会创建新 profile、新 UUID、新 `user_data_dir`；不会覆盖既有 profile 或调用方传入的 `user_data_dir`。
  - 调用方附带的 cookies、local storage、profile dir archive、runtime/viewer/VNC/automation 字段、Project Mileage 钱包/订单/支付/权限/审计事实会被忽略，不导入、不回显。
  - 非法 bundle 固定返回 `422 Invalid profile bundle document`，不回显调用方 payload。
  - 本小闭环不读取磁盘 profile dir、不导入 cookie/local storage 明文、不写 audit、不新增前端入口、不接 Project Mileage DTO、不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 Profile Bundle config export API 小闭环：
  - 新增 `POST /api/profiles/{profile_id}/bundle/export`。
  - 请求体支持 `include_sensitive_proxy`，默认 `false`，必须是 JSON boolean，不接受字符串或数字宽松转换；route 级敏感 proxy 导出还必须同时传入 `confirm_sensitive_proxy_export=true`。
  - 成功响应返回 `profile_id` 和 `cloakbrowser.profile-bundle.v1` config-only `bundle`。
  - 默认 `profile.config` 只包含 `ProfileConfigExport` 白名单字段，proxy 默认脱敏；`cookies/local_storage/profile_dir` 均为 `included=false` 和低敏空统计。
  - endpoint 不读取磁盘 profile dir，不导出 cookie/local storage 明文，不写 audit，不新增前端入口，不实现 bundle import。
  - 无效请求体固定返回 `422 Invalid profile bundle export request`，不回显调用方 payload；profile 不存在返回 `404 Profile not found`。
  - 本小闭环不接 Project Mileage DTO、不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 Profile Bundle manifest/config-only 格式层小闭环：
  - 新增 `backend/profile_bundle.py` 和 `backend/tests/test_profile_bundle.py`。
  - 定义 `cloakbrowser.profile-bundle.v1` / `schema_version=1` 格式模型。
  - 新增 `build_profile_config_bundle()`，只构造 manifest/config-only bundle，不新增公开 API，不读取 profile dir。
  - `profile.config` 复用既有 `ProfileConfigExport` 白名单字段；默认 proxy 脱敏；内部 builder 只有显式 `include_sensitive_proxy=True` 才保留完整 proxy，公开 route 级导出还需要 `confirm_sensitive_proxy_export=true`。
  - 默认 bundle 只包含低敏 metadata、`cookies.included=false`、`local_storage.included=false`、`profile_dir.included=false` 和空统计。
  - 默认不包含 `user_data_dir`、Firefox profile dir 原始目录、cookie/local storage 明文、runtime/viewer/VNC/automation/lease 字段、Project Mileage 钱包/订单/支付/权限/审计事实或 secret/token。
  - `ProfileBundleDocument.profile` 设置为 `repr=False`，避免显式敏感 proxy 通过模型 repr 出现在测试失败或调试输出中。
  - 本小闭环不新增 REST API、不写 audit、不新增前端入口、不接 Project Mileage DTO、不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 Profile Bundle 边界与分阶段方案小闭环：
  - 新增 `docs/ai-docs/v1/profile-bundle-boundary-plan.md`。
  - 明确后续 bundle 采用 `cloakbrowser.profile-bundle.v1` manifest 思路，先从 config/metadata 低风险能力开始，不直接整目录打包。
  - 记录当前 `user_data_dir` / invisible_playwright `profile_dir` / Firefox startup cleanup / profile 删除行为。
  - 默认允许包含 profile config 白名单字段、cookie summary 和低敏 manifest metadata。
  - 默认禁止包含 `user_data_dir` 绝对路径、Firefox profile dir 原始目录、cookie/local storage 明文、browser cache/history/download/session restore/cert DB、runtime/viewer/VNC/automation/lease 字段、Project Mileage 钱包/订单/权限/支付/审计事实、`.env`、数据库 dump、secret、token 和 proxy password。
  - 显式敏感导出必须拆成独立 JSON boolean，不接受字符串或数字宽松转换。
  - 停止态 profile dir 当前只允许先做只读评估和 allowlist/denylist，不实现整目录 zip 导出/导入。
  - 后续切片拆为 manifest 格式层、bundle config export/import API、running cookie bundle、local storage 只读评估和 profile dir archive 评估。
  - 本小闭环只新增/更新 CloakBrowser 文档，不新增 API，不读取 profile dir，不导出 cookie/local storage 明文，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成前端 Netscape Cookie 管理入口小闭环：
  - `frontend/src/lib/api.ts` 新增 `api.importProfileCookiesNetscape(profileId, text)` 和 `api.exportProfileCookiesNetscape(profileId)`。
  - `api.importProfileCookiesNetscape()` 调用 `POST /api/profiles/{profile_id}/cookies/import/netscape`，请求体 `{ text }`。
  - `api.exportProfileCookiesNetscape()` 调用 `POST /api/profiles/{profile_id}/cookies/export/netscape`，请求体固定 `{ confirm_export: true }`。
  - `ProfileCookieManager` 新增 `JSON / Netscape` 双模式；切换模式会清空 textarea、notice、error 和 summary，避免 cookie 明文跨模式残留。
  - Cookie 管理入口仍只对 running profile 启用 import/export；stopped profile 不调用 JSON 或 Netscape cookie API。
  - Netscape import 成功或失败后清空 textarea；Netscape export 仍必须勾选显式确认。
  - Netscape export 响应里的 `text` 只用于下载 `.txt` 文件，不渲染到页面文本。
  - 页面与组件测试覆盖不渲染 cookie value、cookie name、domain、URL query、fragment 或 token。
  - 本小闭环只修改 CloakBrowser 本仓，不新增后端 API、不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 Netscape cookie REST API 小闭环：
  - 新增 `POST /api/profiles/{profile_id}/cookies/import/netscape`，请求体为 Netscape cookie 文件文本，解析后复用运行中 Playwright browser context `add_cookies()`。
  - 新增 `POST /api/profiles/{profile_id}/cookies/export/netscape`，必须显式传入 JSON boolean `confirm_export: true`，执行时从运行中 context `cookies()` 导出 Netscape cookie 文件文本。
  - import/export 都只允许运行中 profile；停止状态 profile 不读写 Firefox profile dir，不尝试直接修改磁盘 cookie 存储。
  - export 未显式确认时不读取 browser context、不写 audit；字符串或数字确认值不会被宽松转换。
  - export 成功沿用 `cookie.exported` audit 事件，metadata 只包含 `format/total_count/secure_count/session_count/persistent_count/http_only_count` 等低敏统计。
  - import/export 固定错误、logger warning 和 audit metadata 均不回显 cookie value、cookie name、domain、URL、query、fragment、原始 Netscape 行或 Playwright 原始异常 message。
  - Cookie JSON import 和 Netscape import 对无效请求形状都返回固定错误，不使用 FastAPI 默认 validation response 回显原始 input。
  - Netscape export 响应里的 `text` 包含 cookie 明文，因此该 API 仅限 CloakBrowser 可信本地管理侧并要求显式确认。
  - 本小闭环不新增前端入口、不接 Project Mileage DTO、不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
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
  - 10 审计安全阶段已补导入确认：该接口必须显式传入 JSON boolean `confirm_import: true`；缺失确认、`false` 或字符串 `"true"` 返回固定 `422 Profile config import requires explicit confirmation`，不创建 profile、不写 import audit。
  - 请求体固定 `schema_version=1`，`configs[]` 为 profile config JSON 数组。
  - 每条 config 只从白名单字段创建 profile：`name/fingerprint_seed/proxy/timezone/locale/platform/user_agent/screen_width/screen_height/gpu_vendor/gpu_renderer/hardware_concurrency/humanize/human_preset/headless/geoip/clipboard_sync/auto_launch/color_scheme/launch_args/notes/tags`。
  - 调用方附带的 cookie、local storage、profile dir、`user_data_dir`、runtime session、viewer token、VNC token、automation task、wallet/order/payment/permission/Project Mileage 业务字段不会被导入、写库或回显。
  - 有效 config 创建新 profile；无效 config 返回行级 `ok=false` 和校验错误，不阻塞同批其他有效 config。
  - `schema_version` 非 `1` 时整体返回 `422`，不产生数据库副作用。
  - 支持从 `POST /api/profiles/export` 的 `config` 结果 round-trip 导入；若导出时同时传入 `include_sensitive: true` 和 `confirm_sensitive_export: true`，proxy 凭证会按可信本地管理 API 语义随 config 导入。
  - 本小闭环不新增前端入口、不写 audit、不导入 cookie/local storage/profile dir、不接 Project Mileage DTO。
  - 本小闭环只修改 CloakBrowser 本仓，不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
- 本轮继续 08 Cookie、Profile 导入导出，完成 profile config export 敏感字段默认脱敏小闭环：
  - 既有 `POST /api/profiles/export` 支持 `include_sensitive`，默认 `false`。
  - `include_sensitive` 必须是 JSON boolean，不接受字符串或数字宽松转换。
  - 默认导出的 `config.proxy` 会移除 `username:password@`，只保留 scheme、host、port。
  - 显式 `include_sensitive: true` 且 `confirm_sensitive_export: true` 时，才返回完整 proxy URL，用于可信本地管理侧明确选择导出敏感配置。
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

## 2026-05-28 当前小闭环记录

- 本轮参考旧仓 `/home/jeff/local/repos/CloakBrowser`，完成 CloakBrowser 自仓 VNC 大画面与无 proxy GeoIP 复刻收口。
- GeoIP：
  - 当前本仓已有无 proxy 直连 GeoIP 路径；新增测试明确启动链路在 `geoip=true` 且无 proxy/timezone/locale 时调用 `resolve_network_geo(None)`。
  - 启动成功后仍只把 `last_geoip_*` 低敏结果写入 profile，不把 IP、proxy、URL、headers 或异常原文写入 audit metadata。
- VNC/浏览器尺寸：
  - `backend/browser_manager.py` 将 1080p 可用高度对齐旧仓 Windows 口径为 `1032`。
  - Firefox 启动完成后通过 X11 `xdotool` 做 best-effort 窗口移动和尺寸整理；用户传入的 `--width`、`--height`、`--window-size` 会被过滤，避免覆盖管理器尺寸。
  - `Dockerfile` 新增 `xdotool` runtime 依赖。
  - `frontend/src/App.tsx` 在 running profile viewer 模式隐藏左侧 profile 列表，让 VNC 主画面占满主工作区。
  - `frontend/src/components/ProfileViewer.tsx` 新增受控 `All profiles` 返回入口。
- 真实容器 smoke：
  - 新镜像 `invisible-browser-manager:vnc-geoip-window-fix` 已构建成功，服务运行在 `http://127.0.0.1:18082`。
  - 创建无 proxy profile 后，未确认 launch 返回 `422 Profile launch requires explicit confirmation`；带 `{"confirm_launch": true}` 后 4.55 秒启动成功。
  - profile 写入 `last_geoip_*`：`US / America/Los_Angeles / en-US / ip-api`。
  - 容器内 `Xvnc` 为 `-geometry 1920x1080`；`xdotool` 可用；Firefox 可见窗口为 `Position: 0,0`、`Geometry: 1920x1080`；Firefox 主进程没有保留用户传入的 `--width=800` / `--height 600`。
  - 浏览器 UI 验收：viewer 页面非空白，连接态为 `Connected`，canvas 后端帧为 `1920x1080`，当前 1440x1000 viewport 下显示约 `1440x810`，左侧 profile list/table 在 viewer 模式隐藏，`All profiles` 可返回列表。
- 验证：
  - `. .venv/bin/activate && python -m pytest backend/tests -q` -> `479 passed in 28.65s`。
  - `cd frontend && npm test -- --run` -> `15 files passed, 214 tests passed`。
  - `cd frontend && npm run build` -> `tsc -b && vite build` 成功。
  - `git diff --check` -> passed。
- 本轮不修改 Project Mileage app/payload；当前没有 Project Mileage 配合需求。
