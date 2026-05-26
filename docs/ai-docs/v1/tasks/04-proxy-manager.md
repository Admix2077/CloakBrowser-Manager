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
- [x] 支持将 proxy 分配到 profile。
  - [x] 后端 `POST /api/proxies/{id}/assign` 将 proxy asset 分配给 profiles。
  - [x] 前端 Proxy Manager 分配入口。
- [x] 支持从 profile 当前 proxy 保存为 proxy asset。
- [x] 前端新增 Proxy Manager 页面。
- [x] 支持搜索、筛选、批量检测。
- [x] 支持按国家、provider、tag 筛选。
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

## 2026-05-26 Proxy Manager 前端 API Client 小闭环

背景：

- 继续 04 Proxy Manager，在后端 proxy asset CRUD、单个检测、批量检测、分配到 profile、从 profile 当前 proxy 保存为 asset 已完成后，先补齐前端 API client 契约。
- 本小闭环只修改 `frontend/src/lib/api.ts` 和 `frontend/src/lib/api.test.ts`，不新增 Proxy Manager 页面、导航、表格、表单、筛选、CSV 导入或分配 UI。
- 使用 TDD：先补充 assign / save-from-profile client 测试，确认缺少方法红灯后再实现。

红灯确认：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts
# 1 failed, 2 failed | 18 passed
# api.assignProxyToProfiles / api.saveProfileProxyAsAsset 当前不存在
```

已完成：

- [x] `frontend/src/lib/api.ts`
  - 新增 `ProxyAsset`、`ProxyCreateData`、`ProxyUpdateData`。
  - 新增 `ProxyBulkCheckResult`、`ProxyBulkCheckResponse`。
  - 新增 `ProxyAssignResult`、`ProxyAssignResponse`。
  - 新增 `ProxyFromProfileCreateData`，等同 `ProxyCreateData` 去掉 `url`，避免前端向 `POST /api/profiles/{id}/proxy-asset` 提交 URL。
  - 新增 `listProxies()` / `getProxy()` / `createProxy()` / `updateProxy()` / `deleteProxy()`。
  - 新增 `checkProxy()` / `bulkCheckProxies()`。
  - 新增 `assignProxyToProfiles()`，请求体为 `{profile_ids}`。
  - 新增 `saveProfileProxyAsAsset()`，请求体只包含 proxy asset metadata。
- [x] `frontend/src/lib/api.test.ts`
  - 覆盖 proxy list / get / create / update / delete。
  - 覆盖单个 check 与 bulk check endpoint、method、body shape。
  - 覆盖 assign endpoint、method、`profile_ids` body shape。
  - 覆盖从 profile 当前 proxy 保存为 asset 时不提交 `url`。

验证：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts
# 1 passed, 21 passed

cd frontend && npm test -- --run
# 11 passed, 127 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

范围说明：

- 前端 Proxy Manager 页面未做。
- 前端 Proxy Manager 分配入口未做，因此顶层 `支持将 proxy 分配到 profile` 暂不勾选完成。
- 前端搜索、筛选、批量检测交互未做；API client 的 `bulkCheckProxies()` 不等于 UI 批量检测交互完成。
- 按国家、provider、tag 筛选未做。
- CSV 粘贴导入未做。
- 不迁移 `profiles.proxy` 为 `proxy_id`。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

## 2026-05-26 Proxy Manager 前端只读页面小闭环

背景：

- 继续 04 Proxy Manager，在前端 API client 已覆盖后，新增 Proxy Manager 最小可见页面，让运营者能从主界面查看 proxy asset 库。
- 本小闭环只接入 `GET /api/proxies` 做只读列表和脱敏展示，不接线新增、编辑、删除、单个检测、批量检测、分配到 profile、CSV 导入或搜索筛选。
- UI 方向继续遵守 B2B data-dense operations console：紧凑统计、稳定表格、浅色高对比、移动端不撑破 body。

红灯确认：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 1 failed, no tests
# ./ProxyManagerPage 组件不存在

cd frontend && npm test -- --run src/App.test.tsx
# 1 failed
# 当前没有 Proxy Manager section 入口
```

已完成：

