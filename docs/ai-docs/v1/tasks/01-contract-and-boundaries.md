# 01 契约边界与事实源

## 目标

明确 `cloakbrowser-invisible-manager`、`project-mileage-v3-app`、`project-mileage-v3-payload` 的职责边界，避免后续远程工作台集成时把业务授权、钱包扣费和浏览器 runtime 混在一起。

## 输入

- `../proposal.md`
- `../high-level-design.md`
- `../detailed-design.md`
- `../2026-05-25-session-memory.md`
- `/home/jeff/code/project-mileage-v3-app/doc/tasks-v1/15-inventory-airline-services.md`
- `/home/jeff/code/project-mileage-v3-payload/doc/tasks/api-contract.md`

## 输出

- 本模块完成后，应形成可实现的 runtime API 契约草案。
- 如果进入 Project Mileage 跨仓实现，必须先把契约同步到 app/payload 对应任务文档或 Contract Change Proposal。

## 当前结论

本模块只冻结契约边界和 runtime API 草案，不进入 Project Mileage 跨仓实现。当前 Project Mileage 远程工作台、VNC 页面和运营远程监控仍保持安全占位；解除占位前必须先在 Payload/API contract 或 Contract Change Proposal 中确认用户授权、订单/账号映射、钱包扣费、VNC token 生命周期、审计 metadata 和异常恢复策略。

## 当前事实证据

- Payload API contract 当前已确认接口清单不包含远程工作台、remote session、VNC 或 viewer token；远程工作台仍归“待补接口”，未实现时只能走真实路径返回 `404` / `501`，不得由 adapter 伪造成功。
  - `/home/jeff/code/project-mileage-v3-payload/doc/tasks/api-contract.md`
- App 进度文档明确 `/app/remote-workspace`、`/app/remote-workspace/[id]/vnc` 和 `/ops/remote-monitor` 已从 preview-only 收敛为安全未接入状态，远程账号列表、会话激活、续期、屏幕流、控制 mutation、VNC token 生命周期、钱包扣费、审计 metadata 均未确认。
  - `/home/jeff/code/project-mileage-v3-app/doc/tasks/progress-v1.md`
  - `/home/jeff/code/project-mileage-v3-app/doc/tasks-v1/15-inventory-airline-services.md`
- App 当前页面只展示“待契约/暂未接入”，关键动作保持 disabled；源码守卫禁止 P2 占位页重新出现直接 `fetch`、`/api/`、`VNC_TOKEN`、`vncToken`、`password`、`privateKey`、`providerSecret`、`exec(` 或 `spawn(` 等敏感/执行能力。
  - `/home/jeff/code/project-mileage-v3-app/app/app/remote-workspace/page.tsx`
  - `/home/jeff/code/project-mileage-v3-app/app/app/remote-workspace/[id]/vnc/page.tsx`
  - `/home/jeff/code/project-mileage-v3-app/app/ops/remote-monitor/page.tsx`
  - `/home/jeff/code/project-mileage-v3-app/app/p2-placeholders-source.test.ts`
- 账号商品 DTO/API contract 当前未确认远程接管、VNC 会话、远程加购或会话扣费字段；不能由库存可用、frontend-lab preview 或 UI 展示派生 `remoteSupported` / `vncEnabled`。
  - `/home/jeff/code/project-mileage-v3-app/doc/ui-absorption-contracts/ops-inventory-airline-services.md`
- CloakBrowser 当前已实现单机 runtime 基础：可选单 `AUTH_TOKEN`、profile CRUD、单 profile launch/stop/status、KasmVNC/noVNC WebSocket 代理、Automation REST API 和 launch 时 GeoIP 解析并写入 `last_geoip_*`。这些能力是 05 Session Broker 的底座，但还不是 Project Mileage remote session API。
  - `backend/main.py`
  - `backend/browser_manager.py`
  - `backend/database.py`
  - `backend/models.py`
