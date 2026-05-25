# CloakBrowser Invisible Manager V1 概要设计

## 1. 总体架构

系统分为四层：

```text
Project Mileage App
  ├─ 用户端远程工作台
  └─ 运营端远程监控

Project Mileage Payload
  ├─ 用户/角色/权限
  ├─ 账号订单/账号库存
  ├─ 钱包扣费/续期
  └─ 业务审计

CloakBrowser Manager
  ├─ Profile 管理
  ├─ 指纹健康
  ├─ Proxy Manager
  ├─ VNC Viewer
  ├─ Automation API
  ├─ Script Runner
  └─ Runtime Audit

Browser Runtime
  ├─ invisible_playwright / Firefox
  ├─ profile dir
  ├─ KasmVNC
  └─ noVNC WebSocket
```

核心原则：

- Project Mileage 是业务事实源。
- CloakBrowser 是浏览器 runtime 事实源。
- Payload 和 Manager 之间通过明确 service API 协作。
- 用户端永远不直接拿到底层 profile 密钥、VNC 原始 token、proxy 密码或 cookie 明文。

## 2. 模块划分

### 2.1 Contract Boundary 模块

职责：

- 定义三仓边界。
- 定义 Project Mileage 与 CloakBrowser 的 API 契约。
- 明确哪些数据属于业务事实源，哪些数据属于 runtime 事实源。

输出：

- API contract 草案。
- 远程会话状态机。
- 权限矩阵。
- 审计事件表。

### 2.2 Health Engine 模块

职责：

- 计算 profile 健康状态。
- 执行 GeoIP / proxy / timezone / locale 检测。
- 输出 warning 和修复建议。

依赖：

- `backend/geoip.py`
- profile 数据库。
- browser manager status。

### 2.3 Profile Operations Console 模块

职责：

- 提供多 profile 运营台。
- 支持搜索、筛选、排序、多选、批量操作。
- 将 health、GeoIP、proxy、runtime status 可视化。

依赖：

- Profile API。
- Health API。
- Bulk API。

### 2.4 Proxy Manager 模块

职责：

- 管理 proxy 资产。
- 检测 proxy 出口。
- 将 proxy 分配到 profile。

依赖：

- GeoIP resolver。
- SQLite 数据表。
- Health Engine。

### 2.5 Session Broker 模块

职责：

- 为 Project Mileage 提供受控远程会话入口。
- 将业务 session 映射到 CloakBrowser profile。
- 生成短生命周期 VNC access。

依赖：

- Payload 授权 API。
- BrowserManager。
- Runtime audit。

### 2.6 VNC Remote Workspace 模块

职责：

- 管理 noVNC viewer。
- 用户端展示远程桌面。
- 运营端可监控远程会话。

依赖：

- Session Broker。
- VNC websocket。
- Project Mileage App 页面。

### 2.7 Automation / Script Runner 模块

职责：

- 扩展现有 Automation REST API。
- 支持可记录的自动化 task。
- 支持 warm-up、批量打开 URL、截图和简单流程。

依赖：

- BrowserManager running context。
- task queue。
- audit log。

### 2.8 Import / Export 模块

职责：

- cookie 导入导出。
- profile 配置导入导出。
- 后续支持完整 profile 包。

依赖：

- profile dir。
- browser context。
- 权限和审计。

### 2.9 Security / Audit 模块

职责：

- 记录高风险操作。
- 提供权限和 token 策略。
- 遮蔽敏感字段。
- 支撑 Project Mileage 审计对接。

依赖：

- 所有 mutation API。
- Project Mileage Payload audit。

### 2.10 Deployment / Observability 模块

职责：

- Docker 部署。
- healthcheck。
- resource quota。
- metrics。
- logs。
- backup/restore。

依赖：

- Dockerfile。
- FastAPI status。
- SQLite data dir。

## 3. 关键数据流

### 3.1 独立 profile 启动

```text
Frontend -> POST /api/profiles/{id}/launch
Backend -> load profile
Backend -> validate proxy
Backend -> start VNC
Backend -> resolve GeoIP
Backend -> build invisible_playwright kwargs
Backend -> launch Firefox
Backend -> inject language / clipboard script
Backend -> save last_geoip_*
Frontend -> open VNC Viewer
```

### 3.2 健康检测

```text
Frontend -> POST /api/profiles/{id}/health/check
Backend -> load profile
Backend -> validate proxy
Backend -> resolve GeoIP through proxy or container
Backend -> compare manual override and detected values
Backend -> save last_geoip_*
Backend -> return health status + warnings + actions
```

### 3.3 Project Mileage 远程会话

```text
User -> Project Mileage App remote workspace
App -> Payload: request remote session
Payload -> validate user/order/wallet/permissions
Payload -> CloakBrowser Session Broker: create or resume runtime session
CloakBrowser -> launch/lease profile
CloakBrowser -> return short-lived viewer URL/token to Payload
Payload -> return safe session DTO to App
App -> render remote viewer through brokered URL
CloakBrowser/Payload -> write audit events
```

### 3.4 运营远程监控

```text
Operator -> Project Mileage Ops remote monitor
App -> Payload: list sessions
Payload -> CloakBrowser: runtime statuses
Payload -> merge business + runtime status
App -> show session list
Operator -> terminate / observe / annotate
Payload -> permission check + audit
Payload -> CloakBrowser broker control API
```

## 4. 状态机草案

### 4.1 Profile Runtime Status

```text
stopped
launching
running
stopping
failed
```

当前代码只有 `running | stopped`。后续为了运营台和 Project Mileage 会话，需要补充中间态和失败态。

### 4.2 Health Status

```text
unknown
good
warning
error
```

### 4.3 Remote Session Status

```text
requested
authorized
starting
active
idle
expired
terminated
failed
```

Payload 是 remote session 状态事实源；CloakBrowser 只返回 runtime 状态和错误。

## 5. UI 总体结构

CloakBrowser Manager UI：

```text
Top Bar
  ├─ system status
  ├─ running count
  ├─ health summary
  └─ global actions

Left Rail
  ├─ Profiles
  ├─ Proxy Manager
  ├─ Templates
  ├─ Automation
  ├─ Audit
  └─ Settings

Main Area
  ├─ Operations Table
  ├─ Profile Detail
  ├─ Viewer
  ├─ Script Runner
  └─ Diagnostics
```

Project Mileage App UI：

- `/app/remote-workspace`
  - 用户可访问的远程账号列表。
  - 会话状态。
  - 进入远程桌面。
  - 续期或结束。
- `/app/remote-workspace/[id]/vnc`
  - 远程桌面 viewer。
  - 会话剩余时间。
  - 网络/连接状态。
- `/ops/remote-monitor`
  - 所有远程会话。
  - 用户、订单、账号、profile、状态。
  - 运营控制。

## 6. 分阶段落地原则

先完成 CloakBrowser 内部闭环，再对接 Project Mileage。

原因：

- Project Mileage 远程能力涉及钱包、订单、凭证、权限和审计，必须走契约确认。
- CloakBrowser 当前已有 runtime 基础，独立成熟化风险更低。
- 独立健康运营台完成后，Project Mileage 接入会更清晰。
