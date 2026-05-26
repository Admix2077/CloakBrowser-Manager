# 04 Proxy Manager

## 目标

把 profile 内的单个 proxy 字符串升级为可管理的代理资产池，支持保存、检测、筛选、批量导入和分配。

## 主要文件

预计修改：

- `backend/database.py`
- `backend/models.py`
- `backend/main.py`
- `backend/geoip.py`
- `frontend/src/lib/api.ts`
- `frontend/src/App.tsx`

预计新增：

- `backend/proxies.py`
- `backend/tests/test_proxies.py`
- `frontend/src/components/ProxyTable.tsx`
- `frontend/src/components/ProxyForm.tsx`
- `frontend/src/components/ProxyCheckResult.tsx`

## 任务清单

- [x] 新增 `proxies` 表。
- [x] 新增 proxy CRUD。
- [x] 新增 `POST /api/proxies/{id}/check`。
- [x] 新增 `POST /api/proxies/bulk/check`。
- [x] 支持字段：
  - name。
  - url。
  - country_code。
  - city。
  - asn。
  - provider。
  - tags。
  - notes。
  - last_check_*。
- [x] proxy URL 保存时保留原始配置，但 UI 默认遮蔽用户名密码。
- [x] 检测时复用 GeoIP resolver。
- [ ] 支持将 proxy 分配到 profile。
  - [x] 后端 `POST /api/proxies/{id}/assign` 将 proxy asset 分配给 profiles。
  - [ ] 前端 Proxy Manager 分配入口。
- [x] 支持从 profile 当前 proxy 保存为 proxy asset。
- [ ] 前端新增 Proxy Manager 页面。
- [ ] 支持搜索、筛选、批量检测。
- [ ] 支持按国家、provider、tag 筛选。
- [ ] 支持 CSV 粘贴导入第一版。

## 验证命令

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [x] 无效 proxy 不会保存为可用状态。
- [x] 检测失败保留错误原因。
- [x] proxy 密码不在列表中明文展示。
- [x] 删除 proxy 不应删除已存在 profile，只解除引用或阻止删除并提示。

## 2026-05-26 Proxy asset 表与 CRUD API 小闭环

背景：

- 03 Profile 运营台已完成；按 `tasks/progress.md` 进入 04 Proxy Manager。
- 本小闭环只做后端 proxy asset 存储和 CRUD API，不进入检测、批量检测、前端页面、CSV 导入或 profile 分配，避免一次扩大过多契约。
- 使用 TDD：先新增 `backend/tests/test_proxies.py` 并确认失败，再实现最小后端代码。

已完成：

- [x] `backend/database.py`
  - 新增 `proxies` 表，字段覆盖 name、url、country_code、city、asn、provider、tags、notes、last_check_*、created_at、updated_at。
  - 新增 `create_proxy()`、`list_proxies()`、`get_proxy()`、`update_proxy()`、`delete_proxy()`。
  - `url` 入库前复用 proxy normalize / validate，`host:port` 会规范化为 `http://host:port`。
  - tags 第一版用 JSON 数组保存，避免过早拆 `proxy_tags` 表。
- [x] `backend/proxies.py`
  - 新增 `normalize_proxy_asset_url()`、`redact_proxy_asset_url()`。
  - 复用 `backend/browser_manager.py` 已有 `_normalize_proxy()`、`_validate_proxy()`、`_redact_proxy_url()`，没有复制第三套 proxy 解析逻辑。
- [x] `backend/models.py`
  - 新增 `ProxyCreate`、`ProxyUpdate`、`ProxyResponse`。
- [x] `backend/main.py`
  - 新增 `GET /api/proxies`。
  - 新增 `POST /api/proxies`。
  - 新增 `GET /api/proxies/{proxy_id}`。
  - 新增 `PUT /api/proxies/{proxy_id}`。
  - 新增 `DELETE /api/proxies/{proxy_id}`。
  - API 响应中的 `url` 默认脱敏，例如 `socks5://user:hiddenpass@jp.proxy.example:1080` 返回为 `socks5://jp.proxy.example:1080`。
  - 无效 proxy 创建 / 更新返回 400，并且错误响应不泄露密码。