- CloakBrowser 当前没有公开 CDP API/URL；已有测试明确要求 profile/list/status 不暴露 `cdp_url` 且 `/cdp*` 返回 404。后续自动化契约必须继续以 Firefox / `invisible_playwright` / Automation REST API 为准。
  - `backend/tests/test_api.py`
- CloakBrowser 当前 auth 不是多用户 RBAC：只有环境变量 token、Bearer/cookie 校验；runtime 状态存在 `BrowserManager.running` 内存字典中，未持久化为可跨进程恢复的 session 表。
  - `backend/main.py`
  - `backend/browser_manager.py`

## 任务清单

- [x] 梳理三仓职责边界：
  - CloakBrowser：runtime、profile、VNC、Automation、GeoIP、proxy、health。
  - Payload：auth、roles、wallet、orders、remote session authorization、audit。
  - App：用户远程工作台、运营远程监控、viewer 页面。
- [x] 定义数据事实源：
  - profile runtime 状态由 CloakBrowser 提供。
  - 用户是否能访问远程账号由 Payload 决定。
  - 钱包扣费和续期由 Payload 决定。
  - VNC viewer access 由 CloakBrowser 签发，但必须由 Payload 请求。
- [x] 设计 service-to-service 调用方式：
  - Payload 调用 CloakBrowser runtime API。
  - 使用 `RUNTIME_SERVICE_TOKEN` 或等价内部 token。
  - 用户浏览器不能直接调用 service API。
- [x] 设计远程 session 状态机：
  - `requested`
  - `authorized`
  - `starting`
  - `active`
  - `idle`
  - `expired`
  - `terminated`
  - `failed`
- [x] 定义敏感字段白名单：
  - 不返回 proxy password。
  - 不返回 cookie value。
  - 不返回 VNC 原始 token。
  - 不返回账号密码。
  - 不返回内部 AUTH_TOKEN。
- [x] 定义审计事件清单：
  - remote_session.requested。
  - remote_session.started。
  - remote_session.viewer_issued。
  - remote_session.renewed。
  - remote_session.terminated。
  - remote_session.failed。
  - profile.launch。
  - profile.stop。
  - proxy.check。
- [x] 明确 Project Mileage 安全占位解除条件：
  - Payload session API 已确认。
  - App adapter 已接真实 API。
  - VNC token 生命周期已确认。
  - 钱包扣费策略已确认。
  - 审计 metadata 已确认。

## 三仓职责边界

| 仓库 | 负责 | 不负责 |
|---|---|---|
| `cloakbrowser-invisible-manager` | browser runtime、profile、fingerprint、GeoIP、proxy、health、VNC runtime、Automation REST API、runtime session lease、viewer access 签发和 runtime audit。 | 不判断 Project Mileage 用户是否有权访问账号；不扣钱包；不决定订单归属；不返回账号密码、cookie 明文、proxy 密码或 VNC 原始 token 给业务前端。 |
| `project-mileage-v3-payload` | 用户认证、角色/权限、账号订单、账号库存、钱包扣费/续期、远程账号授权、remote session 业务状态机、业务审计和安全 DTO 白名单。 | 不承载浏览器内核；不保存浏览器 cookie 明文；不把底层 profile secrets 或 VNC token 明文暴露给 App。 |
| `project-mileage-v3-app` | 用户端远程工作台、受控 viewer 页面、运营端远程监控、真实 Payload API adapter 和浏览器验收。 | 不直接调用 CloakBrowser runtime service API；不伪造 VNC token、模拟远程画面、本地倒计时成功态或本地权限。 |

## 数据事实源

