# 08 Cookie、Profile 导入导出

## 目标

提供成熟指纹浏览器常见的 cookie 和 profile 迁移能力，同时控制敏感数据暴露风险。

## 任务清单

- [x] 定义 cookie JSON import 格式。
- [x] 定义 cookie JSON export 格式。
- [x] 支持 Netscape cookie import 格式层。
- [x] 支持 Netscape cookie export 格式层。
- [x] 支持 running profile Netscape cookie import API。
- [x] 支持 running profile Netscape cookie export API。
- [x] 仅运行中 profile 允许通过 browser context 导入 cookie。
- [ ] 停止状态 profile 可通过 profile dir 方式导入 cookie 时必须先评估 Firefox 存储格式，不强行实现。
- [x] 导出 cookie 必须写 audit。
- [x] 导出 cookie 必须有显式确认。
- [x] 前端新增 Cookie 管理入口。
- [x] 支持 profile config export：
  - 不包含 cookie。
  - 不包含 proxy password，除非用户选择包含敏感字段。
- [x] 支持 profile config import。
- [x] 完成完整 profile bundle 边界与分阶段方案：
  - manifest。
  - 默认包含/排除项。
  - 显式敏感导出边界。
  - 停止态 profile dir 风险。
- [x] 支持 profile bundle manifest/config-only 格式层。
- [x] 支持 profile bundle config export API。
- [x] 支持 profile bundle config import API。
- [x] 支持 running profile cookie bundle export。
- [x] 完成 local storage 只读评估。
- [x] 支持 running profile 当前 origin local storage bundle export。
- [ ] 后续按分阶段方案实现完整 profile bundle：
  - profile dir。
  - cookies。
  - local storage。
  - fingerprint config。
  - metadata。

## 安全规则

- cookie value 不进入日志。
- cookie 导出文件不自动提交。
- proxy password 默认遮蔽。
- profile bundle 导出必须带风险提示。

## 2026-05-27 Cookie JSON v1 格式层小闭环

当前状态：

- 已新增后端格式辅助模块 `backend/cookie_formats.py`。
- Cookie JSON v1 格式名为 `cloakbrowser.cookie-json.v1`，`schema_version` 固定为 `1`。
- 单条 cookie 支持字段：
  - `name`。
  - `value`。
  - `domain` 或 `url`，必须至少提供一个。
  - `path`，默认 `/`。
  - `expires`。
  - `secure`。
  - `httpOnly`。
  - `sameSite`：`Strict | Lax | None`。
- `CookieJsonDocument` 可作为导入格式校验模型。
- `build_cookie_json_export()` 可基于 Playwright 风格 cookie dict 生成导出文档。
- `cookies_for_playwright()` 可把格式文档转换回 Playwright `context.add_cookies()` 可用的 dict 列表。
- `cookie_json_audit_summary()` 只返回低敏计数：cookie 数、domain/url scope 数、secure/httpOnly 数、session/persistent 数和 sameSite 计数。
- 模型 repr 不显示 cookie `value`；低敏审计摘要不包含 cookie value、cookie name、domain、URL 或 query。
- 本小闭环只定义格式层，不新增公开 API，不读写浏览器 context，不写 `audit_events`，不新增前端入口，不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；App 未来仍不能直连 CloakBrowser cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py -q
# 4 passed
```

## 2026-05-27 JSON cookie import 运行中 profile 小闭环

当前状态：

- 已新增 `POST /api/profiles/{profile_id}/cookies/import`。
- 请求体复用 Cookie JSON v1 格式：
  - `format`：可选，默认 `cloakbrowser.cookie-json.v1`。
  - `schema_version`：固定 `1`。
  - `cookies[]`：复用 `name/value/domain/url/path/expires/secure/httpOnly/sameSite`。
- 该 endpoint 只允许运行中 profile：
  - profile 未运行返回 `404 Profile not running`。
  - 停止状态 profile 不写 Firefox profile dir，不尝试直接修改磁盘 cookie 存储。
- 执行时调用运行中 Playwright browser context 的 `add_cookies()`。
- 响应只返回：
  - `profile_id`。
  - `imported`。
  - 低敏 `summary` 计数。
- 响应、固定错误和 logger warning 均不回显 cookie value、cookie name、domain、URL、query 或 Playwright 原始异常 message。
- 非法 Cookie JSON 文档返回固定 `422 Invalid cookie JSON document`。
- 非 dict 请求体也返回固定 `422 Invalid cookie JSON document`，不使用 FastAPI 默认 validation response 回显原始 input。
- `add_cookies()` 执行失败返回固定 `400 Cookie import failed`。
- 本小闭环不实现 cookie export、不写 `audit_events`、不新增前端入口、不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；App 未来仍不能直连 CloakBrowser cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_cookie_json_adds_cookies_to_running_profile_without_leaking_values backend/tests/test_api.py::test_import_cookie_json_requires_running_profile_without_leaking_payload backend/tests/test_api.py::test_import_cookie_json_rejects_invalid_document_without_leaking_payload backend/tests/test_api.py::test_import_cookie_json_add_cookies_failure_uses_fixed_error_without_leaking_payload -q
# 4 passed
```