- [x] `backend/tests/test_proxies.py`
  - 覆盖 `proxies` 表创建。
  - 覆盖数据库 CRUD、tags 往返、URL 规范化、无效 URL 拒绝。
  - 覆盖删除 proxy asset 不删除仍使用同一 proxy 字符串的 profile。
  - 覆盖 API CRUD、响应脱敏、404、无效 URL 不保存。

保持不变：

- Profile 仍保留原有 `proxy` 字符串字段；本轮不强制迁移 `proxy_id`。
- 本轮不改 profile launch / health check 的 proxy 行为。
- 本轮不新增前端 Proxy Manager 页面，因此没有前端 build 要求。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 7 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 15 passed

.venv/bin/python -m pytest backend/tests -q
# 224 passed

git diff --check
# passed
```

范围说明：

- `POST /api/proxies/{id}/check` 未做，下一小闭环进入。
- `POST /api/proxies/bulk/check` 未做。
- 前端 Proxy Manager 页面、搜索筛选、批量检测、CSV 粘贴导入未做。
- 将 proxy 分配到 profile、从 profile 当前 proxy 保存为 proxy asset 未做。

## 2026-05-26 Proxy 单个检测 API 小闭环

背景：

- 继续 04 Proxy Manager，基于上一轮 proxy asset CRUD API 增加单个代理检测。
- 本小闭环只做 `POST /api/proxies/{id}/check`，不进入 bulk check、前端 Proxy Manager 页面、CSV 导入或 profile 分配。
- 使用 TDD：先补充 `backend/tests/test_proxies.py` 并确认红灯，再实现最小后端能力。

红灯确认：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 3 failed, 6 passed
# POST /api/proxies/missing/check 当前 405，POST /api/proxies/{id}/check 当前 405
```

已完成：

- [x] `backend/tests/test_proxies.py`
  - 覆盖 `POST /api/proxies/missing/check` 返回 404。
  - 覆盖成功检测时调用 `resolve_network_geo(raw_proxy_url)`，传入包含凭据的原始 proxy URL。
  - 覆盖成功检测写入 `last_check_status/ip/country_code/timezone/locale/source/at`。
  - 覆盖失败检测返回 200 并写入 `last_check_status="error"` 和脱敏 `last_check_error`。
  - 覆盖 API 响应与 DB 中的 `last_check_error` 不泄露 proxy 密码。
- [x] `backend/database.py`
  - `proxies` 表新增 `last_check_error`。
  - 兼容旧 DB：启动时若缺少该列，执行 `ALTER TABLE proxies ADD COLUMN last_check_error TEXT`。
  - `create_proxy()` / `update_proxy()` 支持写入 `last_check_error`。
- [x] `backend/models.py`
  - `ProxyResponse` 新增 `last_check_error`。
- [x] `backend/main.py`
  - 新增 `POST /api/proxies/{proxy_id}/check`。
  - 成功时复用 `resolve_network_geo()`，写入 `last_check_*` 并清空 `last_check_error`。
  - 失败时不抛 500，写入 `last_check_status="error"`、`last_check_at` 和脱敏错误原因。
  - API 响应继续通过 `_proxy_response()`，`url` 默认脱敏。

保持不变：

- Profile 仍保留原有 `proxy` 字符串字段；本轮不引入 `proxy_id` 分配。
- 本轮不改 profile launch / health check 的 proxy 行为。
- 本轮不新增前端 Proxy Manager 页面，因此没有前端测试或 build 要求。
- 本轮不做 `POST /api/proxies/bulk/check`。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 9 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 17 passed

.venv/bin/python -m pytest backend/tests/test_health.py backend/tests/test_api.py -q
# 70 passed

.venv/bin/python -m pytest backend/tests -q
# 226 passed

git diff --check
# passed
```

范围说明：

- `POST /api/proxies/bulk/check` 未做。
- 前端 Proxy Manager 页面、搜索筛选、批量检测、CSV 粘贴导入未做。
- 将 proxy 分配到 profile、从 profile 当前 proxy 保存为 proxy asset 未做。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 2026-05-26 Proxy 批量检测 API 小闭环

背景：

- 继续 04 Proxy Manager，基于单个 proxy check 增加后端批量检测接口。
- 本小闭环只做 `POST /api/proxies/bulk/check`，不进入前端 Proxy Manager 页面、搜索筛选、CSV 导入或 profile 分配。
- 使用 TDD：先补充 `backend/tests/test_proxies.py` 并确认红灯，再实现最小后端能力。

红灯确认：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 2 failed, 9 passed
# /api/proxies/bulk/check 当前被 /api/proxies/{proxy_id}/check 动态路由匹配为 proxy_id=bulk，返回 404
```

