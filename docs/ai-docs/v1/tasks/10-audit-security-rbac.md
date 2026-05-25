# 10 审计、安全与权限

## 目标

建立适合远程浏览器平台的安全基线：认证、权限、敏感字段遮蔽、审计、token 生命周期和高风险操作保护。

## 任务清单

### Auth

- [ ] 保留当前 `AUTH_TOKEN` 本地部署模式。
- [ ] 新增 service token，用于 Payload 调用 runtime API。
- [ ] 区分 user API、admin API、service API。
- [ ] WebSocket viewer token 校验。

### Sensitive Data

- [ ] proxy password 列表遮蔽。
- [ ] audit metadata 不记录敏感字段。
- [ ] API response 不返回 AUTH_TOKEN。
- [ ] cookie 导出不写日志。
- [ ] VNC token hash 存储，不存明文。

### Audit

- [ ] 新增 audit_events 表。
- [ ] profile mutation 写 audit。
- [ ] proxy mutation 写 audit。
- [ ] health check 写 audit。
- [ ] bulk action 写 audit。
- [ ] automation task 写 audit。
- [ ] runtime session 写 audit。

### RBAC 远期设计

- [ ] 单机版先支持 admin。
- [ ] 后续支持 viewer/operator/admin。
- [ ] Project Mileage 权限以 Payload roles 为准。
- [ ] CloakBrowser 内部 RBAC 不替代 Payload 业务权限。

## 验证

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_auth.py backend/tests/test_audit.py -q
cd frontend && npm test -- --run
```

## 验收标准

- [ ] 未授权不能访问 protected API。
- [ ] WebSocket origin 检查不退化。
- [ ] audit 中没有 proxy password、cookie value、token。
- [ ] 删除、导出、终止等高风险操作有确认或权限限制。
