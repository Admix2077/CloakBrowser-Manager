# 08 Cookie、Profile 导入导出

## 目标

提供成熟指纹浏览器常见的 cookie 和 profile 迁移能力，同时控制敏感数据暴露风险。

## 任务清单

- [x] 定义 cookie JSON import 格式。
- [x] 定义 cookie JSON export 格式。
- [ ] 支持 Netscape cookie import。
- [ ] 支持 Netscape cookie export。
- [ ] 仅运行中 profile 允许通过 browser context 导入 cookie。
- [ ] 停止状态 profile 可通过 profile dir 方式导入 cookie 时必须先评估 Firefox 存储格式，不强行实现。
- [ ] 导出 cookie 必须写 audit。
- [ ] 导出 cookie 必须有显式确认。
- [ ] 前端新增 Cookie 管理入口。
- [ ] 支持 profile config export：
  - 不包含 cookie。
  - 不包含 proxy password，除非用户选择包含敏感字段。
- [ ] 支持 profile config import。
- [ ] 后续支持完整 profile bundle：
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

## 验证

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [ ] JSON cookie 导入后页面可读到 cookie。
- [ ] JSON cookie 导出不破坏字段。
- [ ] Netscape 格式基础兼容。
- [ ] 导出动作写 audit 且不记录 cookie 明文。