## 2026-05-27 JSON cookie export 显式确认与审计小闭环

当前状态：

- 已新增 `POST /api/profiles/{profile_id}/cookies/export`。
- 请求体必须显式传入 JSON boolean `confirm_export: true`，不接受字符串或数字宽松转换；缺失或 `false` 返回固定 `422 Cookie export requires explicit confirmation`，且不读取 browser context、不写 audit。
- 该 endpoint 只允许运行中 profile：
  - profile 未运行返回 `404 Profile not running`。
  - 停止状态 profile 不读 Firefox profile dir，不尝试直接解析磁盘 cookie 存储。
- 执行时调用运行中 Playwright browser context 的 `cookies()`，再构造成 Cookie JSON v1 导出文档。
- 响应返回：
  - `profile_id`。
  - `exported`。
  - 低敏 `summary` 计数。
  - `document`：Cookie JSON v1 文档，包含 cookie 明文；该 API 仅限可信本地管理侧并要求显式确认。
- 成功导出会写 `audit_events`：
  - `event_type`：`cookie.exported`。
  - `actor_type`：`local_admin`。
  - `profile_id`：目标 profile。
  - `metadata`：只包含低敏计数，使用 `total_count/session_count/persistent_count` 等不含 `cookie` 字样的 key，避免通用 audit sanitizer 删除统计字段。
- audit metadata、固定错误和 logger warning 均不回显 cookie value、cookie name、domain、URL、query 或 Playwright 原始异常 message。
- `cookies()` 执行失败返回固定 `400 Cookie export failed`，不写 audit。
- 本小闭环不实现 Netscape 格式、不新增前端入口、不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；App 未来仍不能直连 CloakBrowser cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_cookie_json_requires_explicit_confirmation_without_reading_context backend/tests/test_api.py::test_export_cookie_json_returns_document_and_writes_redacted_audit backend/tests/test_api.py::test_export_cookie_json_requires_running_profile backend/tests/test_api.py::test_export_cookie_json_context_failure_uses_fixed_error_without_audit_or_leak -q
# 4 passed
```

## 2026-05-27 profile config export 敏感字段默认脱敏小闭环

当前状态：

- 既有 `POST /api/profiles/export` 已补齐敏感字段默认边界。
- 请求体支持 `include_sensitive`：
  - 默认 `false`。
  - 必须是 JSON boolean，不接受字符串或数字宽松转换。
  - `false` 时，导出的 `config.proxy` 会移除 `username:password@`，只保留 scheme、host、port。
  - `true` 时，才返回完整 proxy URL，用于可信本地管理侧明确选择导出敏感配置。
- profile config export 仍只导出 profile 配置字段，不包含 cookie、local storage、profile dir、viewer token、runtime session、automation task、钱包、订单、权限或 Project Mileage 业务事实源。
- 本小闭环不新增前端入口、不新增 audit 事件、不实现 profile config import、不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；App 未来仍不能直连 CloakBrowser profile/cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profiles_redacts_proxy_credentials_by_default backend/tests/test_api.py::test_export_profiles_can_include_sensitive_proxy_when_explicitly_requested backend/tests/test_api.py::test_export_profiles_rejects_coerced_sensitive_flag -q
# 3 passed
```

## 2026-05-27 profile config import JSON 小闭环

当前状态：

- 已新增 `POST /api/profiles/config/import`，独立于既有 CSV `POST /api/profiles/import`，避免破坏 CSV 粘贴导入契约。
- 请求体：
  - `schema_version`：固定 `1`。
  - `configs[]`：profile config JSON 数组。
- 每条 config 只从白名单字段创建 profile：
  - `name/fingerprint_seed/proxy/timezone/locale/platform/user_agent/screen_width/screen_height/gpu_vendor/gpu_renderer/hardware_concurrency/humanize/human_preset/headless/geoip/clipboard_sync/auto_launch/color_scheme/launch_args/notes/tags`。
- 明确不导入、不写库、不回显调用方附带的运行态或跨系统事实字段：
  - cookie。
  - local storage。
  - profile dir / `user_data_dir`。
  - runtime session / viewer token / VNC token。
  - automation task。
  - wallet/order/payment/permission/Project Mileage 业务字段。
- 行级导入结果：
  - 有效 config 创建新 profile，返回 `ProfileResponse`。
  - 无效 config 返回 `ok=false` 和固定校验错误，不阻塞同批其他有效 config。
  - `schema_version` 非 `1` 时整体返回 `422`，不产生数据库副作用。
