# 05 Project Mileage 会话 Broker

## 目标

设计并实现 CloakBrowser 与 Project Mileage Payload 之间的受控 runtime session API，为用户端远程工作台和运营远程监控提供底层会话能力。

## 重要边界

本模块进入实现前，必须确认 Project Mileage 的 Contract Change Proposal 或任务级契约。

禁止：

- CloakBrowser 直接扣 Project Mileage 用户钱包。
- CloakBrowser 直接判断用户订单是否有效。
- App 前端直接调用 runtime service API。

## 预计新增

CloakBrowser：

- `backend/session_broker.py`
- `backend/tests/test_session_broker.py`
- runtime session API。

Project Mileage Payload：

- remote session API。
- wallet billing。
- audit。

Project Mileage App：

- remote workspace adapter。
- remote monitor adapter。

## 任务清单

- [x] 定义 service token：
  - `RUNTIME_SERVICE_TOKEN`
  - 仅 Payload 侧持有。
- [x] 定义 `POST /api/runtime/sessions`：
  - 输入 business session id。
  - 输入 requested profile id 或 template id。
  - 输入 lease seconds。
  - 返回 runtime session id。
- [x] 定义 `GET /api/runtime/sessions/{id}`。
- [x] 定义 `POST /api/runtime/sessions/{id}/viewer-token`：
  - 返回短生命周期 viewer token。
- [x] 定义 `POST /api/runtime/sessions/{id}/terminate`。
- [ ] 定义 `POST /api/runtime/sessions/{id}/renew`。
- [x] 设计 runtime session 表：
  - id。
  - profile_id。
  - external_session_id。
  - status。
  - lease_expires_at。
  - viewer_token_hash。
  - created_at。
  - updated_at。
- [x] session 创建时如果 profile 未运行，启动 profile。
- [x] session 终止时撤销 viewer token 并让 runtime VNC 访问失效。
- [x] viewer token 过期后不能进入 VNC。
- [ ] 所有 service API 写 audit。
- [ ] Payload 侧确认授权、扣费、续期后再调用 runtime API。

## 验证

CloakBrowser：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
```

Project Mileage 跨仓阶段：

```bash
cd /home/jeff/code/project-mileage-v3-payload && pnpm vitest run <remote-session-tests>
cd /home/jeff/code/project-mileage-v3-app && pnpm test <remote-workspace-tests>
```

## 验收标准

- [x] 无 service token 不能创建 runtime session。
- [x] viewer token 短生命周期有效。
- [x] 过期 token 无法连接。
- [x] 终止 session 后 VNC 访问失效。
- [x] Runtime session 不包含用户钱包逻辑。

## 2026-05-26 历史接力状态：CloakBrowser 侧最小 runtime session API 红灯测试草稿

当前状态：

- 本节是 2026-05-26 的历史接力状态，已被 2026-05-27 最小 runtime session API 小闭环接续。
- 已开始 05，但只推进 CloakBrowser 侧 runtime service 契约，不进入 Project Mileage 跨仓实现。
- 当时新增测试草稿：`backend/tests/test_session_broker.py`。
- 当时测试尚未运行，生产代码尚未实现。

测试草稿覆盖的最小闭环：

- `RUNTIME_SERVICE_TOKEN` 通过 `X-Runtime-Service-Token` header 校验。
- 无 service token 不能创建 runtime session。
- `POST /api/runtime/sessions` 可用既有 `profile_id` 创建 runtime session。
- 如果 profile 未运行，创建 session 时调用 `browser_mgr.launch(profile)`。
- `GET /api/runtime/sessions/{id}` 返回已创建 session。
- `POST /api/runtime/sessions` 可用 `template_id` 创建 profile，再创建 runtime session。
- `profile_id` 和 `template_id` 缺失或同时存在时返回 `422`。
- Runtime session response 不包含 `wallet`、`order`、`billing` 字段。

当时下一步：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
```

当时预期为红灯，因为以下生产能力尚未实现：

- `RUNTIME_SERVICE_TOKEN`。
- `runtime_sessions` 表。
- runtime session DB CRUD。
- `POST /api/runtime/sessions`。
- `GET /api/runtime/sessions/{id}`。

当时实现建议：

- 新增 `backend/session_broker.py` 放 service token 校验和 runtime session helper/router。
- 在 `backend/models.py` 新增 runtime session request/response model。
- 在 `backend/database.py` 新增 `runtime_sessions` 表和最小 CRUD。
- 在 `backend/main.py` include runtime router；如果 `AUTH_TOKEN` 启用，`/api/runtime/*` 需要允许 runtime service token 自己鉴权，避免被 UI auth middleware 先拦截。

边界：

- 不改 Project Mileage app/payload。
- 不在 CloakBrowser 做钱包、订单、用户权限判断。
- 不让 Project Mileage 前端绕过 Payload 直接访问 CloakBrowser runtime API。
- viewer token、terminate、renew、audit、Payload 授权扣费联动留给后续小闭环。

## 2026-05-27 CloakBrowser 侧最小 runtime session API 小闭环

当前状态：

