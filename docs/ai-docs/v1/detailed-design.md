# CloakBrowser Invisible Manager V1 详细设计

## 1. 后端设计

### 1.1 Health Engine

新增模块建议：

```text
backend/health.py
```

职责：

- 输入 profile dict。
- 输出 health result。
- 不直接处理 HTTP。
- 不直接修改数据库，除非通过调用方显式保存。

核心类型：

```python
HealthStatus = Literal["good", "warning", "error", "unknown"]

class HealthWarning(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"]
    action: str | None = None

class ProfileHealthResponse(BaseModel):
    profile_id: str
    status: HealthStatus
    geoip: GeoIPPayload | None
    manual_overrides: dict[str, bool]
    warnings: list[HealthWarning]
    checked_at: str
```

规则：

- 无 `last_geoip_*`：`unknown`。
- proxy 格式错误：`error`。
- GeoIP 查询失败：`warning` 或 `error`，取决于是否已有旧检测结果。
- 手动 timezone/locale 与自动结果冲突：`warning`。
- profile running 但缺 VNC/Automation：`warning`。
- 检测结果超过配置阈值：`warning`。
- 无 warning/error：`good`。

### 1.2 Health API

新增接口：

```http
POST /api/profiles/{profile_id}/health/check
GET /api/profiles/{profile_id}/health
```

`POST` 行为：

- 加载 profile。
- 校验 proxy。
- 调用 GeoIP。
- 计算 health。
- 成功 GeoIP 时写入 `last_geoip_*`。
- 返回 health result。

`GET` 行为：

- 不访问网络。
- 基于已有 profile 字段和 runtime status 计算当前 health。

### 1.3 Bulk API

新增接口：

```http
POST /api/profiles/bulk
```

请求：

```json
{
  "action": "launch",
  "profile_ids": ["..."],
  "options": {
    "concurrency": 2,
    "tags": [{"tag": "US", "color": "#22c55e"}]
  }
}
```

支持 action：

- `launch`
- `stop`
- `health_check`
- `refresh_geoip`
- `set_tags`
- `delete`

返回：

```json
{
  "action": "launch",
  "total": 10,
  "succeeded": 8,
  "failed": 2,
  "results": [
    {"profile_id": "...", "ok": true},
    {"profile_id": "...", "ok": false, "error": "Profile is already running"}
  ]
}
```

规则：

- 部分失败不能让整批失败。
- launch 默认并发 2。
- delete 必须先 stop。
- 所有失败返回稳定 message。

### 1.4 Proxy Manager

新增表：

