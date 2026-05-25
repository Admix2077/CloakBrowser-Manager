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

- [ ] 新增 `proxies` 表。
- [ ] 新增 proxy CRUD。
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
- [ ] proxy URL 保存时保留原始配置，但 UI 默认遮蔽用户名密码。
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

- [ ] 无效 proxy 不会保存为可用状态。
- [ ] 检测失败保留错误原因。
- [ ] proxy 密码不在列表中明文展示。
- [ ] 删除 proxy 不应删除已存在 profile，只解除引用或阻止删除并提示。
