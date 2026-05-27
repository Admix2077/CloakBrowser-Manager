# Stopped Profile Cookie Storage 只读评估

## 目标

为“停止态 profile 是否可以通过 Firefox profile dir 导入 cookie”建立安全边界。本评估只讨论风险、推荐方向和未来测试要求，不代表已经实现停止态 cookie 导入 API。

当前结论：本阶段不实现对停止态 Firefox profile dir 的 `cookies.sqlite` 直接写入。现有 Cookie JSON / Netscape import 继续只支持 running profile，并通过 Playwright browser context `add_cookies()` 完成。

## 当前事实

- `POST /api/profiles/{profile_id}/cookies/import` 只允许运行中 profile。
- `POST /api/profiles/{profile_id}/cookies/import/netscape` 只允许运行中 profile。
- stopped profile 调用上述 import API 会返回固定 `404 Profile not running`。
- 当前实现不会读取或写入 Firefox profile dir，不会直接打开 `cookies.sqlite`。
- `profile_bundle` import 当前只导入 profile config，忽略 cookies、local storage 和 profile dir archive。
- `docs/ai-docs/v1/profile-dir-archive-evaluation.md` 已明确 profile dir archive 当前不实现。

## 风险判断

直接写停止态 Firefox cookie 存储不是普通 JSON 导入，风险高于 running context `add_cookies()`：

- Firefox cookie 存储通常是 SQLite 数据库，且可能存在 WAL/SHM 文件。
- Firefox 版本、invisible_playwright 封装和 profile 历史可能影响表结构和字段含义。
- `host/domain`、`path`、`expiry`、`secure`、`httpOnly`、`sameSite`、partition/origin attributes 等字段需要和 Firefox 当前 schema 一致。
- 错误写入可能造成 cookie 丢失、数据库损坏、启动失败或跨站点状态污染。
- 文件路径、SQLite 错误、cookie host/name/value、URL query 或 token 不能进入 API 响应、日志或 audit。
- 停止态离线导入绕过浏览器 API，更难获得浏览器自身校验和规范化。

## 当前禁止范围

当前阶段明确禁止：

- 新增停止态 cookie import REST API。
- 在 stopped profile 上打开或写入 `cookies.sqlite`。
- 直接写 SQLite、WAL 或 SHM 文件。
- 用字符串拼接 SQL 写 cookie 数据。
- 通过 archive 或 bundle import 写入 cookie 明文。
- 自动启动 profile 作为停止态 import 的隐式副作用。
- 在错误、日志、audit、task result 或前端文本中回显 cookie value、cookie name、domain、URL query、fragment、profile dir 绝对路径或 SQLite 原始异常。
- 为 Project Mileage App 暴露任何直接 cookie/profile dir API。

## 推荐方向

如果未来确实需要停止态 cookie 导入，优先级建议如下：

1. 首选继续使用 running profile import：由操作者明确启动 profile，再通过 browser context `add_cookies()` 导入。
2. 如果需要批量导入 stopped profile，优先设计“受控临时启动 -> browser context import -> 受控停止”的显式操作，而不是直接写 SQLite；该操作必须有独立确认、状态可见和失败清理。
3. 只有在确认浏览器 API 方案无法满足时，才评估 SQLite 离线写入，并且必须先完成 disposable profile schema 探测、备份、事务、锁检测和损坏恢复测试。

## 未来 SQLite 评估要求

如后续必须评估离线写入 `cookies.sqlite`，必须先满足：

- 只使用一次性生成的 disposable Firefox/invisible_playwright profile 样本，不读取真实用户 profile dir。
- 通过 SQLite schema introspection 记录当前 `cookies.sqlite` 表结构，不能凭记忆硬编码。
- 使用 SQLite 参数化语句，不拼接 cookie value、domain、path 或 name。
- 在写入前确认 profile 已停止且没有 lock 文件。
- 在写入前备份目标 cookie DB；失败时恢复备份。
- 写入必须包裹在事务内；失败时 rollback。
- 明确 WAL/SHM 处理策略，不能忽略一致性问题。
- 明确 cookie 去重策略：同一 host/name/path/origin attributes 的覆盖或拒绝必须可测试。
- 明确时间字段单位、过期 session cookie 语义和 SameSite 映射。
- 明确 partition/origin attributes 不支持时的拒绝策略，不静默降级。
- 只写 cookie 存储，不写 local storage、IndexedDB、history、downloads、permissions 或 cert/key DB。

