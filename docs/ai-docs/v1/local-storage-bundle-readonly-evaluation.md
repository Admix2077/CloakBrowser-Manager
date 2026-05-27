# Local Storage Bundle 只读评估

## 目标

为后续 profile bundle 支持 local storage 建立低风险边界。本评估只讨论可行方案和安全约束，不代表已经实现 local storage 导入导出 API。

local storage 和 cookie 一样可能包含登录态、业务 token、用户输入和站点内部状态，因此不能作为普通 metadata 默认导出，也不能从停止态 profile 目录直接读取。

## 当前事实

- 当前 `backend/profile_bundle.py` 只保留 `local_storage.included=false` 和 `origin_count=0` 的占位统计。
- 当前 `POST /api/profiles/{profile_id}/bundle/export` 已支持：
  - config-only manifest。
  - 显式敏感 proxy。
  - running profile cookie bundle。
- 当前 Automation API 已支持 page 级 `evaluate`，但该能力是通用可信管理 API，不适合作为 Project Mileage App 直接入口。
- 当前没有专用 local storage API。
- 当前没有读取停止态 Firefox profile dir 的实现。

## 可选方案

### 方案 A：使用 Playwright context storage_state

优点：

- 可能一次拿到多个 origin 的 local storage。
- 更接近浏览器上下文迁移语义。

风险：

- 可能跨 origin 导出大量站点数据，不符合最小授权。
- 难以向操作者清楚说明具体包含哪些 origin。
- 容易把登录 token、第三方应用状态、缓存身份标识混入 bundle。
- audit 和错误处理更容易误记录 origin 或 key 细节。

结论：当前阶段不采用。

### 方案 B：running page 当前 origin 固定脚本读取

优点：

- 只读取操作者当前正在看的页面 origin。
- 不扫描跨 origin 数据。
- 不读取停止态 profile dir。
- 可以复用已有 running profile/page_ref 边界。
- 失败面小，容易测试“只读、不泄露 audit、不宽松确认”。

风险：

- 只能覆盖当前页面 origin，迁移完整性较弱。
- 响应仍包含 local storage 明文，必须显式确认并限定可信本地管理 API。
- 需要明确 `about:blank`、`file:`、无 origin 页面不支持。

结论：推荐作为后续最小实现切片。

### 方案 C：停止态 profile dir 读取

优点：

- 理论上可以做完整迁移。

风险：

- Firefox local storage、IndexedDB、SQLite/WAL/SHM、Cache Storage 等数据结构复杂。
- 可能破坏一致性或导出大量无关账号状态。
- 需要完整 allowlist/denylist、文件类型审计、路径安全、版本兼容和导入隔离设计。

结论：当前阶段禁止实现。必须等 profile dir archive 评估完成后再重新审查。

## 推荐后续 API 形态

建议继续扩展可信本地管理 API：

```http
POST /api/profiles/{profile_id}/bundle/export
```

新增请求字段：

```json
{
  "include_local_storage": true,
  "confirm_local_storage_export": true,
  "local_storage_page_ref": "0"
}
```

字段规则：

- `include_local_storage` 默认 `false`，必须是 JSON boolean。
- `confirm_local_storage_export` 默认 `false`，必须是 JSON boolean。
- `local_storage_page_ref` 默认 `"0"`，必须是当前 running profile 里的 page index 或 page id。
- `include_local_storage=true` 时必须要求 `confirm_local_storage_export=true`。
- 未确认时不读取 page、不写 audit。
- profile 未运行返回固定 `404 Profile not running`。
- page 不存在返回固定 `404 Page not found`。
- 当前 page URL 无安全 origin 时返回固定错误，例如 `400 Local storage origin unavailable`。

建议响应片段：

```json
{
  "local_storage": {
    "included": true,
    "format": "cloakbrowser.local-storage.v1",
    "schema_version": 1,
    "origin": "https://example.com",
    "entry_count": 2,
    "entries": [
      {"key": "name", "value": "value"}
    ]
  },
  "metadata": {
    "local_storage_included": true
  }
}
```

## 安全边界

- 只允许 running profile。
- 只读取指定 `page_ref` 当前 origin 的 `window.localStorage`。
- 使用固定内部脚本读取，不接受调用方提供的 JavaScript expression。
- 不扫描所有 tabs。
- 不使用 `context.storage_state()` 做默认实现。
- 不读取停止态 Firefox profile dir。
- 不读取 IndexedDB、Cache Storage、Service Worker cache、sessionStorage、history、downloads、form history、cert/key DB。
- 不自动导航页面到指定 URL。
- 不把 local storage key/value 写入 logger。
- 不把 local storage key/value 写入 audit metadata。
- 不把 local storage key/value 写入 task result。
- 不接 Project Mileage DTO。

## Audit 边界

成功导出 local storage bundle 时，建议写低敏 audit：

- `event_type=profile_bundle.local_storage_exported`。
- `actor_type=local_admin`。
- `profile_id` 为目标 profile。
- metadata 只包含：
  - `format`。
  - `schema_version`。
  - `entry_count`。
  - `total_value_bytes`。
  - `origin_hash`，如确实需要关联来源时使用 hash，不写 origin 原文。

metadata 禁止包含：

- local storage key。
- local storage value。
- origin 原文。
- 完整 URL、query、fragment。
- token、secret、cookie、Authorization。

## 导入边界

后续如果实现 import，必须单独切片，不能混入只读 export：

- 只允许 running profile。
- 只允许写入当前 page origin 的 localStorage。
- bundle origin 必须与当前 page origin 完全一致。
- 不自动导航。
- 不跨 origin 写入。
- 不覆盖未在 bundle 中出现的既有 key，除非另有显式 destructive flag。
- destructive flag 必须是 JSON boolean 且另有确认。

## Project Mileage 边界

- Project Mileage App 不能直接调用 CloakBrowser local storage、bundle、cookie 或 runtime API。
- Payload 仍是账号、订单、钱包、权限、续期、viewer token 和审计事实源。
- 如果远程账号工作台未来需要 local storage 迁移能力，必须先提交跨仓 Proposal，由主 agent/Jeff 确认 Payload 安全 DTO、权限、审计和用户可见风险提示。
- 本评估不要求修改 `/home/jeff/code/project-mileage-v3-app` 或 `/home/jeff/code/project-mileage-v3-payload`。

## 建议测试

后续实现方案 B 时，建议先补失败测试：

- `include_local_storage=true` 且未确认时返回固定 422，不调用 page evaluate，不写 audit。
- 字符串或数字 boolean 不被宽松转换。
- stopped profile 返回 `404 Profile not running`。
- page 不存在返回固定 `404 Page not found`。
- `about:blank` 或无 origin 页面返回固定错误，不回显完整 URL。
- 成功只读取当前 page origin 的 localStorage。
- 响应包含 local storage 明文，但 audit/log/error 不包含 key/value/origin 原文/URL query/fragment。
- config-only 和 cookie bundle 既有响应不受影响。

建议命令：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py backend/tests/test_cookies.py -q
git diff --check
```