- 支持从 `POST /api/profiles/export` 的 `config` 结果 round-trip 导入；若导出时 `include_sensitive: true`，proxy 凭证会按可信本地管理 API 语义随 config 导入。
- 本小闭环不新增前端入口、不写 audit、不导入 cookie/local storage/profile dir、不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；App 未来仍不能直连 CloakBrowser profile/cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_profile_configs_creates_profiles_from_safe_config_without_runtime_fields backend/tests/test_api.py::test_import_profile_configs_reports_invalid_rows_without_creating_them backend/tests/test_api.py::test_import_profile_configs_rejects_invalid_schema_without_side_effects -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_profile_config_export_can_round_trip_through_config_import -q
# 1 passed
```

## 2026-05-27 Netscape cookie 格式层小闭环

当前状态：

- 已在 `backend/cookie_formats.py` 新增 Netscape cookie 文件格式 helper。
- `parse_netscape_cookies(text, profile_id=None, exported_at=None)`：
  - 解析标准 7 列 Netscape cookie 行。
  - 跳过空行和普通注释行。
  - 支持 `#HttpOnly_` 前缀并映射为 Cookie JSON v1 的 `httpOnly=true`。
  - 解析结果统一转换为 `CookieJsonDocument`，便于复用既有 Cookie JSON v1 导入链路。
  - 非法行返回固定 `Invalid Netscape cookie line <line_number>`，不回显 cookie value、cookie name、domain、URL 或原始行内容。
- `build_netscape_cookie_export(document)`：
  - 从 `CookieJsonDocument` 生成 Netscape cookie 文本。
  - 保留 cookie value 作为导出文件内容；该输出只用于调用方明确导出的文件文本，不写日志或 audit。
  - 对只有 `url` 的 cookie 只提取 hostname，不把 query/fragment/token 写入 Netscape domain 字段。
- `netscape_cookie_audit_summary(document)`：
  - 只输出低敏计数：格式名、cookie 数、secure 数、session/persistent 数、httpOnly 数。
  - 不包含 cookie value、cookie name、domain、URL、query 或 fragment。
- 本小闭环只实现格式层，不新增 REST API，不读写运行中 browser context，不写 `audit_events`，不新增前端入口，不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；App 未来仍不能直连 CloakBrowser cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py -q
# 7 passed
```

## 2026-05-27 前端 Cookie 管理入口小闭环

当前状态：

- 已新增 `frontend/src/components/ProfileCookieManager.tsx`，并接入 `ProfileSummaryPanel` 的单 profile `Cookies` 区域。
- 前端 API adapter 已新增：
  - `api.importProfileCookies(profileId, document)` -> `POST /api/profiles/{profile_id}/cookies/import`。
  - `api.exportProfileCookies(profileId)` -> `POST /api/profiles/{profile_id}/cookies/export`，请求体固定 `{ "confirm_export": true }`。
- Cookie 管理入口只面向 CloakBrowser 可信本地管理台：
  - 只对 `status=running` profile 启用 import/export。
  - stopped profile 显示固定提示并禁用按钮，不调用 cookie API。
  - Import 只接受粘贴 Cookie JSON v1；JSON parse 失败时显示固定 `Invalid Cookie JSON document`。
  - Import 成功或失败后清空 textarea，避免 cookie 明文长时间留在页面。
  - Import 成功只显示 `imported` 数量和低敏 summary 数量。
  - Export 必须先勾选显式确认；响应里的 Cookie JSON document 只用于下载文件，不渲染到页面文本。
- 页面和组件测试覆盖不渲染：
  - cookie value。
  - cookie name。
  - domain。
  - URL query / fragment。
  - token。
- 本小闭环不新增后端 API、不新增 audit 类型、不接 Project Mileage DTO、不修改 Project Mileage app/payload。
- Project Mileage app/payload 本轮无需配合；未来 App 仍不能直连 CloakBrowser cookie/runtime API，必须通过 Payload 安全 DTO。

浏览器验收记录：

- Browser plugin 不在当前工具列表中；本轮使用 Playwright MCP 做渲染验收。
- 使用临时后端 `127.0.0.1:18081` 和临时 SQLite 数据目录 `/tmp/cloakbrowser-ui-check`，不污染真实 `/data`。
- 页面 `http://127.0.0.1:18081/` 标题为 `Invisible Browser Manager`。
- Profile summary 中可见 `Cookies` / `Cookie management` 区域，running profile 显示可用状态。
- 粘贴包含 `cookie name/value/domain/token/fragment` 的非法 JSON 后点击 `Import cookies`：
  - 页面显示固定 `Invalid Cookie JSON document`。
  - textarea 被清空。
  - 页面文本不包含 `browser-secret-value`、`secret-cookie-name`、`private.example`、`browser-token` 或 `#frag`。
- `browser_console_messages(level=warning, all=true)` 返回 `Errors: 0, Warnings: 0`。
- 截图证据：`cloakbrowser-cookie-manager-ui-check.png`。

验证记录：

```bash
cd frontend && npm test -- src/lib/api.test.ts
# 33 passed

cd frontend && npm test -- src/components/ProfileCookieManager.test.tsx
# 4 passed

cd frontend && npm test -- src/components/ProfileSummaryPanel.test.tsx
# 2 passed

cd frontend && npm test -- --run
# 15 files / 208 tests passed

cd frontend && npm run build
# built successfully

. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_api.py -q
# 165 passed
```

## 2026-05-27 Netscape cookie REST API 小闭环

当前状态：

- 已新增 `POST /api/profiles/{profile_id}/cookies/import/netscape`。
- 请求体为 `{ "text": "<Netscape cookie file text>" }`：
  - `text` 必须非空。
  - parser 复用 `parse_netscape_cookies()`，并转换为 Cookie JSON v1 document 后调用运行中 Playwright browser context `add_cookies()`。
