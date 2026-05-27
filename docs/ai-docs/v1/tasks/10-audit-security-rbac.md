# 10 审计、安全与权限

## 目标

建立适合远程浏览器平台的安全基线：认证、权限、敏感字段遮蔽、审计、token 生命周期和高风险操作保护。

## 任务清单

### Auth

- [x] 保留当前 `AUTH_TOKEN` 本地部署模式：
  - `Authorization: Bearer <AUTH_TOKEN>` 继续可访问受保护 API。
  - `/api/auth/login` 仍使用用户输入 token 与 `AUTH_TOKEN` 做常量时间比对。
  - 登录成功后写入的 `auth_token` cookie 改为由 `AUTH_TOKEN` 派生的 `v1.<hmac-sha256>` 值，避免 `Set-Cookie` 响应头回显环境变量明文。
  - 为避免本地已登录页面立刻失效，认证中间件暂时兼容读取旧明文 cookie；新登录不会再签发旧明文 cookie。
- [x] 新增 service token，用于 Payload 调用 runtime API：
  - `RUNTIME_SERVICE_TOKEN` 作为 runtime service API 专用凭证。
  - runtime service API 只接受 `X-Runtime-Service-Token`，不接受 `AUTH_TOKEN` bearer 或 `auth_token` cookie。
  - 普通受保护 `/api/*` local admin API 只接受 `AUTH_TOKEN` bearer 或 `auth_token` cookie，不接受 `X-Runtime-Service-Token`。
  - `/api/auth/status` 会忽略 runtime service token，不把它当作登录态。
  - 当前测试覆盖 service token 与 local admin token/cookie 的双向隔离。
- [ ] 区分 user API、admin API、service API：
  - 当前已完成 local admin API 与 runtime service API 的 token 隔离。
  - 当前尚未实现 viewer/operator/admin 多角色 RBAC；Project Mileage 业务权限仍必须以后续 Payload DTO 为准。
- [x] WebSocket viewer token 校验：
  - runtime VNC `WebSocket /api/runtime/sessions/{id}/vnc` 要求有效、未过期 viewer token。
  - missing/wrong/expired viewer token 会拒绝连接并写低敏 `runtime.viewer.failed` reason code，不记录 token 明文、URL query、viewer URL 或 token hash。

### Sensitive Data

- [x] proxy password 列表遮蔽：
  - `GET /api/proxies`、`GET /api/proxies/{id}`、create/update/check/bulk-check/assign/random-assign/profile-proxy-asset 等返回 `ProxyResponse` 的路径统一通过 `_proxy_response()` 调用 `redact_proxy_asset_url()`。
  - 响应中的 `proxy.url` 只保留 scheme、host 和 port，不回显 username/password。
  - proxy check 失败时 `last_check_error` 也会替换完整 raw proxy URL 和 password 明文。
  - DB 内部仍保存完整 proxy URL，用于真实启动、健康检查和批量分配；这是 CloakBrowser 本地可信管理侧能力，不对 Project Mileage App 直连暴露。
- [x] audit metadata 不记录敏感字段：
  - 当前已覆盖 runtime service audit metadata。
  - 已禁止 viewer token、viewer URL、viewer token hash、runtime service token、proxy URL/password、cookie 等进入 audit metadata。
- [x] API response 不返回 AUTH_TOKEN：
  - `/api/auth/status` 只返回 `auth_required` / `authenticated`。
  - `/api/auth/login` 成功 JSON 只返回 `{ ok: true }`。
  - 登录成功 `Set-Cookie` 不再包含 `AUTH_TOKEN` 明文。
- [x] cookie 导出不写日志：
  - JSON cookie export、Netscape cookie export 和 profile bundle cookie export 的成功路径不写 logger。
  - 以上 cookie export 失败路径只返回固定错误，不写 manager logger，不写失败 audit，不记录异常类型、profile id、cookie value、cookie name、domain、URL、query 或 fragment。
  - 成功路径 audit 仅写低敏计数 metadata。
- [x] VNC token hash 存储，不存明文：
  - viewer token 明文只在 `POST /api/runtime/sessions/{id}/viewer-token` 响应中返回一次。
  - `runtime_sessions.viewer_token_hash` 只保存 hash，且对外 `RuntimeSessionResponse` 不暴露 hash。
  - terminate 会撤销 viewer token，renew 不延长既有短生命周期 viewer token。

### Audit

- [x] 新增 audit_events 表。
- [x] profile mutation 写 audit：
  - `POST /api/profiles` 成功写 `profile.created`。
  - `PUT /api/profiles/{id}` 成功写 `profile.updated`。
  - `DELETE /api/profiles/{id}` 成功写 `profile.deleted`。
  - actor 固定为 `local_admin`；顶层 `profile_id` 指向目标 profile。
  - metadata 只含 `name/platform/tag_count/updated_fields` 等低敏字段。
  - metadata 不记录 proxy URL、proxy username/password、notes、`user_data_dir`、runtime/viewer、cookie/local storage、请求体、错误详情或 Project Mileage 业务字段。
- [x] proxy mutation 写 audit：
  - `POST /api/proxies` 成功写 `proxy.created`。
  - `PUT /api/proxies/{id}` 成功写 `proxy.updated`。
  - `DELETE /api/proxies/{id}` 成功写 `proxy.deleted`。
  - actor 固定为 `local_admin`；metadata 只含 `proxy_id/name/provider/country_code/tag_count/updated_fields` 等低敏字段。
  - metadata 不记录 proxy URL、username/password、notes、请求体、错误详情或 Project Mileage 业务字段。