- [x] `frontend/src/components/ProxyManagerPage.tsx`
  - 内部调用 `api.listProxies()` 加载 proxy assets。
  - 展示 total / good / needs review / unchecked summary。
  - 展示只读 proxy assets table：name、credential-safe URL、location、provider、health、last check、tags。
  - 对 URL 和检测错误文本额外执行 `redactUrlCredentials()`，即使 mock 或异常文本带凭据也不会渲染密码。
  - 空状态明确说明 API 创建的 proxy asset 会显示在此处。
  - 错误状态提供只读 refresh/retry，不触发 mutation。
- [x] `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖只读列表、统计、脱敏 URL、error message、空状态、横向滚动隔离。
  - 覆盖页面不出现 Delete / Assign 等高风险 mutation action。
- [x] `frontend/src/App.tsx`
  - 新增顶层 section switch：`Profiles` / `Proxy Manager`。
  - Proxy Manager section 隐藏 Profile 专用 sidebar、`New Profile`、Launch/Stop 和 Profile table。
  - 返回 Profiles 时保留原 Profile operations 工作流。
- [x] `frontend/src/App.test.tsx`
  - 覆盖 Profile operations 与 Proxy Manager section 来回切换。

范围说明：

- 前端 Proxy Manager 页面当前是只读列表，不代表搜索、筛选、批量检测交互完成。
- 前端 Proxy Manager 分配入口未做，因此顶层 `支持将 proxy 分配到 profile` 暂不勾选完成。
- 单个检测 / 批量检测按钮未接线。
- 新建 / 编辑 / 删除 proxy UI 未做。
- 按国家、provider、tag 筛选未做。
- CSV 粘贴导入未做。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

验证：

```bash
cd frontend && npm test -- --run src/App.test.tsx src/components/ProxyManagerPage.test.tsx
# 2 passed, 21 passed

cd frontend && npm test -- --run
# 12 passed, 132 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:5176/`，通过临时 Vite config 代理 `/api` 到隔离 QA 后端 `127.0.0.1:8093`。
- QA 后端 seed 了 1 个 profile 和 2 个 proxy assets，其中 proxy URL 与 `last_check_error` 均包含凭据，用于验证 UI 脱敏。
- 桌面 `1440x900`：
  - `Proxy Manager` section 可从顶栏进入。
  - `Proxy assets table` 显示 2 行 proxy assets。
  - 表格区域 `overflow: auto`，`document.documentElement.scrollWidth === window.innerWidth === 1440`。
  - 页面文本不包含 `hiddenpass`、`topsecret`、`user:`、`secret:`。
- 移动 `390x844`：
  - Proxy Manager 页面可见。
  - 表格横向滚动限制在 `Proxy assets table` 区域。
  - `document.documentElement.scrollWidth === window.innerWidth === 390`。
  - 页面文本不包含 `hiddenpass` 或 `topsecret`。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-proxy-manager-v1-screens/desktop-proxy-manager-real-api.png`
- `/tmp/cloakbrowser-proxy-manager-v1-screens/mobile-proxy-manager-real-api.png`

## 2026-05-26 Proxy Manager 搜索与筛选小闭环

背景：

- 继续 04 Proxy Manager，在只读 Proxy Manager 页面基础上补齐纯客户端搜索与运营筛选能力。
- 本小闭环只做搜索、国家/provider/tag 筛选、过滤空态和清空筛选，不接线单个检测、批量检测、分配、新建、编辑、删除或 CSV 导入。
- 设计方向延续 B2B data-dense operations console：筛选栏放在表格上方，主库存统计保持全量口径，新增 visible count 说明当前筛选结果。

红灯确认：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 3 failed, 4 passed
# 红灯：Search proxy assets、Country filter 等筛选控件尚不存在
```

已完成：

- [x] `frontend/src/components/ProxyManagerPage.tsx`
  - 新增 `Search proxy assets` 输入框。
  - 新增 `Country filter`、`Provider filter`、`Tag filter` 下拉筛选。
  - 筛选选项从 `ProxyAsset` 本地数据派生并去重排序，忽略空值。
  - 筛选选项和匹配逻辑使用同一套 trim 后值，避免字段带前后空格时选项可见但匹配不到行。
  - `All` 使用不可与真实 provider/tag 冲突的内部 sentinel，不占用真实字段值 `all`。
  - 搜索匹配 name、脱敏 endpoint、country、city、ASN、provider、脱敏 notes、health、last check metadata 和 tag。
  - 使用 `useDeferredValue(searchQuery)` 降低快速输入时的渲染压力。
  - 筛选采用 AND 语义，表格渲染 `filteredProxies`。
  - 新增 `{visible} of {total} visible` badge。
  - 新增过滤空态 `No proxy assets match filters` 和 `Clear proxy filters`。
  - 保留只读语义：本轮没有调用 `checkProxy`、`bulkCheckProxies`、`assignProxyToProfiles` 或其它 mutation API。
  - 修复浏览器验证发现的细节：`last_check_error` 与 notes 的可见文本 / `title` 属性都必须使用脱敏文本，避免 hover tooltip 泄露 proxy 凭据。