- import 只允许运行中 profile：
  - profile 未运行返回 `404 Profile not running`。
  - 停止状态 profile 不写 Firefox profile dir，不尝试直接修改磁盘 cookie 存储。
- import 成功响应只返回：
  - `profile_id`。
  - `imported`。
  - Netscape 低敏 `summary` 计数。
- import 非法 Netscape 文档或无效请求形状返回固定 `422 Invalid Netscape cookie document`，不使用 FastAPI 默认 validation response 回显原始 input；`add_cookies()` 执行失败返回固定 `400 Cookie import failed`。
- 已新增 `POST /api/profiles/{profile_id}/cookies/export/netscape`。
- export 请求体必须显式传入 JSON boolean `confirm_export: true`：
  - 缺失或 `false` 返回固定 `422 Cookie export requires explicit confirmation`。
  - 字符串 `"true"`、`"yes"` 或数字 `1` 不会被宽松转换。
  - 未确认时不读取 browser context、不写 audit。
- export 只允许运行中 profile；profile 未运行返回 `404 Profile not running`，停止状态 profile 不读 Firefox profile dir。
- export 成功时调用运行中 Playwright browser context `cookies()`，先规范化为 Cookie JSON v1，再生成 Netscape cookie 文本。
- export 响应返回：
  - `profile_id`。
  - `exported`。
  - Netscape 低敏 `summary`。
  - `text`：Netscape cookie 文件文本，包含 cookie 明文；该 API 仅限可信本地管理侧并要求显式确认。
- export 成功写 `audit_events`：
  - `event_type`：`cookie.exported`。
  - `actor_type`：`local_admin`。
  - `profile_id`：目标 profile。
  - `metadata`：只包含 `format/total_count/secure_count/session_count/persistent_count/http_only_count` 等低敏统计。
- audit metadata、固定错误和 logger warning 均不回显 cookie value、cookie name、domain、URL、query、fragment、原始 Netscape 行或 Playwright 原始异常 message。
- 本小闭环不新增前端入口、不接 Project Mileage DTO、不修改 Project Mileage app/payload。
- Project Mileage app/payload 本轮无需配合；未来 App 仍不能直连 CloakBrowser cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_cookie_netscape_adds_cookies_to_running_profile_without_leaking_values backend/tests/test_api.py::test_import_cookie_netscape_rejects_malformed_text_without_leaking_payload backend/tests/test_api.py::test_import_cookie_netscape_requires_running_profile_without_leaking_payload backend/tests/test_api.py::test_import_cookie_netscape_add_cookies_failure_uses_fixed_error_without_leaking_payload backend/tests/test_api.py::test_export_cookie_netscape_requires_explicit_confirmation_without_reading_context backend/tests/test_api.py::test_export_cookie_netscape_rejects_coerced_confirmation_without_reading_context backend/tests/test_api.py::test_export_cookie_netscape_returns_text_and_writes_redacted_audit backend/tests/test_api.py::test_export_cookie_netscape_requires_running_profile backend/tests/test_api.py::test_export_cookie_netscape_context_failure_uses_fixed_error_without_audit_or_leak -q
# failed before implementation: 9 failed with 405 Method Not Allowed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_cookie_netscape_adds_cookies_to_running_profile_without_leaking_values backend/tests/test_api.py::test_import_cookie_netscape_rejects_malformed_text_without_leaking_payload backend/tests/test_api.py::test_import_cookie_netscape_requires_running_profile_without_leaking_payload backend/tests/test_api.py::test_import_cookie_netscape_add_cookies_failure_uses_fixed_error_without_leaking_payload backend/tests/test_api.py::test_export_cookie_netscape_requires_explicit_confirmation_without_reading_context backend/tests/test_api.py::test_export_cookie_netscape_rejects_coerced_confirmation_without_reading_context backend/tests/test_api.py::test_export_cookie_netscape_returns_text_and_writes_redacted_audit backend/tests/test_api.py::test_export_cookie_netscape_requires_running_profile backend/tests/test_api.py::test_export_cookie_netscape_context_failure_uses_fixed_error_without_audit_or_leak -q
# 9 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_cookie_json_rejects_invalid_request_shape_without_echoing_input backend/tests/test_api.py::test_import_cookie_netscape_rejects_invalid_request_shape_without_echoing_input -q
# failed before implementation: 2 failed with default validation response echoing input

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_cookie_json_rejects_invalid_request_shape_without_echoing_input backend/tests/test_api.py::test_import_cookie_netscape_rejects_invalid_request_shape_without_echoing_input -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py -q
# 7 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q
# 167 passed
```

## 2026-05-27 前端 Netscape Cookie 管理入口小闭环

当前状态：

- 前端 Cookie 管理入口已从单一 Cookie JSON v1 粘贴框扩展为双模式：
  - `JSON`：沿用 `POST /api/profiles/{profile_id}/cookies/import` 和 `POST /api/profiles/{profile_id}/cookies/export`。
  - `Netscape`：新增调用 `POST /api/profiles/{profile_id}/cookies/import/netscape` 和 `POST /api/profiles/{profile_id}/cookies/export/netscape`。
- 前端 API adapter 已新增：
  - `api.importProfileCookiesNetscape(profileId, text)` -> `POST /api/profiles/{profile_id}/cookies/import/netscape`，请求体 `{ "text": ... }`。
  - `api.exportProfileCookiesNetscape(profileId)` -> `POST /api/profiles/{profile_id}/cookies/export/netscape`，请求体固定 `{ "confirm_export": true }`。
- `ProfileCookieManager` 新增 `JSON / Netscape` 分段模式：
  - 切换模式会清空 textarea、notice、error 和 summary，避免 cookie 明文跨模式残留。
  - 只对 running profile 启用 import/export；stopped profile 继续禁用按钮且不调用任何 cookie API。
  - Netscape import 成功或失败后清空 textarea。
  - Netscape export 仍必须勾选显式确认。
  - Netscape export 响应里的 `text` 只用于下载 `.txt` 文件，不渲染到页面文本。
- 页面和组件测试覆盖不渲染：
  - cookie value。
  - cookie name。
  - domain。
  - URL query / fragment。
  - token。
- 本小闭环不新增后端 API、不新增 audit 类型、不接 Project Mileage DTO、不修改 Project Mileage app/payload。
- Project Mileage app/payload 本轮无需配合；未来 App 仍不能直连 CloakBrowser cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
cd frontend && npm test -- src/lib/api.test.ts
# failed before implementation: 2 failed, api.importProfileCookiesNetscape/api.exportProfileCookiesNetscape missing

cd frontend && npm test -- src/components/ProfileCookieManager.test.tsx
# failed before implementation: 2 failed, Netscape mode button missing

cd frontend && npm test -- src/lib/api.test.ts
# 35 passed

cd frontend && npm test -- src/components/ProfileCookieManager.test.tsx
# 6 passed

cd frontend && npm test -- --run
# 15 files / 212 tests passed

cd frontend && npm run build
# built successfully
```