```sql
CREATE TABLE proxies (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  country_code TEXT,
  city TEXT,
  asn TEXT,
  provider TEXT,
  tags TEXT DEFAULT '[]',
  notes TEXT,
  last_check_status TEXT,
  last_check_ip TEXT,
  last_check_country_code TEXT,
  last_check_timezone TEXT,
  last_check_locale TEXT,
  last_check_source TEXT,
  last_check_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

新增接口：

```http
GET /api/proxies
POST /api/proxies
GET /api/proxies/{id}
PUT /api/proxies/{id}
DELETE /api/proxies/{id}
POST /api/proxies/{id}/check
POST /api/proxies/bulk/check
```

Profile 可继续保留 `proxy` 字符串字段；第一阶段不强制迁移为 proxy_id，避免破坏现有数据。后续可增加 `proxy_id`。

### 1.5 Runtime Status

当前 status 为 `running | stopped`。建议扩展内部运行态：

```text
stopped
launching
running
stopping
failed
```

第一阶段可先在前端通过行级 loading 管理 `launching/stopping`，后端后续再持久化 `last_error`。

### 1.6 Runtime Audit

新增表：

```sql
CREATE TABLE audit_events (
  id TEXT PRIMARY KEY,
  actor_type TEXT NOT NULL,
  actor_id TEXT,
  action TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT,
  status TEXT NOT NULL,
  message TEXT,
  metadata TEXT DEFAULT '{}',
  created_at TEXT NOT NULL
);
```

第一阶段记录：

- profile.create。
- profile.update。
- profile.delete。
- profile.launch。
- profile.stop。
- profile.health_check。
- proxy.create。
- proxy.update。
- proxy.check。
- bulk.launch。
- bulk.stop。

敏感信息不得进入 metadata：

- proxy password。
- cookie value。
- account password。
- VNC token。
- auth token。

### 1.7 Session Broker

新增模块建议：

```text
backend/session_broker.py
```

职责：

- 接收 Project Mileage Payload 的 service request。
- 校验 service token。
- 创建 runtime session。
- 绑定 profile。
- 返回短期 viewer access。

Manager 侧接口草案：

```http
POST /api/runtime/sessions
GET /api/runtime/sessions/{id}
POST /api/runtime/sessions/{id}/terminate
POST /api/runtime/sessions/{id}/renew
```

注意：

- 这些接口不直接给最终用户调用。
- 调用方应是 Payload 或内部 service。
- viewer token 必须短生命周期。

## 2. 前端设计

### 2.1 信息架构

页面：

- `Profiles`
  - 运营台默认页。
- `Profile Detail`
  - 摘要、健康、配置、历史。
- `Viewer`
  - VNC。
- `Proxy Manager`
  - proxy 列表和检测。
- `Templates`
  - profile/proxy 模板。
- `Automation`
  - API、脚本任务。
- `Audit`
  - 操作日志。
- `Settings`
  - auth、并发、GeoIP provider、资源限制。

### 2.2 组件拆分

建议新增：

```text
frontend/src/components/HealthBadge.tsx
frontend/src/components/ProfileTable.tsx
frontend/src/components/ProfileFilters.tsx
frontend/src/components/BulkActionBar.tsx
frontend/src/components/ProfileSummaryPanel.tsx
frontend/src/components/EnvironmentStrip.tsx
frontend/src/components/ProxyTable.tsx
frontend/src/components/ConfirmDialog.tsx
frontend/src/lib/health.ts
frontend/src/lib/filters.ts
```

### 2.3 视觉系统

方向：

- 专业安全运营台。
- 深色低噪声。
- 高密度但清晰。
- emerald/cyan 表示健康。
- amber/red 表示风险。
- 不做营销 hero。
- 不做夸张 cyberpunk。

基础 token：

```text
background: #020617
surface-1: #0f172a
surface-2: #111827
border: #1f2937
text: #f8fafc
muted: #94a3b8
success: #22c55e
warning: #f59e0b
danger: #ef4444
accent: #06b6d4
```

### 2.4 Profile Table

列：

- select。
- name。
- status。
- health。
- proxy。
- ip。
- country。
- timezone。
- locale。
- tags。
- last checked。
- actions。

交互：

- 单击选中。
- 双击打开详情。
- 行内 launch/stop。
- 批量操作。
- filter chips。
- search debounce。

### 2.5 Profile Summary

展示：

- Health score。
- last GeoIP。
- manual override。
- proxy summary。
- device summary。
- runtime status。
- last error。
- quick actions。

### 2.6 Viewer

EnvironmentStrip：

- profile name。
- connected。
- IP / country。
- timezone / locale。
- clipboard。
- automation。
- fullscreen。

要求：

- 不遮挡 VNC。
- 窄屏仍可换行。
- 按钮有 tooltip。

## 3. Project Mileage 集成设计

### 3.1 Payload 新增事实源概念

后续需要在 Payload 确认：

- RemoteAccount。
- RemoteSession。
- RemoteSessionAudit。
- wallet billing policy。
- session permission。

### 3.2 App 用户端页面

`/app/remote-workspace`：

- 列出可用远程账号。
- 显示账号授权来源。
- 显示可启动/运行中/已过期。
- 启动会话。

`/app/remote-workspace/[id]/vnc`：

- 嵌入受控 viewer。
- 显示剩余时长。
- 显示连接状态。
- 允许续期或结束。

### 3.3 App 运营端页面

`/ops/remote-monitor`：

- 会话列表。
- 用户。
- 订单。
- 账号。
- profile。
- runtime status。
- risk。
- start time。
- last activity。
- terminate。

### 3.4 安全边界

- App 不保存 VNC token。
- Payload 不保存浏览器 cookie 明文。
- Manager 不读取用户钱包。
- Manager runtime session 只信任 Payload service token。
- 用户 viewer token 短期有效，可撤销。

## 4. 测试策略

### 4.1 Manager 后端

- `pytest backend/tests -q`
- Health Engine 单元测试。
- GeoIP fallback。
- proxy validation。
- bulk partial failure。
- audit metadata 脱敏。
- session broker auth。

### 4.2 Manager 前端

- `cd frontend && npm test -- --run`
- `cd frontend && npm run build`
- Profile filters。
- BulkActionBar。
- HealthBadge。
- Viewer EnvironmentStrip。
- Proxy Manager。

### 4.3 Docker

- build。
- container healthcheck。
- launch profile。
- VNC connect。
- BrowserScan smoke。

### 4.4 Project Mileage 跨仓

只有进入集成阶段才执行：

- Payload integration tests。
- App adapter tests。
- App browser tests。
- 三仓分别提交。

## 5. 风险

- Firefox/invisible_playwright 不支持 CDP，自动化设计必须坚持 REST API。
- 代理检测和 GeoIP provider 会受网络影响，测试需要 mock。
- 批量启动可能耗尽资源，必须限制并发。
- VNC token 和 cookie 是敏感面，必须短生命周期和审计。
- Project Mileage 的远程能力涉及钱包和订单，不能绕过 contract。
