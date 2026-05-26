# 06 远程工作台与 VNC 会话

## 目标

在 Project Mileage 中把安全占位的远程工作台升级为真实远程会话入口，同时复用 CloakBrowser 的 VNC runtime。

## 前置条件

- 05 会话 Broker 已完成。
- Project Mileage Payload 已确认 remote session contract。
- App 当前 P2 placeholder 测试需要改为真实 API 测试。
- 当前跨仓契约提案见 `../project-mileage-remote-workspace-contract-proposal.md`；未确认前不修改 Project Mileage app/payload。

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
- [x] EnvironmentStrip 支持业务 session 标识：
  - `ProfileViewer` 支持可选 `externalSessionId`，显示为短格式 `Session <id>`。
  - `ProfileViewer` 支持可选 `vncUrl`，为后续受控 runtime viewer 连接短生命周期 viewer URL 留出入口。
  - 普通 profile viewer 不显示 session chip，仍连接 `/api/profiles/{profileId}/vnc`。
  - 不渲染 viewer token、viewer URL、runtime service token、订单、钱包或用户权限信息。
- [x] runtime viewer 访问失败安全提示：
  - 仅在 `ProfileViewer` 收到 `vncUrl` 的 runtime viewer 分支启用。
  - `securityfailure` 不渲染 noVNC 原始 reason，避免把 viewer token、URL query 或完整 viewer URL 暴露到 UI。
  - runtime viewer 在建立连接前断开时显示固定提示，不调用普通断开回调，避免把访问失败伪装成正常退出。
  - runtime viewer 初始化/构造异常显示固定提示，不渲染异常 message，避免把 viewer token、URL query 或完整 viewer URL 暴露到 UI。
  - 已成功连接后的 runtime viewer 断开继续走原有 `onDisconnect()`。
  - 普通 profile viewer 的 VNC 断开行为保持不变。
- [x] 记录 viewer connected/disconnected audit：
  - 当前覆盖成功进入 runtime VNC 后的 `runtime.viewer.connected`。
  - 当前覆盖成功连接后的断开 `runtime.viewer.disconnected`。
  - metadata 仅记录 `subprotocol` 和 `close_code`。
  - 不记录 viewer token、viewer URL、viewer token hash、Origin 原文、请求头或 URL query。
- [x] 记录 viewer failed audit：
  - 当前覆盖 `runtime.viewer.failed`。
  - metadata 仅记录固定 `reason_code`。
  - 当前 reason code：`origin_not_allowed`、`runtime_session_not_live`、`viewer_credential_missing`、`viewer_credential_invalid`、`viewer_credential_expired`、`profile_not_running`、`backend_vnc_unavailable`。
  - 不记录 viewer token、viewer URL、viewer token hash、Origin 原文、请求头、URL query、后端 VNC 地址或异常 message。
  - missing session 不写 audit，避免把未认证 path 输入和扫描噪声写入审计表。

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

## 2026-05-27 CloakBrowser runtime viewer failure reason audit 小闭环

当前状态：

- 已完成 CloakBrowser 侧 runtime VNC 失败事件 reason code 审计。
- 本轮只覆盖低敏失败分类，不改变 Project Mileage 业务权限、订单、钱包或扣费逻辑。
- Project Mileage app/payload 未修改；业务远程工作台仍需要 Payload contract 确认后再进入跨仓实现。

已完成：

- `backend/tests/test_session_broker.py`
  - 新增 TDD 覆盖，确认初始红灯：失败 VNC 连接不会写 `runtime.viewer.failed`。
  - 覆盖缺失、错误、过期 viewer credential 分别写 `viewer_credential_missing`、`viewer_credential_invalid`、`viewer_credential_expired`。
  - 覆盖跨域 Origin 拒绝写 `origin_not_allowed`，但不记录 Origin 原文。
  - 覆盖 terminated session 写 `runtime_session_not_live`。
  - 覆盖 missing session 不写 failure audit，避免未认证输入刷表。
  - 覆盖 profile 未运行写 `profile_not_running`。
  - 覆盖后端 KasmVNC 连接失败写 `backend_vnc_unavailable`，但仍不写 connected/disconnected。
  - 覆盖审计不包含 viewer token、viewer URL、viewer token hash、后端 VNC 地址或异常 message。
- `backend/main.py`
  - 新增 `_audit_runtime_viewer_failure()`。
  - runtime VNC 的 origin、session live、credential、profile running 和 backend VNC connect 失败分支写 `runtime.viewer.failed`。
  - `_proxy_running_vnc()` 新增 `on_connect_failed` 回调；只有未成功 connected 的 backend connect 异常才触发 failed audit。
  - failure audit metadata 固定为 `{ "reason_code": "<enum>" }`。
  - failure audit 异常不阻断 WebSocket close 路径。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_vnc_rejects_missing_wrong_or_expired_viewer_token backend/tests/test_session_broker.py::test_runtime_vnc_rejects_cross_origin_even_with_valid_viewer_token backend/tests/test_session_broker.py::test_runtime_vnc_failure_audits_session_not_live_and_skips_missing_session backend/tests/test_session_broker.py::test_runtime_vnc_failure_audits_profile_not_running backend/tests/test_session_broker.py::test_runtime_vnc_backend_connect_failure_writes_redacted_failure_audit -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 24 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_ws_rejects_cross_origin backend/tests/test_api.py::test_ws_allows_same_origin backend/tests/test_api.py::test_ws_allows_no_origin backend/tests/test_api.py::test_vnc_proxy_connects_websockify_path -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 281 passed