## 2026-05-27 Profile Bundle 边界与分阶段方案小闭环

当前状态：

- 已新增 `docs/ai-docs/v1/profile-bundle-boundary-plan.md`。
- 该文档明确 profile bundle 的目标是迁移 profile config、cookie、local storage 和必要元数据，但不能把运行态、Project Mileage 业务事实、凭证或审计事实混进可复制包。
- 当前事实已记录：
  - `backend/database.py:create_profile()` 生成 `/data/profiles/{profile_id}` 作为 `user_data_dir`。
  - `backend/browser_manager.py:_build_invisible_kwargs()` 把 `user_data_dir` 作为 invisible_playwright 的 `profile_dir`。
  - `backend/browser_manager.py:_clean_firefox_startup_state()` 只清理 Firefox lock 和 session restore 文件。
  - `backend/main.py:delete_profile()` 删除 profile 时会删除 `user_data_dir`。
- 建议后续格式为 `cloakbrowser.profile-bundle.v1`，先从 manifest/config 低风险能力开始。
- 默认允许包含 profile config 白名单字段、cookie summary 和低敏 manifest metadata。
- 默认禁止包含：
  - `user_data_dir` 绝对路径。
  - Firefox profile dir 原始目录。
  - cookie/local storage 明文。
  - IndexedDB、Cache Storage、Service Worker cache、session restore、history、downloads、form history、cert/key DB。
  - runtime/viewer/VNC/automation/lease 字段。
  - Project Mileage 钱包、订单、支付、扣费、权限、续期、远程工作台 session 或审计事实。
  - `.env`、数据库 dump、secret、token、proxy password。
- 显式敏感导出必须拆成独立 JSON boolean，例如 `include_sensitive_proxy/include_cookies/include_local_storage/include_profile_dir_archive`，不得接受字符串或数字宽松转换。
- 停止态 profile dir 当前只允许先做只读评估和 allowlist/denylist，不实现整目录 zip 导出/导入。
- 后续最小切片已拆为：
  - bundle manifest 格式层。
  - bundle config export API。
  - bundle config import API。
  - running profile cookie bundle。
  - local storage 只读评估。
  - profile dir archive 评估。
