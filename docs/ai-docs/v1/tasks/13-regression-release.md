# 13 总回归、交付与上线门禁

## 目标

在所有模块完成后做整体回归，确保 manager 独立可用，并且 Project Mileage 联动不破坏安全边界。

## Manager 回归清单

- [ ] profile 创建。
- [ ] profile 编辑。
- [ ] profile 删除。
- [ ] launch。
- [ ] stop。
- [ ] VNC viewer。
- [ ] clipboard sync。
- [ ] Automation API。
- [ ] GeoIP 自动同步。
- [ ] health check。
- [ ] Proxy Manager。
- [ ] bulk actions。
- [ ] audit。
- [ ] Docker build。
- [ ] Docker run。

## BrowserScan / 检测站人工验收

- [x] 无代理场景。
- [ ] US proxy。
- [ ] JP proxy。
- [ ] DE proxy。
- [x] timezone 与出口一致。
- [ ] language 与 Accept-Language 一致。
- [ ] BrowserScan 无 `Language mismatch`。
- [x] BrowserScan 无 `Different time zones`。
- [x] BrowserScan browser-checker 内核版本与 UA 一致。
- [x] BrowserScan WebRTC 不泄漏 local IP。
- [ ] BrowserLeaks WebRTC / Canvas / WebGL / Fonts 无明显平台不一致。
- [ ] CreepJS 无 webdriver/headless/lie detection 严重红灯。
- [ ] Pixelscan/IPhey 无 IP、timezone、language、WebRTC、hardware/software 高风险不一致。
- [ ] 同一 seed 停止/重启后核心指纹稳定。
- [ ] 不同 seed 的 profile 核心指纹有合理差异。

详细矩阵见 `../fingerprint-consistency-qa-plan.md`。

## Project Mileage 联动回归

仅在 05/06 跨仓实现后执行：

- [ ] `/app/remote-workspace` 不再是占位。
- [ ] 用户只看到自己的远程账号。
- [ ] 创建 session 走 Payload。
- [ ] 钱包扣费或授权策略正确。
- [ ] VNC viewer 可进入。
- [ ] token 过期后不可用。
- [ ] `/ops/remote-monitor` 显示真实 session。
- [ ] 运营终止写审计。
- [ ] App 不显示 VNC token。
- [ ] Payload 不返回浏览器 cookie。

## 验证命令

Manager：

```bash
. .venv/bin/activate && python -m pytest backend/tests -q
cd frontend && npm test -- --run
cd frontend && npm run build
docker build --network=host --platform linux/amd64 -t invisible-browser-manager:latest .
```

Project Mileage：

```bash
cd /home/jeff/code/project-mileage-v3-app && pnpm test
cd /home/jeff/code/project-mileage-v3-app && pnpm lint
cd /home/jeff/code/project-mileage-v3-app && pnpm build
cd /home/jeff/code/project-mileage-v3-payload && pnpm vitest run
cd /home/jeff/code/project-mileage-v3-payload && pnpm lint
cd /home/jeff/code/project-mileage-v3-payload && pnpm build
```

## 发布门禁

- [ ] 所有自动化测试通过。
- [ ] Docker 镜像构建通过。
- [ ] 浏览器人工验收通过。
- [ ] 文档更新。
- [ ] 不包含敏感文件。
- [ ] `git diff --check` 通过。
- [ ] 当前工作区只包含预期变更。

## 2026-06-02 BrowserScan no-proxy P0 复验

环境：

- 镜像：`invisible-browser-manager:goal-smoke`
- 临时容器和临时 `/data`，复验后已清理。
- profile：无 proxy，`geoip=true`，Windows profile，`fingerprint_seed=24680`，`1920x1080`，`hardwareConcurrency=8`。

结果：

- browser-checker 页显示 `You are currently using Firefox 149`。
- browser-checker 页显示 `Your browser version and User Agent match`。
- `navigator.userAgent` 为 `Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0`。
- `navigator.buildID` 为 `20260521160037`，`navigator.webdriver=false`。
- WebRTC 页显示 `No Public IP Leak`，public IP 为 `23.144.4.92`，页面文本未显示 local IP。
- timezone 页显示 IP timezone、JavaScript Date timezone、Intl timezone 均为 `America/Los_Angeles`。
- bot-detection 页显示 WebDriver、WebDriver Advance、Selenium、Headless Chrome、CDP、Dev Tool 均为 `Normal`。

边界：

- 本轮只完成 no-proxy BrowserScan P0 复验；US/JP/DE proxy、BrowserLeaks、Pixelscan/IPhey、CreepJS、同 seed 重启稳定性和不同 seed 差异仍未标记完成。
- 复验输出只记录低敏页面结论、UA、BuildID、language/timezone 和固定 Normal/Leak 文本；不保存 cookie、local storage、proxy、token、headers、截图或 profile dir 内容。