- [x] `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖搜索命中脱敏 endpoint、provider、tag，且不触发额外 API 请求。
  - 覆盖 country/provider/tag 组合筛选 AND 语义。
  - 覆盖筛选选项去重、排序、忽略空值、trim 后仍可匹配来源行。
  - 覆盖过滤空态和 `Clear proxy filters` 恢复列表。
  - 覆盖 URL、`last_check_error` 和 notes 中的 proxy 凭据不会出现在页面正文或任何 `title` 属性。

范围说明：

- 顶层 `支持搜索、筛选、批量检测` 暂不勾选，因为本轮未做批量检测 UI。
- 前端 Proxy Manager 分配入口未做，因此顶层 `支持将 proxy 分配到 profile` 暂不勾选完成。
- 单个检测 / 批量检测按钮未接线。
- 新建 / 编辑 / 删除 proxy UI 未做。
- CSV 粘贴导入未做。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

验证：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 1 passed, 7 passed

cd frontend && npm test -- --run
# 12 passed, 135 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8094/`，由临时 FastAPI 进程服务当前 `frontend/dist` 生产 build，并使用 `/tmp/cloakbrowser-proxy-manager-filters-data-8094/profiles.db` 隔离 seed 数据。
- QA seed：
  - 1 个 profile。
  - 3 个 proxy assets：`Credential Pool`、`Broken JP Pool`、`DE Backup`。
  - `Credential Pool` 与 `Broken JP Pool` 的 URL / error 含凭据，用于验证正文和 tooltip 脱敏。
  - `Broken JP Pool` 的 country/provider/tag 含前后空格，用于验证 trim 后选项仍可匹配来源行。
  - `DE Backup` 的 provider/tag 使用真实值 `all`，用于验证内部 `All` sentinel 不与真实业务值冲突。
- 桌面 `1440x900`：
  - 顶栏可进入 `Proxy Manager`。
  - 全量状态显示 `3 of 3 visible`。
  - 搜索 `jp.proxy.example` 后显示 `1 of 3 visible`，只剩 `Broken JP Pool`。
  - 组合筛选 `country=JP + provider=ProxyJP + tag=asia` 后只剩 `Broken JP Pool`，证明 trim 后匹配正常。
  - 搜索 `does-not-exist` 后显示过滤空态和 `Clear proxy filters`。
  - `document.body.innerText` 与全部 `[title]` 属性不包含 `hiddenpass`、`topsecret`、`user:`、`secret:`。
  - `document.documentElement.scrollWidth === window.innerWidth === 1440`。
  - `Proxy assets table` 区域 `overflowX` 为 `auto`。
- 移动 `390x844`：
  - Proxy Manager 筛选栏与表格可见。
  - `document.documentElement.scrollWidth === window.innerWidth === 390`，body 未被表格撑宽。
  - `document.body.innerText` 与全部 `[title]` 属性不包含 `hiddenpass`、`topsecret`、`user:`、`secret:`。
  - 搜索 `proxyco` 后显示 `1 of 3 visible`。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-proxy-manager-filters-screens/desktop-filtered-search.png`
- `/tmp/cloakbrowser-proxy-manager-filters-screens/desktop-empty-state.png`
- `/tmp/cloakbrowser-proxy-manager-filters-screens/mobile-full-list.png`
- `/tmp/cloakbrowser-proxy-manager-filters-screens/mobile-filtered-search.png`

## 2026-05-26 Proxy Manager 批量检测 UI 小闭环

背景：

- 继续 04 Proxy Manager，基于已完成的搜索与筛选，把后端 `POST /api/proxies/bulk/check` 接入到 Proxy Manager 表格。
- 本小闭环只做已选 proxy asset 的批量检测，不进入单个检测、新建、编辑、删除、分配到 profile 或 CSV 导入。
- 交互边界：`Select all visible` 只选择当前筛选后的可见 proxy，批量检测响应中的部分失败不视作整批失败，错误与检测结果继续保持 credential-safe。

已完成：

- [x] `frontend/src/components/ProxyManagerPage.tsx`
  - 新增表格选择列、单行选择和 `Select all visible proxy assets`。
  - 新增 `selected` 计数和 `Check selected` 操作；未选择或检测中时按钮 disabled。
  - 调用 `api.bulkCheckProxies(selectedIds)`，并用响应中的 `results[].proxy` 局部刷新对应行健康状态。
  - 成功后展示 `Bulk check complete: X succeeded, Y failed`。
  - request 抛错时展示脱敏后的 `Bulk check failed: ...`。
  - 保持高风险 create/update/delete/assign/CSV action 不出现。
  - 表格继续在自身容器内横向滚动，避免移动端 body 横向撑破。
- [x] `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖选择多个 proxy 后触发批量检测并刷新 row health。
  - 覆盖 `Select all visible` 只选择筛选后的可见 proxy。
  - 覆盖批量检测失败提示不泄露 proxy 凭据。
  - 覆盖页面仍不出现 delete / assign 等高风险 action。