- 本小闭环只新增文档，不新增 API，不读取 profile dir，不导出 cookie/local storage 明文，不修改 Project Mileage app/payload。
- Project Mileage app/payload 本轮无需配合；未来 App 仍不能直连 CloakBrowser bundle/cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
git diff --check
# passed
```

## 2026-05-27 Profile Bundle manifest/config-only 格式层小闭环

当前状态：

- 已新增 `backend/profile_bundle.py` 和 `backend/tests/test_profile_bundle.py`。
- Profile Bundle 格式名固定为 `cloakbrowser.profile-bundle.v1`，`schema_version` 固定为 `1`。
- 新增 `build_profile_config_bundle(profile, exported_at, app_version=None, include_sensitive_proxy=False)`：
  - 只构造 manifest/config-only bundle 文档。
  - 复用既有 `ProfileConfigExport` 白名单字段。
  - 默认对 `config.proxy` 调用 `redact_proxy_asset_url()` 脱敏，移除 `username:password@`。
  - 只有显式 `include_sensitive_proxy=True` 时，才在 `profile.config.proxy` 中保留完整 proxy。
- 默认 bundle 结构包含：
  - `profile.config`：profile config 白名单字段。
  - `cookies`：`included=false` 和低敏 `cookie_count=0`。
  - `local_storage`：`included=false` 和 `origin_count=0`。
  - `profile_dir`：`included=false`、文件统计为 0、`archive=null`。
  - `metadata`：app/source profile/include flag 等低敏元数据。
- 默认不包含、不读取、不回显：
  - `user_data_dir`。
  - Firefox profile dir 原始目录。
  - cookie/local storage 明文。
  - runtime session、viewer token、viewer token hash、VNC 字段、automation URL、lease owner。
  - Project Mileage 钱包、订单、支付、权限、续期、远程工作台 session 或审计事实。
- `ProfileBundleDocument.profile` 设置为 `repr=False`，避免显式敏感 proxy 在测试失败、调试输出或日志拼接中通过模型 repr 泄露。
- 本小闭环不新增公开 API，不读取 profile dir，不导出 cookie/local storage 明文，不写 audit，不新增前端入口，不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；未来 App 仍不能直连 CloakBrowser bundle/cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py -q
# failed before implementation: ModuleNotFoundError: No module named 'backend.profile_bundle'

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py -q
# failed before repr hardening: 1 failed, explicit sensitive proxy appeared in repr(bundle)

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py backend/tests/test_bulk.py::test_bulk_export_profile_configs_returns_partial_results backend/tests/test_bulk.py::test_profile_config_export_can_round_trip_through_config_import -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_api.py -q
# 176 passed
```

## 2026-05-27 Profile Bundle config export API 小闭环

当前状态：

- 已新增 `POST /api/profiles/{profile_id}/bundle/export`。
- 请求体：
  - `include_sensitive_proxy`：默认 `false`。
  - 必须是 JSON boolean，不接受字符串或数字宽松转换。
- 成功响应返回：
  - `profile_id`。
  - `bundle`：`cloakbrowser.profile-bundle.v1` config-only manifest。
- 默认响应行为：
  - `profile.config` 只包含既有 `ProfileConfigExport` 白名单字段。
  - proxy 默认脱敏，移除 `username:password@`。
  - `cookies.included=false`，只返回低敏空统计。
  - `local_storage.included=false`，只返回低敏空统计。
  - `profile_dir.included=false`，`archive=null`，不读取磁盘 profile 目录。
- 显式 `include_sensitive_proxy: true` 时，才在可信本地管理 API 响应中保留完整 proxy。
- 请求体 shape 或 `include_sensitive_proxy` 类型非法时，返回固定 `422 Invalid profile bundle export request`，不使用 FastAPI 默认 validation response 回显调用方 payload。
- profile 不存在返回固定 `404 Profile not found`。
- 本小闭环不导出 cookie/local storage 明文，不读取 profile dir，不写 audit，不新增前端入口，不实现 bundle import，不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；未来 App 仍不能直连 CloakBrowser bundle/cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_returns_config_only_manifest_without_sensitive_fields backend/tests/test_api.py::test_export_profile_bundle_can_include_sensitive_proxy_only_when_explicit backend/tests/test_api.py::test_export_profile_bundle_rejects_coerced_sensitive_flag_without_echoing_payload backend/tests/test_api.py::test_export_profile_bundle_requires_existing_profile -q
# failed before implementation: 4 failed with 405 Method Not Allowed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_returns_config_only_manifest_without_sensitive_fields backend/tests/test_api.py::test_export_profile_bundle_can_include_sensitive_proxy_only_when_explicit backend/tests/test_api.py::test_export_profile_bundle_rejects_coerced_sensitive_flag_without_echoing_payload backend/tests/test_api.py::test_export_profile_bundle_requires_existing_profile -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py backend/tests/test_api.py -q
# 177 passed

. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_bulk.py::test_bulk_export_profile_configs_returns_partial_results backend/tests/test_bulk.py::test_profile_config_export_can_round_trip_through_config_import -q
# 9 passed
```

## 2026-05-27 Profile Bundle config import API 小闭环

当前状态：

- 已新增 `POST /api/profiles/bundle/import`。
- 请求体为 `{ "bundle": ... }`，只接受 `cloakbrowser.profile-bundle.v1` / `schema_version=1`。
- import 只读取 `bundle.profile.config`：
  - 复用既有 `ProfileConfigExport` 和 `ProfileCreate` 校验。
  - 只按 profile config 白名单字段创建新 profile。
  - 创建新 profile、新 UUID、新 `user_data_dir`。
- import 明确忽略、不导入、不回显：
  - 调用方附带的 `user_data_dir`、`status`、`automation_url`、VNC 字段。
  - `cookies` 明文。
  - `local_storage` 明文。
  - `profile_dir.archive` 或完整 profile dir。
  - Project Mileage 钱包、订单、支付、权限、viewer token 或审计事实。
- 非法 bundle 返回固定 `422 Invalid profile bundle document`，不使用 FastAPI 默认 validation response 回显调用方 payload。
- config 校验失败时返回 `ProfileConfigImportResponse` 行级失败结果，不创建 profile。
- 本小闭环不导入 cookie/local storage/profile dir，不读取磁盘 profile 目录，不覆盖既有 profile，不写 audit，不新增前端入口，不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；未来 App 仍不能直连 CloakBrowser bundle/cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_profile_bundle_creates_new_profile_from_config_only_manifest backend/tests/test_api.py::test_import_profile_bundle_rejects_invalid_bundle_without_echoing_payload -q
# failed before implementation: 2 failed with 405 Method Not Allowed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_profile_bundle_creates_new_profile_from_config_only_manifest backend/tests/test_api.py::test_import_profile_bundle_rejects_invalid_bundle_without_echoing_payload -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py backend/tests/test_api.py -q
# 179 passed

. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_bulk.py::test_profile_config_export_can_round_trip_through_config_import -q
# 8 passed

git diff --check
# passed
```

