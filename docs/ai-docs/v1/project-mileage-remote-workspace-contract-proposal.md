# Project Mileage 远程账号工作台跨仓契约提案

## 目标

把 Project Mileage 当前安全占位的远程账号工作台接入 CloakBrowser runtime，使购买了远程工作台账号的用户可以在 `/app/remote-workspace` 看到自己有权访问的远程账号或 profile，启动 runtime session，并进入受控 VNC viewer 在线操控。

本提案只定义 Project Mileage App/Payload 与 CloakBrowser 的协作契约，不授权直接修改 `/home/jeff/code/project-mileage-v3-app` 或 `/home/jeff/code/project-mileage-v3-payload`。主仓实现必须由 Jeff 或主 agent 确认后再进入明确范围。

## 动机

当前 CloakBrowser 已具备底层 runtime 能力：

- `RUNTIME_SERVICE_TOKEN` / `X-Runtime-Service-Token`。
- `POST /api/runtime/sessions`。
- `GET /api/runtime/sessions/{id}`。
- `POST /api/runtime/sessions/{id}/viewer-token`。
- `POST /api/runtime/sessions/{id}/renew`。
- `POST /api/runtime/sessions/{id}/terminate`。
- `WebSocket /api/runtime/sessions/{id}/vnc`。
- runtime service 成功动作审计。
- runtime viewer connected/disconnected/failed 低敏审计。
- `ProfileViewer` 支持 `externalSessionId` 和受控 `vncUrl`。

但 Project Mileage 的远程工作台不能直接使用这些 runtime API。Payload 才是订单、钱包、权限、用户、审计和业务 session 的事实源。App 只能通过 Payload 返回的安全 DTO 接入，不能持有 `RUNTIME_SERVICE_TOKEN`，不能直接调用 CloakBrowser runtime service API。

## 总体链路

推荐链路：

```text
Project Mileage App
  -> Project Mileage Payload remote workspace API
    -> CloakBrowser runtime service API
      -> CloakBrowser profile / VNC runtime
```

App 只消费 Payload 安全 DTO。Payload 负责业务校验、扣费/核销、业务审计和 server-to-server 调用 CloakBrowser。CloakBrowser 只负责 profile/runtime/VNC，不理解 Project Mileage 的钱包、订单、角色或购买规则。

## Payload 建议 API 契约

### 用户端账号列表

`GET /api/app/remote-accounts`

用途：返回当前登录用户可访问的远程账号/profile 列表。

建议响应：

```ts
type RemoteAccountDTO = {
  id: string
  label: string
  authorizationSource: 'account_order' | 'support_grant' | 'ops_grant'
  status: 'available' | 'active' | 'expired' | 'disabled'
  remainingSeconds: number
  healthStatus: 'unknown' | 'good' | 'warning' | 'error'
  activeSessionId: string | null
}
```

禁止返回：账号邮箱、账号密码、邮箱密码、`secretPayload`、CloakBrowser profile 内部敏感配置、proxy password、viewer token、viewer URL、runtime service URL 或 `RUNTIME_SERVICE_TOKEN`。

### 用户端创建 session

`POST /api/app/remote-sessions`

请求：

```ts
type CreateRemoteSessionRequest = {
  remoteAccountId: string
  leaseSeconds?: number
  idempotencyKey?: string
}
```

Payload 责任：

- 校验当前用户只能启动自己有权访问的 remote account。
- 校验订单或授权仍有效。
- 校验账号状态可用。
- 校验钱包余额、赠送时长或套餐剩余时长。
- 执行扣费、冻结或时长核销。
- 创建 Project Mileage 业务 session 记录，生成 `external_session_id`。
- 使用 server-to-server token 调用 CloakBrowser `POST /api/runtime/sessions`。
- 写 Project Mileage 业务审计。

响应：

