# CloakBrowser 部署备份与恢复 Runbook

## 目标

本文说明单机 Docker 部署下如何备份和恢复 CloakBrowser 的持久化数据，并明确哪些内容不能进入 Git、日志、issue、截图或 Project Mileage 前端链路。

当前 runbook 是人工运维步骤和安全边界，不代表已经实现自动 backup/restore API，也不代表已经完成恢复后真实 profile 启动验收。

## 数据范围

默认 Docker/Compose 部署把宿主持久化目录挂载到容器内 `/data`。需要作为同一个快照整体保存的内容：

- `/data/profiles.db`：SQLite 数据库，包含 profile、proxy、automation task、audit、runtime session 等本地事实。
- `/data/profiles/`：Firefox profile dirs，可能包含 cookie、local storage、session、cache、扩展数据和站点状态。

`/data/profiles.db` 与 `/data/profiles/` 必须按同一时间点备份。只备份其中一个会造成 DB 记录和浏览器磁盘状态不一致。

## 备份前检查

1. 确认当前没有正在启动、运行或自动化中的 profile。
2. 停止 CloakBrowser 容器，推荐执行：

```bash
docker compose down
```

3. 当前不支持热备。不要在 profile 运行中复制 `/data/profiles.db` 或 `/data/profiles/`。
4. 备份前不要打开、读取、打印 `.env`、token、cookie、local storage、proxy password 或 profile dir 内部文件内容。

## 备份步骤

以下示例只描述操作形态，实际备份路径应放在受控的服务器备份目录或加密介质中，不要放进项目仓库：

```bash
BACKUP_DIR=/secure-backups/cloakbrowser/$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$BACKUP_DIR"
cp -a ~/.invisible-browser-manager/profiles.db "$BACKUP_DIR/profiles.db"
cp -a ~/.invisible-browser-manager/profiles "$BACKUP_DIR/profiles"
```

备份完成后记录低敏信息即可，例如备份时间、文件数量、总大小和操作者。不要记录 cookie value、local storage value、proxy URL、proxy password、AUTH_TOKEN、RUNTIME_SERVICE_TOKEN、viewer token、runtime service token、订单号、钱包流水或用户凭证。

## 恢复前检查

恢复前先备份当前 /data，避免覆盖现场后无法回滚：

```bash
docker compose down
ROLLBACK_DIR=/secure-backups/cloakbrowser/pre-restore-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$ROLLBACK_DIR"
cp -a ~/.invisible-browser-manager/profiles.db "$ROLLBACK_DIR/profiles.db"
cp -a ~/.invisible-browser-manager/profiles "$ROLLBACK_DIR/profiles"
```

确认目标备份来自同一部署环境或明确兼容的版本。不要把未知来源的 profile dir 直接恢复到生产实例；未知来源备份可能包含恶意扩展、持久登录态、过期 session、损坏 SQLite 或路径污染风险。

## 恢复步骤

1. 停止服务：

```bash
docker compose down
```

2. 清空或移走当前 `/data` 对应宿主目录中的旧 `profiles.db` 和 `profiles/`。
3. 从同一个备份快照恢复：

```bash
cp -a "$BACKUP_DIR/profiles.db" ~/.invisible-browser-manager/profiles.db
cp -a "$BACKUP_DIR/profiles" ~/.invisible-browser-manager/profiles
```

4. 启动服务：

```bash
docker compose up -d
```

5. 做低敏健康检查：

```bash
curl -fsS http://127.0.0.1:8080/api/status
```

`/api/status` 只用于确认服务可用和低敏计数，不代表每个 profile 都已恢复成功。后续应在本地可信管理台中手动启动一个低风险测试 profile 验证浏览器可启动、VNC 可连接、停止可释放资源。

## 禁止范围

- 不要提交备份包、`.env`、SQLite dump、profile dir archive、cookie、local storage、proxy password、AUTH_TOKEN、RUNTIME_SERVICE_TOKEN、viewer token 或任何 secret。
- 不要把备份包复制到 `/home/jeff/code` 下的项目仓库、`_archive/` 敏感恢复资料之外的公共位置、issue、聊天记录或截图。
- 不要在日志中打印 `cp` 出来的文件内容、SQLite row、cookie value、local storage value、完整 proxy URL、完整 profile path 或 token。
- 不要把本 runbook 当作 Project Mileage 权限、订单、钱包、支付、退款、续期、viewer token 或远程屏幕流实现。
- Project Mileage app/payload 当前不参与本地备份恢复。App 不能直连 CloakBrowser runtime、diagnostics、backup 或 restore 能力；未来如需远程工作台备份/恢复状态，只能由 Payload 通过安全 DTO 定义，并由 Payload 持有服务端凭证。

## 验收建议

命令行验收：

```bash
docker compose down
docker compose up -d
curl -fsS http://127.0.0.1:8080/api/status
```

浏览器验收：

- 打开 `http://localhost:8080`。
- 确认 profile 列表存在预期条目。
- 启动一个低风险 profile。
- 确认 VNC viewer 能连接。
- 停止该 profile 后确认状态恢复为 stopped。

本轮只完成 runbook 和 guardrail 测试；`备份 SQLite`、`备份 profile dirs`、`恢复后可启动 profile` 仍需要后续真实命令和浏览器验收后才能标完成。