- [x] health check 写 audit：
  - `POST /api/profiles/{profile_id}/health/check` 完成主动检测后写 `profile.health_checked`。
  - `GET /api/profiles/{profile_id}/health` 仍是只读派生计算，不写 audit，避免前端自动刷新产生噪声。
  - missing profile 不写 audit，避免扫描 path 或伪造 ID 落库。
  - actor 固定为 `local_admin`；顶层 `profile_id` 指向目标 profile。
  - metadata 只含 `status/warning_codes/warning_count/lookup_attempted/lookup_result/geoip_source/geoip_country_code/manual_*_override/runtime_status` 等低敏字段。
  - metadata 不记录 proxy URL、proxy host、proxy username/password、IP、timezone/locale 原文、warning message/action、异常 message、请求体、headers、token、cookie、`user_data_dir`、viewer URL、VNC 地址、automation URL 或 Project Mileage 业务字段。
- [x] bulk action 写 audit：
  - `POST /api/profiles/import` 至少成功创建 1 个 profile 后写 `profile.imported` 汇总 audit。
  - `POST /api/profiles/export` 至少成功导出 1 个 profile config 后写 `profile.config_exported` 汇总 audit。
  - `POST /api/profiles/config/import` 至少成功创建 1 个 profile 后写 `profile.config_imported` 汇总 audit。
  - `POST /api/proxies/bulk/check` 至少检查到 1 个真实 proxy 后写 `proxy.bulk_checked` 汇总 audit。
  - `POST /api/proxies/{proxy_id}/assign` 至少成功分配 1 个 profile 后写 `proxy.assigned` 汇总 audit。
  - `POST /api/proxies/assign/random` 至少成功分配 1 个 profile 后写 `proxy.random_assigned` 汇总 audit。
  - `POST /api/profiles/import/preview`、列表读取、逐项 missing 失败、没有真实成功/检查动作的请求不写 bulk audit。
  - metadata 只含 source format、schema version、include_sensitive boolean、total/requested/counts、proxy/profile/candidate/tag 计数、provider/country_code 和 proxy/preset id 等低敏汇总字段。
  - metadata 不记录 CSV 原文、导出 config 内容、proxy URL/host/username/password、notes、last_check_error、IP、timezone/locale 原文、cookie/local storage、token、headers、路径或 Project Mileage 业务字段。
- [x] automation task 写 audit：
  - `POST /api/tasks` 成功创建 queued task 后写 `automation.task.created`。
  - `POST /api/tasks/{id}/cancel` 对 queued task 成功终止写 `automation.task.cancelled`；对 running task 成功接受协作取消写 `automation.task.cancel_requested`。
  - `POST /api/tasks/{id}/retry` 成功创建新 queued task 后写 `automation.task.retried`。
  - `POST /api/tasks/{id}/run` 同步 runner 终态写 `automation.task.succeeded`、`automation.task.failed` 或 `automation.task.cancelled_by_runner`。
  - 内部 `run_automation_worker_once()` worker 终态同样写任务级低敏 audit。
  - `GET /api/tasks`、`GET /api/tasks/{id}`、claim/lease renew/heartbeat/worker loop idle、逐 step 成功失败不写 audit，避免噪声和 payload 泄露。
  - metadata 只含 `task_id/status/previous_status/step_count/step_types/runner_type/source_task_id/new_task_id/succeeded_step_count/failed_step_count/cancelled_step_count/reason_code` 等低敏字段。
  - metadata 不记录原始 steps、完整 result、error 原文、URL/query/fragment/host/path、selector、fill value、keyboard text、evaluate expression/result、screenshot、clipboard、console/network、headers、body、lease owner、profile dir、cookie/local storage、token、proxy URL、notes 或 Project Mileage 业务字段。
- [x] runtime session 写 audit：
  - 当前已覆盖 runtime service API 成功动作。
  - 当前已覆盖 runtime VNC 成功 connected/disconnected。
  - 当前已覆盖 runtime VNC 失败 reason code。
  - failure metadata 仅记录固定 `reason_code`，不记录 viewer token、viewer URL、token hash、Origin 原文、请求头、URL query、后端 VNC 地址或异常 message。

### RBAC 远期设计

- [x] 单机版先支持 admin：
  - 单机本地管理侧继续使用 `AUTH_TOKEN` 作为 local admin 凭证。
  - audit actor 仍固定为 `local_admin`。
- [ ] 后续支持 viewer/operator/admin。
- [ ] Project Mileage 权限以 Payload roles 为准。
- [ ] CloakBrowser 内部 RBAC 不替代 Payload 业务权限。

## 验证

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_auth.py backend/tests/test_session_broker.py -q
cd frontend && npm test -- --run
```

## 验收标准

- [x] 未授权不能访问 protected API。
- [x] runtime service API 与 local admin API token 隔离。
- [x] WebSocket origin 检查不退化。
- [x] audit 中没有 proxy password、cookie value、token。
- [ ] 删除、导出、终止等高风险操作有确认或权限限制：
  - [x] `DELETE /api/profiles/{profile_id}` 后端强制要求 JSON boolean `confirm_delete: true`。
  - [x] 缺失确认、`false` 或字符串 `"true"` 返回固定 `422 Profile delete requires explicit confirmation`，不停止运行 profile、不删除 DB、不删除 `user_data_dir`、不写 delete audit。
  - [x] 前端 `api.deleteProfile()` 固定发送 `{ confirm_delete: true }`，保留既有 UI 删除确认。
  - [ ] 其余 delete/export/terminate 类高风险操作仍需按风险逐项补齐后端确认或权限限制。
