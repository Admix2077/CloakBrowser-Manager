# invisible_playwright 迁移剩余产品缺口

本文记录第一阶段收口后仍未完成、但要达到“Manager 面板功能完整且后端采用 `invisible_playwright`”所需的后续工作。当前环境未安装 `bd`，因此先落盘到文档；后续可迁移为 beads issue。

## 第一阶段已收口口径

- Profile CRUD、tags、启动/停止/status、删除运行中 profile、auth、auto-launch、剪贴板 API、noVNC WebSocket path 已有后端测试覆盖。
- Docker 镜像预下载 `invisible_playwright` patched Firefox，并保留 KasmVNC/noVNC 网页操控链路。
- 运行中 profile 的 `cdp_url` 固定为 `null`，CDP HTTP 返回 `501`，CDP WebSocket 关闭为不可用。
- 前端不再把第一阶段未生效的 `platform`、`geoip`、`user_agent`、`human_preset` 暴露为可编辑或生效身份标签。

## 后续必须设计

### 自动化 API 替代 CDP

`invisible_playwright` 使用 Firefox/Juggler，不提供 Chromium CDP。完整产品如果仍要支持“外部脚本控制已运行 profile，同时网页 noVNC 可见”，需要单独设计：

- Juggler/Playwright 桥接 API 的进程模型和权限边界。
- 每个 running profile 的可寻址会话标识、并发控制和错误恢复。
- 与现有 `/api/profiles/{id}/cdp*` 路由的兼容策略：保留 501、替换为新路由，或提供明确迁移文档。
- Python/Node 客户端示例和端到端测试。

### 未映射 profile 字段

这些字段目前仍保留在数据库/API 中，但第一阶段不参与 `invisible_playwright` 启动参数：

- `platform`
- `user_agent`
- `geoip`
- `human_preset`

完整产品需要二选一：

- 实现真实映射，并用 `invisible_playwright` 实测验证；或
- 从 API/数据库迁移方案中标记为 deprecated，避免长期保留无效配置。

### GPU / WebGL preset 校准

当前 GPU preset 仍来自 Chromium/ANGLE 语境。后端虽然会 pin `gpu.vendor` / `gpu.renderer`，但 Firefox/invisible 的真实输出需要重新采样：

- 建立 Firefox patched binary 下的 WebGL 输出基线。
- 用同一 seed、多 profile、多容器重启验证稳定性。
- 将 UI preset 改成已验证的 Firefox/invisible preset，或由后端返回可用 preset。

### 发布与法务文档

README 已说明本分支不再运行 CloakBrowser Chromium binary，但发布前仍需统一：

- UI 标题/品牌是否保留 `CloakBrowser Manager`，或统一为 `CloakBrowser Manager with invisible_playwright`。
- `LICENSE` / `BINARY-LICENSE.md` 对旧 Chromium binary 的叙述是否保留为上游历史背景。
- Docker 镜像说明中明确 patched Firefox 的来源、版本和再分发边界。

### 真实浏览器 CI / smoke

当前单元测试用 mock 覆盖参数映射，容器 smoke 手动验证真实 Firefox 启动。后续应加入可重复的自动化验证：

- Docker build 后运行 `/api/status`、create、launch、VNC handshake、CDP 501、stop。
- 使用容器内 `invisible_playwright` 打开 Manager UI，验证关键字段和 noVNC viewer 基础渲染。
- 对同一 profile 连续 launch/stop/relaunch，验证 stale locks 和 scoped Firefox cleanup。
