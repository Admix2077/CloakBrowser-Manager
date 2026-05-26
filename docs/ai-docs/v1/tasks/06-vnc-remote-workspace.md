# 06 远程工作台与 VNC 会话

## 目标

在 Project Mileage 中把安全占位的远程工作台升级为真实远程会话入口，同时复用 CloakBrowser 的 VNC runtime。

## 前置条件

- 05 会话 Broker 已完成。
- Project Mileage Payload 已确认 remote session contract。
- App 当前 P2 placeholder 测试需要改为真实 API 测试。

## 任务清单

### Project Mileage Payload

- [ ] 新增远程账号/会话契约。
- [ ] 用户只能看到自己有权访问的远程账号。
- [ ] 创建 session 前检查订单、角色、钱包和账号状态。
- [ ] 创建 session 后调用 CloakBrowser runtime API。
- [ ] 续期时执行钱包扣费或使用业务赠送时长。
- [ ] 结束 session 时调用 runtime terminate。
- [ ] 写业务审计。

### Project Mileage App

- [ ] `/app/remote-workspace` 从安全占位改为真实列表。
- [ ] 显示：
  - 账号标签。
  - 授权来源。
  - 状态。
  - 剩余时长。
  - 健康状态。
- [ ] 启动会话按钮调用真实 API。
- [ ] `/app/remote-workspace/[id]/vnc` 嵌入受控 viewer。
- [ ] 不在前端显示 VNC token。
- [ ] 续期和结束操作显示真实成功/失败。
- [ ] `/ops/remote-monitor` 显示真实会话列表。
- [ ] 运营终止 session 需要权限和确认。

### CloakBrowser

- [x] viewer token 校验接入 VNC WebSocket。
- [ ] EnvironmentStrip 支持业务 session 标识。
- [x] 记录 viewer connected/disconnected audit：
  - 当前覆盖成功进入 runtime VNC 后的 `runtime.viewer.connected`。
  - 当前覆盖成功连接后的断开 `runtime.viewer.disconnected`。
  - metadata 仅记录 `subprotocol` 和 `close_code`。
  - 不记录 viewer token、viewer URL、viewer token hash、Origin 原文、请求头或 URL query。
  - 上游 KasmVNC 连接失败不写 connected/disconnected；失败事件 reason code 留给后续小闭环。

## 验证

Manager：

```bash
. .venv/bin/activate && python -m pytest backend/tests -q
```

App：

```bash
cd /home/jeff/code/project-mileage-v3-app && pnpm test
cd /home/jeff/code/project-mileage-v3-app && pnpm lint
cd /home/jeff/code/project-mileage-v3-app && pnpm build
```

Payload：

```bash
cd /home/jeff/code/project-mileage-v3-payload && pnpm vitest run
cd /home/jeff/code/project-mileage-v3-payload && pnpm lint
cd /home/jeff/code/project-mileage-v3-payload && pnpm build
```

浏览器验收：

- [ ] 用户登录后看到真实远程账号列表。
- [ ] 点击进入会话后 VNC 画面可用。
- [ ] 刷新页面后 token 仍按策略可用或重新换取。
- [ ] 过期/终止后无法继续查看。
- [ ] 运营端能看到 active session。

## 2026-05-27 CloakBrowser runtime viewer connected/disconnected audit 小闭环

当前状态：

- 已完成 CloakBrowser 侧 runtime VNC 成功连接和断开审计。
- 本轮只覆盖成功建立 runtime VNC 的低敏审计摘要，不覆盖失败事件。
- Project Mileage app/payload 未修改；业务远程工作台仍需要 Payload contract 确认后再进入跨仓实现。

已完成：

- `backend/tests/test_session_broker.py`
  - 新增 TDD 覆盖，确认初始红灯：成功进入 runtime VNC 后没有 `runtime.viewer.connected` / `runtime.viewer.disconnected`。
  - 覆盖成功连接 runtime VNC 后写 `runtime.viewer.connected` 和 `runtime.viewer.disconnected`。
  - 覆盖 viewer audit 使用 `actor_type=runtime_viewer`。
  - 覆盖事件绑定 runtime session id、profile id 和 external session id。
  - 覆盖 connected metadata 只记录 `subprotocol`。
  - 覆盖 disconnected metadata 只记录 `close_code`。
  - 覆盖审计不包含 viewer token、viewer URL、viewer token hash、Origin 原文。
  - 覆盖上游 KasmVNC 连接失败时不写 connected/disconnected，避免把失败事件混成成功断开事件。
- `backend/main.py`
  - 新增 `_audit_runtime_viewer_event()`。
  - `runtime_vnc_proxy()` 通过回调给 `_proxy_running_vnc()` 注入 runtime viewer 审计。
  - `_proxy_running_vnc()` 保持普通 profile VNC 路径可复用；只有 runtime VNC 传入回调时才写 viewer 审计。
  - `_proxy_running_vnc()` 只有在成功连接 KasmVNC 后才写 connected，并且只有已经 connected 才写 disconnected。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_vnc_success_writes_redacted_connect_and_disconnect_audit backend/tests/test_session_broker.py::test_runtime_vnc_backend_connect_failure_does_not_write_viewer_audit -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 22 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_ws_rejects_cross_origin backend/tests/test_api.py::test_ws_allows_same_origin backend/tests/test_api.py::test_ws_allows_no_origin backend/tests/test_api.py::test_vnc_proxy_connects_websockify_path -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 279 passed
```

仍未完成：

- Project Mileage Payload 侧 remote session contract、授权、扣费、续期和业务审计。
- Project Mileage App 侧真实远程账号列表和受控 viewer 页面。
- runtime VNC 失败事件 reason code 审计。