已完成：

- [x] `backend/tests/test_proxies.py`
  - 覆盖批量请求中成功、检测失败、缺失 id 三种结果共存。
  - 覆盖 HTTP 仍返回 200，按 `total/succeeded/failed/results` 汇总，部分失败不让整批失败。
  - 覆盖 GeoIP resolver 使用包含凭据的原始 proxy URL 进行真实检测。
  - 覆盖响应、`results[].error`、`results[].proxy.last_check_error` 和 DB 中的 `last_check_error` 不泄露 proxy 密码。
  - 覆盖 `proxy_ids=[]` 返回 422。
- [x] `backend/models.py`
  - 新增 `ProxyBulkCheckRequest`。
  - 新增 `ProxyBulkCheckResult`。
  - 新增 `ProxyBulkCheckResponse`。
- [x] `backend/main.py`
  - 新增 `POST /api/proxies/bulk/check`，路由放在 `POST /api/proxies/{proxy_id}/check` 前，避免 `bulk` 被动态 id 路由吞掉。
  - 抽出 `_run_proxy_check()`，让单个检测和批量检测共用 GeoIP 调用、`last_check_*` 写库和错误处理。
  - 抽出 `_safe_proxy_check_error()`，将异常中的原始 proxy URL 替换为脱敏 URL，并额外移除独立出现的 proxy password。
  - 缺失 proxy id 只记录该项失败，不抛整批 404。

接口响应形态：

```json
{
  "total": 3,
  "succeeded": 1,
  "failed": 2,
  "results": [
    {"proxy_id": "...", "ok": true, "error": null, "proxy": "...redacted ProxyResponse..."},
    {"proxy_id": "...", "ok": false, "error": "...redacted...", "proxy": "...redacted ProxyResponse..."},
    {"proxy_id": "missing", "ok": false, "error": "Proxy not found", "proxy": null}
  ]
}
```

保持不变：

- Profile 仍保留原有 `proxy` 字符串字段；本轮不引入 `proxy_id` 分配。
- 本轮不新增前端 Proxy Manager 页面，因此没有前端测试或 build 要求。
- 本轮不做前端搜索、筛选、批量检测交互。
- 本轮不进入 Project Mileage 跨仓联动，不引入 Chromium CDP 能力。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 11 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 19 passed

.venv/bin/python -m pytest backend/tests/test_health.py backend/tests/test_api.py -q
# 70 passed

.venv/bin/python -m pytest backend/tests -q
# 228 passed
```

范围说明：

- 前端 Proxy Manager 页面、搜索筛选、批量检测交互未做。
- 按国家、provider、tag 筛选未做。
- CSV 粘贴导入未做。
- 将 proxy 分配到 profile、从 profile 当前 proxy 保存为 proxy asset 未做。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 2026-05-26 Proxy 分配到 Profile 后端 API 小闭环

背景：

- 继续 04 Proxy Manager，在 proxy asset 已可保存、检测和批量检测后，补齐后端层面的 proxy 分配能力。
- 本小闭环只做后端 `POST /api/proxies/{id}/assign`，不做前端 Proxy Manager 分配入口，不调整通用 profile CRUD 响应，不迁移 `profiles.proxy` 为 `proxy_id`。
- 关键边界：前端只提交 `proxy_id` 和 `profile_ids`，后端内部把 proxy asset 的原始 URL 写入 `profiles.proxy`；API 响应只返回脱敏后的 proxy asset 和逐项结果，不返回完整 `ProfileResponse`，避免暴露 proxy 密码。

红灯确认：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 2 failed, 11 passed
# POST /api/proxies/{id}/assign 当前 405
```

已完成：

- [x] `backend/tests/test_proxies.py`
  - 覆盖带凭据 proxy asset 分配给多个 profile。
  - 覆盖同批存在 missing profile 时部分失败，HTTP 仍返回 200。
  - 覆盖响应不包含 `hiddenpass`，但 DB 中 `profiles.proxy` 写入 raw proxy URL，保持 launch / health 兼容。
  - 覆盖 missing proxy 返回 404。
  - 覆盖 `profile_ids=[]` 返回 422。