| 数据 | 事实源 | 说明 |
|---|---|---|
| profile 配置、profile runtime status、VNC runtime、Automation runtime | CloakBrowser | 状态包括 `stopped`、`launching`、`running`、`stopping`、`failed`；业务系统只能读取安全摘要。 |
| 指纹参数、GeoIP 检测、proxy 检测、health warnings | CloakBrowser | 可被 Payload/运营端引用，但不替代业务授权。 |
| 用户身份、角色、权限、账号订单、账号库存、钱包余额、扣费、续期 | Payload | CloakBrowser 不读取也不修改这些业务事实。 |
| remote session 业务状态 | Payload | Payload 决定 `requested` 到 `failed` 的业务状态；CloakBrowser 只回传 runtime 状态和错误。 |
| viewer access 令牌 | CloakBrowser 签发，Payload 请求和转交 | App 只能拿到 Payload 返回的受控 viewer 入口，不保存、不记录、不展示原始 token。 |
| 用户界面展示和用户/运营交互状态 | App | 展示必须来自 Payload 安全 DTO 或 CloakBrowser 经 Payload 转发的 runtime 摘要。 |

## Runtime Service 调用方式

本节是后续 05 Session Broker 的目标契约草案，不代表当前代码已经实现 `/api/runtime/*`。当前代码已经有 profile runtime、VNC WebSocket 和 Automation REST API，但没有 service-to-service session broker、viewer-token、runtime session 表或多用户 RBAC。

### 基本规则

- 调用方向固定为 `Payload -> CloakBrowser`，只允许服务端到服务端调用。
- CloakBrowser runtime service API 必须校验 `RUNTIME_SERVICE_TOKEN` 或等价内部 token。
- 用户浏览器、Project Mileage App 前端组件和普通运营页面不得直接调用 `/api/runtime/*`。
- Payload 调用 runtime API 前必须已经完成用户身份、角色、订单/账号归属、钱包扣费或续期策略校验。
- runtime API 不接收用户 cookie、不解析 Payload session cookie、不读取 Project Mileage 数据库。
- runtime API 返回稳定错误码和安全 message；错误 message 不包含 proxy 密码、cookie、VNC token、账号密码或内部 AUTH_TOKEN。
- runtime API 不承诺 CDP 兼容，不返回 `cdp_url`，不把 `automation_url` 表达为 DevTools endpoint。

### Runtime API 草案

#### `POST /api/runtime/sessions`

用途：由 Payload 在业务 session 已授权后创建或恢复 CloakBrowser runtime session。

请求头：

```http
Authorization: Bearer <RUNTIME_SERVICE_TOKEN>
Idempotency-Key: <payload-remote-session-id-or-stable-key>
```

请求体：

```json
{
  "externalSessionId": "pm_remote_session_123",
  "profileId": "profile_123",
  "requestedBy": {
    "actorType": "payload",
    "actorId": "payload-service"
  },
  "lease": {
    "ttlSeconds": 1800,
    "renewableUntil": "2026-05-25T12:30:00Z"
  },
  "context": {
    "businessAccountId": "account_123",
    "orderId": "order_123",
    "purpose": "remote_workspace"
  }
}
```

响应体：

```json
{
  "runtimeSession": {
    "id": "rt_123",
    "externalSessionId": "pm_remote_session_123",
    "profileId": "profile_123",
    "runtimeStatus": "running",
    "leaseStatus": "active",
    "expiresAt": "2026-05-25T12:00:00Z",
    "createdAt": "2026-05-25T11:30:00Z",
    "updatedAt": "2026-05-25T11:30:00Z"
  }
}
```

规则：

- `externalSessionId` 由 Payload 生成并保持唯一。
- `Idempotency-Key` 相同且请求语义一致时返回同一个 runtime session。
- 如果 profile 未运行，CloakBrowser 可启动 profile；启动失败时返回 `RUNTIME_PROFILE_LAUNCH_FAILED`。
- 响应不包含 VNC 原始 token，不包含 proxy/cookie/账号密码。

#### `GET /api/runtime/sessions/{id}`

用途：Payload 查询 runtime session 当前状态。

响应字段：