- 已完成并提交测试覆盖的 CloakBrowser 侧最小 runtime session API。
- 05 模块整体仍未完成：terminate、renew、audit、Payload 授权扣费联动尚未实现，因此 `tasks/progress.md` 中 05 仍保持未勾选。

已完成：

- `backend/models.py`
  - 新增 `RuntimeSessionCreate`。
  - 新增 `RuntimeSessionResponse`。
  - 校验 `profile_id` 与 `template_id` 必须且只能提供一个。
  - Runtime session API 响应不暴露内部 `viewer_token_hash`。
- `backend/database.py`
  - 新增 `runtime_sessions` 表。
  - 新增 `create_runtime_session()`。
  - 新增 `get_runtime_session()`。
- `backend/main.py`
  - 新增 `RUNTIME_SERVICE_TOKEN`。
  - `AuthMiddleware` 对 `/api/runtime/*` 放行到 runtime service token 自身鉴权，避免 UI `AUTH_TOKEN` 抢先拦截。
  - 新增 `POST /api/runtime/sessions`。
  - 新增 `GET /api/runtime/sessions/{session_id}`。
  - 从 `template_id` 创建 runtime profile 时复制 template 指纹字段，并命名为 `Runtime <external_session_id>`。
  - 创建 runtime session 时如果 profile 未运行，会调用 `browser_mgr.launch(profile)`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 5 passed
```

## 2026-05-27 Runtime viewer token 小闭环

当前状态：

- 已完成 CloakBrowser 侧 runtime viewer token 小闭环。
- 该小闭环只提供 runtime service API 和 runtime VNC token 校验，不进入 Project Mileage app/payload 跨仓实现。

已完成：

- `backend/tests/test_session_broker.py`
  - 新增 viewer token TDD 覆盖。
  - 覆盖无 runtime service token 不能颁发 viewer token。
  - 覆盖不存在 session 返回 404。
  - 覆盖 viewer token response 不包含 wallet/order/billing，也不暴露 `viewer_token_hash`。
  - 覆盖 DB 只保存 token hash 和过期时间，不保存明文 token。
  - 覆盖缺失、错误、过期 viewer token 无法连接 runtime VNC。
  - 覆盖跨域 Origin 即使带有效 viewer token 也无法连接 runtime VNC。
  - 覆盖有效 viewer token 可连接 `/api/runtime/sessions/{id}/vnc` 并代理到对应 profile 的 KasmVNC websockify。
- `backend/models.py`
  - 新增 `RuntimeViewerTokenCreate`。
  - 新增 `RuntimeViewerTokenResponse`。
- `backend/database.py`
  - `runtime_sessions` 新增 `viewer_token_expires_at` 字段和迁移。
  - 新增 `set_runtime_session_viewer_token()`。
- `backend/main.py`
  - 新增 `POST /api/runtime/sessions/{session_id}/viewer-token`。
  - 新增 `WebSocket /api/runtime/sessions/{session_id}/vnc`。
  - viewer token 使用随机明文返回给调用方，DB 仅保存 sha256 hash。
  - runtime VNC 路径校验同源 Origin、session active、lease 未过期、viewer token hash、viewer token 过期时间和 profile running。
  - 抽出 `_proxy_running_vnc()`，让既有 `/api/profiles/{profile_id}/vnc` 与 runtime VNC 路径复用同一 VNC 代理逻辑。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 11 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_ws_rejects_cross_origin backend/tests/test_api.py::test_ws_allows_same_origin backend/tests/test_api.py::test_ws_allows_no_origin backend/tests/test_api.py::test_vnc_proxy_connects_websockify_path -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 268 passed

git diff --check
# passed
```

仍未完成：

- `POST /api/runtime/sessions/{id}/renew`。
- runtime audit。
- Project Mileage Payload 侧授权、扣费、续期后调用 runtime API。

## 2026-05-27 Runtime session terminate 小闭环

当前状态：

- 已完成 CloakBrowser 侧 runtime session terminate 小闭环。
- 当前 terminate 策略是：将 session 标记为 `terminated`，清空 viewer token hash 和过期时间，使 runtime VNC 访问失效；不自动 stop profile。profile 停止/lease 释放策略留给后续更完整的 session lease 管理，避免误杀未来可能共享同一 profile 的其他业务会话。

已完成：

- `backend/tests/test_session_broker.py`
  - 新增 terminate TDD 覆盖。
  - 覆盖无 runtime service token 不能 terminate。
  - 覆盖不存在 session 返回 404。
  - 覆盖 terminate 后 response 不暴露 `viewer_token_hash`。
  - 覆盖 terminate 后 DB status 为 `terminated`，viewer token hash 和过期时间被清空。
  - 覆盖 terminate 后原 viewer token 无法继续连接 runtime VNC。
- `backend/database.py`
  - 新增 `terminate_runtime_session()`。
- `backend/main.py`
  - 新增 `POST /api/runtime/sessions/{session_id}/terminate`。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 14 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 271 passed

git diff --check
# passed
```

仍未完成：

- `POST /api/runtime/sessions/{id}/renew`。
- runtime audit。
- Project Mileage Payload 侧授权、扣费、续期后调用 runtime API。
