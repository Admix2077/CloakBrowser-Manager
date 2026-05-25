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

- [x] 新增 `backend/health.py`，实现纯函数健康计算。
- [x] 定义健康状态：
  - `unknown`
  - `good`
  - `warning`
  - `error`
- [x] 定义 warning code：
  - `geoip_missing`
  - `geoip_stale`
  - `proxy_invalid`
  - `geoip_lookup_failed`
  - `manual_timezone_mismatch`
  - `manual_locale_mismatch`
  - `runtime_vnc_missing`
  - `runtime_automation_missing`
  - `launch_failed`
- [x] 新增 `GET /api/profiles/{id}/health`：
  - 不访问网络。
  - 基于已有 profile、last_geoip 和 runtime status 计算。
- [x] 新增 `POST /api/profiles/{id}/health/check`：
  - 校验 proxy。
  - 调用 GeoIP。
  - 写入 `last_geoip_*`。
  - 返回 health result。
- [x] 补测试：无 `last_geoip_*` 返回 `unknown`。
- [x] 补测试：proxy 格式错误返回 `error`。
- [x] 补测试：GeoIP fallback 成功写入 `last_geoip_*`。
- [x] 补测试：手动 timezone 不一致返回 warning，但不覆盖手动字段。
- [x] 补测试：手动 locale 不一致返回 warning，但不覆盖手动字段。
- [x] 前端新增 `HealthBadge`。
- [x] 前端 profile 类型增加 health response 类型。
- [x] 前端显示健康状态和 warning summary。

## 验证命令

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py backend/tests/test_geoip.py backend/tests/test_api.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [x] 无代理、有代理、无效代理都能得到稳定 health response。（后端 API 已覆盖无代理、有代理归一化和无效代理；前端展示待接入。）
- [x] 自动检测结果只写 `last_geoip_*`。
- [x] 手动 `timezone` / `locale` 不被覆盖。
- [x] health API 失败不会清空旧检测结果。

## 2026-05-25 后端健康引擎小闭环

已完成：

- 新增 `backend/health.py`，实现不依赖 HTTP 的健康计算。
- 新增 `HealthWarning`、`HealthGeoIP`、`ProfileHealthResponse` 和 `HEALTH_WARNING_CODES`。
- 新增 `GET /api/profiles/{id}/health`，只基于 DB profile 和 runtime status 计算，不访问网络。
- 新增 `POST /api/profiles/{id}/health/check`，校验 proxy、调用 GeoIP、成功时写入 `last_geoip_*`，失败时返回稳定 health response 且不清空旧检测结果。
- 保持手动 `timezone` / `locale` 语义：检测结果只写 `last_geoip_*`，不覆盖手动字段。
- 从 UI/UE 角度预审 HealthBadge：后续前端接入推荐放在 profile 列表第一行右侧，用低饱和状态 badge，短文案为 `可继续` / `需关注` / `不可用` / `未检测`，不要只靠颜色表达状态。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q
# 11 passed

. .venv/bin/activate && python -m pytest backend/tests/test_health.py backend/tests/test_geoip.py backend/tests/test_api.py -q
# 77 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 216 passed
```

未完成：

- 无。

## 2026-05-26 前端健康状态展示小闭环

已完成：

- 新增前端 health 类型：
  - `HealthStatus`
  - `HealthWarning`
  - `HealthGeoIP`
  - `ProfileHealthResponse`
- 新增 API client：
  - `api.getProfileHealth(id)`
  - `api.checkProfileHealth(id)`
- 新增 `frontend/src/lib/health.ts`，集中维护健康状态文案、可访问名称、状态色和 summary 提取。
- 新增 `frontend/src/components/HealthBadge.tsx`：
  - `good` 显示 `可继续`。
  - `warning` 显示 `需关注`。
  - `error` 显示 `不可用`。
  - `unknown` 或未加载显示 `未检测`。
  - 状态不只靠颜色表达，提供 `aria-label` 和 `title`。
- `useProfiles()` 增加 `healthByProfileId`：
  - 首屏根据 profile id 集合拉取 cached health。
  - `launch` / `stop` / `create` / `update` 后刷新对应 profile health。
  - 3 秒 profile status 轮询不重复触发全量 health 请求，避免明显 N+1 压力。
- `ProfileList` 在 profile 名称同行右侧展示 `HealthBadge`，第二行展示 warning summary 与 GeoIP 摘要。
- 搜索仍只按 profile name，不因 `需关注`、`不可用` 等 health 文案产生误匹配。

验证：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts src/components/HealthBadge.test.tsx src/components/ProfileList.test.tsx src/hooks/useProfiles.test.ts
# 4 passed, 28 passed

cd frontend && npm test -- --run
# 6 passed, 33 passed

cd frontend && npm run build
# built successfully

. .venv/bin/activate && python -m pytest backend/tests/test_health.py backend/tests/test_geoip.py backend/tests/test_api.py -q
# 77 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 216 passed
```

浏览器 UI/UE 验证：

- 后端使用临时 QA 数据目录 `/tmp/cloakbrowser-manager-qa-data` 启动，避免本机没有 `/data` 写权限影响验证。
- Vite dev server：`http://127.0.0.1:5173/`。
- 使用 `agent-browser` 走查：
  - 桌面视口 `1440x900`。
  - 移动视口 `390x844`。
  - 四种状态 `可继续` / `需关注` / `不可用` / `未检测` 均可扫读。
  - warning summary、error summary、GeoIP 摘要在侧栏行内可见且不重叠。
  - 搜索 `需关注` 返回 `No matches`，证明搜索不被 health 文案污染。
  - 搜索 `Warning` 后选择 profile，编辑表单和 `Launch` 按钮仍可用。
  - 浏览器控制台无相关应用错误，仅有 Vite debug 和 React DevTools 提示。

模块结论：

- 02 指纹健康引擎后端、前端、测试、build 和浏览器 UI/UE 验证已完成。
