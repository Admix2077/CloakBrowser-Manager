# CloakBrowser Invisible Manager V1 Goal Prompt

## 使用方式

新开 Codex session 后，可以把下面这段作为 `/goal` 的目标说明。

当前接力版本：2026-05-27。

最新已提交 CloakBrowser commit：

```text
087097a add proxy provider preset manager
```

当前 05 已完成最小 runtime session API、runtime viewer token、runtime terminate 和 runtime renew 小闭环，涉及文件：

```text
backend/database.py
backend/main.py
backend/models.py
backend/tests/test_session_broker.py
docs/ai-docs/v1/2026-05-25-fingerprint-health-ops-plan.md
docs/ai-docs/v1/2026-05-25-session-memory.md
docs/ai-docs/v1/goal-prompt.md
docs/ai-docs/v1/tasks/05-session-broker-project-mileage.md
docs/ai-docs/v1/tasks/progress.md
```

`backend/tests/test_session_broker.py` 已覆盖并通过：

- `RUNTIME_SERVICE_TOKEN` / `X-Runtime-Service-Token`。
- `runtime_sessions` 表和最小 CRUD。
- `POST /api/runtime/sessions`。
- `GET /api/runtime/sessions/{id}`。
- `POST /api/runtime/sessions/{id}/viewer-token`。
- `WebSocket /api/runtime/sessions/{id}/vnc`。
- `POST /api/runtime/sessions/{id}/terminate`。
- `POST /api/runtime/sessions/{id}/renew`。
- 从 profile 创建 runtime session。
- 从 template 创建 runtime session。
- runtime response 不包含 wallet/order/billing 字段，也不暴露 `viewer_token_hash`。
- viewer token 错误或过期时不能连接 runtime VNC。
- terminate 后 session 标记为 `terminated`，viewer token 被撤销，runtime VNC 失效。
- renew 后 active session lease 延长，短生命周期 viewer token 保持自身 TTL。

05 模块整体仍未完成，`tasks/progress.md` 顶层 05 不要勾选；audit、Payload 授权扣费联动仍待后续小闭环。

## Goal

请自主推进 `/home/jeff/code/cloakbrowser-invisible-manager/docs/ai-docs/v1/2026-05-25-fingerprint-health-ops-plan.md` 中定义的 CloakBrowser Invisible Manager V1 产品目标。

## 必读文档

先读取：

1. `/home/jeff/code/cloakbrowser-invisible-manager/docs/ai-docs/v1/2026-05-25-fingerprint-health-ops-plan.md`
2. `/home/jeff/code/cloakbrowser-invisible-manager/docs/ai-docs/v1/proposal.md`
3. `/home/jeff/code/cloakbrowser-invisible-manager/docs/ai-docs/v1/high-level-design.md`
4. `/home/jeff/code/cloakbrowser-invisible-manager/docs/ai-docs/v1/detailed-design.md`
5. `/home/jeff/code/cloakbrowser-invisible-manager/docs/ai-docs/v1/tasks/progress.md`
6. `/home/jeff/code/cloakbrowser-invisible-manager/docs/ai-docs/v1/2026-05-25-session-memory.md`

然后找到 `tasks/progress.md` 中第一个未完成模块，读取对应模块任务文档并推进。

## 执行规则

- 每次只推进一个可验证小闭环。
- 后端改动优先写测试。
- 前端改动必须跑前端测试和 build。
- Docker/运行时改动必须做容器构建或说明无法验证原因。
- 完成任务后更新对应任务文档 checkbox。
- 完成模块后更新 `tasks/progress.md`。
- 不要把文档写到 `docs/ai-docs/v1` 外面。
- 不要把 Project Mileage 的钱包、订单、权限逻辑写进 CloakBrowser。
- 不要让 Project Mileage 前端绕过 Payload 直接访问 CloakBrowser runtime service API。
- 不要把 Chromium CDP 作为基础能力；当前自动化以 Firefox/invisible_playwright 和 Automation REST API 为准。

## 当前优先级

第一优先级是让 CloakBrowser 独立成熟化：

1. 契约边界与事实源。
2. 指纹健康引擎。
3. Profile 运营台。
4. UI 视觉系统与体验升级。
5. Proxy Manager。
6. 模板、批量创建与批量运营。

Project Mileage 远程工作台联动必须等契约边界明确后再进入跨仓实现。

## 当前接力点

新会话启动后先执行：

```bash
cd /home/jeff/code/cloakbrowser-invisible-manager
git status --short --branch
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
```

`test_session_broker.py` 当前应通过。随后继续按 TDD 推进 05 的后续小闭环：

1. runtime audit。

后续小闭环不要改 Project Mileage app/payload，不要实现钱包、订单、用户权限判断，不要 push。
