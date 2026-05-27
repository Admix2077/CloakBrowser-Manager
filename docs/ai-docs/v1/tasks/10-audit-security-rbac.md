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
- [ ] 新增 service token，用于 Payload 调用 runtime API。
- [ ] 区分 user API、admin API、service API。
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
- [ ] cookie 导出不写日志。
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
- [ ] bulk action 写 audit。
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

- [ ] 单机版先支持 admin。
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
- [x] WebSocket origin 检查不退化。
- [x] audit 中没有 proxy password、cookie value、token。
- [ ] 删除、导出、终止等高风险操作有确认或权限限制。