- `id`
- `externalSessionId`
- `profileId`
- `runtimeStatus`
- `leaseStatus`
- `expiresAt`
- `lastActivityAt`
- `lastErrorCode`
- `lastErrorMessage`

规则：

- `lastErrorMessage` 必须脱敏。
- 不返回 profile 完整配置，只返回必要 runtime 摘要。

#### `POST /api/runtime/sessions/{id}/viewer-token`

用途：Payload 为已授权用户请求短生命周期 viewer access。

请求体：

```json
{
  "ttlSeconds": 120,
  "mode": "interactive",
  "audience": "project-mileage-app"
}
```

响应体：

```json
{
  "viewerAccess": {
    "viewerUrl": "https://cloakbrowser.example/runtime/viewer/opaque-access-id",
    "expiresAt": "2026-05-25T11:32:00Z",
    "mode": "interactive"
  }
}
```

规则：

- `viewerUrl` 是短生命周期受控入口；App 不应获得单独的 VNC 原始 token 字段。
- viewer token 到期、session 终止或 Payload 撤销后必须失效。
- 每次签发写 `remote_session.viewer_issued` / runtime audit。

#### `POST /api/runtime/sessions/{id}/renew`

用途：Payload 在完成续期授权和扣费策略后延长 runtime lease。

请求体：

```json
{
  "ttlSeconds": 1800,
  "renewalReason": "payload_authorized_renewal"
}
```

规则：

- CloakBrowser 只延长 runtime lease，不执行钱包扣费。
- 如果 session 已 `terminated` 或 `failed`，返回稳定冲突错误。

#### `POST /api/runtime/sessions/{id}/terminate`

用途：Payload 或授权运营操作终止 runtime session。

请求体：

```json
{
  "reason": "user_requested",
  "stopProfile": false
}
```

规则：

- `stopProfile` 的默认策略由后续 05 Session Broker 模块实现时确认。
- 终止后 viewer access 立即失效。
- 终止不自动退款、不改订单状态；这些业务动作只由 Payload 决定。

## 远程 Session 状态机

Payload 业务状态：

| 状态 | 进入条件 | 事实源 |
|---|---|---|
| `requested` | App 用户或运营在 Payload 创建远程会话请求。 | Payload |
| `authorized` | Payload 完成用户、订单/账号、钱包和权限校验。 | Payload |
| `starting` | Payload 已调用 CloakBrowser 创建 runtime session。 | Payload |
| `active` | CloakBrowser 返回 runtime 可用，Payload 允许用户进入 viewer。 | Payload，runtime 状态由 CloakBrowser 提供 |
| `idle` | Payload 判定会话空闲但未过期。 | Payload，可参考 CloakBrowser last activity |
| `expired` | Payload 判定租约到期且未续期。 | Payload |
| `terminated` | 用户、运营或策略结束会话。 | Payload，CloakBrowser 执行 runtime terminate |
| `failed` | 授权、扣费、runtime 启动、viewer 签发或其他关键步骤失败。 | Payload 记录业务失败，CloakBrowser 提供 runtime 错误摘要 |

CloakBrowser runtime 状态只描述底层资源，不替代业务状态：

```text
creating -> launching -> running -> terminating -> terminated
                         \-> failed
```

说明：这是 05 模块的目标 runtime session 状态，不是当前 `BrowserManager.running` 的持久化实现。当前已实现 profile status 主要是 `running` / `stopped` 运行摘要，后续扩展必须通过测试覆盖状态转换和进程重启语义。

## 敏感字段白名单

默认拒绝返回或写入日志/审计 metadata：

- `proxy password`
- `cookie value`
- `VNC token`
- `AUTH_TOKEN`
- `RUNTIME_SERVICE_TOKEN`
- `account password`
- `email password`
- `secretPayload`
- 浏览器 profile secrets
- 用户完整 session cookie

允许返回给 Payload/App 的安全摘要：

