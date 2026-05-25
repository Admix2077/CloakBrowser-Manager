# 12 部署、观测与资源治理

## 目标

让产品在 Docker 中长期稳定运行，并能观察运行状态、资源压力和失败原因。

## 任务清单

### Docker

- [ ] 保持 Dockerfile 可构建。
- [ ] healthcheck 覆盖 `/api/status`。
- [ ] 数据目录 `/data` 可持久化。
- [ ] 文档说明 backup/restore。
- [ ] 支持 `AUTH_TOKEN`。
- [ ] 支持 service token。

### Resource Limits

- [ ] 配置最大同时运行 profile 数。
- [ ] 配置批量启动并发。
- [ ] 启动前检查可用 display / ws port。
- [ ] 停止时释放 VNC 和 browser context。
- [ ] 清理 stale process。

### Observability

- [ ] `/api/status` 增加：
  - running_count。
  - launching_count。
  - failed_count。
  - profiles_total。
  - proxy_count。
  - task_queue_count。
- [ ] 新增 `/api/diagnostics`。
- [ ] 日志中包含 profile id 和 action。
- [ ] 错误响应稳定。
- [ ] 前端 settings/diagnostics 页面显示系统状态。

### Backup

- [ ] 备份 SQLite。
- [ ] 备份 profile dirs。
- [ ] 导出配置不含敏感字段。
- [ ] 恢复后可启动 profile。

## 验证

```bash
docker build --network=host --platform linux/amd64 -t invisible-browser-manager:latest .
docker run --rm -p 8080:8080 -v invisible-browser-profiles-test:/data invisible-browser-manager:latest
```

## 验收标准

- [ ] 容器 healthcheck 通过。
- [ ] 重启后 profiles 仍存在。
- [ ] 强杀后再次启动 profile 不因 lock/session restore 卡死。
- [ ] status 能反映运行中数量。