范围说明：

- 前端 Proxy Manager 分配入口未做，因此顶层 `支持将 proxy 分配到 profile` 暂不勾选完成。
- Proxy Manager 单个检测 UI 未做。
- 新建 / 编辑 / 删除 proxy UI 未做。
- CSV 粘贴导入未做。
- `profiles.proxy` 到 `proxy_id` 的数据模型迁移未做。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

验证：

```bash
cd frontend && npm test -- --run
# 12 passed, 138 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8094/`，隔离数据库 `/tmp/cloakbrowser-proxy-manager-bulk-check-data-8094`。
- QA seed 包含 3 条 proxy assets，其中 JP proxy 的检测异常包含 raw credentials，用于验证 UI 脱敏。
- 桌面 `1440x900`：
  - Proxy Manager 可进入，`Select all visible` 后 `Check selected` 可用。
  - 批量检测后展示 `Bulk check complete: 2 succeeded, 1 failed`。
  - 正文和 `[title]` 属性均不包含 `hiddenpass`、`topsecret`、`user:`、`secret:`。
  - `document.documentElement.scrollWidth === window.innerWidth === 1440`。
- 移动 `390x844`：
  - `Select all visible` 与 `Check selected` 可用。
  - 批量检测后展示 `Bulk check complete: 2 succeeded, 1 failed`。
  - 表格在自身容器横向滚动，body 未横向撑破：`document.documentElement.scrollWidth === window.innerWidth === 390`。
  - 正文和 `[title]` 属性均无 proxy 凭据泄露。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-proxy-manager-bulk-check-screens/desktop-bulk-check-results.png`
- `/tmp/cloakbrowser-proxy-manager-bulk-check-screens/mobile-bulk-check-results.png`

## 2026-05-26 Proxy Manager 前端分配入口小闭环

背景：

- 继续 04 Proxy Manager，在后端 `POST /api/proxies/{id}/assign` 和前端 API client 已完成后，补齐运营台里从 proxy asset 分配到 profiles 的入口。
- 本小闭环只做“选择一个 proxy asset -> 搜索/勾选 profiles -> 调用 assign API -> 刷新 profile 数据”的闭环，不做单个检测 UI、新建/编辑/删除 proxy UI、CSV 导入或 `profiles.proxy` 到 `proxy_id` 的迁移。
- 交互边界：只允许选择一个 proxy asset 时进入分配；批量检测仍可多选；profile 列表使用主 App 已加载的 profiles，不额外绕过 Profile 事实源。

已完成：

- [x] `frontend/src/App.tsx`
  - 将 `useProfiles()` 的 `profiles` 和 `refresh` 传入 `ProxyManagerPage`。
  - Proxy Manager 顶栏文案从只读库存改为包含 assignment controls，但不改变 Profile 运营台原有创建、编辑、VNC、批量操作语义。
- [x] `frontend/src/components/ProxyManagerPage.tsx`
  - 新增 `Assign to profiles` 操作；仅当恰好选择一个 proxy asset 且存在 profiles 时可用。
  - 新增 `Assign proxy to profiles` dialog，展示当前 proxy asset 的 credential-safe URL。
  - dialog 支持按 name、id、runtime status、current proxy 搜索 profiles。
  - 支持单行勾选与 `Select visible`，只对当前搜索结果执行可见批量选择。
  - 提交时调用 `api.assignProxyToProfiles(selectedProxy.id, profileIds)`，请求体仍由 API client 生成 `{profile_ids}`。
  - 成功后展示 `Assigned proxy to X profile(s), Y failed`，关闭 dialog，清理临时选择并调用 `onProfilesAssigned()` 刷新 Profile 数据。
  - 如果 assignment 已成功但 profile refresh 失败，不把写入成功误报为 `Assign failed`，而是保留成功提示并追加脱敏后的 refresh 失败信息。
  - assignment 错误、当前 proxy URL、profile 当前 proxy、tooltip title 均走 `redactUrlCredentials()`。
  - `redactUrlCredentials()` 补充兼容旧格式 `host:port:user:pass`，避免 assignment dialog 中 profile 当前 proxy 泄露历史凭据。
- [x] `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖 assignment action 仅在单选 proxy 时启用。
  - 覆盖选择 profiles 后调用 `assignProxyToProfiles(proxyId, profileIds)` 并触发 profile refresh。
  - 覆盖搜索后 `Select visible` 只选择当前可见 profiles。
  - 覆盖 assignment 失败提示不泄露 URL 凭据。
  - 覆盖旧格式 `host:port:user:pass` 当前 proxy 在正文与 `title` 中都不泄露凭据。
  - 覆盖 assignment 成功但 refresh 失败时不误报为 assign failure。