- `runtimeSession.id`
- `externalSessionId`
- `profileId`
- `runtimeStatus`
- `leaseStatus`
- `expiresAt`
- `viewerUrl` opaque 短期入口
- `lastErrorCode`
- 脱敏后的 `lastErrorMessage`
- profile name、health status、GeoIP country/timezone/locale 等非敏感运行摘要

## 审计事件清单

| 事件 | 写入方 | 必填 metadata | 禁止 metadata |
|---|---|---|---|
| `remote_session.requested` | Payload | user id、account/order reference、request source | 钱包明细、账号密码、cookie、VNC token |
| `remote_session.authorized` | Payload | authorization result、policy snapshot id | 余额明细之外的敏感账务内部字段 |
| `remote_session.started` | Payload + CloakBrowser | external session id、runtime session id、profile id | proxy 密码、profile secrets |
| `remote_session.viewer_issued` | CloakBrowser，Payload 可记录业务摘要 | runtime session id、expiresAt、mode | viewer token 原文、viewerUrl query secret |
| `remote_session.renewed` | Payload + CloakBrowser | ttl、expiresAt、reason code | 扣费内部流水明细、token |
| `remote_session.terminated` | Payload + CloakBrowser | actor、reason code、runtime session id | cookie、token、账号密码 |
| `remote_session.failed` | Payload + CloakBrowser | stable error code、脱敏 message、阶段 | 原始异常栈中可能包含的 secret |
| `profile.launch` | CloakBrowser | profile id、runtime status、geoip summary | proxy 密码 |
| `profile.stop` | CloakBrowser | profile id、reason code | profile secrets |
| `proxy.check` | CloakBrowser | proxy id/name、country/timezone/locale、status | proxy URL 密码 |

## Project Mileage 安全占位解除条件

只有以下条件全部满足，Project Mileage 才能把 `/app/remote-workspace`、`/app/remote-workspace/[id]/vnc` 和 `/ops/remote-monitor` 从安全占位改为真实能力：

- Payload `RemoteAccount` / `RemoteSession` / `RemoteSessionAudit` 或等价模型已通过任务文档或 Contract Change Proposal 确认。
- Payload 已确认用户可访问远程账号的来源：账号订单、库存凭证、人工授权或其他明确业务模型。
- 钱包扣费/续期策略已确认：按分钟、按次、赠送或免费策略必须有唯一事实源。
- Payload API 已提供用户端远程账号列表、创建/恢复 session、续期、终止、会话详情和运营远程监控接口。
- Payload 调用 CloakBrowser runtime API 的 service token、错误模型和审计 metadata 已确认。
- CloakBrowser 已实现 viewer token 短生命周期、撤销和 terminate 后失效。
- App adapter 已接 Payload 真实 API，页面不直接调用 CloakBrowser runtime service API。
- 浏览器验收能证明 App 不展示 VNC 原始 token、不模拟远程画面、不用本地倒计时伪造成功态。

## 未确认问题

以下问题不阻塞 CloakBrowser 独立成熟化，但进入 05/06 跨仓实现前必须确认：

- 远程会话扣费方式：按分钟、按次、随账号订单赠送或免费。
- 用户是否允许同时打开多个远程账号。
- Profile 与 Project Mileage 账号库存是一对一、一对多，还是会话级临时绑定。
- 运营是否允许实时接管用户正在使用的会话。
- 是否需要录屏、截图留存，还是只写审计事件。
- 自动化脚本是否允许在用户远程会话中运行。
- `terminate` 后是否 stop profile，还是只释放业务 lease 并保留 profile 运行。

## 验收标准

- [x] 后续任何实现者能根据本模块明确哪个仓库负责哪类逻辑。
- [x] Project Mileage 远程工作台不会绕过 Payload 直接访问 CloakBrowser。
- [x] CloakBrowser 不直接处理用户余额、订单归属或业务权限。
