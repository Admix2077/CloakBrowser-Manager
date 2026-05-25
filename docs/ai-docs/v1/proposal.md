# CloakBrowser Invisible Manager V1 需求文档

## 1. 目标

开发一个成熟的指纹浏览器运行时与多账号运营平台，最终支撑 Project Mileage 的远程账号工作台。

产品必须同时满足两类使用场景：

1. 独立指纹浏览器管理：
   - 管理 profile。
   - 配置代理和指纹。
   - 启动 Firefox 隔离环境。
   - 通过 VNC 操作。
   - 通过 Automation REST API 自动化。
   - 检测指纹健康。
2. 业务平台远程账号运行时：
   - Project Mileage 用户购买账号后进入远程浏览器。
   - 运营监控远程会话。
   - Payload 负责授权、扣费、审计和敏感字段保护。
   - CloakBrowser 负责实际浏览器 runtime。

## 2. 用户角色

### 2.1 系统管理员

关注点：

- Docker 部署是否稳定。
- profile 数据是否可备份。
- 运行中浏览器数量是否可控。
- VNC / Automation API 是否安全。
- 出问题时是否能定位日志和恢复。

### 2.2 多账号运营人员

关注点：

- 哪些 profile 可用。
- 哪些 profile 指纹异常。
- 哪些代理失效。
- 哪些账号正在运行。
- 能否批量启动、停止、检测、打标签。
- 能否快速进入 VNC 操作。

### 2.3 自动化脚本使用者

关注点：

- 是否能通过 API 启动 profile。
- 是否能列出页面、跳转、执行 JS、截图。
- 是否能批量跑任务。
- 失败原因是否明确。
- 是否有并发限制和任务日志。

### 2.4 Project Mileage 用户

关注点：

- 在业务平台中打开远程账号。
- 不需要理解 profile、代理、指纹细节。
- 会话稳定、可续期、可恢复。
- 不看到账号密码、VNC token 或基础设施细节。

### 2.5 Project Mileage 运营

关注点：

- 哪些用户正在使用远程账号。
- 哪些会话异常。
- 能否终止违规会话。
- 是否有审计记录。
- 能否把账号库存和浏览器 profile 对应起来。

## 3. 功能需求

### 3.1 Profile 管理

必须支持：

- 创建 profile。
- 编辑 profile。
- 删除 profile。
- 启动 profile。
- 停止 profile。
- 查看运行状态。
- 查看 VNC 入口。
- 查看 Automation API 入口。
- notes。
- tags。
- 运行中 profile 防重复启动。

增强目标：

- folders / groups。
- profile clone。
- profile template。
- profile import/export。
- profile history。
- last launch time。
- last stop time。
- last error。

### 3.2 指纹参数

当前必须支持：

- fingerprint seed。
- proxy。
- timezone。
- locale。
- platform。
- user agent。
- screen width / height。
- GPU vendor。
- GPU renderer。
- hardware concurrency。
- color scheme。
- humanize。
- launch args。
- profile dir。

增强目标：

- 参数来源标记：
  - seed 派生。
  - 手动覆盖。
  - GeoIP 自动同步。
  - template 继承。
- 参数冲突提示。
- Firefox 参数兼容性提示。
- 不同国家 locale/timezone 自动建议。

### 3.3 GeoIP 与语言时区同步

必须支持：

- 按当前出口 IP 自动解析：
  - IP。
  - country。
  - timezone。
  - locale。
  - provider source。
  - resolved_at。
- 有代理时通过代理出口解析。
- 无代理时通过容器出口解析。
- 多 provider fallback。
- 自动结果写入 `last_geoip_*`。
- 不覆盖手动 `timezone` / `locale`。
- 启动时注入一致的 `navigator.language`、`navigator.languages` 和 `Accept-Language`。

增强目标：

- 健康检测不启动浏览器即可执行。
- GeoIP 过期提醒。
- 手动覆盖与自动检测冲突提醒。
- 多国家语言映射表。
- provider 失败统计。

### 3.4 健康检测

健康状态：

```text
good | warning | error | unknown
```

检测项：

- proxy 格式。
- proxy 连通性。
- 出口 IP。
- country。
- timezone。
- locale。
- language header。
- manual override。
- GeoIP 结果是否过期。
- VNC 是否可达。
- Automation API 是否可达。
- profile 是否运行中。
- 最近启动失败原因。

输出：

- 状态。
- 风险项。
- 推荐修复动作。
- 最近检测时间。
- 检测来源。

### 3.5 Proxy Manager

必须支持：