- [x] `frontend/src/App.test.tsx`
  - 覆盖 App 向 Proxy Manager 传递 profiles 与 refresh callback。

范围说明：

- Proxy Manager 单个检测 UI 未做。
- 新建 / 编辑 / 删除 proxy UI 未做。
- CSV 粘贴导入未做。
- `profiles.proxy` 到 `proxy_id` 的数据模型迁移未做。
- 04 模块仍未完成，不更新 `tasks/progress.md` 完成状态。

验证：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 红灯：2 failed, 14 passed
# legacy host:port:user:pass 当前 proxy 会泄露；refresh 失败会被误报为 Assign failed

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 1 passed, 16 passed

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx src/App.test.tsx
# 2 passed, 34 passed

cd frontend && npm test -- --run
# 12 passed, 145 passed

cd frontend && npm run build
# built successfully

.venv/bin/python -m pytest backend/tests -q
# 232 passed

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 使用 `agent-browser` + `AGENT_BROWSER_ARGS=--no-sandbox`。
- QA 地址：`http://127.0.0.1:8095/`，由当前 `frontend/dist` 生产 build 服务，隔离数据库 `/tmp/cloakbrowser-user-test-8095/profiles.db`。
- 桌面 `1440x900`：
  - 进入 Proxy Manager 后选择 `Credential Pool`，`Assign to profiles` 从 disabled 变为可用。
  - 打开 assignment dialog，搜索 `gamma` 后只显示 `Gamma Search Target`。
  - dialog 中历史旧格式 proxy 显示为 `legacy.proxy.example:8080`，不显示 legacy user/pass。
  - `Select visible` 后执行 `Assign proxy`，成功展示 `Assigned proxy to 1 profile(s), 0 failed`，dialog 关闭。
  - API 验证 `Gamma Search Target.proxy` 已写入 `http://user:hiddenpass@proxy.example:8080`。
  - 页面正文和全部 `[title]` 属性无 `hiddenpass`、`topsecret`、`user:`、`secret:`、`legacy-user`、`legacypass`；`document.documentElement.scrollWidth === window.innerWidth === 1440`。
- 移动 `390x844`：
  - Proxy Manager 页面 body 未横向撑破：`document.documentElement.scrollWidth === window.innerWidth === 390`。
  - 选择 `Credential Pool` 后打开 assignment dialog，搜索 `beta`、`Select visible`、执行 `Assign proxy` 成功。
  - 成功后展示 `Assigned proxy to 1 profile(s), 0 failed`，dialog 关闭。
  - API 验证 `Beta Running Candidate.proxy` 已写入 `http://user:hiddenpass@proxy.example:8080`。
  - 页面正文和全部 `[title]` 属性无 proxy 凭据泄露。
- `agent-browser errors --clear` 无输出；`agent-browser console --clear` 无相关前端错误。

截图：

- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/desktop-proxy-manager-before-assign.png`
- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/desktop-assign-dialog-search.png`
- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/desktop-assign-success.png`
- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/mobile-assign-dialog-search.png`
- `/tmp/cloakbrowser-proxy-manager-assign-final-screens/mobile-assign-success.png`
