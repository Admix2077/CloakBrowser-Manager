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
- [ ] 新增 `POST /api/proxies/{id}/check`。
- [ ] 新增 `POST /api/proxies/bulk/check`。
- [ ] 支持字段：
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
- [ ] 检测时复用 GeoIP resolver。
- [ ] 支持将 proxy 分配到 profile。
- [ ] 支持从 profile 当前 proxy 保存为 proxy asset。
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
- [ ] 检测失败保留错误原因。
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