- [x] `backend/models.py`
  - 新增 `ProxyAssignRequest`。
  - 新增 `ProxyAssignResult`。
  - 新增 `ProxyAssignResponse`。
- [x] `backend/main.py`
  - 新增 `POST /api/proxies/{proxy_id}/assign`。
  - 查不到 proxy asset 时返回 404。
  - 对每个 profile 调用 `db.update_profile(profile_id, proxy=raw_url)`。
  - 响应按 `total/succeeded/failed/results` 汇总，并通过 `_proxy_response(proxy)` 返回脱敏 proxy asset。

接口响应形态：

```json
{
  "proxy_id": "...",
  "proxy": {"id": "...", "name": "...", "url": "http://assign.example:8080"},
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "results": [
    {"profile_id": "...", "ok": true, "error": null},
    {"profile_id": "missing", "ok": false, "error": "Profile not found"}
  ]
}
```

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 13 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 21 passed

.venv/bin/python -m pytest backend/tests/test_health.py backend/tests/test_api.py -q
# 70 passed

.venv/bin/python -m pytest backend/tests -q
# 230 passed
```

范围说明：

- 前端 Proxy Manager 分配入口未做，因此顶层 `支持将 proxy 分配到 profile` 暂不勾选完成。
- 从 profile 当前 proxy 保存为 proxy asset 未做。
- 前端 Proxy Manager 页面、搜索筛选、批量检测交互未做。
- 按国家、provider、tag 筛选未做。
- CSV 粘贴导入未做。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 2026-05-26 Profile 当前 Proxy 保存为 Proxy Asset 后端 API 小闭环

背景：

- 继续 04 Proxy Manager，在 profile 已经能被分配 proxy asset 后，补齐反向迁移入口：把 profile 当前 proxy 字符串保存成可管理的 proxy asset。
- 本小闭环只做后端 `POST /api/profiles/{id}/proxy-asset`，不做前端 Proxy Manager 页面或按钮，不迁移 `profiles.proxy` 为 `proxy_id`。
- 关键边界：请求体不允许前端提交 `url`；后端只从 profile 当前 `proxy` 字段读取原始 URL，保存时复用 proxy asset 的 normalize / validate，响应继续脱敏。

红灯确认：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 2 failed, 13 passed
# POST /api/profiles/{id}/proxy-asset 当前 405
```

已完成：

- [x] `backend/tests/test_proxies.py`
  - 覆盖 profile 当前 proxy 含凭据时保存为 proxy asset。
  - 覆盖 API 响应 `url` 脱敏，不包含 `hiddenpass`。
  - 覆盖 DB 中 proxy asset 保留 raw proxy URL，后续真实连接仍可用。
  - 覆盖 profile 没有 proxy 返回 400。
  - 覆盖 profile proxy 无效时返回 400，错误响应不泄露密码。
  - 覆盖 missing profile 返回 404。
- [x] `backend/models.py`
  - 新增 `ProxyFromProfileCreate`，字段为 `ProxyCreate` 去掉 `url` 后的元信息子集。
- [x] `backend/main.py`
  - 新增 `POST /api/profiles/{profile_id}/proxy-asset`。
  - 查不到 profile 时返回 404。
  - profile 没有 proxy 时返回 `Profile has no proxy`。
  - 保存时调用 `db.create_proxy(**data)`，复用现有 proxy normalize / validate。
  - 响应通过 `_proxy_response(proxy)` 返回脱敏后的 `ProxyResponse`。

接口响应形态：

```json
{
  "id": "...",
  "name": "Saved from profile",
  "url": "http://profile-proxy.example:8080",
  "provider": "ProfilePool",
  "tags": [{"tag": "saved", "color": "#2563eb"}],
  "notes": "Migrated from profile current proxy"
}
```

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 15 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py backend/tests/test_geoip.py -q
# 23 passed

.venv/bin/python -m pytest backend/tests/test_health.py backend/tests/test_api.py -q
# 70 passed

.venv/bin/python -m pytest backend/tests -q
# 232 passed
```

范围说明：

- 前端 Proxy Manager 页面和按钮未做。
- 前端 Proxy Manager 分配入口未做，因此顶层 `支持将 proxy 分配到 profile` 暂不勾选完成。
- 前端搜索、筛选、批量检测交互未做。
- 按国家、provider、tag 筛选未做。
- CSV 粘贴导入未做。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。