## 2026-06-03 Language consistency 自动 guardrail

本轮补强了浏览器启动映射中的语言一致性边界：

- `Accept-Language` 与页面端 `navigator.languages` 现在共用同一 locale 派生逻辑。
- 区域 locale 会同时暴露精确语言和基础语言回退，例如 `en-US,en;q=0.9` 对应 `navigator.languages=["en-US","en"]`。
- 单项 locale 仍保持单项，避免重复语言值。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_browser_init_script_aligns_navigator_languages_with_accept_language_fallback backend/tests/test_browser_manager.py::test_accept_language_header_includes_base_language backend/tests/test_browser_manager.py::test_launch_uses_invisible_playwright_on_vnc_display -q
# 3 passed
```

边界：

- 这是自动化单元 guardrail，不代表 BrowserScan `Language mismatch`、Pixelscan/IPhey language consistency 或多国家代理矩阵已经通过。
- 未记录真实 header、cookie、local storage、proxy、token、截图或 profile dir 内容。

## 2026-06-03 自动门禁复跑

本轮在语言一致性 guardrail 变更后复跑 Manager 自动门禁：

```bash
. .venv/bin/activate && python -m pytest backend/tests -q
# 507 passed in 30.53s

cd frontend && npm test -- --run
# Test Files 16 passed；Tests 221 passed

cd frontend && npm run build
# tsc -b && vite build；built in 5.30s

docker build --network=host --platform linux/amd64 -t invisible-browser-manager:language-guardrail .
# Successfully tagged invisible-browser-manager:language-guardrail

docker run -d --rm --name cloakbrowser-language-guardrail-smoke -p 127.0.0.1::8080 invisible-browser-manager:language-guardrail
curl -fsS http://127.0.0.1:32775/api/status
# {"running_count":0,"launching_count":0,"failed_count":0,"binary_version":"invisible-playwright","profiles_total":0,"proxy_count":0,"task_queue_count":0,"automation_task_counts":{}}
docker stop cloakbrowser-language-guardrail-smoke
# cloakbrowser-language-guardrail-smoke

git diff --check
# passed
```

边界：

- 本轮 Docker smoke 只验证镜像构建、服务启动和 `/api/status` 低敏 health JSON；没有启动真实 profile、VNC 或外站检测页。
- 手工 create/edit/delete、launch/stop、VNC viewer、clipboard sync、Automation API、GeoIP、Proxy Manager、bulk actions、audit、代理国家矩阵和 BrowserLeaks/Pixelscan/IPhey/CreepJS 仍未标记完成。

## 2026-06-03 Automation console summary 低敏 guardrail

本轮补强 direct Automation API 的 console log 摘要边界：

- console message text 中的 `http://` / `https://` URL 只保留 scheme、host、port 和 path，移除 userinfo、query、fragment。
- console message text 中的 `token=`、`authorization=`、`password=`、`cookie=`、`*_token=`、`secret=` 等敏感键值会替换为 `[redacted]`。
- `Bearer ...` token 会替换为 `Bearer [redacted]`。
- console message location URL 同样只保留低敏 URL 形态。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_console_logs_redacts_sensitive_text_and_location_urls backend/tests/test_api.py::test_automation_console_logs_returns_in_memory_page_logs backend/tests/test_api.py::test_automation_console_logs_captures_recent_console_messages backend/tests/test_api.py::test_automation_network_summary_redacts_urls_and_returns_recent_events backend/tests/test_api.py::test_automation_network_summary_keeps_recent_redacted_events -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "automation" -q
# 75 passed, 132 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 508 passed in 29.65s

cd frontend && npm test -- --run
# Test Files 16 passed；Tests 221 passed

cd frontend && npm run build
# tsc -b && vite build；built in 4.91s

docker build --network=host --platform linux/amd64 -t invisible-browser-manager:automation-console-redaction .
# Successfully tagged invisible-browser-manager:automation-console-redaction

docker run -d --rm --name cloakbrowser-automation-console-redaction-smoke -p 127.0.0.1::8080 invisible-browser-manager:automation-console-redaction
curl -fsS http://127.0.0.1:32776/api/status
# {"running_count":0,"launching_count":0,"failed_count":0,"binary_version":"invisible-playwright","profiles_total":0,"proxy_count":0,"task_queue_count":0,"automation_task_counts":{}}
docker stop cloakbrowser-automation-console-redaction-smoke
# cloakbrowser-automation-console-redaction-smoke

git diff --check
# passed
```

边界：

- 这是 Automation API 摘要层 guardrail，不代表手工 Automation API 外站验收或 VNC 交互 smoke 已完成。
- 不记录真实 console payload、headers、cookies、local storage、proxy、token、截图或 profile dir 内容。