```ts
type RemoteSessionDTO = {
  id: string
  remoteAccountId: string
  externalSessionId: string
  status: 'starting' | 'active' | 'expired' | 'terminated'
  runtimeStatus: 'not_created' | 'starting' | 'active' | 'expired' | 'terminated' | 'failed'
  billingStatus: 'not_required' | 'pending' | 'charged' | 'refunded' | 'failed'
  leaseExpiresAt: string
  remainingSeconds: number
  canRenew: boolean
  canTerminate: boolean
  viewer: {
    available: boolean
    reasonCode: null | 'starting' | 'expired' | 'terminated' | 'permission_denied'
  }
}
```

`id` 是 Project Mileage 业务 session id，不直接暴露 CloakBrowser runtime session id，除非 Payload 明确决定把 runtime id 作为低敏关联字段放入服务端内部记录。

`status` 是 Project Mileage 业务 session 状态，不等同于 CloakBrowser runtime session 状态、订单状态或钱包流水状态。为避免状态源混乱，建议 DTO 显式拆出 `runtimeStatus` 与 `billingStatus`，页面展示时由 App ViewModel 做清晰映射，不把任一底层状态直接当作全局成功态。

### 用户端 session 详情

`GET /api/app/remote-sessions/[id]`

返回当前用户自己的 session 安全 DTO。不存在、非本人或无权访问时建议统一 `404`，避免枚举。

### 用户端 viewer 入口

`POST /api/app/remote-sessions/[id]/viewer-token`

Payload 责任：

- 校验当前用户拥有该业务 session。
- 校验 session 仍 active 且未过期。
- 调用 CloakBrowser `POST /api/runtime/sessions/{runtimeSessionId}/viewer-token`。
- 不记录 viewer token 明文。
- 写业务审计 `remote_session.viewer_token_issued`，metadata 只放业务 session id、remote account id、ttl 和 reason code。

建议响应：

```ts
type RemoteViewerAccessDTO = {
  session: RemoteSessionDTO
  viewerUrl: string
  expiresAt: string
}
```

注意：`viewerUrl` 可包含短 TTL viewer token，只能由受控 viewer 页面立即使用。App 不得展示、复制、写入 localStorage、写入日志或放入长期可分享链接。更安全的后续版本可以由 Payload 提供同源 viewer relay，避免 App 直接持有 token query。

### 用户端续期

`POST /api/app/remote-sessions/[id]/renew`

请求：

```ts
type RenewRemoteSessionRequest = {
  leaseSeconds: number
  idempotencyKey?: string
}
```

Payload 必须先完成余额/套餐/赠送时长校验和扣费或核销，再调用 CloakBrowser `POST /api/runtime/sessions/{runtimeSessionId}/renew`。

CloakBrowser 当前 renew 语义是 `lease_expires_at = now + lease_seconds`，不是在旧 lease 上累加。Payload DTO 和 App 倒计时必须按返回的 `leaseExpiresAt` 展示。

### 用户端结束 session

`POST /api/app/remote-sessions/[id]/terminate`

用户只能结束自己的 active session。Payload 调用 CloakBrowser terminate 后更新业务 session 状态并写审计。结束 session 不等于订单退款、账号禁用或钱包调账。

### 运营端列表与详情

`GET /api/ops/remote-sessions`

`GET /api/ops/remote-sessions/[id]`

仅 `admin` 或具备明确远程监控权限的 `support` 可访问。

建议 DTO：

```ts
type OpsRemoteSessionDTO = {
  id: string
  remoteAccountId: string
  user: {
    id: string
    email: string | null
    displayName: string | null
  }
  status: 'starting' | 'active' | 'expired' | 'terminated'
  leaseExpiresAt: string
  startedAt: string
  endedAt: string | null
  viewerAvailable: boolean
}
```

运营列表禁止返回 viewer token、viewer URL、runtime service token、账号密码、proxy password、cookie、raw CloakBrowser headers、内部异常文本或完整审计 metadata。

### 运营端 viewer 与终止

`POST /api/ops/remote-sessions/[id]/viewer-token`

