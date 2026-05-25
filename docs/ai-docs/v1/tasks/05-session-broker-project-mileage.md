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

- [ ] 定义 service token：
  - `RUNTIME_SERVICE_TOKEN`
  - 仅 Payload 侧持有。
- [ ] 定义 `POST /api/runtime/sessions`：
  - 输入 business session id。
  - 输入 requested profile id 或 template id。
  - 输入 lease seconds。
  - 返回 runtime session id。
- [ ] 定义 `GET /api/runtime/sessions/{id}`。
- [ ] 定义 `POST /api/runtime/sessions/{id}/viewer-token`：
  - 返回短生命周期 viewer token。
- [ ] 定义 `POST /api/runtime/sessions/{id}/terminate`。
- [ ] 定义 `POST /api/runtime/sessions/{id}/renew`。
- [ ] 设计 runtime session 表：
  - id。
  - profile_id。
  - external_session_id。
  - status。
  - lease_expires_at。
  - viewer_token_hash。
  - created_at。
  - updated_at。
- [ ] session 创建时如果 profile 未运行，启动 profile。
- [ ] session 终止时按策略 stop profile 或释放 lease。
- [ ] viewer token 过期后不能进入 VNC。
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

- [ ] 无 service token 不能创建 runtime session。
- [ ] viewer token 短生命周期有效。
- [ ] 过期 token 无法连接。
- [ ] 终止 session 后 VNC 访问失效。
- [ ] Runtime session 不包含用户钱包逻辑。