## 2026-05-27 running profile cookie bundle export 小闭环

当前状态：

- `POST /api/profiles/{profile_id}/bundle/export` 已支持 running profile cookie bundle。
- 请求体新增：
  - `include_cookies`：默认 `false`，必须是 JSON boolean。
  - `confirm_cookie_export`：默认 `false`，必须是 JSON boolean。
- 只有 `include_cookies=true` 且 `confirm_cookie_export=true` 时，才读取运行中 browser context 的 `cookies()`。
- `include_cookies=true` 但未显式确认时返回固定 `422 Profile bundle cookie export requires explicit confirmation`，不读取 context、不写 audit。
- `include_cookies=true` 但 profile 未运行时返回固定 `404 Profile not running`，不读取停止态 Firefox profile dir。
- 成功响应中：
  - `bundle.cookies.included=true`。
  - `bundle.cookies.document` 为 Cookie JSON v1 文档，包含 cookie 明文；该能力仅限可信本地管理 API 和显式确认。
  - `bundle.cookies.summary` 为低敏计数。
  - `bundle.metadata.cookies_included=true`。
- config-only 默认响应不输出 `cookies.document: null`，避免误导调用方认为存在 cookie payload。
- 成功 cookie bundle export 写低敏 audit：
  - `event_type=profile_bundle.cookie_exported`。
  - `actor_type=local_admin`。
  - `profile_id` 为目标 profile。
  - metadata 只包含格式、schema 和计数，不包含 cookie value、cookie name、domain、URL、query 或 fragment。
- 本小闭环不导入 cookie，不读取停止态 profile dir，不导出 local storage，不新增前端入口，不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；未来 App 仍不能直连 CloakBrowser bundle/cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_cookie_bundle_requires_explicit_confirmation_without_reading_context backend/tests/test_api.py::test_export_profile_bundle_cookie_bundle_rejects_coerced_flags_without_reading_context backend/tests/test_api.py::test_export_profile_bundle_cookie_bundle_requires_running_profile backend/tests/test_api.py::test_export_profile_bundle_cookie_bundle_embeds_cookie_json_and_writes_redacted_audit -q
# failed before implementation: 4 failed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_cookie_bundle_requires_explicit_confirmation_without_reading_context backend/tests/test_api.py::test_export_profile_bundle_cookie_bundle_rejects_coerced_flags_without_reading_context backend/tests/test_api.py::test_export_profile_bundle_cookie_bundle_requires_running_profile backend/tests/test_api.py::test_export_profile_bundle_cookie_bundle_embeds_cookie_json_and_writes_redacted_audit -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_returns_config_only_manifest_without_sensitive_fields backend/tests/test_api.py::test_export_profile_bundle_cookie_bundle_embeds_cookie_json_and_writes_redacted_audit -q
# 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py backend/tests/test_api.py -q
# 183 passed

. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_bulk.py::test_profile_config_export_can_round_trip_through_config_import -q
# 8 passed
```

## 2026-05-27 local storage 只读评估小闭环

当前状态：

- 已新增 `docs/ai-docs/v1/local-storage-bundle-readonly-evaluation.md`。
- 本小闭环只做评估文档，不新增 API，不读取 profile dir，不读取 local storage 明文，不修改前端。
- 评估结论：
  - 不采用 `context.storage_state()` 作为默认实现，因为它可能跨 origin 导出大量站点状态。
  - 不实现停止态 profile dir 读取，因为 Firefox local storage / IndexedDB / SQLite / cache 数据结构复杂且泄露面大。
  - 推荐后续最小实现只读取 running profile 指定 `page_ref` 当前 origin 的 `window.localStorage`。
- 推荐后续扩展 `POST /api/profiles/{profile_id}/bundle/export`：
  - `include_local_storage`：默认 `false`，必须 JSON boolean。
  - `confirm_local_storage_export`：默认 `false`，必须 JSON boolean。
  - `local_storage_page_ref`：默认 `"0"`，必须是当前 running profile 的 page index 或 page id。
- 推荐安全边界：
  - 只允许 running profile。
  - 只读取当前 page origin。
  - 使用固定内部脚本读取，不接受调用方提供 JavaScript expression。
  - 不扫描所有 tabs。
  - 不读取 sessionStorage、IndexedDB、Cache Storage、Service Worker cache、history、downloads、form history、cert/key DB。
  - 不写 local storage key/value 到 logger、audit metadata 或 task result。
- 推荐 audit 只写低敏计数和可选 `origin_hash`，不写 origin 原文、key、value、URL query 或 fragment。
- 本小闭环不接 Project Mileage DTO，不修改 Project Mileage app/payload；未来 App 仍不能直连 CloakBrowser bundle/local storage/cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
git diff --check
# passed
```