`POST /api/ops/remote-sessions/[id]/terminate`

运营查看屏幕和强制终止必须是独立权限点，并写强审计。终止请求建议要求 reason code：

```ts
type OpsTerminateRemoteSessionRequest = {
  reasonCode: 'user_request' | 'abuse' | 'support' | 'maintenance' | 'other'
}
```

强制终止不自动触发退款、订单取消、账号禁用或钱包调账。

## Payload 建议文件范围

建议新增或修改范围：

- `project-mileage-v3-payload/src/app/api/app/remote-accounts/route.ts`
- `project-mileage-v3-payload/src/app/api/app/remote-sessions/route.ts`
- `project-mileage-v3-payload/src/app/api/app/remote-sessions/[id]/route.ts`
- `project-mileage-v3-payload/src/app/api/app/remote-sessions/[id]/viewer-token/route.ts`
- `project-mileage-v3-payload/src/app/api/app/remote-sessions/[id]/renew/route.ts`
- `project-mileage-v3-payload/src/app/api/app/remote-sessions/[id]/terminate/route.ts`
- `project-mileage-v3-payload/src/app/api/ops/remote-sessions/route.ts`
- `project-mileage-v3-payload/src/app/api/ops/remote-sessions/[id]/route.ts`
- `project-mileage-v3-payload/src/app/api/ops/remote-sessions/[id]/viewer-token/route.ts`
- `project-mileage-v3-payload/src/app/api/ops/remote-sessions/[id]/terminate/route.ts`
- `project-mileage-v3-payload/src/app/api/_lib/auth.ts`
- `project-mileage-v3-payload/src/app/api/_lib/cors.ts`
- `project-mileage-v3-payload/src/app/api/_lib/dto.ts`
- `project-mileage-v3-payload/src/core/auditLog.ts`
- 可新增 `project-mileage-v3-payload/src/core/remoteSessions.ts`
- 如需持久化，可新增 `project-mileage-v3-payload/src/collections/RemoteSessions.ts`

禁止顺手修改：

- 钱包 core 调账语义。
- 订单取消/退款状态机。
- Bitcart 支付 webhook。
- 账号凭证 `secretPayload` 存储语义。
- 用户角色模型。

## App 建议文件范围

建议新增或修改范围：

- `project-mileage-v3-app/lib/api/remote.ts`
- `project-mileage-v3-app/lib/api/remote.test.ts`
- `project-mileage-v3-app/app/app/remote-workspace/page.tsx`
- `project-mileage-v3-app/app/app/remote-workspace/[id]/vnc/page.tsx`
- `project-mileage-v3-app/app/ops/remote-monitor/page.tsx`
- 可能新增 `project-mileage-v3-app/components/remote/*`
- 浏览器报告目录：`project-mileage-v3-app/doc/tasks-browser-test-v1/runs/<date>-remote-workspace-runtime/`

App 必须继续通过统一 API adapter 调 Payload，所有真实请求携带 `credentials: 'include'`。App 不得直接调用 CloakBrowser runtime API，不得持有 `RUNTIME_SERVICE_TOKEN`。

## 权限风险

- 用户只能访问自己的 remote account 和 remote session。
- 非本人 session 建议返回 `404`，避免枚举。
- `customer` / `supplier` 不能访问 `/ops/remote-monitor`。
- `support` 是否可查看屏幕、签发 viewer token、强制终止 session，需要明确权限节点，例如：
  - `remote_session:read`
  - `remote_session:view_screen`
  - `remote_session:terminate`
- 运营 viewer token 签发必须写审计并要求受权操作人。

## 资金与续期风险

