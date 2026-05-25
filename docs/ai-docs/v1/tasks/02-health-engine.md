# 02 指纹健康引擎

## 目标

把当前 GeoIP 同步能力升级为通用健康引擎，支持不启动浏览器的轻检测、运行中状态诊断、风险提示和修复建议。

## 主要文件

预计修改：

- `backend/geoip.py`
- `backend/browser_manager.py`
- `backend/main.py`
- `backend/models.py`
- `backend/database.py`
- `frontend/src/lib/api.ts`

预计新增：

- `backend/health.py`
- `backend/tests/test_health.py`
- `frontend/src/lib/health.ts`
- `frontend/src/components/HealthBadge.tsx`

## 任务清单

- [ ] 新增 `backend/health.py`，实现纯函数健康计算。
- [ ] 定义健康状态：
  - `unknown`
  - `good`
  - `warning`
  - `error`
- [ ] 定义 warning code：
  - `geoip_missing`
  - `geoip_stale`
  - `proxy_invalid`
  - `geoip_lookup_failed`
  - `manual_timezone_mismatch`
  - `manual_locale_mismatch`
  - `runtime_vnc_missing`
  - `runtime_automation_missing`
  - `launch_failed`
- [ ] 新增 `GET /api/profiles/{id}/health`：
  - 不访问网络。
  - 基于已有 profile、last_geoip 和 runtime status 计算。
- [ ] 新增 `POST /api/profiles/{id}/health/check`：
  - 校验 proxy。
  - 调用 GeoIP。
  - 写入 `last_geoip_*`。
  - 返回 health result。
- [ ] 补测试：无 `last_geoip_*` 返回 `unknown`。
- [ ] 补测试：proxy 格式错误返回 `error`。
- [ ] 补测试：GeoIP fallback 成功写入 `last_geoip_*`。
- [ ] 补测试：手动 timezone 不一致返回 warning，但不覆盖手动字段。
- [ ] 补测试：手动 locale 不一致返回 warning，但不覆盖手动字段。
- [ ] 前端新增 `HealthBadge`。
- [ ] 前端 profile 类型增加 health response 类型。
- [ ] 前端显示健康状态和 warning summary。

## 验证命令

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py backend/tests/test_geoip.py backend/tests/test_api.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [ ] 无代理、有代理、无效代理都能得到稳定 health response。
- [ ] 自动检测结果只写 `last_geoip_*`。
- [ ] 手动 `timezone` / `locale` 不被覆盖。
- [ ] health API 失败不会清空旧检测结果。