git diff --check
# passed
```

仍未完成：

- Project Mileage Payload 侧 remote session contract、授权、扣费、续期和业务审计。
- Project Mileage App 侧真实远程账号列表和受控 viewer 页面。

## 2026-05-27 CloakBrowser EnvironmentStrip business session marker 小闭环

当前状态：

- 已完成 CloakBrowser 前端 viewer 环境条对业务 session 标识的低敏展示能力。
- 本轮只改 CloakBrowser 前端组件，不进入 Project Mileage app/payload 跨仓实现。

已完成：

- `frontend/src/components/ProfileViewer.tsx`
  - `ProfileViewer` 新增可选 `externalSessionId`。
  - 有 `externalSessionId` 时，环境条显示短格式 `Session <short externalSessionId>`，`title` 保存完整低敏业务 session 标识。
  - 无 `externalSessionId` 时，普通 profile viewer 不显示 session chip。
  - `ProfileViewer` 新增可选 `vncUrl`；传入时 noVNC 连接该 URL，否则保持原 `/api/profiles/{profileId}/vnc`。
  - `vncUrl` 仅用于 noVNC 连接，不在 UI 文案中渲染。
- `frontend/src/components/ProfileViewer.test.tsx`
  - 覆盖有 `externalSessionId` 时显示 session chip。
  - 覆盖普通 profile viewer 不显示 session chip。
  - 覆盖传入 runtime viewer URL 时 noVNC 使用该 URL，并且页面文本不渲染 viewer token 或完整 viewer URL。

验证记录：

```bash
npm test -- ProfileViewer.test.tsx
# 9 passed

npm test -- App.test.tsx
# 27 passed

npm test -- lib/api.test.ts
# 29 passed

npm test -- --run
# 187 passed

npm run build
# built successfully

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 24 passed

git diff --check
# passed
```

仍未完成：

- Project Mileage Payload 侧 remote session contract、授权、扣费、续期和业务审计。
- Project Mileage App 侧真实远程账号列表和受控 viewer 页面。
- 真实 runtime viewer 页面如何刷新过期 viewer token，仍应由 Payload/App 契约确认。

## 2026-05-27 Project Mileage remote workspace contract proposal 小闭环

当前状态：

- 已完成跨仓契约提案文档：`../project-mileage-remote-workspace-contract-proposal.md`。
- 本轮只读 Project Mileage app/payload 并输出建议，不修改主仓。

提案覆盖：

- Payload 用户端 `remote-accounts`、`remote-sessions`、viewer-token、renew、terminate API。
- Payload 运营端 remote sessions 列表、详情、viewer-token 和强制终止 API。
- App 远程工作台、受控 VNC viewer、运营远程监控建议文件范围。
- 权限、扣费/续期、viewer token、审计、CORS/service token、跨系统一致性和状态源风险。
- 禁止范围、测试命令和验收证据。

当前阻塞项：

- 需要 Jeff/主 agent 确认 API 名称、DTO 字段、权限节点、扣费模型、viewer token 刷新策略和跨系统补偿策略。
- 未确认前不得直接修改 `/home/jeff/code/project-mileage-v3-app` 或 `/home/jeff/code/project-mileage-v3-payload`。

## 2026-05-27 CloakBrowser runtime viewer access failure hint 小闭环

当前状态：

- 已完成 CloakBrowser 前端 runtime viewer 访问失败的固定安全提示。
- 本轮只改 CloakBrowser 前端组件和测试，不进入 Project Mileage app/payload。
- 该提示不替代 Payload/App 的 viewer token 刷新、权限、扣费或审计契约。

已完成：

- `frontend/src/components/ProfileViewer.tsx`
  - 新增 runtime viewer 固定失败提示文案。
  - `vncUrl` 存在时，`securityfailure` 显示固定提示，不渲染 noVNC 原始 reason。
  - `vncUrl` 存在且连接建立前触发 `disconnect` 时，显示固定提示，并且不调用普通 `onDisconnect()`。
  - `vncUrl` 存在且 noVNC 初始化/构造抛出异常时，显示固定提示，不渲染异常 message。
  - `vncUrl` 存在且已经成功连接后再断开时，继续调用 `onDisconnect()`，保持正常退出路径。
  - 未传 `vncUrl` 的普通 profile viewer 断开行为保持不变。
- `frontend/src/components/ProfileViewer.test.tsx`
  - 覆盖 runtime viewer `securityfailure` 不渲染 viewer token、完整 runtime viewer URL 或原始 reason。
  - 覆盖 runtime viewer 建立连接前断开时显示固定提示，且不调用普通断开回调。
  - 覆盖 runtime viewer 初始化/构造异常不渲染 viewer token、完整 runtime viewer URL 或原始异常 message。
  - 覆盖 runtime viewer 成功连接后断开仍走普通断开回调。

验证记录：

```bash
npm test -- ProfileViewer.test.tsx
# 13 passed

npm test -- App.test.tsx
# 27 passed

npm test -- lib/api.test.ts
# 29 passed

npm test -- --run
# 191 passed

npm run build
# built successfully

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 24 passed

git diff --check
# passed
```

仍未完成：

- Project Mileage Payload 侧确认 viewer token 刷新策略、权限、扣费/续期和业务审计。
- Project Mileage App 侧通过 Payload DTO 接入刷新/重开会话能力。
- 不允许 App 直接调用 CloakBrowser runtime API。