- CloakBrowser 禁止直接扣 Project Mileage 钱包。
- Payload 必须在创建或续期 runtime session 前完成扣费、冻结、套餐时长扣减或赠送时长核销。
- 创建和续期需要幂等键，避免重复点击重复扣费。
- CloakBrowser renew 不是累加旧 lease；Payload 必须以 runtime 返回的 lease 时间作为事实源同步业务 session。
- 续期失败不得延长 runtime session；扣费成功但 runtime renew 失败必须进入明确补偿或人工审计路径。
- runtime 创建成功但扣费/核销失败不得向 App 返回可用 viewer；应立即 terminate runtime session 或进入人工补偿队列，并写 `remote_session.billing_failed` / `remote_session.runtime_compensation_required`。
- 扣费/核销成功但 runtime 创建失败不得静默吞掉；必须回滚、退款、恢复时长或进入人工补偿队列，并写可检索审计。

## Viewer Token 风险

- viewer token 明文只允许短 TTL，只返回一次。
- 不进 DB 明文、不进日志、不进 localStorage、不进审计 metadata、不进错误响应。
- App 页面文本、浏览器报告和测试快照不得包含 viewer token、完整 viewer URL 或 token query。
- viewer token 过期后的刷新策略必须由 Payload/App 契约确认；CloakBrowser 只负责验证 token 失效。
- `ProfileViewer.vncUrl` 只应接收 Payload 下发的受控 viewer URL，不应由用户输入拼接。
- 即使 UI 不显示 token，也要检查 Network 面板、错误边界、异常上报、测试快照、浏览器验收报告和前端 console，避免 token query 被间接固化。

## 审计风险

Payload 需要记录业务审计，建议事件：

- `remote_session.created`
- `remote_session.viewer_token_issued`
- `remote_session.renewed`
- `remote_session.terminated`
- `remote_session.ops_viewer_token_issued`
- `remote_session.ops_terminated`
- `remote_session.billing_failed`
- `remote_session.runtime_failed`
- `remote_session.runtime_compensation_required`

审计 metadata 只记录低敏 id、reason code、ttl、lease seconds、amountCents、billing mode、visible sections 等摘要。

禁止记录：

- viewer token。
- viewer URL。
- runtime service token。
- proxy password。
- cookie / header 原文。
- 账号密码或邮箱密码。
- 完整异常 message。
- 原始 CloakBrowser URL query。

CloakBrowser runtime audit 已记录 service API 成功动作和 viewer connected/disconnected/failed 的低敏摘要，但不替代 Project Mileage 业务审计。

## CORS 与 Service Token 风险

- `RUNTIME_SERVICE_TOKEN` 只能存在 Payload 服务端环境变量中。
- App 不能通过环境变量、Next public env、URL 参数或响应 DTO 获得 service token。
- Payload 调 CloakBrowser runtime API 是 server-to-server 调用，不需要给浏览器开放 CloakBrowser runtime CORS。
- App 浏览器只访问 Payload API。Payload API 继续按 Project Mileage app origin CORS 规则处理。

## 状态源风险

远程工作台至少包含四类事实源：

- Project Mileage 业务 session：用户能否进入、是否已结束、是否还能续期。
- CloakBrowser runtime session：profile 是否运行、lease 是否过期、viewer token 是否有效。
- 订单/账号授权：用户是否购买或仍有授权访问该远程账号。
- 钱包/套餐/赠送时长：创建和续期是否已经扣费、冻结或核销。

Payload DTO 必须避免只暴露一个含糊 `status`。建议业务 DTO 明确区分 `status`、`runtimeStatus`、`billingStatus` 和 `viewer.reasonCode`，并把最终按钮可用性派生为 `canRenew`、`canTerminate`、`viewer.available`。App 不应自行猜测跨系统状态。

## 禁止范围

- 禁止直接修改 Project Mileage app/payload，除非 Jeff 或主 agent 对明确文件范围授权。
- 禁止 App 直接调用 CloakBrowser runtime API。
- 禁止 App 持有 `RUNTIME_SERVICE_TOKEN`。
- 禁止 CloakBrowser 判断 Project Mileage 订单、钱包、用户权限或扣费规则。
- 禁止伪造订单、VNC、登录、余额、续期、终止或成功状态。
- 禁止读取或提交 `.env`、secret、cookie、proxy password、viewer token、service token 或数据库 dump。
- 禁止将 frontend-lab preview 字段反推为真实 Payload schema。
- 禁止把远程 session 接入顺手混入退款、订单取消、账号禁用、钱包调账、支付确认或凭证删除。

