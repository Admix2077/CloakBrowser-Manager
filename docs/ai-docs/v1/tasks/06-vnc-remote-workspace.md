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

- [ ] viewer token 校验接入 VNC WebSocket。
- [ ] EnvironmentStrip 支持业务 session 标识。
- [ ] 记录 viewer connected/disconnected audit。

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