- 保存 proxy。
- 编辑 proxy。
- 删除 proxy。
- 测试 proxy。
- 标记国家、城市、ASN、供应商、成本、备注。
- 给 profile 分配 proxy。
- 批量检测。

增强目标：

- CSV 导入。
- 随机分配。
- 按标签分配。
- proxy pool。
- 失败自动下线。
- 按国家匹配 locale/timezone。
- proxy 成本统计。

### 3.6 Profile 运营台

首页必须从“空态 + 单 profile 编辑”升级成运营台。

必须显示：

- profile 名称。
- status。
- health。
- proxy。
- IP。
- country。
- timezone。
- locale。
- tags。
- 最近检测时间。
- 操作按钮。

必须支持：

- 搜索。
- 筛选。
- 排序。
- 多选。
- 批量启动。
- 批量停止。
- 批量检测。
- 批量打标签。
- 批量删除。

### 3.7 VNC Viewer

必须支持：

- 嵌入 noVNC。
- 连接状态。
- 全屏。
- 剪贴板同步。
- Automation API URL 复制。
- 环境条显示 IP、country、timezone、locale、profile name。

增强目标：

- 多窗口 tiled view。
- 会话重连。
- 只读模式。
- 运营监控模式。
- 临时访问 token。
- 会话水印。
- 截图。
- 录屏或关键帧记录。

### 3.8 Automation REST API

必须支持：

- 获取 profile automation info。
- list pages。
- goto。
- evaluate。
- screenshot。
- clipboard get/set。

增强目标：

- create page。
- close page。
- wait for selector。
- click。
- fill。
- upload file。
- download file。
- network logs。
- console logs。
- script task。
- task queue。
- task logs。
- webhook。

### 3.9 Script Runner / RPA

目标：

- 用配置化步骤替代手写脚本。
- 支持账号 warm-up、批量打开 URL、截图、简单表单。

第一阶段步骤：

- open URL。
- wait。
- click。
- fill。
- scroll。
- evaluate。
- screenshot。
- close。

后续阶段：

- 条件判断。
- 循环。
- 变量。
- 失败重试。
- 定时任务。
- 并发限制。

### 3.10 Cookie 与 Profile 导入导出

必须支持：

- cookie JSON 导入。
- cookie JSON 导出。
- Netscape cookie 导入。
- Netscape cookie 导出。

增强目标：

- profile 配置导入导出。
- profile 完整包导出。
- profile 完整包导入。
- 敏感字段加密。
- 导出权限控制。

### 3.11 Project Mileage 远程会话

目标：

- Project Mileage 用户通过业务页面进入浏览器。
- CloakBrowser 提供 runtime。
- Payload 控制授权、扣费、审计。

必须设计：

- remote account 和 browser profile 的映射。
- remote session 生命周期。
- VNC access token。
- session lease。
- wallet billing。
- renewal。
- termination。
- audit。
- operator monitor。

默认边界：

- CloakBrowser 不直接读取 Project Mileage 用户余额。
- CloakBrowser 不直接决定用户是否有权访问账号。
- Project Mileage 不暴露底层 VNC token 和 profile secrets 给用户。

## 4. 非功能需求

### 4.1 安全

- API 可启用 `AUTH_TOKEN`。
- WebSocket 防跨站。
- VNC token 需要短生命周期。
- proxy 密码遮蔽。
- cookie/profile 导出需要权限和审计。
- Automation API 需要权限隔离。
- 删除、导出、终止会话等高风险操作需要确认。

### 4.2 稳定性

- profile 启动失败要可恢复。
- stale lock 自动清理。
- session restore 不破坏登录态。
- 并发启动有限制。
- 容器重启后 auto_launch 可控。
- VNC 断开可重连。

### 4.3 可观测性

- 运行中 profile 数。
- 启动失败数。
- proxy 检测失败数。
- GeoIP provider 失败数。
- VNC 连接数。
- task queue 状态。
- 最近错误。

### 4.4 可维护性

- 模块拆分清晰。
- 健康规则可测试。
- API schema 明确。
- 前端状态可测试。
- 三仓集成契约独立文档化。

## 5. 不确定问题

后续进入实现前需要逐步确认：

- Project Mileage 远程会话扣费模型。
- 账号库存和 browser profile 的绑定方式。
- 运营是否能接管用户会话。
- 是否需要录屏。
- 是否需要团队权限。
- 是否需要对外商业化 API。
- 是否需要跨机器调度多个 browser worker。

本文默认先实现 CloakBrowser 独立运行时能力，再进入 Project Mileage 契约落地。
