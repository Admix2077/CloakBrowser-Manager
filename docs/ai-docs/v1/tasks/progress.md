# CloakBrowser Invisible Manager V1 任务总进度

## 目标

把 `cloakbrowser-invisible-manager` 推进为成熟的指纹浏览器运行时平台，并为 Project Mileage 的远程账号工作台提供底层浏览器能力。

## 使用方式

新 session 或 `/goal` 推进时：

1. 读取 `../2026-05-25-fingerprint-health-ops-plan.md`。
2. 读取 `../proposal.md`、`../high-level-design.md`、`../detailed-design.md`。
3. 读取本文。
4. 找到第一个未完成模块。
5. 读取对应模块文档并逐项执行。
6. 每完成一个小闭环，更新模块文档和本文 checkbox。

## 模块进度

- [x] 01 契约边界与事实源：`01-contract-and-boundaries.md`
- [x] 02 指纹健康引擎：`02-health-engine.md`
- [x] 03 Profile 运营台：`03-profile-operations-console.md`
- [ ] 04 Proxy Manager：`04-proxy-manager.md`
- [ ] 05 Project Mileage 会话 Broker：`05-session-broker-project-mileage.md`
- [ ] 06 远程工作台与 VNC 会话：`06-vnc-remote-workspace.md`
- [ ] 07 Automation API 与脚本运行器：`07-automation-api-script-runner.md`
- [ ] 08 Cookie、Profile 导入导出：`08-cookie-profile-import-export.md`
- [ ] 09 模板、批量创建与批量运营：`09-templates-bulk-ops.md`
- [ ] 10 审计、安全与权限：`10-audit-security-rbac.md`
- [ ] 11 UI 视觉系统与体验升级：`11-ui-visual-system.md`
- [ ] 12 部署、观测与资源治理：`12-deployment-observability.md`
- [ ] 13 总回归、交付与上线门禁：`13-regression-release.md`

## 推荐执行顺序

第一阶段：CloakBrowser 独立成熟化。

1. 01 契约边界与事实源。
2. 02 指纹健康引擎。
3. 03 Profile 运营台。
4. 11 UI 视觉系统与体验升级。
5. 04 Proxy Manager。
6. 09 模板、批量创建与批量运营。

第二阶段：运行时平台化。

1. 10 审计、安全与权限。
2. 07 Automation API 与脚本运行器。
3. 08 Cookie、Profile 导入导出。
4. 12 部署、观测与资源治理。

第三阶段：Project Mileage 联动。

1. 05 Project Mileage 会话 Broker。
2. 06 远程工作台与 VNC 会话。
3. 13 总回归、交付与上线门禁。

## 全局验证命令

Manager 后端：

```bash
. .venv/bin/activate && python -m pytest backend/tests -q
```

Manager 前端：

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

Docker：

```bash
docker build --network=host --platform linux/amd64 -t invisible-browser-manager:latest .
```

Project Mileage 跨仓阶段才运行：

```bash
cd /home/jeff/code/project-mileage-v3-app && pnpm test
cd /home/jeff/code/project-mileage-v3-app && pnpm lint
cd /home/jeff/code/project-mileage-v3-app && pnpm build
cd /home/jeff/code/project-mileage-v3-payload && pnpm vitest run
cd /home/jeff/code/project-mileage-v3-payload && pnpm lint
cd /home/jeff/code/project-mileage-v3-payload && pnpm build
```

## 全局禁止事项

- 不把 Chromium CDP 当成基础能力。
- 不覆盖用户未授权的 git 改动。
- 不把 Project Mileage 的钱包、订单、权限逻辑写进 CloakBrowser。
- 不在 Project Mileage 前端伪造远程会话、VNC token、倒计时或成功态。
- 不把 proxy 密码、cookie、VNC token、AUTH_TOKEN 写入日志或审计 metadata。
- 不用第三方检测站抓取结果作为 V1 必需依赖。