## 测试命令建议

Payload 阶段：

```bash
cd /home/jeff/code/project-mileage-v3-payload
pnpm vitest run tests/int/remoteSessionsApi.int.spec.ts tests/int/opsRemoteSessionsApi.int.spec.ts
pnpm exec tsc --noEmit
pnpm lint
pnpm build
```

App 阶段：

```bash
cd /home/jeff/code/project-mileage-v3-app
pnpm test lib/api/remote.test.ts
pnpm test app/p2-placeholders-source.test.ts
pnpm exec tsc --noEmit
pnpm lint
pnpm build
```

CloakBrowser 回归：

```bash
cd /home/jeff/code/cloakbrowser-invisible-manager
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
cd frontend && npm test -- ProfileViewer.test.tsx
cd frontend && npm test -- --run
cd frontend && npm run build
```

浏览器验收应单独记录到：

```text
/home/jeff/code/project-mileage-v3-app/doc/tasks-browser-test-v1/runs/<date>-remote-workspace-runtime/REPORT.md
```

## 验收证据

最低验收应覆盖：

- 用户登录后 `/app/remote-workspace` 显示真实授权账号列表。
- 未购买或无授权用户看不到账号，不能启动 session。
- 用户启动 session 后，Payload 创建业务 session 并调用 CloakBrowser runtime session。
- `/app/remote-workspace/[id]/vnc` 通过 Payload 下发的安全 viewer DTO 进入 viewer。
- 页面不展示 viewer token、完整 viewer URL、service token、账号密码、proxy password、cookie 或 token hash。
- viewer token 过期后无法连接。
- terminate 后原 viewer token 失效。
- renew 前先完成 Payload 侧扣费/核销；失败不延长 runtime session。
- 非本人 session 访问返回 404/403。
- `customer` / `supplier` 无法访问 `/ops/remote-monitor`。
- 运营查看屏幕和强制终止均要求权限并写业务审计。
- Payload 审计和 CloakBrowser 审计均不含 token、secret、cookie、账号密码、proxy password 或 raw query。
- 扣费成功/runtime 失败、runtime 成功/扣费失败、renew 部分失败三类跨系统异常都有自动测试或人工补偿审计证据。
- App DTO 和页面能区分业务 session 状态、runtime 状态和扣费状态，不把单一 `status` 当作所有事实源。

## 当前阻塞项

- Project Mileage Payload 尚未确认 remote account/session collection 或映射来源。
- 购买了“支持远程工作台账号”的订单如何映射到 CloakBrowser `profile_id` 或 `template_id` 尚未确认。
- 计费模式尚未确认：按 session、按分钟、按套餐时长、按订单赠送时长，或混合模式。
- viewer token 刷新策略尚未确认：刷新页面后重新签发、短期复用，或 Payload viewer relay。
- 运营 screen view 权限和强制终止权限节点尚未确认。
- 跨系统失败补偿策略尚未确认：扣费成功但 runtime 创建失败、runtime 创建成功但扣费失败、renew 两边部分成功时如何回滚或人工处理。

## 建议推进顺序

1. 主 agent / Jeff 确认本提案的 API 名称、DTO 字段、权限节点和扣费模型。
2. Payload 先做只读/低风险数据模型和 `GET /api/app/remote-accounts`，不签发 viewer token。
3. Payload 再做 `POST /api/app/remote-sessions`，完成授权、幂等、扣费/核销和 runtime session 创建。
4. Payload 再做 viewer token、renew、terminate，逐项补测试和审计。
5. App 最后把安全占位页替换为真实 adapter 和受控 viewer 页面。