## 未来 API 边界

如果未来实现 stopped cookie import，必须是独立可信本地管理 API，不能复用 running import 的默认行为。

建议形态只作为评估占位：

```http
POST /api/profiles/{profile_id}/cookies/import/stopped-profile-dir
```

请求必须包含：

```json
{
  "confirm_stopped_profile_cookie_import": true,
  "document": {
    "format": "cloakbrowser.cookie-json.v1",
    "schema_version": 1,
    "cookies": []
  }
}
```

边界：

- `confirm_stopped_profile_cookie_import` 必须是 JSON boolean，不接受字符串或数字宽松转换。
- profile 必须是 stopped；running profile 应继续使用既有 browser context import。
- 未确认时不读取 profile dir、不打开 SQLite、不写 audit。
- 非法 cookie 文档返回固定错误，不回显 cookie payload。
- SQLite/schema/lock/backup/restore 失败返回固定错误，不回显路径或原始异常。
- 成功响应只返回 `profile_id`、`imported` 和低敏 summary。

## Audit 边界

未来成功导入 stopped profile cookie 时，建议写低敏 audit：

- `event_type=profile_cookie.stopped_dir_imported`。
- `actor_type=local_admin`。
- `profile_id` 为目标 profile。
- metadata 只包含：
  - `format`。
  - `schema_version`。
  - `imported_count`。
  - `session_count`。
  - `persistent_count`。
  - `secure_count`。
  - `http_only_count`。

metadata 禁止包含：

- cookie value。
- cookie name。
- domain、host、path、URL。
- profile dir 路径。
- SQLite 文件名、SQL 语句或原始异常。
- token、secret、proxy password、Authorization。
- Project Mileage 订单、钱包、权限、扣费、续期或审计事实。

## Project Mileage 边界

- Project Mileage App 不能直接调用 CloakBrowser cookie、bundle、profile dir 或 runtime API。
- Payload 仍是账号、订单、钱包、权限、续期、viewer token 和审计事实源。
- 如果远程账号工作台未来需要 stopped profile cookie 导入，必须先提交跨仓 Proposal，由主 agent/Jeff 确认 Payload 安全 DTO、权限、审计、用户风险提示和运营可见边界。
- 本评估不要求修改 `/home/jeff/code/project-mileage-v3-app` 或 `/home/jeff/code/project-mileage-v3-payload`。

## 建议测试清单

未来实现前必须先补失败测试：

- stopped import API 未确认时返回固定 422，不读取 profile dir，不打开 SQLite，不写 audit。
- 字符串或数字确认值不被宽松转换。
- running profile 调用 stopped import API 返回固定错误，并提示使用 running import 路径。
- profile dir 不存在、`cookies.sqlite` 不存在、DB schema 不支持、lock 文件存在时返回固定错误，不回显绝对路径。
- 非法 Cookie JSON / Netscape 文档不回显 cookie payload。
- SQLite 写入使用参数化语句，cookie value/domain/name/path 不进入 logger。
- 写入失败时 rollback 并恢复备份。
- 成功写入后重新启动 disposable profile 能通过 browser context 读回 cookie。
- audit metadata 只包含低敏计数，不包含 cookie value/name/domain/path/profile dir/SQL/异常。
- Project Mileage 字段、viewer token、runtime session、automation task、钱包、订单、权限和审计事实不会进入请求、响应或 audit。

建议命令：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_api.py -q
git diff --check
```

## 本轮验收口径

本轮只要求文档落地：

- 明确当前不实现 stopped profile `cookies.sqlite` 写入。
- 明确 running profile browser context import 仍是当前唯一 cookie import 路径。
- 明确未来如果评估 SQLite 写入，必须先完成 schema、锁、备份、事务、WAL/SHM、一致性、审计和 disposable profile 验证。
- 明确不修改 Project Mileage app/payload。