## 2026-05-27 running profile local storage bundle export 小闭环

当前状态：

- `POST /api/profiles/{profile_id}/bundle/export` 已支持 running profile 当前 origin local storage bundle。
- 请求体新增：
  - `include_local_storage`：默认 `false`，必须是 JSON boolean。
  - `confirm_local_storage_export`：默认 `false`，必须是 JSON boolean。
  - `local_storage_page_ref`：默认 `"0"`，必须是当前 running profile 的 page index 或 page id。
- 只有 `include_local_storage=true` 且 `confirm_local_storage_export=true` 时，才读取指定 page 的 `window.localStorage`。
- 未显式确认时返回固定 `422 Profile bundle local storage export requires explicit confirmation`，不读取 page、不写 audit。
- 字符串或数字 boolean 不会被宽松转换；非法请求体返回固定 `422 Invalid profile bundle export request`，不回显调用方 payload。
- profile 未运行返回固定 `404 Profile not running`。
- page 不存在沿用固定 `404 Automation page not found`。
- 当前 page URL 没有 `http/https` origin 时返回固定 `400 Local storage origin unavailable`，不回显完整 URL。
- 成功响应中：
  - `bundle.local_storage.included=true`。
  - `bundle.local_storage.format=cloakbrowser.local-storage.v1`。
  - `bundle.local_storage.schema_version=1`。
  - `bundle.local_storage.origin` 只包含 scheme/host/port，不包含 path/query/fragment。
  - `bundle.local_storage.entries` 包含 local storage 明文；该能力仅限可信本地管理 API 和显式确认。
  - `bundle.metadata.local_storage_included=true`。
- config-only 默认响应仍只保留 `local_storage.included=false` 和 `origin_count=0`，不输出 `entries=null`、`origin=null` 或误导性格式字段。
- 成功 local storage bundle export 写低敏 audit：
  - `event_type=profile_bundle.local_storage_exported`。
  - `actor_type=local_admin`。
  - `profile_id` 为目标 profile。
  - metadata 只包含格式、schema、entry_count、total_value_bytes 和 `origin_hash`。
  - audit 不包含 local storage key、value、origin 原文、URL query 或 fragment。
- 本小闭环不导入 local storage，不读取停止态 profile dir，不使用 `context.storage_state()`，不扫描所有 tabs，不读取 sessionStorage/IndexedDB/cache/history，不新增前端入口，不接 Project Mileage DTO。
- Project Mileage app/payload 本轮无需配合；未来 App 仍不能直连 CloakBrowser bundle/local storage/cookie/runtime API，必须通过 Payload 安全 DTO。

验证记录：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_local_storage_requires_explicit_confirmation_without_reading_page backend/tests/test_api.py::test_export_profile_bundle_local_storage_rejects_coerced_flags_without_reading_page backend/tests/test_api.py::test_export_profile_bundle_local_storage_requires_running_profile backend/tests/test_api.py::test_export_profile_bundle_local_storage_rejects_pages_without_safe_origin backend/tests/test_api.py::test_export_profile_bundle_local_storage_embeds_current_origin_entries_and_redacted_audit -q
# failed before implementation: 5 failed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_local_storage_requires_explicit_confirmation_without_reading_page backend/tests/test_api.py::test_export_profile_bundle_local_storage_rejects_coerced_flags_without_reading_page backend/tests/test_api.py::test_export_profile_bundle_local_storage_requires_running_profile backend/tests/test_api.py::test_export_profile_bundle_local_storage_rejects_pages_without_safe_origin backend/tests/test_api.py::test_export_profile_bundle_local_storage_embeds_current_origin_entries_and_redacted_audit -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py::test_build_profile_config_bundle_defaults_to_safe_manifest_without_sensitive_fields backend/tests/test_api.py::test_export_profile_bundle_returns_config_only_manifest_without_sensitive_fields backend/tests/test_api.py::test_export_profile_bundle_local_storage_embeds_current_origin_entries_and_redacted_audit -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py backend/tests/test_api.py -q
# 188 passed

. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_bulk.py::test_profile_config_export_can_round_trip_through_config_import -q
# 8 passed
```

## 验证

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_api.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [ ] JSON cookie 导入后页面可读到 cookie。
- [ ] JSON cookie 导出不破坏字段。
- [x] Netscape 格式基础兼容。
- [x] Netscape import/export API 只作用于 running profile。
- [x] 导出动作写 audit 且不记录 cookie 明文。
