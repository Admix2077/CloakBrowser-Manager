# 13 总回归、交付与上线门禁

## 目标

在所有模块完成后做整体回归，确保 manager 独立可用，并且 Project Mileage 联动不破坏安全边界。

## Manager 回归清单

- [x] profile 创建。
- [x] profile 编辑。
- [x] profile 删除。
- [x] launch。
- [x] stop。
- [x] VNC viewer。
- [x] clipboard sync。
- [x] Automation API。
- [x] GeoIP 自动同步。
- [x] health check。
- [x] Proxy Manager。
- [x] bulk actions。
- [x] audit。
- [x] Docker build。
- [x] Docker run。

## BrowserScan / 检测站人工验收

- [x] 无代理场景。
- [ ] US proxy。
- [ ] JP proxy。
- [ ] DE proxy。
- [x] timezone 与出口一致。
- [x] language 与 Accept-Language 一致。
- [x] BrowserScan 无 `Language mismatch`。
- [x] BrowserScan 无 `Different time zones`。
- [x] BrowserScan browser-checker 内核版本与 UA 一致。
- [x] BrowserScan WebRTC 不泄漏 local IP。
- [x] BrowserLeaks WebRTC / Canvas / WebGL / Fonts 无明显平台不一致。
- [x] CreepJS 无 webdriver/headless/lie detection 严重红灯。
- [ ] Pixelscan/IPhey 无 IP、timezone、language、WebRTC、hardware/software 高风险不一致。
- [x] 同一 seed 停止/重启后核心指纹稳定。
- [x] 不同 seed 的 profile 核心指纹有合理差异。

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

## 2026-06-03 Docker profile/VNC/Automation release smoke

环境：

- 镜像：`invisible-browser-manager:automation-console-redaction`
- 临时容器：`cloakbrowser-release-profile-smoke`
- 临时数据卷：`cloakbrowser-release-profile-smoke-data`
- 服务端口：随机绑定到 `127.0.0.1:32777`
- profile：无 proxy，`geoip=false`，Windows profile，`fingerprint_seed=24680`，`1280x720`，`hardwareConcurrency=4`
- smoke 完成后已停止容器并删除临时数据卷。

已覆盖：

- `/api/status` 初始返回 0 运行、0 profile、0 proxy、0 task。
- profile create 成功，返回 stopped。
- profile launch 需要 `confirm_launch=true`；确认后返回 running、`display=:100`、`vnc_ws_port=6100`、Automation URL。
- `/api/status` launch 后返回 `running_count=1`、`profiles_total=1`。
- Automation info/pages 可用，初始 page 为 `about:blank`。
- Direct Automation `goto` 打开低敏 `data:` 页面，`wait-for-selector` 命中 `#ready`。
- Direct Automation `evaluate` 返回低敏 fingerprint 摘要：
  - UA 为 Firefox 149 managed identity。
  - `navigator.webdriver=false`。
  - `navigator.language=en-US`、`navigator.languages=["en-US","en"]`。
  - timezone 为 `America/Los_Angeles`。
  - `hardwareConcurrency=4`。
  - screen 为 `1280x720`，`availHeight=672`。
- VNC WebSocket 连接 `/api/profiles/{id}/vnc` 成功并收到 `RFB 003.008` greeting。
- Queued Automation task create/run 成功；响应只回显 step type/status，不回显 evaluate result。
- Clipboard set/get 低敏文本成功。
- profile health endpoint 可用；因为本 profile 关闭 GeoIP，返回 `geoip_missing` info warning。
- profile edit 成功，支持 name、notes、tags 更新。
- profile stop 成功；随后 `/api/status` 返回 `running_count=0`。
- profile delete 成功；随后 `/api/status` 返回 `profiles_total=0`，profile list 为空。
- audit 只做容器内 SQLite 低敏查询，event types 为：
  - `profile.created`
  - `automation.task.created`
  - `automation.task.succeeded`
  - `profile.updated`
  - `profile.deleted`
  metadata keys 只包含 name/platform/tag_count、task id、status、step types/count、runner/result counts 和 updated_fields。

边界：

- 本轮没有保存截图、cookie、local storage、headers、proxy、token、profile dir 内容或完整 console/network payload。
- GeoIP 自动同步未覆盖，因为 smoke profile 明确设置 `geoip=false`。
- Proxy Manager、bulk actions、BrowserLeaks、Pixelscan/IPhey、CreepJS 和多国家代理矩阵仍未标记完成。

## 2026-06-03 GeoIP / Proxy Manager / bulk actions release smoke

环境：

- 镜像：`invisible-browser-manager:automation-console-redaction`
- 临时容器：`cloakbrowser-release-proxy-bulk-smoke`
- 临时数据卷：`cloakbrowser-release-proxy-bulk-smoke-data`
- 服务端口：随机绑定到 `127.0.0.1:32781`
- smoke 完成后已停止容器并删除临时数据卷。

已覆盖：

- `/api/status` 初始返回 0 running、0 profile、0 proxy。
- GeoIP profile 创建后调用 `/api/profiles/{id}/health/check`：
  - `status=good`
  - `has_geoip=true`
  - country 为 `US`
  - timezone 为 `America/Los_Angeles`
  - locale 为 `en-US`
  - warning codes 为空。
- Proxy Manager：
  - 创建 2 个 proxy asset。
  - 更新 proxy city/notes。
  - list proxies 返回 2 条。
  - 显式确认 assign，把 proxy 分配给 2 个 profile，`assign_succeeded=2`。
  - random assign 使用 provider/country/tag 过滤，candidate count 为 2，`random_succeeded=1`。
  - bulk check 传入 2 个 proxy 和 1 个 missing id，`total=3`、`succeeded=2`、`failed=1`。
  - Proxy Manager 响应未回显 fake credential secret，也未回显 userinfo。
- Bulk actions：
  - CSV import preview：`total=1`、`valid=1`。
  - CSV import：`succeeded=1`。
  - profile config export：`total=4`、`exported=3`、`failed=1`。
  - profile config import：`imported=1`。
  - profile export 响应不回显 userinfo。
- `/api/status` smoke 后返回 0 running、5 profiles、2 proxies；API cleanup 后返回 0 running、0 profiles、0 proxies。
- audit 只做容器内 SQLite 低敏查询，event types 为：
  - `profile.created`
  - `profile.health_checked`
  - `proxy.created`
  - `proxy.updated`
  - `proxy.assigned`
  - `proxy.random_assigned`
  - `proxy.bulk_checked`
  - `profile.imported`
  - `profile.config_exported`
  - `profile.config_imported`
  metadata keys 只包含 name/platform/tag_count、geoip country/source、lookup/status/warning counts、proxy/task/profile counts、provider/country/tag counts、schema/source format、updated_fields 和 include_sensitive 标志等低敏键。

边界：

- 本轮没有启动真实代理出口，也没有完成 US/JP/DE proxy-country 外站矩阵。
- 本轮没有保存截图、cookie、local storage、headers、token、profile dir 内容、完整 proxy URL 或完整 audit metadata。
- BrowserLeaks、Pixelscan/IPhey、CreepJS、same-seed restart stability 和 different-seed variation 仍未标记完成。

## 2026-06-03 Seed stability / variation release smoke

环境：

- 镜像：`invisible-browser-manager:automation-console-redaction`
- 临时容器：`cloakbrowser-seed-stability-smoke`
- 临时数据卷：`cloakbrowser-seed-stability-smoke-data`
- 两个无代理 Windows profile，均为 `geoip=false`、`timezone=America/Los_Angeles`、`locale=en-US`、`1280x720`、`hardwareConcurrency=4`
- same-seed profile seed 为 `24680`；different-seed 对照 profile seed 为 `97531`
- smoke 完成后已停止容器并删除临时数据卷。

已覆盖：

- `/api/status` 初始返回 0 running、0 profile、0 proxy，`binary_version=invisible-playwright`。
- 同一 profile 使用 seed `24680` launch、evaluate、stop、relaunch、evaluate、stop。
- 同一 seed 重启前后低敏核心指纹摘要 hash 均为 `930cebe5f91b4041`，`diff_keys=[]`。
- 不同 seed 对照 hash 为 `5db346eac7a0defa`，与 seed `24680` 不同。
- 不同 seed 差异字段为 `audioHash`、`canvasHash`、`webglVendor`。
- 检查字段包括 UA/appVersion、BuildID、webdriver、platform/vendor、language/languages、timezone、hardwareConcurrency、screen、colorDepth/pixelDepth、maxTouchPoints、WebGL vendor/renderer/version/shading language、canvas hash 和 audio hash。
- cleanup 后 `/api/status` 返回 0 running、0 profile、0 proxy。

诊断记录：

- 首次 smoke 的 evaluate 脚本在 `about:blank` 调用了 `crypto.subtle.digest` 导致固定错误 `Automation page action failed`。
- 分段诊断确认 Firefox 页面 `isSecureContext=false` 且 `crypto.subtle=undefined`；navigator、WebGL、canvas 和 audio 分段均可用。
- 最终 smoke 改用页面内简单哈希，避免依赖 secure context；该问题属于 smoke 脚本前提错误，不是 Manager runtime 缺口。

边界：

- 本轮没有访问外部检测站，也没有启动真实代理出口。
- 本轮没有保存截图、cookie、local storage、headers、token、profile dir 内容、完整 canvas data URL、完整 audio buffer、完整 proxy URL 或完整 audit metadata。
- BrowserLeaks、Pixelscan/IPhey、CreepJS 和 US/JP/DE proxy-country 外站矩阵仍未标记完成。

## 2026-06-03 BrowserLeaks WebRTC / Canvas / WebGL / Fonts smoke

环境：

- 镜像：`invisible-browser-manager:automation-console-redaction`
- 临时容器：`cloakbrowser-browserleaks-smoke`
- 临时数据卷：`cloakbrowser-browserleaks-smoke-data`
- profile：无 proxy，`geoip=true`，Windows profile，`fingerprint_seed=24680`，`1920x1080`，`hardwareConcurrency=8`
- smoke 完成后已停止容器并删除临时数据卷。

已覆盖：

- `/api/status` 初始返回 0 running、0 profile、0 proxy，`binary_version=invisible-playwright`。
- BrowserLeaks 页面均通过 direct Automation 打开并进入 `readyState=complete`：
  - `browserleaks.com/webrtc`：`WebRTC Leak Test - BrowserLeaks`
  - `browserleaks.com/canvas`：`Canvas Fingerprinting - BrowserLeaks`
  - `browserleaks.com/webgl`：`WebGL Browser Report - WebGL Fingerprinting - BrowserLeaks`
  - `browserleaks.com/fonts`：`Font Fingerprinting - BrowserLeaks`
- 四个页面上下文均显示 managed identity：
  - Firefox 149 UA 断言通过，`navigator.buildID=20260521160037`
  - `navigator.webdriver=false`
  - `navigator.platform=Win32`
  - `navigator.language=en-US`、`navigator.languages=["en-US","en"]`
  - timezone 为 `America/Los_Angeles`
  - `hardwareConcurrency=8`
- 四个页面的标题/低敏样本文本未出现 `linux`、`x11`、`headless`、`webdriver`、`selenium`、`chromedriver`、`swiftshader`、`llvmpipe`、`mesa`、`debian`、`ubuntu` 风险关键词。
- WebGL 摘要显示硬件形态 renderer：`ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0), or similar`；未出现 SwiftShader、llvmpipe、Mesa 等软件渲染风险关键词。
- Fonts 低敏探针显示常见 Windows 字体 `Arial`、`Times New Roman`、`Courier New`、`Segoe UI`、`Calibri`、`Cambria`、`Consolas` 可用；`DejaVu Sans`、`Liberation Sans` 不可用。
- cleanup 后 `/api/status` 返回 0 running、0 profile、0 proxy。

补充 WebRTC 全文检查：

- 临时容器：`cloakbrowser-browserleaks-webrtc-check`
- 临时数据卷：`cloakbrowser-browserleaks-webrtc-check-data`
- BrowserLeaks WebRTC full body 检查 `hasPrivateIpInFullBody=false`。
- BrowserLeaks WebRTC full body IPv4 candidate count 为 0。
- 页面包含 Local IP 说明标签文本，但没有 private/local IP pattern。
- cleanup 后 `/api/status` 返回 0 running、0 profile、0 proxy，并删除临时容器和数据卷。

边界：

- 本轮没有保存截图、cookie、local storage、headers、token、profile dir 内容、完整页面文本、完整 URL 参数、完整 canvas data URL、完整 font list、完整 WebRTC candidate 或完整 audit metadata。
- 本轮没有启动真实代理出口，也没有覆盖 US/JP/DE proxy-country 外站矩阵。
- Pixelscan/IPhey、CreepJS、BrowserScan `Language mismatch` 外站确认和多国家代理矩阵仍未标记完成。

## 2026-06-03 BrowserScan language mismatch smoke

环境：

- 镜像：`invisible-browser-manager:automation-console-redaction`
- 临时容器：`cloakbrowser-browserscan-language-smoke`
- 临时数据卷：`cloakbrowser-browserscan-language-smoke-data`
- profile：无 proxy，`geoip=true`，Windows profile，`fingerprint_seed=24680`，`1920x1080`，`hardwareConcurrency=8`
- smoke 完成后已停止容器并删除临时数据卷。

已覆盖：

- `/api/status` 初始返回 0 running、0 profile、0 proxy，`binary_version=invisible-playwright`。
- BrowserScan `browser-checker` 页面通过 direct Automation 打开并进入 `readyState=complete`：
  - title 为 `Browser kernel detection - Browser detection, kernel version detection, version detection, vulnerability detection - BrowserScan | BrowserScan`
  - full body scan：`languageMismatch=false`、`differentLanguages=false`、`acceptLanguageWarning=false`、`mismatchCount=0`
- BrowserScan `bot-detection` 页面通过 direct Automation 打开并进入 `readyState=complete`：
  - title 为 `BrowserScan - Robot Detection/WebDriver | BrowserScan`
  - full body scan：`languageMismatch=false`、`differentLanguages=false`、`acceptLanguageWarning=false`、`mismatchCount=0`
  - 页面 `normalCount=18`
- 两个页面上下文均显示 managed identity：
  - Firefox 149 UA 断言通过，`navigator.buildID=20260521160037`
  - `navigator.webdriver=false`
  - `navigator.platform=Win32`
  - `navigator.language=en-US`、`navigator.languages=["en-US","en"]`
  - `Intl.DateTimeFormat().resolvedOptions().locale=en-US`
  - timezone 为 `America/Los_Angeles`
  - `hardwareConcurrency=8`
- 两个页面均未出现 webdriver/headless warning pattern。
- cleanup 后 `/api/status` 返回 0 running、0 profile、0 proxy。

边界：

- BrowserScan 页面没有直接展示 `Accept-Language` 字段；本轮只标记 BrowserScan `Language mismatch` 外站确认通过，`language 与 Accept-Language 一致` 仍保留未完成。
- 本轮没有保存截图、cookie、local storage、headers、token、profile dir 内容、完整页面文本、完整 URL 参数、完整 network payload 或完整 audit metadata。
- 本轮没有启动真实代理出口，也没有覆盖 US/JP/DE proxy-country 外站矩阵。
- Pixelscan/IPhey、CreepJS、`language 与 Accept-Language 一致` 和多国家代理矩阵仍未标记完成。

## 2026-06-03 CreepJS smoke

环境：

- 镜像：`invisible-browser-manager:automation-console-redaction`
- 临时容器：`cloakbrowser-creepjs-diagnostic`
- 临时数据卷：`cloakbrowser-creepjs-diagnostic-data`
- profile：无 proxy，`geoip=true`，Windows profile，`fingerprint_seed=24680`，`1920x1080`，`hardwareConcurrency=8`
- smoke 完成后已停止容器并删除临时数据卷。

已覆盖：

- CreepJS 页面 `https://abrahamjuliot.github.io/creepjs/` 通过 direct Automation 打开并进入 `readyState=complete`。
- 页面 title 为 `CreepJS`，页面文本长度为 3842。
- 低敏计数：
  - `lies=0`
  - `webdriver=0`
  - `severe=0`
  - `headless=3`
- `headless` 命中行均为非风险结论：
  - `0% like headless: bada4467`
  - `0% headless: 52defe05`
- 页面上下文显示 managed identity：
  - Firefox 149 UA 断言通过，`navigator.buildID=20260521160037`
  - `navigator.webdriver=false`
  - `navigator.platform=Win32`
  - `navigator.language=en-US`、`navigator.languages=["en-US","en"]`
  - `Intl.DateTimeFormat().resolvedOptions().locale=en-US`
  - timezone 为 `America/Los_Angeles`
  - `hardwareConcurrency=8`
- 页面主身份行包含 Windows / Win32 / Windows 10 / Firefox 149。
- WebGL 摘要显示硬件形态 renderer：`ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0), or similar`。
- cleanup 后 `/api/status` 返回 0 running、0 profile、0 proxy。

诊断记录：

- 首次 CreepJS smoke 以全文 `linux` 关键词为硬失败条件，命中 `linuxMention=true`。
- 后续低敏诊断确认该命中来自单行 `Sans:Linux`，不是 UA、navigator platform、WebGL renderer、webdriver、headless 或 lie detection 严重红灯。

边界：

- CreepJS 对字体类别显示 `Sans:Linux`，本轮不将其判定为 webdriver/headless/lie detection 严重红灯；但该字体分类线应在后续更细的字体一致性工作中继续观察。
- 本轮没有保存截图、cookie、local storage、headers、token、profile dir 内容、完整页面文本、完整 URL 参数、完整 font list、完整 WebRTC candidate 或完整 audit metadata。
- 本轮没有启动真实代理出口，也没有覆盖 US/JP/DE proxy-country 外站矩阵。
- Pixelscan/IPhey、`language 与 Accept-Language 一致` 和多国家代理矩阵仍未标记完成。

## 2026-06-03 Accept-Language echo smoke

环境：

- 镜像：`invisible-browser-manager:automation-console-redaction`
- 临时容器：`cloakbrowser-accept-language-smoke`
- 临时数据卷：`cloakbrowser-accept-language-smoke-data`
- profile：无 proxy，`geoip=false`，Windows profile，`fingerprint_seed=24680`，`1280x720`，`hardwareConcurrency=4`，`locale=en-US`，`timezone=America/Los_Angeles`
- smoke 完成后已停止容器并删除临时数据卷。

已覆盖：

- `/api/status` 初始返回 0 running、0 profile、0 proxy，`binary_version=invisible-playwright`。
- 容器内启动只记录 `Accept-Language` 的本地 echo server，Firefox 通过 direct Automation 访问 `127.0.0.1` echo 页面。
- profile launch 成功，返回 `display=:100`、`vnc_ws_port=6100`。
- echo server 捕获的浏览器请求头：
  - `Accept-Language=en-US,en;q=0.9`
- 页面端语言值：
  - `navigator.language=en-US`
  - `navigator.languages=["en-US","en"]`
  - `Intl.DateTimeFormat().resolvedOptions().locale=en-US`
- 其他 managed identity 断言：
  - Firefox 149 UA 断言通过，`navigator.buildID=20260521160037`
  - `navigator.webdriver=false`
  - `navigator.platform=Win32`
  - timezone 为 `America/Los_Angeles`
  - `hardwareConcurrency=4`
- cleanup 后 `/api/status` 返回 0 running、0 profile、0 proxy。

边界：

- 本轮只记录单项 `Accept-Language` 值和页面端低敏语言摘要；没有保存完整 headers、network payload、cookie、local storage、token、profile dir 内容、截图或完整页面文本。
- 本轮没有启动真实代理出口，也没有覆盖 US/JP/DE proxy-country 外站矩阵。
- Pixelscan/IPhey 和多国家代理矩阵仍未标记完成。

## 2026-06-03 Pixelscan / IPhey diagnostic smoke

环境：

- 镜像：`invisible-browser-manager:automation-console-redaction`
- 临时容器：`cloakbrowser-pixelscan-iphey-smoke`
- 临时数据卷：`cloakbrowser-pixelscan-iphey-smoke-data`
- profile：无 proxy，`geoip=true`，Windows profile，`fingerprint_seed=24680`，`1920x1080`，`hardwareConcurrency=8`
- smoke 完成后已停止容器并删除临时数据卷。

已覆盖：

- `/api/status` 初始返回 0 running、0 profile、0 proxy，`binary_version=invisible-playwright`。
- profile launch 成功，返回 `display=:100`、`vnc_ws_port=6100`。
- Pixelscan `https://pixelscan.net/fingerprint` 通过 direct Automation 打开，最终路径为 `pixelscan.net/fingerprint-check`，页面 `readyState=complete`。
- Pixelscan managed identity 断言通过：
  - Firefox 149 UA 断言通过，`navigator.buildID=20260521160037`
  - `navigator.webdriver=false`
  - `navigator.platform=Win32`
  - `navigator.language=en-US`、`navigator.languages=["en-US","en"]`
  - `Intl.DateTimeFormat().resolvedOptions().locale=en-US`
  - timezone 为 `America/Los_Angeles`
  - `hardwareConcurrency=8`
  - WebGL renderer 为 NVIDIA / Direct3D11 形态，未出现 SwiftShader / llvmpipe / Mesa 标记。
- IPhey `https://iphey.com/` 通过 direct Automation 打开，页面 title 为 `Iphey - Real-Time Browser Fingerprinting Test -  IPhey`，低敏状态行包含 `Trustworthy`。
- IPhey home managed identity 断言同样通过。
- cleanup 后 `/api/status` 返回 0 running、0 profile、0 proxy。

失败 / 未完成项：

- Pixelscan 页面实际状态行显示 `Your Browser Fingerprint is inconsistent`。
- Pixelscan 诊断行还显示 Browser、Location、Fingerprint、WebRTC IP Address、Timezone from JS、HardwareConcurency、Language、Languages from Javascript、Accept-Language header 和 Hardware 等卡片，说明这不是单纯说明文案。
- IPhey `/leaks` 返回 `ERROR: The request could not be satisfied`，不能作为有效 leak check 通过证据。
- 已创建 `cbim-23h.6` 跟踪 Pixelscan no-proxy fingerprint inconsistency 根因修复。

边界：

- 本轮没有保存截图、cookie、local storage、headers、token、IP 值、profile dir 内容、完整页面文本、完整 URL 参数、完整 font list、完整 WebRTC candidate 或完整 audit metadata。
- `Pixelscan/IPhey 无 IP、timezone、language、WebRTC、hardware/software 高风险不一致` 仍未标记完成。
- 本轮没有启动真实代理出口，也没有覆盖 US/JP/DE proxy-country 外站矩阵。

## 2026-06-03 Pixelscan root-cause diagnostic

环境：

- 镜像：`invisible-browser-manager:automation-console-redaction`
- 临时容器：
  - `cloakbrowser-pixelscan-rootcause-step`
  - `cloakbrowser-pixelscan-dom`
  - `cloakbrowser-pixelscan-minimal`
- 对应临时数据卷均已删除。

新增证据：

- 阶段化复现稳定到达 `pixelscan.net/fingerprint-check`，页面 `readyState=complete`，cleanup 后 `/api/status` 返回 0 running、0 profile。
- Pixelscan DOM 明确显示总状态条 `data-state=error`，状态文本为 `Your Browser Fingerprint is inconsistent`。
- 失败卡片不是 Proxy、Location、Language、WebRTC 或 Bot check：
  - Proxy 卡片：`No proxy detected Proxy`，未带 failed class。
  - Location 卡片：`United States / Los Angeles Location`，未带 failed class。
  - Bot check 卡片：`No automated behavior detected Bot check`，未带 failed class。
  - 唯一 failed card 为 `PXLSCN-FINGERPRINT-MASKING`，class 为 `checker-card--failed`，文本为 `Masking detected Fingerprint`。
- 最小 profile 对照复现仍失败在同一张卡：
  - 去掉显式 `gpu_vendor`、`gpu_renderer`、`hardware_concurrency` 后，Pixelscan 仍返回 `failedCards=["Masking detected Fingerprint"]`。
  - 这说明失败不是 Manager 显式 GPU/hardwareConcurrency pin 单点导致。
- 页面端低敏身份仍保持一致：
  - HTTP UA 与 JavaScript UA 均为 Firefox 149 Windows 形态。
  - `navigator.webdriver=false`。
  - `navigator.platform=Win32`。
  - `navigator.buildID=20260521160037`。
  - language / Intl locale / Accept-Language 对齐。
  - timezone 与 Pixelscan 页面显示的 location/timezone 对齐。
  - WebGL 为 NVIDIA / Direct3D11 形态，无 SwiftShader / llvmpipe / Mesa 标记。
- 后续复核确认 `invisible-browser-manager:automation-console-redaction` 镜像内底层 `invisible_playwright` 版本为 `0.1.8`；Firefox `application.ini` 显示 `Version=150.0.1`、`BuildID=20260521160037`。
- 底层 `invisible_playwright` 的 `seed` 会生成完整 stealth fingerprint profile，并写入 `zoom.stealth.*` prefs，包括 canvas、audio、WebGL、font、screen、hardware 和 cross-process seed；当前 Pixelscan 红灯与这类 fingerprint masking 行为一致。

A/B 边界：

- 尝试在一次性容器内覆盖 `zoom.stealth.fpp.hw_seed=0`、`zoom.stealth.seed=0` 和极低 canvas noise 频率，Firefox launch 失败；不作为生产修复候选。
- 尝试只把 `zoom.stealth.canvas.noise_skip_mask` 提高到较低噪声值也导致 Firefox launch 失败；不作为生产修复候选。
- 本轮未找到一个同时满足 Pixelscan、BrowserScan、BrowserLeaks、CreepJS 和 seed-stability 的 Manager 侧安全修复。

当前判断：

- `cbim-23h.6` 继续保持 open / in-progress。
- 根因更接近底层 patched Firefox / `invisible_playwright` 的 fingerprint masking 可检测面，而不是 Manager 的 proxy、GeoIP、language、WebRTC 或显式 GPU/hardwareConcurrency 配置。
- 在没有通过全矩阵验证的替代 runtime/prefs 前，不应为了单个 Pixelscan 红灯移除 seed-based fingerprint profile；否则会破坏同 seed 稳定性、不同 seed 差异、Windows WebGL 形态或其他已通过 gate。

边界：

- 本轮没有保存截图、cookie、local storage、完整 headers、token、IP 值、profile dir 内容、完整页面文本、完整 URL 参数、完整 font list、完整 WebRTC candidate 或完整 audit metadata。
- Pixelscan/IPhey gate 仍未标记完成。
- US/JP/DE proxy-country 外站矩阵仍未覆盖。

## 2026-06-03 diagnostics Firefox identity observability

背景：

- Pixelscan root-cause 诊断确认 Manager 对外 Firefox 149 identity 与底层 Firefox `application.ini` `Version=150.0.1` / `BuildID=20260521160037` 同时存在。
- 为避免后续排障再次临时进入容器读取依赖包，本轮把该低敏 identity 摘要纳入受保护 diagnostics。

已覆盖：

- `GET /api/diagnostics` 的 `runtime` 节点新增：
  - `managed_user_agent_version`
  - `invisible_playwright_version`
  - `firefox_binary_version`
  - `firefox_binary_build_id`
- 前端 System diagnostics Runtime 区块显示 Managed UA、Engine package、Firefox binary 和 Firefox BuildID。
- 后端 diagnostics 测试继续断言不加载 profile/proxy/task 明细，不泄漏 profile id、路径、proxy、token、automation steps 等敏感内容，并新增完整 UA 不出现在响应中的 guardrail。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# RED: KeyError: 'invisible_playwright_version'

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx
# RED: Unable to find group "Engine package: invisible_playwright 0.1.8"

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 2 passed

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 508 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully
```

边界：

- 本轮没有修改底层 Firefox / `invisible_playwright` fingerprint masking 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker。

## 2026-06-03 Firefox identity diagnostics version redaction

背景：

- Firefox identity diagnostics 是 release smoke 中比对 Manager managed UA、installed `invisible_playwright` package、Firefox `application.ini` version 和 BuildID 的低敏信号。
- 为防御异常 package/application metadata，版本字段和 BuildID 不能把非版本文本原样展示成 diagnostics 值。

已覆盖：

- `managed_user_agent_version`、`invisible_playwright_version` 和 `firefox_binary_version` 只公开数字段版本。
- `firefox_binary_build_id` 只公开 8 到 20 位数字。
- 非白名单值返回 `None`，前端显示 `unknown`。
- 当前本地有效 summary 仍保留 Firefox 149 / invisible_playwright 0.1.8 / Firefox binary 150.0.1 / BuildID 20260521160037。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_managed_firefox_identity_summary_discards_non_public_version_metadata -q
# RED then GREEN; final 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_managed_firefox_identity_summary_discards_non_public_version_metadata backend/tests/test_browser_manager.py::test_stealth_pref_category_normalizes_sensitive_pref_keys backend/tests/test_browser_manager.py::test_invisible_stealth_pref_summary_degrades_without_full_package backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# 4 passed

. .venv/bin/activate && python - <<'PY'
from backend import browser_manager as bm
bm._firefox_application_ini_metadata.cache_clear()
bm._invisible_stealth_pref_summary.cache_clear()
print(bm.managed_firefox_identity_summary())
PY
# {'managed_user_agent_version': '149.0', 'invisible_playwright_version': '0.1.8', 'firefox_binary_version': '150.0.1', 'firefox_binary_build_id': '20260521160037', 'stealth_pref_count': 29, 'stealth_pref_categories': ['audio', 'canvas', 'debugger', 'fingerprint', 'font', 'hardware', 'screen', 'storage', 'timezone', 'voices', 'webgl', 'webrtc']}

. .venv/bin/activate && python -m pytest backend/tests -q
# 515 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA 或 patched Firefox 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 automation task page_ref redaction guardrail

背景：

- `cbim-23h.6` 下一阶段范围要求继续保护 automation、proxy、profile、WebRTC、headers、screenshots 和 audit metadata redaction guardrails。
- 检查 Automation task redaction 时发现 `page_ref` 会原样持久化并在 task create/get/list/cancel/run 响应中回显；契约上它只应是 page index 或 UUID page_id，如果调用方传入 URL/token/path，会形成低敏响应边界缺口。

已覆盖：

- `page_ref` 入库和响应前先清洗：
  - 十进制 page index 保留。
  - UUID page_id 规范化为小写 UUID。
  - 其他字符串或非字符串值统一保存/回显为 `invalid`。
- 新测试证明带 query/fragment/token 的 `page_ref` 不会出现在 create/get/list/cancel 响应或 persisted task 中。
- 相邻 focused tests 证明现有 evaluate redaction、worker step failure redaction 和 UUID page_id 稳定性未被破坏。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_page_ref_before_persisting_or_responding -q
# RED: response echoed https://app.example.com/dashboard?token=page-ref-super-secret#frag

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_page_ref_before_persisting_or_responding backend/tests/test_api.py::test_automation_task_responses_redact_evaluate_steps backend/tests/test_api.py::test_automation_worker_run_once_fails_http_step_errors_without_leaking_payload backend/tests/test_api.py::test_automation_page_id_remains_stable_when_page_order_changes -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 509 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 本轮没有修改底层 Firefox / `invisible_playwright` fingerprint masking 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker。

## 2026-06-03 diagnostics stealth pref surface observability

背景：

- Pixelscan no-proxy blocker 当前唯一 failed card 是 `PXLSCN-FINGERPRINT-MASKING` / `Masking detected Fingerprint`。
- 继续排障需要确认当前 Manager 所用 `invisible_playwright` 包生成的 stealth pref 结构面，但 release notes 不能保存 seed、IP、pref value、完整 key、profile dir、proxy、headers、cookies、local storage 或页面文本。

已覆盖：

- `GET /api/diagnostics` 的 `runtime` 节点新增：
  - `stealth_pref_count`
  - `stealth_pref_categories`
- categories 是低敏粗分类，例如 canvas、fingerprint、hardware、screen、webgl、webrtc。
- 原始 `zoom.stealth.*` key 不出现在 API 响应或前端页面；`hw_seed`、seed value、WebRTC host IP、pref value 和 package path 均不返回。
- 前端 System diagnostics 显示 Stealth prefs 和 Stealth categories，长分类列表在视觉上截断但保留完整 aria-label 供测试和辅助技术读取。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# RED: KeyError: 'stealth_pref_count'

npm --prefix frontend test -- --run src/components/SystemDiagnosticsPage.test.tsx src/lib/api.test.ts -t "diagnostics"
# RED: Unable to find group "Stealth prefs: 29 keys"

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_browser_manager.py::test_stealth_pref_category_normalizes_sensitive_pref_keys backend/tests/test_browser_manager.py::test_invisible_stealth_pref_summary_degrades_without_full_package -q
# 3 passed

npm --prefix frontend test -- --run src/components/SystemDiagnosticsPage.test.tsx src/lib/api.test.ts -t "diagnostics"
# 2 files / 3 tests passed, 39 skipped

. .venv/bin/activate && python -m pytest backend/tests -q
# 511 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 本轮没有修改底层 Firefox / `invisible_playwright` fingerprint masking 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker。

## 2026-06-03 stealth pref category diagnostics redaction

背景：

- `stealth_pref_categories` 是 release smoke 中排查 Pixelscan fingerprint masking 的低敏聚合信号。
- 为防御底层 `invisible_playwright` 未来新增异常 `zoom.stealth.*` key，category 不能把非白名单文本原样展示成 diagnostics 值。

已覆盖：

- Stealth pref diagnostics category 只公开已知低敏分类和 `unknown`。
- `fpp/seed/hw_concurrency/webgl2` 继续归一化为 `fingerprint/hardware/webgl`。
- 非白名单 category 归并到 `unknown`，测试覆盖敏感 category 文本不会出现在 public category 中。
- 当前本地 package summary 仍返回 29 个 stealth prefs 和 12 个已知分类，没有引入生产行为变化。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_stealth_pref_category_normalizes_sensitive_pref_keys -q
# RED then GREEN; final 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_stealth_pref_category_normalizes_sensitive_pref_keys backend/tests/test_browser_manager.py::test_invisible_stealth_pref_summary_degrades_without_full_package backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# 3 passed

. .venv/bin/activate && python - <<'PY'
from backend import browser_manager as bm
bm._invisible_stealth_pref_summary.cache_clear()
print(bm._invisible_stealth_pref_summary())
PY
# {'stealth_pref_count': 29, 'stealth_pref_categories': ['audio', 'canvas', 'debugger', 'fingerprint', 'font', 'hardware', 'screen', 'storage', 'timezone', 'voices', 'webgl', 'webrtc']}

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA 或 patched Firefox 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 automation task type/result summary redaction guardrail

背景：

- `cbim-23h.6` 下一阶段范围要求持续保护 automation payload、result、audit metadata 和历史数据响应边界。
- 未知 step `type` 是调用方可控字符串，旧实现会把它原样持久化、响应并写入 audit `step_types`。
- 历史 result summary 的 `index/type/status` 旧实现也允许非整数 index 或非白名单 type/status 原样回显。

已覆盖：

- 未知或非字符串 task step `type` 统一归一化为 `unknown`。
- 归一化覆盖 create/get/list/cancel/run 响应、persisted task、runner result step type 和 automation audit `step_types`。
- `result.steps[]` 摘要字段清洗：
  - `index` 只保留非负整数，否则为 `null`。
  - `type` 只保留支持的 step type，否则为 `unknown`。
  - `status` 只保留 `succeeded | failed | cancelled`，否则为 `unknown`。
- 前端 Automation task viewer 对 `index: null` 显示为 `-`。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_unknown_step_type_before_persisting_responding_or_audit backend/tests/test_api.py::test_automation_task_result_summary_sanitizes_corrupted_summary_fields -q
# RED: unknown step type and corrupted result summary fields leaked raw sensitive values

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_unknown_step_type_before_persisting_responding_or_audit backend/tests/test_api.py::test_automation_task_result_summary_sanitizes_corrupted_summary_fields backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_page_ref_before_persisting_or_responding backend/tests/test_api.py::test_automation_task_responses_redact_persisted_result_steps backend/tests/test_api.py::test_automation_task_create_cancel_retry_and_run_write_redacted_audit_events -q
# 5 passed

npm --prefix frontend test -- --run src/components/AutomationTaskLogViewer.test.tsx
# 1 file / 6 tests passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 513 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 本轮没有修改底层 Firefox / `invisible_playwright` fingerprint masking 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker。

## 2026-06-03 launch failure stage diagnostics

背景：

- `cbim-23h.6` 仍然指向 Pixelscan `PXLSCN-FINGERPRINT-MASKING`，但 release smoke 也需要能快速排除 VNC、profile startup cleanup、GeoIP resolution、engine enter 和 context configuration 这类启动链路失败。
- 旧 `/api/diagnostics` 没有最近 launch failure 的低敏 stage 摘要，外站 smoke 失败后很难判断是否需要先处理 runtime 稳定性。

已覆盖：

- `BrowserManager` 记录当前进程内 launch failure stage counts。
- `/api/diagnostics` Runtime 节点返回 `launch_failure_count` 和 `launch_failure_stage_counts`。
- System diagnostics 页面展示 Launch failures 与 Launch failure stages。
- profile launch / runtime session launch 的 500 日志不再记录异常消息正文，只保留固定错误类型，避免把 token、路径、proxy host 或 URL 文本写入日志。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_clears_launching_state_when_vnc_allocation_fails backend/tests/test_browser_manager.py::test_launch_releases_vnc_when_startup_state_cleanup_fails backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_reports_low_sensitive_launch_failure_summary -q
# RED then GREEN; final 4 passed

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx api.test.ts
# RED then GREEN; final 2 files / 42 tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_rejects_when_max_running_profiles_reached_without_allocating_vnc backend/tests/test_api.py::test_launch_invalid_proxy_real_validation_400 backend/tests/test_api.py::test_launch_failure_500 backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows backend/tests/test_session_broker.py::test_runtime_session_create_respects_max_running_profiles backend/tests/test_browser_manager.py::test_launch_uses_invisible_playwright_on_vnc_display -q
# 6 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA 或 patched Firefox 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 automation task status aggregate redaction

背景：

- `automation_task_counts` 是 release smoke 和 diagnostics 中判断 automation queue/running/failed backlog 的低敏聚合信号。
- 为防御历史/损坏 DB row，status counts 不能把非白名单 automation task status 原样展示成可见 `/api/status` 或 `/api/diagnostics` key。

已覆盖：

- Automation task status counts 只公开 `queued`、`running`、`cancel_requested`、`cancelled`、`failed`、`succeeded` 和 `unknown`。
- 非白名单 status 归并到 `unknown`，测试覆盖敏感 status 文本不会出现在 API 响应序列化中。
- 相邻 status/diagnostics count-query 测试和完整后端/前端门禁重新验证。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_status backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# RED then GREEN; final 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_status backend/tests/test_api.py::test_system_status_uses_count_queries_without_loading_sensitive_rows backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA 或 patched Firefox 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 runtime session status diagnostics redaction

背景：

- `runtime_sessions.status_counts` 是 release smoke 中排查 viewer/session 生命周期的低敏聚合信号。
- 为防御历史/损坏 DB row，status counts 不能把非白名单 status 原样展示成可见 diagnostics key。

已覆盖：

- Runtime session diagnostics status counts 只公开 `active`、`terminated` 和 `unknown`。
- 非白名单 status 归并到 `unknown`，测试覆盖敏感 status 文本不会出现在 API 响应序列化中。
- 相邻 session broker、diagnostics、前端 diagnostics、完整后端/前端门禁重新验证。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot -q
# RED then GREEN; final focused diagnostics test passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 30 passed

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx api.test.ts
# 2 files / 42 tests passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA 或 patched Firefox 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 runtime session diagnostics summary

背景：

- 下一阶段 release 收敛目标覆盖 runtime session / VNC viewer session 的低敏可观测性。
- 旧 System diagnostics 不展示 runtime session 聚合状态，外部 smoke 或 Project Mileage viewer 问题只能通过具体 session API/audit 逐项排查。

已覆盖：

- `/api/diagnostics` 新增低敏 `runtime_sessions` 汇总：
  - `status_counts`
  - `live_count`
  - `active_viewer_token_count`
- 汇总来自 SQL 聚合查询，不加载 runtime session 明细、不读取 audit rows。
- System diagnostics 页面新增 Runtime sessions 区块，显示 Live sessions、Viewer credentials、Runtime session statuses。
- 页面文案避免出现 token 相关字样；测试继续断言页面不渲染 token、runtime id、profile id、proxy 或 secret 文本。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# RED then GREEN; final 2 passed

npm --prefix frontend test -- SystemDiagnosticsPage.test.tsx api.test.ts
# RED then GREEN; final 2 files / 42 tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 30 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 514 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA 或 patched Firefox 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Firefox BuildID init script redaction guardrail

背景：

- Release smoke 需要继续比较 BrowserScan/Pixelscan/IPhey 中的 UA、Firefox binary 和 `navigator.buildID` 证据。
- diagnostics 层已限制 Firefox BuildID 只公开数字值，但页面 init script 覆盖路径也必须保持同样边界，避免污染 metadata 进入浏览器上下文。

已覆盖：

- `_firefox_build_id_override()` 只返回 8-20 位数字 BuildID。
- 污染 BuildID 会在 init script 中降为 `null`，不会进入脚本文本。
- 合法数字 BuildID 覆盖 `navigator.buildID` 的行为保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_browser_init_script_drops_non_public_firefox_build_id -q
# RED then GREEN; final focused test passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_browser_init_script_drops_non_public_firefox_build_id backend/tests/test_browser_manager.py::test_browser_init_script_overrides_stale_navigator_build_id backend/tests/test_browser_manager.py::test_managed_firefox_identity_summary_discards_non_public_version_metadata -q
# 3 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 516 passed

npm --prefix frontend test
# 16 files / 221 tests passed

npm --prefix frontend run build
# built successfully

git diff --check
# no output
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA 或 patched Firefox 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 browser locale public-value guardrail

背景：

- Pixelscan/IPhey gate 仍显示 fingerprint masking inconsistency；language / Accept-Language 已有外站和 echo smoke 通过，但启动路径仍应防止非 locale 文本进入浏览器身份面。
- profile locale 会同时影响 invisible launch kwargs、`Accept-Language` 和 `navigator.language(s)`，需要保持同一低敏规范化规则。

已覆盖：

- 非公开 locale 字符串降级为 `en-US`，不进入 launch kwargs、header 或 init script。
- 正常 locale 继续支持 `en-US`、`zh_CN`、`ja` 等既有格式。
- 相邻 BrowserManager 语言/launch 单元测试已复验。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_accept_language_header_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_browser_init_script_drops_non_public_locale_text -q
# RED then GREEN; final focused tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_accept_language_header_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_browser_init_script_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_accept_language_header_includes_base_language backend/tests/test_browser_manager.py::test_browser_init_script_aligns_navigator_languages_with_accept_language_fallback backend/tests/test_browser_manager.py::test_launch_resolves_missing_timezone_and_locale_before_invisible_launch -q
# 6 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 55 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、timezone、proxy 或 patched Firefox 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 browser timezone public-value guardrail

背景：

- Pixelscan/IPhey gate 仍未完成，但 timezone 是外站 release smoke 的关键检查面。
- profile timezone 会进入 invisible launch kwargs，必须避免非 IANA 时区文本影响浏览器身份面或污染调试证据。

已覆盖：

- `_build_invisible_kwargs()` 只把 zoneinfo 可解析的公开 timezone 传给 invisible browser。
- 非公开/header/token/path 风格 timezone 字符串降为空字符串，沿用未指定 timezone 的启动语义。
- 合法 timezone 如 `America/New_York`、`America/Los_Angeles` 在相邻 tests 中保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_timezone_text -q
# RED then GREEN; final focused test passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_timezone_text backend/tests/test_browser_manager.py::test_build_invisible_kwargs_maps_manager_profile backend/tests/test_browser_manager.py::test_build_invisible_kwargs_omits_empty_optional_values backend/tests/test_browser_manager.py::test_launch_resolves_missing_timezone_and_locale_before_invisible_launch -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 56 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、proxy、GeoIP 填充或 profile 存储行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 GPU/WebGL launch pin public-value guardrail

背景：

- BrowserLeaks/Pixelscan release smoke 会检查 Hardware/WebGL 面；GPU pin 文本必须保持低敏、短值、可解释。
- profile GPU 字段是自由文本，旧启动路径会把非公开 renderer/vendor 文本传播到 invisible fingerprint pin。

已覆盖：

- 非公开 GPU vendor/renderer 文本不再进入 launch pin。
- 非公开 renderer 经 coherent WebGL identity path 回落到固定 Firefox WebGL renderer bucket。
- 正常 GPU pin 和 NVIDIA renderer bucket 单元测试已复验。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_non_public_gpu_text backend/tests/test_browser_manager.py::test_with_coherent_webgl_identity_drops_non_public_renderer_text -q
# RED then GREEN; final focused tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_non_public_gpu_text backend/tests/test_browser_manager.py::test_with_coherent_webgl_identity_drops_non_public_renderer_text backend/tests/test_browser_manager.py::test_build_invisible_pin_screen_gpu_hardware_dark_theme backend/tests/test_browser_manager.py::test_coherent_webgl_renderer_collapses_modern_nvidia_to_firefox_sanitize_bucket backend/tests/test_browser_manager.py::test_with_coherent_webgl_identity_rewrites_profile_renderer -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 58 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebRTC、UA、locale、timezone、proxy、GeoIP 填充或 profile 存储行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 screen and hardware launch pin public-value guardrail

背景：

- BrowserLeaks/Pixelscan release smoke 会检查 Screen/Hardware 面；screen 和 hardware concurrency pin 必须保持现实范围。
- profile screen/hardware 字段可能来自导入或历史数据，旧启动路径会把极端值传播到 invisible fingerprint pin，损坏文本还可能触发 pin 构建异常。

已覆盖：

- 极端 screen width/height 和 hardware concurrency 不再进入 launch pin。
- 污染 screen/hardware 字符串不会进入 pin，也不会导致 pin 构建崩溃。
- 正常 2560x1440、1920x1080、1366x768 和 hardware concurrency 8/12 等相邻路径已复验。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_non_public_screen_and_hardware_values -q
# RED then GREEN; final focused test passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_non_public_screen_and_hardware_values backend/tests/test_browser_manager.py::test_build_invisible_pin_drops_corrupted_screen_and_hardware_text backend/tests/test_browser_manager.py::test_build_invisible_pin_screen_gpu_hardware_dark_theme backend/tests/test_browser_manager.py::test_build_invisible_pin_uses_realistic_1080p_available_height backend/tests/test_browser_manager.py::test_build_invisible_kwargs_maps_manager_profile -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 60 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充或 profile 存储行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 VNCManager start log redaction guardrail

背景：

- 发布 smoke 的 launch/VNC viewer 路径依赖 VNCManager `start_vnc()`。
- 旧 Xvnc start 日志会输出内部 `/tmp/xvnc-*.log` path，log 读取失败时会输出 raw exception message。

已覆盖：

- Xvnc start request 只记录固定 action、display、ws_port、width、height。
- Xvnc log read failure 只记录固定 action、display、error_type。
- VNC allocation、start command、process tracking、stop/cleanup 语义保持。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py::test_start_vnc_logs_action_without_internal_log_path backend/tests/test_vnc_manager.py::test_start_vnc_log_read_failure_logs_error_type_without_raw_exception -q
# RED then GREEN; final focused tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py -q
# 15 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸选择、viewer token issuance、profile 存储、VNC command args 或 launch fallback 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Health GeoIP lookup failure log redaction guardrail

背景：

- 发布 smoke 会通过 `/api/profiles/{profile_id}/health/check` 触发 proxy/GeoIP/timezone/locale 检查。
- 旧 lookup failure 日志会输出 raw exception message，可能固化 provider URL、proxy host、credentials、token 或 query。

已覆盖：

- GeoIP lookup failure 只记录固定 action、profile_id、error_type。
- health response、profile last_geoip cache、health audit metadata 语义保持。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_check_lookup_failure_logs_error_type_without_raw_exception -q
# RED then GREEN; final focused test passed

. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q
# 18 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、health status/warning/audit 语义或 launch fallback 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation/clipboard introspection debug log redaction guardrail

背景：

- 发布 smoke 会覆盖 VNC clipboard sync、automation pages list 和 page summary。
- 旧 clipboard/page-title debug 日志会输出 raw exception message，可能固化页面 URL、token、profile path 或页面内容片段。

已覆盖：

- Clipboard page evaluate failure 只记录固定 action、profile_id、error_type。
- Clipboard context/pages failure 只记录固定 action、profile_id、error_type。
- Automation page title failure 只记录固定 action、profile_id、page_index、error_type。
- Clipboard xclip fallback 与 automation page title 空字符串 fallback 语义保持。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_get_clipboard_page_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_get_clipboard_context_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_automation_page_title_failure_logs_error_type_without_raw_exception -q
# RED then GREEN; final focused tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_set_clipboard_not_running backend/tests/test_api.py::test_get_clipboard_not_running backend/tests/test_api.py::test_set_clipboard_success backend/tests/test_api.py::test_get_clipboard_from_page backend/tests/test_api.py::test_get_clipboard_page_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_get_clipboard_context_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_automation_pages_lists_existing_pages backend/tests/test_api.py::test_automation_page_title_failure_logs_error_type_without_raw_exception backend/tests/test_api.py::test_automation_pages_hide_internal_about_home_from_numeric_refs backend/tests/test_api.py::test_automation_pages_create_new_page -q
# 10 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、clipboard text source order、automation page response shape 或 launch fallback 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 BrowserManager diagnostics/bootstrap debug log redaction guardrail

背景：

- 发布 smoke 的 BrowserManager 诊断路径会读取 Firefox application.ini、summarize invisible_playwright stealth prefs，并在 launch 中执行 existing page init、bootstrap page creation、VNC window fit。
- 旧 debug 日志会输出 raw exception message，可能固化 Firefox binary/application.ini path、profile dir、URL、token 或内部路径。

已覆盖：

- application.ini metadata detection failure 只记录固定 action 和 error_type。
- stealth pref summary failure 只记录固定 action 和 error_type。
- window fit failure 只记录固定 action、display、error_type。
- existing page init 与 bootstrap page creation failure 只记录固定 action、profile_id、error_type。
- 这些路径仍保持 best-effort：诊断失败回落低敏 fallback，init/bootstrap/window fit 失败不阻断 profile launch。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_identity_metadata_debug_logs_error_type_without_raw_exception backend/tests/test_browser_manager.py::test_stealth_pref_summary_debug_logs_error_type_without_raw_exception backend/tests/test_browser_manager.py::test_fit_firefox_window_debug_log_uses_error_type_without_raw_exception backend/tests/test_browser_manager.py::test_launch_debug_logs_init_and_bootstrap_error_types_without_raw_exception -q
# RED then GREEN; final focused tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 68 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储或 launch fallback 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 GeoIP/proxy lookup log redaction guardrail

背景：

- GeoIP lookup 支撑 release smoke 的 no-proxy/proxy-country 证据面；日志需要能排查 provider 和配置问题，但不能固化 proxy、token、URL/query 或 provider 返回的原文。
- 旧 GeoIP 日志会输出无效 env 原值、provider failure message/reason、lookup exception text。

已覆盖：

- 无效 GeoIP timeout/cache env 只记录配置名和 fallback 值。
- provider failure 只记录固定 source。
- lookup exception 只记录 provider 名和 exception type。
- GeoIP fallback/provider 顺序、proxy 参数传递、timezone/locale 填充行为保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py::test_geoip_timeout_config_warning_does_not_log_raw_env_value backend/tests/test_geoip.py::test_geoip_provider_failure_warning_does_not_log_raw_response_message backend/tests/test_geoip.py::test_resolve_network_geo_warning_does_not_log_raw_lookup_exception -q
# RED then GREEN; final focused tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py -q
# 14 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸或 profile 存储行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 VNC proxy failure log redaction guardrail

背景：

- 发布 smoke 会覆盖 regular VNC viewer 与 runtime viewer session；两者共享 `_proxy_running_vnc()`。
- 旧 VNC proxy failure 日志会输出 raw exception message，可能固化 viewer URL/token、backend URL、端口或内部路径。

已覆盖：

- backend connect failure 只记录固定 action、profile_id、error_type。
- client→backend、backend→client、websocket close failure 只记录固定 action、profile_id、error_type 和低敏 message count。
- runtime viewer backend failure audit 仍保持 redacted reason_code。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_error_type_without_raw_exception -q
# RED then GREEN; final focused test passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_ws_rejects_cross_origin backend/tests/test_api.py::test_ws_allows_same_origin backend/tests/test_api.py::test_ws_allows_no_origin backend/tests/test_api.py::test_vnc_proxy_connects_websockify_path backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_error_type_without_raw_exception -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_vnc_backend_connect_failure_writes_redacted_failure_audit backend/tests/test_session_broker.py::test_runtime_vnc_accepts_valid_viewer_token_and_proxies_to_profile_vnc backend/tests/test_session_broker.py::test_runtime_vnc_success_writes_redacted_connect_and_disconnect_audit -q
# 3 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸、viewer token issuance 或 profile 存储行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 BrowserManager lifecycle log redaction guardrail

背景：

- 发布 smoke 和生产 triage 依赖 runtime/profile lifecycle 日志，但日志不能固化 profile 自由文本、exception message、profile dir、proxy 或 token。
- stop/teardown/auto-launch 是 release runtime 收敛路径的一部分；旧日志在这些边界会输出 raw exception text，auto-launch 还会输出 profile name。

已覆盖：

- stop runner/context close failure、launch teardown failure、browser closed teardown failure 统一记录固定 action、profile_id、error_type。
- auto-launch 成功/失败日志不再记录 profile name；失败日志不再记录 raw exception message。
- 原有 launch succeeded/failed、stop requested/finished、browser closed 低敏 action 日志语义保持。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_stop_logs_fixed_error_type_without_runner_exception_text backend/tests/test_browser_manager.py::test_stop_logs_fixed_error_type_without_context_exception_text backend/tests/test_browser_manager.py::test_auto_launch_all_logs_profile_ids_and_error_types_without_sensitive_text -q
# RED then GREEN; final focused tests passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 64 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充、VNC 尺寸或 profile 存储行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 VNC/window display dimension launch guardrail

背景：

- 发布 smoke 依赖 VNC 可见工作区稳定；profile screen 值既会影响 fingerprint pin，也会影响 VNC start/window fit。
- 上一轮已清洗 fingerprint pin，但 VNC/window 生命周期仍直接使用原始 `screen_width` / `screen_height`。

已覆盖：

- 非公开或污染 screen 值不再传入 KasmVNC start。
- Firefox window fit 使用同一组安全 display dimensions，避免 `int()` 解析污染文本导致 launch 失败。
- 正常 screen 值仍按 profile 使用；无效值回落到 `1920x1080`。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_uses_safe_display_dimensions_for_non_public_screen_values -q
# RED then GREEN; final focused test passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 61 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy、GeoIP 填充或 profile 存储行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Proxy/launch API error detail redaction guardrail

背景：

- Proxy Manager create/update、profile 当前 proxy 保存为资产、profile launch、runtime session create 都可能在 release smoke 和 proxy-country triage 中返回 4xx 错误。
- 旧实现会把底层 `ValueError` 原文放进 HTTP detail；异常文本可能包含 proxy URL、host、credentials、token、profile/runtime 上下文或内部路径。

已覆盖：

- Proxy asset create/update/storage failure 的 HTTP detail 只暴露固定低敏 proxy 错误类别。
- Profile proxy asset 保存失败的 HTTP detail 只暴露固定低敏 proxy 错误类别。
- Profile launch 与 runtime session create 的 proxy validation failure 只暴露固定低敏 proxy 错误类别。
- 正常 proxy CRUD、profile proxy asset 保存、runtime session create 和 profile launch 错误映射保持原有状态码语义。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "redacts_sensitive_storage_error_detail"
# RED then GREEN；最终 3 passed, 25 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q
# 28 passed

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_invalid_proxy_400 backend/tests/test_api.py::test_launch_invalid_proxy_real_validation_400 backend/tests/test_session_broker.py::test_runtime_session_create_redacts_sensitive_launch_value_error_detail -q
# RED then GREEN；最终 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py -q -k "runtime_session_create or launch"
# 21 passed, 223 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 546 passed in 33.12s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.78s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy normalization、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、runtime session persistence 或 launch fallback 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 CSV profile import template reference redaction guardrail

背景：

- CSV profile import preview/import 会返回行级 errors 和 source，用于批量导入前审阅与导入结果展示。
- 旧缺失模板错误会把原始 template 引用拼进响应；若用户上传 URL、credential、token 或 path 样式模板值，响应会固化这些文本。

已覆盖：

- 缺失模板错误固定为 `Template not found`。
- URL/userinfo/query/fragment/path/token/secret/password/cookie/authorization 样式 `source.template` 返回 `[redacted]`。
- 普通模板名/ID 成功匹配、模板字段复制、显式覆盖、CSV import preview/import 成功路径、bulk audit 和行级错误结构保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q -k "csv_import"
# RED then GREEN；最终 10 passed, 5 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 15 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_api.py -q -k "profile_config or profile_bundle or csv_import or import_profile_configs or import_profile_bundle"
# 37 passed, 193 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 548 passed in 32.28s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.66s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy normalization、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、profile config import、profile bundle import 或 CSV parser 支持字段。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 CSV profile import source/header redaction guardrail

背景：

- CSV profile import preview/import 的 row `source` 和 errors 会进入管理台响应，用于用户检查批量导入问题。
- 旧实现会复制整行 source，并在 unsupported column error 中拼接原始 header；上传内容中的 token、URL、credential、authorization 或 path 样式文本可能被响应固化。

已覆盖：

- Unsupported column error 固定为 `Unsupported column`。
- Unsupported/extra CSV columns 不再作为原始 key/value 出现在 `source`；只返回低敏 `unsupported_column_count`。
- 支持字段的 source value 若像 URL、userinfo、query、fragment、path、token、secret、password、cookie、authorization 或 bearer，则返回 `[redacted]`。
- 普通 CSV import preview/import、proxy redaction、template lookup、profile config import、profile bundle import 相关测试保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_profile_csv_import_preview_redacts_sensitive_source_fields_and_headers backend/tests/test_bulk.py::test_profile_csv_import_redacts_sensitive_source_fields_and_headers -q
# RED then GREEN；最终 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q -k "csv_import"
# 12 passed, 5 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 17 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_api.py -q -k "profile_config or profile_bundle or csv_import or import_profile_configs or import_profile_bundle"
# 39 passed, 193 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 550 passed in 33.26s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.90s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy normalization、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、profile config import、profile bundle import 或 CSV 支持字段。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Launch resource-limit API detail redaction guardrail

背景：

- Profile launch 与 runtime session create 都会向调用方返回 resource-limit 409。
- 旧实现直接返回 `BrowserResourceLimitError` 原文；异常文本如果带入 proxy URL、credential、token 或 profile/runtime 上下文，会进入 API 响应。

已覆盖：

- Profile launch resource-limit 409 detail 固定为 `Maximum running profiles reached`。
- Runtime session create resource-limit 409 detail 固定为 `Maximum running profiles reached`。
- 现有 max running profile、profile launch、runtime session create、proxy validation 和状态码语义保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_resource_limit_detail_does_not_echo_exception_text backend/tests/test_session_broker.py::test_runtime_session_create_resource_limit_detail_does_not_echo_exception_text -q
# RED then GREEN；最终 2 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py -q -k "runtime_session_create or launch"
# 23 passed, 223 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 552 passed in 33.79s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.89s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 resource limit 判断、stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、proxy normalization、GeoIP 填充、VNC 尺寸、viewer token issuance、profile 存储、runtime session persistence 或 launch fallback 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Proxy check API/DB error redaction guardrail

背景：

- Proxy check failure 是 release smoke 中会被 API response 和 persisted `last_check_error` 反复读取的错误面。
- 旧实现把 exception text 做局部替换后返回；provider URL、query token、Authorization/Bearer、provider host 或 redacted proxy host 仍可能出现在单个 check 与 bulk check 结果里。

已覆盖：

- `/api/proxies/{proxy_id}/check` 失败时 `last_check_error` 固定为 `Proxy check failed`。
- `/api/proxies/bulk/check` 失败 result 的 `error` 与嵌套 proxy `last_check_error` 固定为 `Proxy check failed`。
- 成功 check、bulk partial result、missing proxy、stored proxy URL redaction 和 audit 语义保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "generic_failure_without_leaking_provider_details"
# RED then GREEN；初始 2 failed，最终相关用例通过

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "proxy_check"
# 3 passed, 27 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q
# 30 passed in 2.96s

. .venv/bin/activate && python -m pytest backend/tests -q
# 554 passed in 33.75s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.28s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 proxy storage URL、proxy validation、GeoIP lookup behavior、stealth prefs、seed、WebGL、WebRTC、UA、locale、timezone、VNC、viewer token、profile 存储或 runtime session 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 GeoIP source public-value guardrail

背景：

- GeoIP success source 会出现在 proxy check、profile health、persisted health cache 和 health audit metadata 中。
- 真实 provider 当前返回固定 label，但成功路径没有防御 future provider/test double/historical DB source 中的 URL、query token、Authorization/Bearer 或 host/path 文本。

已覆盖：

- `public_geoip_source` 只保留短公开 label，非公开 source 折叠为 `unknown`。
- Proxy check 成功 response/DB 的 `last_check_source` 已过滤。
- Profile health check 新写入、GET health 读取历史 cache、health audit metadata 的 `geoip_source` 已过滤。
- GeoIP fallback、proxy check success、health warning/audit、manual override mismatch 行为保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_check_redacts_sensitive_success_source backend/tests/test_health.py::test_health_check_redacts_sensitive_geoip_source backend/tests/test_health.py::test_health_get_redacts_persisted_sensitive_geoip_source -q
# RED then GREEN；初始 3 failed，最终 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py backend/tests/test_health.py backend/tests/test_proxies.py -q
# 65 passed in 4.66s

. .venv/bin/activate && python -m pytest backend/tests -q
# 557 passed in 33.19s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.87s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 GeoIP provider order、lookup URL、proxy normalization、IP/country/timezone/locale parsing、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、profile 存储 schema 或 runtime session 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Health proxy warning detail redaction guardrail

背景：

- Profile health `proxy_invalid` warning message 会进入 API response 和前端 summary/table。
- 旧实现直接使用 `_validate_proxy()` 的 exception text；missing port / invalid port 等错误会保留 redacted proxy host，仍可能暴露 proxy asset 信息。

已覆盖：

- Health proxy warning detail 固定为低敏分类，不再包含 scheme raw detail、proxy host、userinfo、password 或 raw URL。
- `compute_profile_health()` 和 `/api/profiles/{profile_id}/health/check` invalid proxy 路径均覆盖。
- Health status、warning code、lookup skip、audit metadata 和前端 message rendering 语义保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_invalid_proxy_returns_error backend/tests/test_health.py::test_health_invalid_proxy_warning_uses_low_sensitive_detail backend/tests/test_health.py::test_health_check_invalid_proxy_warning_does_not_echo_proxy_host -q
# RED then GREEN；初始 3 failed，最终 3 passed

. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q
# 21 passed in 1.81s

npm --prefix frontend test -- --run ProfileSummaryPanel ProfileTable
# Test Files 2 passed；Tests 39 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 558 passed in 32.65s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.36s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 proxy validation semantics、profile proxy 存储、GeoIP lookup、health status/warning code、audit event shape、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token 或 runtime session 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Health manual mismatch warning redaction guardrail

背景：

- Profile health manual timezone/locale mismatch warning 是 release smoke 中会出现在 API/UI 的健康提示。
- 旧文案直接回显手动 timezone/locale 和 GeoIP 建议值；用户输入、CSV/import 或历史 DB 值若包含 URL/token/header 样式文本，会被 warning message 暴露。

已覆盖：

- Manual timezone mismatch warning 使用固定低敏文案。
- Manual locale mismatch warning 使用固定低敏文案。
- mismatch 判断、manual override flags、GeoIP values、warning code/severity/action、audit metadata 和前端 rendering 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_manual_mismatch_warning_does_not_echo_manual_values -q
# RED then GREEN；初始 1 failed，最终 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q
# 22 passed in 1.74s

npm --prefix frontend test -- --run HealthBadge ProfileList
# Test Files 2 passed；Tests 16 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 559 passed in 33.22s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.21s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 profile timezone/locale 存储、GeoIP timezone/locale parsing、mismatch detection、health status/warning code、audit event shape、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token 或 runtime session 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Audit metadata string redaction guardrail

背景：

- Audit metadata 是 release smoke 后长期保留的可观测性数据。
- 旧 sanitizer 会删除敏感 key 和清理 URL userinfo，但不会处理普通 string value 中的 standalone `token=...` 或 `Authorization=Bearer ...`。

已覆盖：

- 普通 audit metadata string value 中的 authorization/bearer/token/password/secret/cookie/service token assignments 会被 redacted。
- Nested metadata、sensitive key removal、proxy URL redaction 和安全字符串保留行为保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields -q
# RED then GREEN；初始 1 failed，最终 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py backend/tests/test_proxies.py backend/tests/test_bulk.py backend/tests/test_health.py -q
# 316 passed in 25.76s

. .venv/bin/activate && python -m pytest backend/tests -q
# 559 passed in 32.99s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.05s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 audit event schema、event types、actor/profile/session ids、runtime viewer flow、automation task semantics、profile/proxy CRUD behavior、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token 或 runtime session 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Proxy provider preset audit observability guardrail

背景：

- Proxy provider presets 是 proxy release workflow 的配置面，但 create/update/delete 缺少 audit trail。
- Preset 字段是自由文本，审计必须避免记录 provider host、token、Authorization/Bearer 或 tag/name/notes 内容。

已覆盖：

- Provider preset CRUD 成功路径写入低敏 audit events。
- Metadata 仅记录 `preset_id`、`tag_count` 和 update 的 `updated_fields`。
- Provider preset CRUD、random assign、CSV import preset 使用和前端 proxy manager 行为保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py::test_proxy_provider_preset_crud_writes_low_sensitive_audit_events -q
# RED then GREEN；初始 1 failed，最终 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py backend/tests/test_proxies.py -q
# 40 passed in 3.64s

npm --prefix frontend test -- --run ProxyManagerPage api
# Test Files 2 passed；Tests 61 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 560 passed in 33.39s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.91s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 provider preset storage/response fields、random assign selection semantics、CSV import preset application、profile/proxy CRUD behavior、audit event schema、stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token 或 runtime session 行为。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 GeoIP success field public-value guardrail

背景：

- `cbim-23h.6` 下一阶段继续收敛 release smoke / proxy-country triage / health diagnostics 中的低敏证据边界。
- GeoIP success `country_code`、`timezone`、`locale` 原本在部分路径直接信任 provider/test double/历史 DB 值；这些字段如果携带 URL、query token、Authorization/Bearer 或 provider host/path 文本，会进入 proxy check response/DB、profile health response/DB 和 health audit metadata。

已覆盖：

- GeoIP country/timezone/locale 成功字段新增 public-value filter；合法值保留，非公开值降为 `None`。
- 覆盖 `GeoIPResult.as_dict()`、provider parser、profile launch GeoIP 填充、proxy check success write/read path、health check success write/read path、persisted health cache response 和 health audit metadata。
- 既有低敏 `source` 过滤、proxy check failure 固定错误、health warning redaction、audit metadata string redaction 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py backend/tests/test_health.py backend/tests/test_proxies.py -q
# RED then GREEN；初始 4 failed，最终 71 passed in 4.54s

. .venv/bin/activate && python -m pytest backend/tests -q
# 564 passed in 32.87s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.13s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、proxy lookup order、provider URLs、profile schema 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 GeoIP success IP public-value guardrail

背景：

- 上一轮收敛了 GeoIP `country_code`、`timezone`、`locale` success fields；复查发现 `ip` 仍在 `GeoIPResult.as_dict()`、proxy check success、profile health/cache 和 profile launch GeoIP 填充边界直接信任 `GeoIPResult` 或历史 DB 值。
- 如果 future provider/test double/historical DB 把 URL、query token、Authorization/Bearer 或 provider host/path 文本写入 `ip`，release smoke / proxy-country triage / health response 会形成低敏边界缺口。

已覆盖：

- GeoIP `ip` 成功字段新增 public-value filter；只有 `ipaddress` 可解析的值会保留，非公开值降为 `None`。
- 覆盖 `GeoIPResult.as_dict()`、provider parser、proxy check success write/read path、health check success write/read path、persisted health cache response 和 profile launch GeoIP fill boundary。
- 既有 country/timezone/locale/source 过滤、proxy check failure 固定错误、health warning redaction、audit metadata string redaction 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_geoip.py backend/tests/test_health.py backend/tests/test_proxies.py -q
# RED then GREEN；初始 4 failed，最终 71 passed in 4.60s

. .venv/bin/activate && python -m pytest backend/tests -q
# 564 passed in 32.38s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.16s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、proxy lookup order、provider URLs、profile schema 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 CSV import proxy error detail redaction guardrail

背景：

- Release CSV import smoke 已覆盖 source/header/template redaction；继续复查发现 invalid proxy row `errors` 仍使用底层 proxy validation message。
- 该 message 会隐藏 credentials，但仍可能包含 redacted proxy host，例如 `Proxy URL missing port: http://csv-proxy.example`，会在 preview/import responses 中被客户端看到。

已覆盖：

- `/api/profiles/import/preview` 与 `/api/profiles/import` 的 invalid proxy row errors 现在只返回固定低敏 proxy error category。
- CSV `source.proxy` redacted URL、valid rows、explicit confirmation、bulk audit 和 profile creation 语义保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_profile_csv_import_preview_redacts_sensitive_proxy_error_detail backend/tests/test_bulk.py::test_profile_csv_import_redacts_sensitive_proxy_error_detail -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.64s

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 19 passed in 1.70s

. .venv/bin/activate && python -m pytest backend/tests -q
# 566 passed in 31.98s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.14s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、proxy storage URL semantics、CSV supported columns、profile schema 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation pages summary redaction guardrail

背景：

- Release automation/VNC smoke 会读取 `/api/profiles/{profile_id}/automation/pages` 来展示可操作页面。
- Console/network summary 已使用 safe URL/text redaction；pages summary 仍直接回显 raw `page.url` 和 title，一旦页面 URL 或标题带 query token、userinfo、Authorization/Bearer 或 token-like 文本，会进入 runtime response/UI。

已覆盖：

- Automation pages summary URL 现在保留 scheme/host/port/path，移除 userinfo、params、query 和 fragment。
- Page title 复用 automation text redaction，隐藏 token assignments、Bearer token 和 URL query/fragment。
- `about:*` pages、page ids、page index、goto 和其他 automation page action behavior 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_pages_redacts_sensitive_url_and_title -q
# RED then GREEN；初始 1 failed，最终 1 passed in 1.47s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_pages or automation_console_logs or automation_network_summary or automation_goto"
# 11 passed, 206 deselected in 2.63s

. .venv/bin/activate && python -m pytest backend/tests -q
# 567 passed in 32.77s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.12s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、automation page actions、navigation target URL、console/network capture internals 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation text header credential redaction guardrail

背景：

- 继续复查 release automation/VNC response surfaces 时，发现 automation page title 与 console log text 的共享脱敏 helper 对 header-style credentials 覆盖不足。
- 现有 URL/token/Bearer redaction 不足以处理 `Authorization=Bearer ...`、`Authorization: Basic ...` 和 `Cookie: sid=...`，这些文本可来自页面 title 或 console message。

已覆盖：

- Automation text redaction 现在将 Authorization header-style credentials 固定为 `Authorization=[redacted]`。
- Cookie 与 Set-Cookie header-style credentials 固定为 `Cookie=[redacted]` / `Set-Cookie=[redacted]`。
- 既有 URL userinfo/query/fragment redaction、token assignment redaction、console location URL redaction、network summary 和 page action behavior 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'automation_pages_redacts_sensitive_url_and_title or automation_console_logs_redacts_sensitive_text_and_location_urls'
# RED then GREEN；初始 2 failed，最终 2 passed in 0.76s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'automation_pages or automation_console_logs or automation_network_summary or automation_goto or automation_page_id'
# 12 passed, 205 deselected in 1.65s

. .venv/bin/activate && python -m pytest backend/tests -q
# 567 passed in 33.33s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.97s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC、viewer token、runtime session 行为、automation navigation target URL、console/network capture internals 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 VNC proxy Xvnc log dump redaction guardrail

背景：

- Release VNC/runtime viewer smoke 会走 `_proxy_running_vnc()`，该路径在 disconnect 后仍会 dump `/tmp/xvnc-{display}.log` raw lines。
- Xvnc log 来自外部进程，不适合进入 manager logs；其中可能包含 backend URL、viewer token、Authorization/Bearer、profile path 或内部路径文本。

已覆盖：

- VNC proxy disconnect 只记录固定低敏 `action=vnc.xvnc_log_available` 事件和 display/profile_id。
- 不再读取或输出 raw Xvnc log line。
- 普通 VNC proxy、runtime viewer VNC proxy、connect/disconnect audit、backend failure audit、RFB filter、clipboard bridge 和 subprotocol behavior 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_proxy_disconnect_does_not_dump_raw_xvnc_log -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.86s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'vnc_proxy or vnc_ws or ws_allows'
# 6 passed, 212 deselected in 1.21s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q -k 'runtime_vnc'
# 7 passed, 23 deselected in 1.59s

. .venv/bin/activate && python -m pytest backend/tests -q
# 568 passed in 32.37s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.12s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC viewer token validation、runtime session state machine、RFB filtering 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 WebSocket origin log redaction guardrail

背景：

- 普通 VNC 和 runtime viewer VNC 都经过 `_check_websocket_origin()` 做 Origin/Host 校验。
- 该边界会处理外部 client headers；此前 rejection warning 会输出 raw Origin/Host。恶意 header 可带 query token、path、fragment 或 token-like 文本。

已覆盖：

- Origin rejection logs 只输出低敏 host label，不输出 raw header。
- Cross-origin rejection、same-origin/no-origin allow、runtime viewer `origin_not_allowed` audit 和 VNC proxy behavior 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_vnc_ws_origin_rejection_logs_low_sensitive_origin -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.71s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'vnc_ws or ws_allows or vnc_proxy'
# 7 passed, 212 deselected in 1.13s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_vnc_rejects_cross_origin_even_with_valid_viewer_token -q
# 1 passed in 0.71s

. .venv/bin/activate && python -m pytest backend/tests -q
# 569 passed in 33.95s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.20s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC viewer token validation、runtime session state machine、RFB filtering、proxy logic 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation network summary method/resource redaction guardrail

背景：

- Automation network summary 是 release automation/VNC smoke 的常用可观测面。
- URL 已低敏化，但 `method` 与 `resource_type` 仍直接回显 request object 字段，异常或恶意值可能包含 token/header-like 文本。

已覆盖：

- Network summary `method` 只保留公开 HTTP method whitelist，其他值折叠为 `UNKNOWN`。
- Network summary `resource_type` 只保留 Playwright 公开 resource type whitelist，其他值折叠为 `unknown`。
- URL redaction、event type、status、failure reason、ring buffer、console capture 和 page action behavior 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_network_summary_redacts_urls_and_returns_recent_events -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.75s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'automation_pages or automation_console_logs or automation_network_summary or automation_page_id'
# 10 passed, 209 deselected in 1.43s

. .venv/bin/activate && python -m pytest backend/tests -q
# 569 passed in 33.36s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 6.38s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC/runtime viewer、proxy logic、automation navigation target URL、actual browser request method/resource type、console capture internals 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation cached summary output redaction guardrail

背景：

- Automation console/network summary endpoints 是 release smoke 常用观察面。
- Capture helper 已做低敏化，但 endpoints 仍直接返回当前 in-memory lists；历史 raw entries 或污染 entries 可能绕过捕获时 redaction，network summary 还可能因为 raw status text 触发 response validation error。

已覆盖：

- Console logs endpoint 现在输出前归一化 existing entries：console type whitelist、text redaction、safe location URL、numeric-only line/column。
- Network summary endpoint 现在输出前归一化 existing entries：event/method/resource/failure whitelists、safe status、safe URL。
- 正常 capture path 继续复用同一套 helper；ring buffer、page actions、actual browser behavior 和 audit schema 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_console_logs_redacts_existing_in_memory_entries backend/tests/test_api.py::test_automation_network_summary_redacts_existing_in_memory_events -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.79s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k 'automation_pages or automation_console_logs or automation_network_summary or automation_page_id'
# 12 passed, 209 deselected in 1.62s

. .venv/bin/activate && python -m pytest backend/tests -q
# 571 passed in 34.10s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.33s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC/runtime viewer、proxy logic、automation navigation target URL、actual browser request/console behavior、browser-side capture event subscription 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation task status/error response redaction guardrail

背景：

- Release automation/VNC smoke 会通过 task API 查看 queued/running/finished automation tasks。
- 之前已清洗 task `steps`、`page_ref`、result summary 和 cached console/network summaries。
- 继续复查发现 task response 仍信任 DB 中的 `status` 和 `error` 字段；历史/损坏 row 可把 URL/query token、Authorization/Bearer 或 Cookie 文本回显到 `GET /api/tasks/{task_id}` 和 `GET /api/tasks`。

已覆盖：

- Task response `status` 只保留公开状态 `queued`、`running`、`cancel_requested`、`cancelled`、`failed`、`succeeded`；其他值折叠为 `unknown`。
- Task response `error` 只保留当前执行路径写入的固定低敏错误；其他值折叠为 `Automation task failed`。
- Automation task audit metadata 的 `status` / `previous_status` 同步使用 public status allowlist。
- 正常 create/run/cancel/retry、worker lease、result summary、step redaction 和 audit event schema 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_response_sanitizes_persisted_status_and_error_fields -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.76s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_task or list_automation_tasks or get_automation_task or retry_automation_task or run_automation_worker"
# 38 passed, 184 deselected in 4.66s

. .venv/bin/activate && python -m pytest backend/tests -q
# 572 passed in 32.80s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.95s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、VNC/runtime viewer、proxy logic、automation task execution、worker lease、browser page actions 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile GeoIP response redaction guardrail

背景：

- Release smoke 会反复读取 profile list/detail 来确认 launch、GeoIP、health 和 proxy-country 行为。
- GeoIP result/health/proxy 成功路径已经过滤 provider/test double 的非公开值；继续复查发现 profile response 仍会直接回显历史 DB 中的 `last_geoip_*` 字段。
- 旧版本或损坏 row 中的 URL/query token、Authorization/Bearer、provider host/path 风格 GeoIP 文本可能进入 `/api/profiles` 和 `/api/profiles/{profile_id}`。

已覆盖：

- Profile API 输出新增统一 `_profile_response()` helper。
- `last_geoip_ip`、`last_geoip_country_code`、`last_geoip_timezone`、`last_geoip_locale`、`last_geoip_source` 输出前走 `public_geoip_*` 规则。
- 非公开 source 折叠为 `unknown`，非公开 IP/country/timezone/locale 折叠为 `null`。
- create/list/get/update、CSV import、config import、bundle import 中的 successful profile response 均使用同一 helper。
- 正常 GeoIP success values、health response、profile tags、runtime status、VNC port、automation URL 和 audit metadata 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_redact_persisted_sensitive_geoip_fields -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.72s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile and (geoip or get_profile or list_profiles or create_profile or update_profile or import_profile_configs or import_profile_bundle or launch_persists_resolved_geoip)"
# 19 passed, 204 deselected in 1.83s

. .venv/bin/activate && python -m pytest backend/tests/test_health.py backend/tests/test_geoip.py backend/tests/test_proxies.py -q -k "geoip or health_check or profile_health or proxy_check"
# 38 passed, 33 deselected in 2.23s

. .venv/bin/activate && python -m pytest backend/tests -q
# 573 passed in 31.93s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.95s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、GeoIP provider order、proxy lookup behavior、profile launch behavior、VNC/runtime viewer 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Proxy last-check response redaction guardrail

背景：

- Release smoke 和 Proxy Manager UI 会反复读取 proxy list/detail 来确认 check、bulk check 和分配状态。
- Proxy check success/failure 新写入路径已经低敏化，但 proxy response 仍会信任 DB 中的历史 `last_check_*` 字段。
- 旧版本、手工修复或损坏 row 中的 URL/path marker、Bearer-like 文本或非公开 GeoIP 字段可能进入 `/api/proxies` 与 `/api/proxies/{proxy_id}`。

已覆盖：

- Proxy API 输出新增 last-check 响应层归一化。
- `last_check_status` 只保留 `good`、`error`；其他非空值折叠为 `unknown`。
- `last_check_ip`、`last_check_country_code`、`last_check_timezone`、`last_check_locale`、`last_check_source` 输出前走 `public_geoip_*` 规则。
- 非公开 source 折叠为 `unknown`，非公开 IP/country/timezone/locale 折叠为 `null`。
- `last_check_error` 只保留固定低敏错误 `Proxy check failed`，其他非空历史错误折叠为同一固定文本。
- 正常 proxy check、bulk check、URL redaction、tags 和 audit metadata 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_api_responses_redact_persisted_sensitive_last_check_fields -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.70s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "proxy_crud or proxy_check or bulk_check or persisted_sensitive_last_check"
# 13 passed, 20 deselected in 1.63s

. .venv/bin/activate && python -m pytest backend/tests -q
# 574 passed in 34.34s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.00s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、GeoIP provider order、proxy lookup behavior、proxy check resolver、profile launch behavior、VNC/runtime viewer 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime session status response redaction guardrail

背景：

- Release runtime/VNC viewer smoke 会通过 runtime service API 创建、读取、续期和终止 session。
- Runtime diagnostics aggregate 已有 status allowlist，但 runtime session response 仍直接返回 DB 中的 raw `status`。
- 历史/损坏 runtime session row 可把非公开 status 文本显示到 `/api/runtime/sessions/{session_id}` response。

已覆盖：

- Runtime session response `status` 只保留 `active`、`terminated`；其他值折叠为 `unknown`。
- 正常 create/get/renew/terminate、viewer token、runtime audit、VNC proxy、lease expiration 和 diagnostics aggregate 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_status -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.69s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 31 passed in 3.48s

. .venv/bin/activate && python -m pytest backend/tests -q
# 575 passed in 35.78s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.05s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、viewer token validation、VNC proxying、profile launch behavior 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile template apply public-value guardrail

背景：

- Release smoke 会使用 profile templates 准备 profile 和 runtime sessions。
- 正常 template API 输入有校验，但旧版本/手工 DB row 可能包含非公开或非类型匹配的 fingerprint/launch fields。
- 之前 template apply 会直接复制这些历史字段到 profile create/import 数据，导致 profile response validation error 或污染 profile lifecycle。

已覆盖：

- Template apply 边界过滤 platform、screen_width、screen_height、gpu_vendor、gpu_renderer、hardware_concurrency、color_scheme、human_preset、humanize、geoip 和 launch_args。
- 非公开 screen/hardware/GPU 值不会覆盖 profile 默认值；非公开 launch args 和 Firefox 冲突 args 会被丢弃。
- 正常 template CRUD、template create profile、CSV import preview/import、profile config import/export 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py::test_create_profile_from_template_sanitizes_persisted_identity_fields -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.64s

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 10 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q -k "template or csv_import or config_import"
# 16 passed, 3 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_config or profile_launch_args or create_profile"
# 11 passed, 212 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 576 passed in 33.90s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.13s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Malformed tag response stability guardrail

背景：

- Release smoke 会反复读取 profile list/detail、proxy manager list/detail、proxy provider presets，并在 random proxy assignment 中返回 proxy summaries。
- 历史/手工 DB row 可能包含 malformed tags；此前 profile/proxy/preset response 直接构造 `TagResponse(**tag)`，缺少 `tag` 或非字符串 `color` 会导致响应 500。

已覆盖：

- Profile response、proxy response、proxy provider preset response 和 profile config export 现在共享 tag response normalizer。
- malformed tag item 会被低风险处理：无字符串 `tag` 的 item 丢弃，非字符串/不可解码 `color` 变为 `null`。
- 正常 profile/proxy/provider preset CRUD、proxy random assignment 和 config export 行为保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_response_sanitizes_persisted_malformed_tags backend/tests/test_proxies.py::test_proxy_response_sanitizes_persisted_malformed_tags backend/tests/test_proxy_provider_presets.py::test_proxy_provider_preset_api_sanitizes_persisted_malformed_tags -q
# RED then GREEN；初始 3 failed，最终 3 passed in 1.76s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "profile_response or create_profile_with_all_fields or tags or export_profiles" -q
# 11 passed, 214 deselected in 1.76s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -k "proxy_crud_api or malformed_tags or random_proxy_assignment or assign_proxy" -q
# 7 passed, 27 deselected in 1.69s

. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py -q
# 10 passed in 1.50s

. .venv/bin/activate && python -m pytest backend/tests -q
# 582 passed in 32.13s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.44s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile config export and bundle export identity guardrail

背景：

- Release smoke 会使用 profile config export/import 与 bundle export/import 做备份、迁移和回归验证。
- Profile/template 响应边界已陆续加固，但 `/api/profiles/export` 与 `/api/profiles/{profile_id}/bundle/export` 仍直接信任 DB profile row 构造 `ProfileConfigExport`。
- 历史/损坏 profile row 中的污染 screen/hardware 字段会导致 export 500；污染 GPU/timezone/locale/enum/launch args 可能进入配置导出或 bundle manifest。

已覆盖：

- Bulk profile config export 与 profile bundle export 现在共享 profile config export sanitizer。
- 非公开 platform、screen_width、screen_height、gpu_vendor、gpu_renderer、hardware_concurrency、timezone、locale、color_scheme、human_preset 和 launch_args 会折叠为安全默认值、`null` 或过滤后的公开参数。
- 正常 profile config export/import、sensitive proxy confirmation、bundle export/import 和 profile bundle helper 行为保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py::test_bulk_export_profile_configs_sanitizes_persisted_identity_fields -q
# RED then GREEN；初始 1 failed，最终与 bundle RED/GREEN 组合 2 passed in 1.25s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_sanitizes_persisted_identity_fields -q
# RED then GREEN；初始 1 failed，最终与 bulk RED/GREEN 组合 2 passed in 1.25s

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -k "export_profile_configs or config_import or round_trip" -q
# 6 passed, 14 deselected in 1.19s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "export_profiles or profile_bundle or config_import" -q
# 23 passed, 201 deselected in 2.30s

. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py -q
# 4 passed in 0.23s

. .venv/bin/activate && python -m pytest backend/tests -q
# 579 passed in 32.27s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.45s

git diff --check
# clean
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile template response redaction guardrail

背景：

- Release smoke 会读取 profile template list/detail 来准备 profile/runtime session。
- Template apply 已过滤污染字段，但 list/detail response 仍直接信任 DB row。
- 历史/损坏 template row 可在 response 构造时触发 validation error，或把非公开 GPU/launch arg 文本暴露到 API/UI。

已覆盖：

- Profile template list/detail response 复用 template public-value 过滤。
- 非公开 screen/hardware/GPU/enum/launch arg 值会折叠为安全默认值或过滤结果。
- 正常 template CRUD、template create profile、CSV import preview/import、profile config import/export 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_identity_fields -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.65s

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 11 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q -k "template or csv_import or config_import"
# 16 passed, 3 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_config or profile_launch_args or create_profile"
# 11 passed, 212 deselected

. .venv/bin/activate && python -m pytest backend/tests -q
# 577 passed in 34.81s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.53s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；没有改变 stealth prefs、seed、WebGL、WebRTC、UA、runtime session state transitions、VNC proxying、profile launch manager 或 audit event schema。
- Pixelscan/IPhey gate 仍未标记完成；`cbim-23h.6` 继续保持 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Proxy selection metadata guardrail

背景：

- Random proxy assignment、proxy-country smoke 和 Proxy Manager UI 都依赖 proxy asset 与 provider preset 的 `provider`/`country_code`。
- 历史/手工 DB 污染值此前可直接进入 proxy/preset list/detail response；provider preset 污染值还会进入 random assignment selection、response 和 audit metadata。

已覆盖：

- Proxy asset 与 provider preset response 现在过滤 persisted provider/country selection fields。
- Random assignment 对 request/preset provider 与 candidate proxy provider 使用同一 public provider filter；country selection 使用 public country normalizer。
- Random assignment audit metadata 不再写入 `None` provider/country，也不写入污染 provider/country 文本。
- 正常 `ProxyJP`/`MobileProxy`/`ProxyCo` 和 `JP`/`US` selection、proxy CRUD、provider preset CRUD、assign/random assign 流程保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_api_responses_redact_persisted_sensitive_selection_fields backend/tests/test_proxy_provider_presets.py::test_proxy_provider_preset_api_redacts_persisted_sensitive_selection_fields backend/tests/test_proxies.py::test_random_proxy_assignment_redacts_persisted_sensitive_preset_selection_metadata -q
# RED then GREEN；初始 3 failed，最终 3 passed in 1.00s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py backend/tests/test_proxy_provider_presets.py -q
# 47 passed in 4.40s

. .venv/bin/activate && python -m pytest backend/tests -q
# 585 passed in 33.87s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.14s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Fingerprint seed response/export guardrail

背景：

- Release profile/config/bundle smoke 会读取 profile list/detail、`/api/profiles/export` 和 bundle config manifest。
- 旧 response/export sanitizer 未过滤 historical/manual `fingerprint_seed`，如果 DB row 被污染为 URL/query token/header 风格文本，会让 `ProfileResponse` 或 `ProfileConfigExport` validation 失败。
- runtime launch seed boundary 已覆盖 `InvisiblePlaywright(seed=...)`，但 release evidence 响应面仍需要同等防御。

已覆盖：

- Profile list/detail response 的污染 `fingerprint_seed` 折叠为固定低敏 `0`。
- Profile config export 和 profile bundle config manifest 使用同一 seed boundary。
- 正常整数 seed 继续保留；底层 launch seed、same-seed stability 和 different-seed variation 语义不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_identity_fields backend/tests/test_bulk.py::test_bulk_export_profile_configs_sanitizes_persisted_identity_fields backend/tests/test_profile_bundle.py::test_build_profile_config_bundle_sanitizes_non_public_fingerprint_seed -q
# RED then GREEN；初始 3 failed，最终 3 passed in 0.95s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_identity_fields backend/tests/test_api.py::test_profile_response_sanitizes_persisted_profile_id_and_automation_url backend/tests/test_bulk.py::test_bulk_export_profile_configs_sanitizes_persisted_identity_fields backend/tests/test_profile_bundle.py -q
# 8 passed in 0.95s

. .venv/bin/activate && python -m pytest backend/tests -q
# 635 passed in 39.14s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.58s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Launch args runtime input guardrail

背景：

- Release profile/runtime smoke 会从 persisted profile 构造 `InvisiblePlaywright(extra_args=...)`。
- 旧 launch arg filter 只屏蔽 remote-debugging、user-agent、profile、window-size 等冲突 flags；其它 URL/query token/header 风格参数仍可进入 runtime 启动输入。
- 为避免损坏 DB row、CSV/config import 或内部 profile dict 把敏感文本送入 Firefox 启动参数和 release evidence，需要在 runtime boundary 固定拒绝。

已覆盖：

- `BrowserManager` 新增 launch arg public boundary，拒绝非字符串、空值、控制字符、URL/query/token/password/secret/cookie/Authorization/Bearer 风格文本。
- `_filter_firefox_launch_args()` 先做 public filtering，再应用既有冲突 flag filtering。
- 非 list `launch_args` 退化为空，普通 `--private-window`、`--lang=en-US` 参数继续保留。
- `_build_invisible_kwargs()` 的 `extra_args` 不再携带污染 launch arg 文本。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_launch_args -q
# RED then GREEN；初始 1 failed，最终 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_launch_args backend/tests/test_browser_manager.py::test_build_invisible_kwargs_filters_chromium_only_launch_args -q
# 2 passed in 0.19s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 74 passed in 0.96s

. .venv/bin/activate && python -m pytest backend/tests -q
# 634 passed in 38.92s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.43s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile directory launch guardrail

背景：

- Release profile/VNC/runtime smoke 会依赖 persisted profile `user_data_dir` 启动 Firefox。
- 旧 launch path 直接信任 profile dict 中的 `user_data_dir`，在 VNC allocation 后用于 cleanup 和 `InvisiblePlaywright(profile_dir=...)`。
- 为防御历史/损坏 DB row 或内部 dict 把 URL/query token/header 风格路径送入 release runtime，需要在启动前固定拒绝。

已覆盖：

- `BrowserManager.launch()` 在 VNC allocation 前验证 profile directory。
- `_build_invisible_kwargs()` 构造 `profile_dir` 时复用同一 public boundary。
- 污染 profile dir 返回固定 `Invalid profile directory`，launch failure summary 记录低敏 stage `validate_profile_dir`。
- 正常 profile dir、VNC allocation、startup-state cleanup、launch kwargs、GeoIP/locale/timezone flow 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_rejects_non_public_user_data_dir_before_vnc_allocation -q
# RED then GREEN；初始 1 failed，最终 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_maps_manager_profile backend/tests/test_browser_manager.py::test_build_invisible_kwargs_omits_empty_optional_values backend/tests/test_browser_manager.py::test_launch_rejects_non_public_user_data_dir_before_vnc_allocation backend/tests/test_browser_manager.py::test_launch_clears_launching_state_when_vnc_allocation_fails backend/tests/test_browser_manager.py::test_launch_resolves_missing_timezone_and_locale_before_invisible_launch -q
# 5 passed in 0.06s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 73 passed in 0.95s

. .venv/bin/activate && python -m pytest backend/tests -q
# 633 passed in 42.95s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 6.59s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 VNC start failure exception guardrail

背景：

- Release Docker/profile/VNC smoke 可能遇到 Xvnc 启动失败。
- 旧 `VNCManager.start_vnc()` 会把 Xvnc log 内容拼进 `RuntimeError`；如果 log 中出现 viewer token、websockify URL/path 或其它 raw runtime text，异常输出会成为敏感 release evidence。

已覆盖：

- Xvnc start failure 仍抛出可定位 display 的固定异常：`Xvnc failed to start on :<display>`。
- raw Xvnc log 内容不再进入 exception message。
- log read failure 继续只记录 `action=vnc.start_log_read_failed` 和 `error_type`。
- VNC allocation、start request 低敏日志、cleanup_stale 和全量后端/前端门禁保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py::test_start_vnc_failure_exception_omits_raw_xvnc_log -q
# RED then GREEN；初始 1 failed，最终 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_vnc_manager.py -q
# 16 passed in 0.05s

. .venv/bin/activate && python -m pytest backend/tests -q
# 632 passed in 39.66s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.79s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 GeoIP WebRTC env IP guardrail

背景：

- Release smoke 会验证 WebRTC 不泄漏 local IP，并尽量让 WebRTC public IP 与 GeoIP exit IP 对齐。
- BrowserManager launch path 会用 `_geoip_result["ip"]` 临时设置 `STEALTHFOX_WEBRTC_PUBLIC_IP`。
- 该字段正常来自 GeoIP provider 的 public IP，但 release hardening 需要防御历史/损坏 profile dict 或异常 resolver 把 URL/query token 风格文本传入 launch env。

已覆盖：

- `_geoip_exit_ip()` 现在只返回 `public_geoip_ip()` 认可的 IP 字符串。
- 正常 GeoIP exit IP 仍会传入 `InvisiblePlaywright.__aenter__()` 期间的 env。
- 非 public IP 文本折叠为 `None`，不会覆盖 launch env。
- launch 后环境恢复、GeoIP timezone/locale fill、Accept-Language 和 WebRTC suppression prefs 保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_drops_non_public_geoip_exit_ip_for_webrtc_env -q
# RED then GREEN；初始 1 failed，最终 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_passes_geoip_exit_ip_to_invisible_webrtc_env backend/tests/test_browser_manager.py::test_launch_drops_non_public_geoip_exit_ip_for_webrtc_env backend/tests/test_browser_manager.py::test_launch_resolves_missing_timezone_and_locale_before_invisible_launch -q
# 3 passed in 0.06s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 72 passed in 0.92s

. .venv/bin/activate && python -m pytest backend/tests -q
# 631 passed in 40.83s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.71s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Fingerprint seed launch guardrail

背景：

- Release smoke 的 same-seed stability / different-seed variation 依赖 `fingerprint_seed` 作为底层 fingerprint generation 输入。
- `fingerprint_seed` 正常来自 API/Pydantic 整数，但 release blocker 排查期间仍需要防御历史/损坏 profile row 或内部 dict 把 URL/query token/header 风格文本送入 `InvisiblePlaywright(seed=...)`。

已覆盖：

- `_build_invisible_kwargs()` 现在只把 public int seed 传给 `InvisiblePlaywright`。
- 非整数、bool、URL/query token 风格 seed 折叠为 `None`，不会进入底层 launch kwargs。
- 正常整数 seed、locale/timezone、managed Firefox identity prefs、WebRTC local IP suppression prefs 和 launch args 过滤语义保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_fingerprint_seed_values -q
# RED then GREEN；初始 1 failed，最终 1 passed

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_build_invisible_kwargs_maps_manager_profile backend/tests/test_browser_manager.py::test_build_invisible_kwargs_omits_empty_optional_values backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_fingerprint_seed_values backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_locale_text backend/tests/test_browser_manager.py::test_build_invisible_kwargs_drops_non_public_timezone_text backend/tests/test_browser_manager.py::test_build_invisible_kwargs_pins_managed_firefox_identity -q
# 6 passed in 0.05s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 71 passed in 0.88s

. .venv/bin/activate && python -m pytest backend/tests -q
# 630 passed in 40.55s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.70s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Firefox identity major-version diagnostics guardrail

背景：

- Pixelscan no-proxy gate 当前仍卡在 `PXLSCN-FINGERPRINT-MASKING`。
- 已知低敏 identity summary 中，Manager managed UA version 与 bundled Firefox application.ini version 是排查重点之一。
- Release evidence 需要直接显示 major version 是否一致，避免每次进入容器读取 application.ini 或保存 full UA/path 类敏感证据。

已覆盖：

- `/api/diagnostics` runtime 现在返回 `firefox_identity_major_version_match`。
- System diagnostics 页面显示 `Firefox major match: match|mismatch|unknown`。
- 该字段只来自公开数字 major version 比较，不暴露 full UA、binary path、profile path、package path 或外站页面内容。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_system_diagnostics_returns_low_sensitive_snapshot backend/tests/test_api.py::test_system_diagnostics_uses_count_queries_without_loading_sensitive_rows -q
# 2 passed in 0.86s

npm --prefix frontend test -- --run src/components/SystemDiagnosticsPage.test.tsx src/lib/api.test.ts
# Test Files 2 passed；Tests 42 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 629 passed in 39.55s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.59s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 VNC/clipboard profile-id release-evidence guardrail

背景：

- Release smoke 和 runtime viewer 排障会读取 VNC proxy、Xvnc availability 和 clipboard relay 日志。
- 这些日志此前仍信任 path profile id；如果 profile id 被历史/手工数据污染成 URL/query/header/token 风格文本，release evidence 会保留该文本。

已覆盖：

- clipboard page/context failure、VNC connect failure、client/backend stream failure、Xvnc log available、websocket close failure、VNC connected/finished 日志均改为公开 profile id。
- 正常 UUID profile id 保持可追踪；非 UUID 或 token/header 风格 profile id 统一记录为 `unknown`。
- 不改变 VNC WebSocket proxy、clipboard sync、runtime viewer audit 或 running profile lookup 语义。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_get_clipboard_page_failure_logs_public_profile_id backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_public_profile_id -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.80s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "vnc or clipboard"
# 16 passed, 226 deselected in 1.68s

. .venv/bin/activate && python -m pytest backend/tests -q
# 624 passed in 39.45s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.23s
```

边界：

- 这是 VNC/clipboard release evidence hardening，不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation page/action profile-id release-evidence guardrail

背景：

- Release smoke 会频繁调用 Automation pages、goto、evaluate、screenshot 和其他 page action。
- 这些 failure logs 此前已隐藏异常原文，但仍信任 path/running profile id；污染 profile id 会进入 automation release evidence。

已覆盖：

- `automation.page_title_failed` 日志现在使用公开 profile id。
- automation page action failure helper 统一使用公开 profile id，覆盖 `new_page`、`goto`、`evaluate`、`wait_for_selector`、`click`、`fill`、`keyboard_type`、`scroll`、`screenshot` 和 `close_page`。
- 正常 UUID profile id 仍可追踪；非 UUID 或 token/header 风格 profile id 统一记录为 `unknown`。
- 不改变 Automation API response、page lookup、page action 执行或固定错误响应语义。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_page_title_failure_logs_public_profile_id backend/tests/test_api.py::test_automation_action_failure_logs_public_profile_id -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.78s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation and not task"
# 46 passed, 198 deselected in 4.03s

. .venv/bin/activate && python -m pytest backend/tests -q
# 626 passed in 37.92s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.18s
```

边界：

- 这是 Automation release evidence hardening，不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Cookie/profile bundle profile-id release-evidence guardrail

背景：

- Release smoke 会覆盖 cookie import/export、profile bundle export、local storage export 等数据边界。
- 这些 API 的 response/audit 已经过滤 profile id，但 failure logs 仍可能把污染的 path profile id 写入 release evidence。

已覆盖：

- Cookie JSON import validation/add failure logs 使用公开 profile id。
- Netscape cookie import validation/add failure logs 使用公开 profile id。
- Profile bundle export request validation 和 local storage export failure logs 使用公开 profile id。
- 正常 UUID profile id 仍可追踪；非 UUID 或 token/header 风格 profile id 统一记录为 `unknown`。
- 不改变 cookie/bundle response、audit、running lookup、cookie 写入、bundle 构造或 local storage 读取语义。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_import_cookie_json_failure_logs_public_profile_id backend/tests/test_api.py::test_export_profile_bundle_validation_logs_public_profile_id -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.79s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "cookie or bundle"
# 45 passed, 201 deselected in 3.88s

. .venv/bin/activate && python -m pytest backend/tests -q
# 628 passed in 38.03s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.29s
```

边界：

- 这是 cookie/profile bundle release evidence hardening，不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 VNC/RFB raw frame release-evidence guardrail

背景：

- Release VNC smoke 和远程 viewer 排障会触发 noVNC client frame 转发、RFB filter 和 handshake 日志。
- 旧 debug/info 日志会保留 raw frame hex；clipboard/client text 即使以 hex 形式出现，也不适合进入 release evidence。

已覆盖：

- RFB unknown message drop 不再输出 raw frame hex。
- VNC handshake debug 不再输出 raw handshake bytes hex。
- RFB safety refusal 不再输出 filtered frame hex。
- VNC send debug 不再输出 filtered frame hex。
- 保留低敏排障字段：message type、offset、length、skipped byte count、first_type。
- 不改变 VNC forwarding、RFB filtering 或 noVNC/KasmVNC compatibility behavior。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_rfb_filter_unknown_message_does_not_log_raw_frame_hex -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.77s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "vnc or clipboard or rfb"
# 17 passed, 230 deselected in 1.75s

. .venv/bin/activate && python -m pytest backend/tests -q
# 629 passed in 40.11s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.33s
```

边界：

- 这是 VNC/RFB release evidence hardening，不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 BrowserManager lifecycle profile-id log guardrail

背景：

- Release regression 会依赖 BrowserManager lifecycle logs 判断 launch/stop/browser_closed/auto_launch 过程是否稳定。
- BrowserManager 内部日志此前直接记录传入的 `profile_id`；历史/手工污染 profile id 可能把 URL/query token/header text 带入 release evidence。

已覆盖：

- BrowserManager lifecycle logs 现在通过 public profile log id 过滤。
- 普通低敏 id 继续保留，URL/query/header/token/password/secret/cookie 风格 id 折叠为 `unknown`。
- 覆盖 launch success/failure、launch debug/teardown、stop requested/finished、stop close failures、browser_closed、browser_closed teardown 和 auto_launch success/failure。
- 内部 runtime lookup、running map key、status response 和 API-level response redaction 不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_lifecycle_logs_sanitize_sensitive_profile_ids -q
# RED: 1 failed；BrowserManager lifecycle logs included raw URL/header/token-like profile_id

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_lifecycle_logs_sanitize_sensitive_profile_ids -q
# 1 passed in 0.04s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 70 passed in 0.89s

. .venv/bin/activate && python -m pytest backend/tests -q
# 622 passed in 39.92s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.20s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Launch failure stage diagnostics guardrail

背景：

- Release smoke 使用 `/api/diagnostics` 中的 launch failure summary 判断 profile/VNC/runtime launch failure 是否集中在固定阶段。
- `_record_launch_failure()` 已将正常失败阶段限制在白名单，但 summary 仍直接信任当前 in-memory dict。
- 如果内部状态被污染为 URL/query token/header 风格 stage key 或非整数 count，release diagnostics evidence 可能泄露 raw stage text 或返回 500。

已覆盖：

- `BrowserManager.launch_failure_summary()` 现在只累计正整数 count；bool、非整数、0 和负数会被忽略。
- stage key 只保留固定 `LAUNCH_FAILURE_STAGES`；非白名单 stage 归并为 `unknown`。
- `/api/diagnostics.runtime.launch_failure_stage_counts` 因此只会拿到 public stage labels 和数字 counts。
- 正常 launch failure recording、resource/VNC/startup cleanup diagnostics 和 System diagnostics 前端展示语义保持不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_failure_summary_sanitizes_existing_stage_counts -q
# RED: 1 failed；polluted count caused TypeError and raw stage key was not normalized

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py::test_launch_failure_summary_sanitizes_existing_stage_counts -q
# 1 passed in 0.15s

. .venv/bin/activate && python -m pytest backend/tests/test_browser_manager.py -q
# 69 passed in 0.90s

. .venv/bin/activate && python -m pytest backend/tests -q
# 621 passed in 38.84s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.30s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Management response timestamp guardrail

背景：

- Release regression 和运营台 smoke 会读取 profile/proxy/template/preset list/detail responses 作为低敏证据。
- ProfileResponse、ProxyResponse、ProfileTemplateResponse、ProxyProviderPresetResponse 中的 timestamp 字段此前仍信任历史/手工 DB row。
- 如果这些字段被污染为 URL/query token/header 风格 timestamp text，release evidence 会回显该文本。

已覆盖：

- ProfileResponse `created_at`、`updated_at` 只保留可解析 ISO timestamp；污染值返回 `unknown`。
- ProfileResponse `last_geoip_resolved_at` 和 ProxyResponse `last_check_at` 只保留可解析 ISO timestamp；污染值返回 `null`。
- ProxyResponse、ProfileTemplateResponse、ProxyProviderPresetResponse `created_at`、`updated_at` 只保留可解析 ISO timestamp；污染值返回 `unknown`。
- 内部 DB 排序、更新时间写入、GeoIP/proxy check persistence、profile/template/preset CRUD、random assignment 和 import preview 语义不变。
- 正常管理 API 相邻路径、existing id/identity/GeoIP/provider/tag redaction 和 frontend type/build gates 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_timestamp_fields backend/tests/test_proxies.py::test_proxy_api_responses_sanitize_persisted_timestamp_fields backend/tests/test_proxies.py::test_proxy_provider_preset_responses_sanitize_persisted_timestamp_fields backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_timestamp_fields -q
# RED: 4 failed；created_at 直接保留 token/header-like timestamp text

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_timestamp_fields backend/tests/test_proxies.py::test_proxy_api_responses_sanitize_persisted_timestamp_fields backend/tests/test_proxies.py::test_proxy_provider_preset_responses_sanitize_persisted_timestamp_fields backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_timestamp_fields -q
# 4 passed in 1.18s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py backend/tests/test_proxies.py backend/tests/test_templates.py -q
# 294 passed in 25.61s

. .venv/bin/activate && python -m pytest backend/tests -q
# 620 passed in 39.13s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.96s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime session timestamp guardrail

背景：

- Release runtime/VNC smoke 会创建 runtime session、读取 session、续租/终止 session，并签发 viewer token。
- RuntimeSessionResponse 的 `lease_expires_at`、`created_at`、`updated_at` 是 release evidence 中常见的时间字段；此前如果历史/手工 DB row 里存在 URL/query token/header 风格 timestamp text，response 会直接回显。

已覆盖：

- RuntimeSessionResponse `lease_expires_at`、`created_at`、`updated_at` 现在只保留可解析 ISO timestamp。
- 污染的 timestamp 字段会折叠为 `unknown`，不会把 token、Authorization/Bearer 或 URL host/path context 带进 runtime response evidence。
- 内部 DB row、lease/live 判断、create/get/renew/terminate、viewer token 和 audit flow 不改，只在 response DTO 前做输出侧过滤。
- 正常 runtime session broker、runtime id/profile id/external id/status guardrails 和 session broker 相邻路径保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_timestamp_fields -q
# RED: 1 failed；lease_expires_at 直接保留 token-like timestamp text

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_timestamp_fields -q
# 1 passed in 0.78s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 43 passed in 4.49s

. .venv/bin/activate && python -m pytest backend/tests -q
# 616 passed in 38.24s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.43s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation task timestamp guardrail

背景：

- Release smoke 会读取 automation task list/detail 作为任务队列和 worker 证据。
- 旧实现已清洗 task id/profile id/status/error/steps/result，但仍直接回显历史/手工 DB timestamp 字段。

已覆盖：

- AutomationTaskResponse `created_at` 只保留可解析 ISO timestamp；污染值返回 `unknown`。
- `started_at` 和 `finished_at` 只保留可解析 ISO timestamp；污染值返回 `null`。
- 内部 task ordering、lease、worker、run/cancel/retry 语义不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_response_sanitizes_persisted_timestamp_fields -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.87s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_task"
# 41 passed, 198 deselected in 5.05s

. .venv/bin/activate && python -m pytest backend/tests -q
# 615 passed in 40.58s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.86s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Audit event reader guardrail

背景：

- Release smoke 会使用 audit event 作为低敏证据面。
- 旧实现只在写入 audit event 时清洗 metadata，读取历史/手工 DB row 时仍可能回显污染的顶层字段和原始 metadata。

已覆盖：

- Audit event reader 输出侧现在清洗 `id`、`runtime_session_id`、`profile_id`、`external_session_id`、`event_type`、`actor_type` 和 `created_at`。
- 历史 metadata 读出时也会再次经过 audit metadata sanitizer。
- 正常 runtime viewer/session audit、profile/proxy/cookie/bundle audit 和 automation task audit 保持既有低敏格式。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_audit_event_reader_sanitizes_historical_top_level_fields_and_metadata -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.77s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 42 passed in 5.90s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "audit or automation_task"
# 53 passed, 185 deselected in 7.89s

. .venv/bin/activate && python -m pytest backend/tests -q
# 614 passed in 39.49s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.85s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile template id guardrail

背景：

- Release smoke 会读取 profile template list/detail/update response，也会通过 CSV import preview 验证模板匹配后的 profile preview。
- 旧实现已经清洗 template identity fields，但仍直接回显历史/手工 DB template id。

已覆盖：

- ProfileTemplateResponse `id` 只保留 canonical UUID；非 UUID template id 返回 `unknown`。
- CSV import preview `profile.template_id` 只保留 canonical UUID；非 UUID template id 返回 `unknown`。
- 内部模板 lookup 和 field application 语义不变，普通 UUID template CRUD、CSV preview/import 和 bulk paths 仍保持既有格式。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py::test_profile_template_api_and_import_preview_sanitize_persisted_template_id -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.65s

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py backend/tests/test_bulk.py -q
# 32 passed in 2.63s

. .venv/bin/activate && python -m pytest backend/tests -q
# 613 passed in 39.91s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.98s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation task id guardrail

背景：

- Release smoke 会读取 automation task list/detail、cancel/retry/run response，并查看 automation.task audit metadata。
- 旧实现已经对 profile_id、step、result、status 和 error 做了低敏处理，但仍直接回显历史/手工 DB task id。

已覆盖：

- AutomationTaskResponse `id` 只保留 canonical UUID；非 UUID task id 返回 `unknown`。
- automation.task audit metadata `task_id`、retry `source_task_id` 和 `new_task_id` 只保留 canonical UUID；非 UUID id 省略。
- 内部 task lookup 语义不变，普通 UUID task create/list/detail/cancel/retry/run 和 audit 仍保持既有格式。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_sanitize_persisted_task_id -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.89s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_task"
# 40 passed, 198 deselected in 5.26s

. .venv/bin/activate && python -m pytest backend/tests -q
# 612 passed in 38.90s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.84s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Proxy provider preset id guardrail

背景：

- Release regression 的 random proxy assignment 会使用 provider preset，并记录 response 与 audit metadata。
- 继续复查发现 provider preset response/audit 和 random assignment response/audit 会保留历史/手工污染的非 UUID provider preset id。
- 普通 DB 生成的 UUID preset id 不受影响，但污染 id 会污染低敏 release evidence。

已覆盖：

- Provider preset list/detail/update response id 改为 UUID-only；非 UUID 命中值返回 `unknown`。
- Provider preset audit metadata `preset_id` 改为 UUID-only；非 UUID 值省略。
- Random assignment response `provider_preset_id` 改为命中 preset row 的 public id。
- Random assignment audit metadata `provider_preset_id` 改为 UUID-only；非 UUID 值省略。
- 正常 provider preset flow、random assignment、proxy selection filtering 和 frontend gates 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_provider_preset_responses_and_audits_sanitize_persisted_preset_id -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.88s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "provider_preset or random_proxy_assignment or provider_preset_id"
# 6 passed, 33 deselected in 1.43s

. .venv/bin/activate && python -m pytest backend/tests -q
# 611 passed in 39.19s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.32s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Proxy asset id guardrail

背景：

- Release regression 的 Proxy Manager / proxy-country 准备路径会读取 proxy list/detail、执行 fixed/random assignment、bulk check，并抽查对应 audit。
- 继续复查发现这些边界会保留历史/手工污染的非 UUID proxy asset id。
- 普通 DB 生成的 UUID proxy id 不受影响，但污染 id 会污染低敏 release evidence。

已覆盖：

- Proxy list/detail/update response id 改为 UUID-only；非 UUID 命中值返回 `unknown`。
- Fixed proxy assignment response 顶层 `proxy_id`、nested proxy id、assignment audit metadata 使用 public proxy id。
- Random proxy assignment result `proxy_id` 和 nested proxy id 使用 public proxy id。
- Bulk check result `proxy_id` 和 nested proxy id 使用 public proxy id；ordinary missing proxy id 保持既有语义。
- Proxy CRUD audit metadata 只保留 canonical UUID proxy id。
- 正常 proxy CRUD、audit、fixed/random assignment、bulk check 和 frontend gates 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_asset_responses_and_audits_sanitize_persisted_proxy_id -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.99s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py backend/tests/test_api.py -q -k "proxy_asset_responses_and_audits_sanitize_persisted_proxy_id or proxy_crud_api or proxy_crud_audit or proxy_assign or random_proxy_assignment or proxy_bulk_check or proxy_assignment_responses"
# 19 passed, 256 deselected in 2.75s

. .venv/bin/activate && python -m pytest backend/tests -q
# 610 passed in 36.73s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.03s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile/health audit profile id guardrail

背景：

- Release regression 会保留低敏 profile CRUD audit、profile health audit 和 health lookup failure log 摘要。
- 继续复查发现这些边界仍可从历史/手工污染 DB row 或 path profile id 写入非 UUID profile id。
- 该缺口不会影响普通 UUID profile flow，但会污染 release smoke evidence。

已覆盖：

- Profile CRUD audit 顶层 `profile_id` 改为 UUID-only；非 UUID 值省略。
- Profile audit metadata `platform` 改为 public enum-only；污染值省略。
- Profile health audit 顶层 `profile_id` 改为 UUID-only；非 UUID 值省略。
- Health GeoIP lookup failure log 对非 UUID profile id 输出固定 `unknown`。
- 正常 profile CRUD audit、health audit、health lookup failure log 和 frontend gates 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_crud_audit_sanitizes_persisted_profile_id_and_platform -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.79s

. .venv/bin/activate && python -m pytest backend/tests/test_health.py::test_health_check_audit_and_logs_sanitize_persisted_profile_id -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.70s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_crud_audit or profile.created or profile.updated or profile.deleted"
# 2 passed, 235 deselected in 0.89s

. .venv/bin/activate && python -m pytest backend/tests/test_health.py -q -k "health_check_success_writes_redacted_audit_event or health_check_invalid_proxy_writes_redacted_audit_without_lookup or health_check_lookup_failure_writes_redacted_audit_event or health_check_lookup_failure_logs_error_type_without_raw_exception or health_check_audit_and_logs_sanitize_persisted_profile_id"
# 5 passed, 20 deselected in 1.06s

. .venv/bin/activate && python -m pytest backend/tests -q
# 609 passed in 38.42s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.05s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile config export profile id guardrail

背景：

- Release artifact smoke 会使用 `/api/profiles/export` 导出 profile config，并检查 response 不保留敏感 proxy/profile evidence。
- 旧实现已清洗 profile config payload，但 per-result `profile_id` 仍直接回显 request/profile id。
- 历史/手工污染的非 UUID profile id 不应进入 profile config export response。

已覆盖：

- 成功 profile config export result 的 `profile_id` 现在只保留 canonical UUID；非 UUID 返回 `unknown`。
- Missing profile 的普通低敏 id 继续返回，保持既有 API 语义；敏感/非公开 missing id 折叠为 `unknown`。
- 正常 UUID export、ordinary missing profile result、sensitive proxy confirmation、bulk export audit behavior 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profiles_sanitizes_persisted_profile_id_response -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.80s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py backend/tests/test_bulk.py -q -k "export_profiles or profiles/export or profile_config_export"
# 6 passed, 250 deselected in 1.11s

. .venv/bin/activate && python -m pytest backend/tests -q
# 607 passed in 35.15s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.26s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Proxy assignment profile id guardrail

背景：

- Release proxy-country smoke 会通过 Proxy Manager 进行 fixed proxy assignment 和 random assignment。
- 旧实现已清洗 proxy URL/provider/country/tag metadata，但 assignment result 的 per-profile `profile_id` 仍信任 request/profile id。
- 历史/手工污染的非 UUID profile id 不应进入 proxy assignment release smoke responses。

已覆盖：

- Fixed proxy assignment 成功 result 的 `profile_id` 现在只保留 canonical UUID；命中的非 UUID profile id 返回 `unknown`。
- Random proxy assignment 成功 result 使用同一 public profile id guardrail。
- Missing profile 的普通低敏 id 继续返回，保持既有 API 语义；敏感/非公开 missing id 折叠为 `unknown`。
- 正常 UUID assignment behavior、missing profile behavior、proxy URL redaction、provider/country/tag filtering 和 audit metadata 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_proxy_assignment_responses_sanitize_persisted_profile_id -q
# RED: 1 failed；fixed proxy assignment response 直接保留非 UUID profile id

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_proxy_assignment_responses_sanitize_persisted_profile_id backend/tests/test_proxies.py::test_proxy_assigns_raw_url_to_profiles_without_leaking_credentials backend/tests/test_proxies.py::test_random_proxy_assignment_filters_by_country_tag_and_preset_without_leaking_credentials -q
# 3 passed in 1.13s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py backend/tests/test_proxies.py -q -k "proxy_assignment or proxy_assign or random_proxy_assignment or random_assign or proxy"
# 47 passed, 225 deselected in 4.44s

. .venv/bin/activate && python -m pytest backend/tests -q
# 606 passed in 36.81s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.32s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile bundle export profile id guardrail

背景：

- Release artifact smoke 会导出 profile bundle，并可包含 Cookie JSON 与 local storage sections。
- 旧实现已清洗 profile config、cookie/local-storage payload 和 audit summary，但 bundle response、bundle metadata、embedded cookie metadata 以及 bundle cookie/local-storage audit 顶层 `profile_id` 仍信任 route/profile id。
- 历史/手工污染的非 UUID profile id 不应进入 bundle response、bundle metadata 或低敏 audit evidence。

已覆盖：

- Profile bundle export response 的 `profile_id` 现在只保留 canonical UUID；非 UUID 返回 `unknown`。
- Bundle metadata `source_profile_id` 和 embedded cookie document `profile_id` 现在使用同一 public profile id。
- `profile_bundle.cookie_exported` 与 `profile_bundle.local_storage_exported` audit 顶层 `profile_id` 现在只保留 canonical UUID；非 UUID 省略。
- 正常 UUID bundle config/cookie/local-storage export 和 bundle import behavior 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_export_profile_bundle_sanitizes_persisted_profile_id_response_and_audit -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.80s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_bundle"
# 20 passed, 214 deselected in 2.05s

. .venv/bin/activate && python -m pytest backend/tests -q
# 605 passed in 35.56s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.17s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Cookie import/export profile id guardrail

背景：

- Release artifact smoke 会通过 running profile 导入/导出 Cookie JSON 与 Netscape cookie 文件，并检查 cookie export audit evidence。
- 旧实现已清洗 cookie values、names、domains 和 URL query/fragment，但 cookie API response、JSON export metadata 和 `cookie.exported` audit 顶层 `profile_id` 仍信任 route/profile id。
- 历史/手工污染的非 UUID profile id 不应进入 cookie API response、export metadata 或低敏 audit evidence。

已覆盖：

- Cookie JSON import/export 与 Netscape import/export response 的 `profile_id` 现在只保留 canonical UUID；非 UUID 返回 `unknown`。
- Cookie JSON export document metadata `profile_id` 现在使用同一 public profile id。
- `cookie.exported` audit event 顶层 `profile_id` 现在只保留 canonical UUID；非 UUID 省略。
- 正常 UUID cookie import/export response、document、Netscape text 和 audit summary 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_cookie_import_export_sanitizes_persisted_profile_id_response_and_audit -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.78s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "cookie"
# 28 passed, 205 deselected in 2.63s

. .venv/bin/activate && python -m pytest backend/tests -q
# 604 passed in 36.83s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.25s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation task profile id guardrail

背景：

- Release Automation smoke 会创建、查询、取消、重试和运行 task，并检查 audit event 是否低敏。
- 旧实现已清洗 task steps/result/error/status/lease metadata，但 task response 顶层 `profile_id` 和 automation.task audit 顶层 `profile_id` 仍信任 task profile id。
- 历史/手工污染的非 UUID profile id 不应进入 release smoke task responses 或 audit evidence。

已覆盖：

- AutomationTaskResponse 的 `profile_id` 现在只保留 canonical UUID；非 UUID 返回 `unknown`。
- Automation task audit event 顶层 `profile_id` 现在只保留 canonical UUID；非 UUID 省略。
- 覆盖 create/get/list/cancel/retry/run response 与 created/cancelled/retried/succeeded audit flow。
- 正常 UUID profile task response/audit behavior 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_sanitize_persisted_profile_id -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.86s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "automation_task"
# 39 passed, 193 deselected in 5.16s

. .venv/bin/activate && python -m pytest backend/tests -q
# 603 passed in 36.54s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.05s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile launch/status automation URL guardrail

背景：

- Release profile/API smoke 会启动 profile、读取 status，并进入 Automation info/pages flow。
- 旧实现已清洗 profile list/detail 的顶层 id 和 running automation URL，但 launch success、status 和 automation info 仍使用 raw path/DB profile id 构造 response fields。
- 历史/手工污染的非 UUID profile id 不应进入 release smoke 响应、UI-facing automation URL、Automation pages URL 或低敏交接证据。

已覆盖：

- Launch success response 的 `profile_id` 现在只保留 canonical UUID；非 UUID 返回 `unknown`。
- Launch success response 和 status response 的 `automation_url` 现在由 public profile id 重建。
- Automation info response 的 `profile_id` 和 `pages_url` 现在由 public profile id 重建。
- 正常 UUID launch/status/automation info behavior 保持通过；内部 running profile lookup、route path 和 automation actions 不变。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_success_response_sanitizes_persisted_profile_id_and_automation_url backend/tests/test_api.py::test_status_and_automation_info_sanitize_persisted_profile_id_urls -q
# RED then GREEN；初始 2 failed，最终 2 passed in 1.06s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "launch_success_response or automation_info or running_profile_exposes_automation_url_only or profile_response_sanitizes_persisted_profile_id"
# 7 passed, 224 deselected in 1.12s

. .venv/bin/activate && python -m pytest backend/tests -q
# 602 passed in 34.37s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.94s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile response id / automation URL guardrail

背景：

- Release profile/API smoke 会读取 profile list/detail，并在 running profile 上展示 automation URL。
- 旧实现已清洗 persisted profile identity fields，但 response 顶层 `id` 和由它拼出的 `automation_url` 仍信任 DB row id。
- 历史/手工污染的非 UUID profile id 不应进入 release smoke 响应、UI-facing automation URL 或低敏交接证据。

已覆盖：

- Profile list/detail response 的顶层 `id` 现在只保留 canonical UUID；非 UUID 返回 `unknown`。
- Running profile 的 `automation_url` 现在用 public id 重建，非 UUID path 折叠为 `/api/profiles/unknown/automation`。
- 正常 UUID profile 响应、status、VNC port 和 automation URL 行为保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_response_sanitizes_persisted_profile_id_and_automation_url -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.78s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -q -k "profile_response or get_profile or list_profiles"
# 13 passed, 216 deselected in 1.46s

. .venv/bin/activate && python -m pytest backend/tests -q
# 600 passed in 34.05s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.98s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Launch failure profile id log guardrail

背景：

- Release smoke 和生产 triage 会读取 profile launch/runtime launch failure logs。
- 旧日志已隐藏 raw exception text，但仍直接写 profile id；历史/污染 profile id 可把 URL/query token/header 文本写入日志。

已覆盖：

- 普通 profile launch failure 和 runtime session profile launch failure 日志现在只保留 canonical UUID profile id。
- 非 UUID profile id 折叠为 `unknown`；fixed `error_type` 和 HTTP response 语义保持不变。
- proxy validation detail redaction、resource limit、diagnostics launch failure summary 和 runtime response/audit guardrails 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_failure_log_omits_sensitive_profile_id backend/tests/test_session_broker.py::test_runtime_session_create_launch_failure_log_omits_sensitive_profile_id -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.85s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_launch_failure_500 backend/tests/test_api.py::test_launch_failure_log_omits_sensitive_profile_id backend/tests/test_api.py::test_system_diagnostics_reports_low_sensitive_launch_failure_summary backend/tests/test_session_broker.py::test_runtime_session_create_launch_failure_log_omits_sensitive_profile_id backend/tests/test_session_broker.py::test_runtime_session_create_redacts_sensitive_launch_value_error_detail -q
# 5 passed in 1.02s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_api.py -q -k "runtime_session_create or launch_failure or launch_invalid_proxy or max_running_profiles"
# 16 passed, 253 deselected in 1.84s

. .venv/bin/activate && python -m pytest backend/tests -q
# 599 passed in 34.47s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.13s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile/proxy audit name guardrail

背景：

- Release smoke 与排障会读取 audit event 作为低敏证据。
- Profile/proxy CRUD audit metadata 此前保留普通 `name`，但当 name 本身被用户或历史 DB 污染为 URL/query token/Authorization/Bearer 风格文本时，DB audit sanitizer 仍会留下 host 等上下文。

已覆盖：

- Profile/proxy create/delete audit metadata 现在只保留 public audit name。
- 普通短名称继续保留，URL/header/token/path 风格名称会被省略。
- API response 与持久 profile/proxy name 不变；仅收紧 audit metadata。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py::test_proxy_crud_audit_omits_sensitive_name_metadata backend/tests/test_api.py::test_profile_crud_audit_omits_sensitive_name_metadata -q
# RED then GREEN；初始 2 failed，最终 2 passed in 1.00s

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -k "audit or proxy_crud_api" -q
# 6 passed, 31 deselected in 1.35s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "profile_crud_api_writes_redacted_audit_events or profile_crud_audit_omits_sensitive_name_metadata or delete_profile_stops_running" -q
# 3 passed, 223 deselected in 0.97s

. .venv/bin/activate && python -m pytest backend/tests -q
# 587 passed in 33.60s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.02s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime template identity field guardrail

背景：

- Release runtime smoke 可以通过 `template_id` 创建并启动临时 profile。
- Profile create/import 已过滤历史污染 template identity fields，但 runtime create path 直接复制 template row 并传入 launch。

已覆盖：

- Runtime template-created profile 现在复用 template response sanitizer 后再创建 profile 和 launch。
- 污染 platform、screen、GPU、hardware、color、human preset 和 launch_args 不再进入 runtime-created profile/launch lifecycle。
- 正常 template copy、profile name fallback、runtime response/audit guardrails 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_template_identity_before_launch -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.72s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_creates_profile_then_launches backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_generated_profile_name backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_template_identity_before_launch backend/tests/test_templates.py::test_create_profile_from_template_sanitizes_persisted_identity_fields backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_identity_fields -q
# 5 passed in 1.00s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py backend/tests/test_templates.py -q
# 51 passed in 4.85s

. .venv/bin/activate && python -m pytest backend/tests -q
# 597 passed in 34.10s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.16s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile response identity guardrail

背景：

- Release smoke 会反复调用 profile list/detail/create/update，再进入 launch、VNC 和 automation。
- 历史/手工 DB 污染的 profile identity 字段此前可让 profile detail/list response validation 失败，或把 URL/header/token 风格 identity text 暴露到 API/UI。

已覆盖：

- ProfileResponse 现在会过滤 persisted platform、screen dimensions、GPU text、hardware concurrency、timezone、locale、humanize、human_preset、headless、geoip、clipboard_sync、auto_launch、color_scheme 和 launch_args。
- 普通 response launch args 保持 API 语义；仅丢弃 URL/token/header/cookie 风格参数。
- Template、bulk config export/import、bundle/config 相关测试保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_identity_fields -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.70s

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 11 passed in 1.22s

. .venv/bin/activate && python -m pytest backend/tests/test_api.py -k "profile_responses or profile_response or create_profile_with_all_fields or get_profile or update_profile or profile_config or export_profiles" -q
# 22 passed, 205 deselected in 2.47s

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -k "export_profile_configs or config_import or round_trip or csv_import" -q
# 20 passed in 2.25s

. .venv/bin/activate && python -m pytest backend/tests -q
# 588 passed in 33.33s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.14s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime external session id guardrail

背景：

- Release runtime/VNC smoke 会创建 runtime session、读取 session、签发 viewer token，并检查 audit event。
- `external_session_id` 是 runtime service caller 控制的跨系统关联字段；此前 response 和 audit 顶层字段直接回显历史/调用方值。

已覆盖：

- RuntimeSessionResponse 对非公开 external id 返回 `unknown`。
- Runtime service 与 runtime viewer audit event 顶层 `external_session_id` 现在只保留 public id；URL/query token/header/token-assignment 风格值会省略。
- 正常 `pm-session-*`、`external-1`、viewer token、runtime service token 和 VNC failure audit 流程保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_external_session_id backend/tests/test_session_broker.py::test_runtime_viewer_failure_audit_omits_sensitive_external_session_id -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.75s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 33 passed in 3.59s

. .venv/bin/activate && python -m pytest backend/tests -q
# 590 passed in 34.51s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.87s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime profile id guardrail

背景：

- Release runtime/VNC smoke 会创建 runtime session、读取 session、签发 viewer token，并检查 audit event。
- `profile_id` 是 runtime response/audit 的顶层关联字段；此前如果历史/手工 DB row 里存在非 UUID profile id，response 和 audit 会直接回显该值。

已覆盖：

- RuntimeSessionResponse 对非 UUID profile id 返回 `unknown`。
- Runtime service 与 runtime viewer audit event 顶层 `profile_id` 现在只保留 canonical UUID；URL/query token/header 风格值会省略。
- 正常 UUID profile id、external session id guardrail、viewer token、runtime service token 和 VNC failure audit 流程保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_profile_id backend/tests/test_session_broker.py::test_runtime_viewer_failure_audit_omits_sensitive_profile_id -q
# RED then GREEN；初始 2 failed，最终 2 passed in 0.80s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 35 passed in 3.73s

. .venv/bin/activate && python -m pytest backend/tests -q
# 592 passed in 34.53s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.33s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime session id guardrail

背景：

- Release runtime/VNC smoke 会创建 runtime session、读取 session、签发 viewer token，并检查 audit event。
- `runtime_session_id` 是 runtime response/audit/viewer URL 的顶层关联字段；此前如果历史/手工 DB row 或 URL path 里存在非 UUID session id，response、viewer URL 和 audit 会直接回显该值。

已覆盖：

- RuntimeSessionResponse 对非 UUID session id 返回 `unknown`。
- Runtime service 与 runtime viewer audit event 顶层 `runtime_session_id` 现在只保留 canonical UUID；URL/query token/header 风格值会省略。
- Runtime viewer-token response 的 `viewer_url` session path 现在只使用 canonical UUID；非公开 session id 折叠为 `unknown`。
- 正常 UUID session id、profile/external id guardrails、viewer token、runtime service token 和 VNC failure audit 流程保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_session_id backend/tests/test_session_broker.py::test_runtime_viewer_token_response_sanitizes_persisted_session_id backend/tests/test_session_broker.py::test_runtime_viewer_origin_failure_audit_omits_sensitive_session_id -q
# RED then GREEN；初始 3 failed，最终 3 passed in 0.97s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 38 passed in 3.91s

. .venv/bin/activate && python -m pytest backend/tests -q
# 595 passed in 34.00s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.10s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime template profile name guardrail

背景：

- Release runtime smoke 可以通过 `template_id` 创建临时 profile。
- 旧实现把 caller-controlled `external_session_id` 拼进新 profile name；如果 external id 是 URL/query token/header 风格文本，profile list/detail 会作为 name 语义保留并回显。

已覆盖：

- Template-created runtime profile name 现在只使用 public external session id。
- 非公开 external id 生成固定低敏名称 `Runtime session`。
- 正常 `pm-session-*` external id 仍生成 `Runtime <id>`；template field application、launch、runtime session response 和 audit guardrails 保持通过。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_generated_profile_name -q
# RED then GREEN；初始 1 failed，最终 1 passed in 0.70s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py::test_runtime_session_create_from_template_creates_profile_then_launches backend/tests/test_session_broker.py::test_runtime_session_create_from_template_sanitizes_generated_profile_name backend/tests/test_session_broker.py::test_runtime_session_response_sanitizes_persisted_external_session_id -q
# 3 passed in 3.14s

. .venv/bin/activate && python -m pytest backend/tests/test_session_broker.py -q
# 39 passed in 4.48s

. .venv/bin/activate && python -m pytest backend/tests -q
# 596 passed in 34.65s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.06s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile delete directory release-evidence guardrail

背景：

- Release smoke 会覆盖 profile create/edit/delete；delete 路径需要和 launch 路径使用同一条 profile dir public boundary。
- 启动路径已拒绝 URL/query token/header 风格 `user_data_dir`，但删除路径此前直接信任 DB row 并先删除 DB 后清理磁盘。
- 历史/手工污染的 `user_data_dir` 不应导致 running profile 被 stop、DB row 被删除、磁盘清理被调用或 `profile.deleted` audit 被写入。

已覆盖：

- `DELETE /api/profiles/{id}` 在 stop/delete/rmtree/audit 之前先复用 `_public_profile_dir()` 校验持久化目录。
- 非公开目录返回固定 `400 Invalid profile directory`，响应不包含 URL/query/token/header 文本。
- 校验失败时 profile row 保留、running map 不被 stop、磁盘 marker 保留、`shutil.rmtree()` 未调用、除 `profile.created` 外无新增 audit。
- 正常 delete、显式确认 gate、not found、running profile stop 和 profile CRUD audit 回归通过。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_delete_profile_rejects_non_public_user_data_dir_without_side_effects -q
# RED then GREEN；旧实现返回 200，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k "delete_profile or profile_crud" -q
# 8 passed, 240 deselected

.venv/bin/python -m pytest backend/tests -q
# 636 passed in 38.89s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.74s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Profile response directory release-evidence guardrail

背景：

- Release profile/API smoke 会读取 profile create/list/detail 响应。
- ProfileResponse 仍保留 `user_data_dir` 字段；普通本地管理台语义可以保留，但历史/手工污染 row 不应把 URL/query token/header 风格 profile dir 文本带入 release evidence。
- Launch/delete 已复用 `_public_profile_dir()`；response 层需要同等防御，避免 profile dir、Authorization/Bearer 或 token marker 出现在低敏证据里。

已覆盖：

- `_profile_response()` 对 persisted `user_data_dir` 使用 public profile-dir boundary。
- 正常本地 profile dir 继续返回；非公开 URL/query token/header 风格值折叠为 `unknown`。
- Profile get/list 响应不再包含污染 host、`token=`、Authorization、Bearer 或 secret marker。
- 相邻 profile response、profile CRUD、create/get 和 delete guardrail 回归通过。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_profile_response_sanitizes_persisted_user_data_dir -q
# RED then GREEN；旧实现原样回显污染 user_data_dir，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k "profile_response or profile_responses or profile_crud or delete_profile or create_profile or get_profile" -q
# 25 passed, 224 deselected

.venv/bin/python -m pytest backend/tests -q
# 637 passed in 39.23s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.61s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime viewer close-code release-evidence guardrail

背景：

- Release runtime/VNC smoke 会检查 `runtime.viewer.connected` 和 `runtime.viewer.disconnected` audit event。
- `close_code` 是 WebSocket close code 语义，应只保留整数或 null；污染字符串不应以 `token=[redacted]` / `Authorization=[redacted]` 形态进入 evidence。
- Runtime viewer audit 是 Project Mileage 远程工作台未来的关键交接面，因此需要在 audit helper 层固定边界。

已覆盖：

- `_audit_runtime_viewer_event()` 现在对 metadata 中的 `close_code` 做 public boundary。
- 非 bool 整数 `0..65535` 保留；其他值折叠为 null。
- 正常 runtime VNC success audit 仍记录 `close_code: 1000`。
- 污染 close_code 不再泄漏 secret marker、`token=`、Authorization 或 Bearer 文本。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_viewer_disconnect_audit_sanitizes_non_integer_close_code -q
# RED then GREEN；旧实现保存 token/header 风格 close_code，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 44 passed in 4.65s

.venv/bin/python -m pytest backend/tests -q
# 638 passed in 39.53s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.19s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime viewer metadata allowlist release-evidence guardrail

背景：

- Release runtime/VNC smoke 会读取 `runtime.viewer.connected` 和 `runtime.viewer.disconnected` audit event 作为低敏证据。
- Connected event 只需要 negotiated subprotocol；disconnected event 只需要 close code。
- 如果 helper 接受未知 metadata key，未来 origin、viewer URL、header/token 风格字段可能以 redacted 但仍非低敏的形式进入 release evidence。

已覆盖：

- `_runtime_viewer_audit_metadata()` 现在按 event type 生成固定 metadata shape。
- `runtime.viewer.connected` 只输出 `{"subprotocol": "binary" | null}`。
- `runtime.viewer.disconnected` 只输出 `{"close_code": int | null}`，且整数范围限制为 `0..65535`。
- 未知 viewer event metadata 折叠为空对象。
- 污染 subprotocol、origin、viewer_url、token/header 文本不再进入 audit；正常 VNC success audit 仍保留 `subprotocol: binary` 和 `close_code: 1000`。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_viewer_connected_audit_allows_only_public_subprotocol_metadata -q
# RED then GREEN；旧实现保存污染 subprotocol 和 origin，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_viewer_connected_audit_allows_only_public_subprotocol_metadata backend/tests/test_session_broker.py::test_runtime_viewer_disconnect_audit_sanitizes_non_integer_close_code backend/tests/test_session_broker.py::test_runtime_vnc_success_writes_redacted_connect_and_disconnect_audit -q
# 3 passed in 0.95s

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 45 passed in 4.84s

.venv/bin/python -m pytest backend/tests -q
# 639 passed in 38.09s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.96s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- 不改变 viewer token、VNC/WebSocket 行为、runtime session 状态或 browser fingerprint 行为。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Runtime service metadata allowlist release-evidence guardrail

背景：

- Release runtime service smoke 会读取 `runtime.session.created/read/renewed/terminated` 和 `runtime.viewer_token.created` audit event。
- 这些 event 的 metadata 应保持固定低敏 shape；wallet/order/billing、viewer URL、header/token 或污染 timestamp 不应以 redacted 文本进入 release evidence。
- Runtime service audit 是 Project Mileage 后端接入 CloakBrowser 的关键交接面，因此 helper 层需要和 viewer audit 一样固定白名单。

已覆盖：

- `_audit_runtime_event()` 现在按 event type 生成固定 metadata。
- `runtime.session.created` 只输出 `profile_source` 和 `lease_seconds`，非法值折叠为 `unknown`/null。
- `runtime.viewer_token.created` 只输出 `ttl_seconds` 和 `viewer_token_expires_at`，非法值折叠为 null/`unknown`。
- `runtime.session.renewed` 只输出 `lease_seconds` 和 `lease_expires_at`，非法值折叠为 null/`unknown`。
- `runtime.session.read`、`runtime.session.terminated` 和未知 runtime service events 输出 `{}`。
- 污染 metadata 不再泄漏 secret marker、`token=`、Authorization/Bearer、viewer URL、wallet/order/billing 文本；正常 runtime service audit flow 保持通过。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_service_audit_allows_only_public_metadata_shapes -q
# RED then GREEN；旧实现保存污染 metadata，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_service_audit_allows_only_public_metadata_shapes backend/tests/test_session_broker.py::test_runtime_service_actions_write_redacted_audit_events -q
# 2 passed in 1.04s

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 46 passed in 4.72s

.venv/bin/python -m pytest backend/tests -q
# 640 passed in 37.47s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.27s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- 不改变 runtime service token、viewer token、lease/renew/terminate、VNC/WebSocket 行为、runtime session 状态或 browser fingerprint 行为。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation task runner/reason release-evidence guardrail

背景：

- Release automation smoke 会读取 `automation.task.succeeded/failed/cancelled_by_runner` 等 terminal audit event。
- `runner_type` 应只描述 API runner 或 background worker；`reason_code` 应只描述固定失败分类。
- runner/reason 是 automation worker 和 Project Mileage 接入排障时会查看的字段，因此需要和 task id/status/step type 一样保持低敏枚举边界。

已覆盖：

- `_automation_task_audit_metadata()` 现在过滤 runner/reason metadata。
- `runner_type` 只输出 `api`、`worker` 或 `unknown`。
- `reason_code` 只输出 `automation_step_failed`、`invalid_step`、`unsupported_step_type` 或 `unknown`。
- 正常 create/cancel/retry/run audit、API terminal audit 和 worker terminal audit 保持通过。
- 污染 runner/reason 不再泄漏 secret marker、`token=`、Authorization 或 Bearer 文本。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_audit_sanitizes_runner_type_and_reason_code -q
# RED then GREEN；旧实现保存污染 runner_type/reason_code，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_audit_sanitizes_runner_type_and_reason_code backend/tests/test_api.py::test_automation_task_create_cancel_retry_and_run_write_redacted_audit_events backend/tests/test_api.py::test_automation_worker_run_once_writes_redacted_terminal_audit_event -q
# 3 passed in 1.18s

.venv/bin/python -m pytest backend/tests/test_api.py -k "automation_task or automation_worker" -q
# 55 passed, 195 deselected in 6.61s

.venv/bin/python -m pytest backend/tests -q
# 641 passed in 38.07s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.07s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- 不改变 automation execution、worker lease、task retry/cancel/run、runtime session、VNC/WebSocket 或 browser fingerprint 行为。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation task persisted-step shape release-evidence guardrail

背景：

- Release automation smoke 会读取 task get/list/cancel responses 和 automation task audit。
- 历史/手工 DB row 可能把 `steps` list item 污染为 URL/query token/header 风格字符串；旧 response redaction 会对该字符串调用 `.get()` 并导致 500。
- `step_count` 和 `step_types` 也应基于 public step objects，而不是任意 list item。

已覆盖：

- `_automation_task_public_steps()` 现在过滤 persisted steps list，只保留 dict item。
- Task response redaction、audit step types 和 audit step count 使用同一个 public step boundary。
- 非 dict persisted step 被跳过；污染 dict step type 折叠为 `unknown`。
- Task get/list/cancel 对污染 persisted steps 仍返回低敏响应，并且 audit step_count 只统计 public dict steps。
- 污染 step URL/host/token/header 文本不再进入 response 或 audit evidence。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_skip_non_dict_persisted_steps -q
# RED then GREEN；旧实现对 string step 调用 .get() 并 500，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_responses_and_audit_skip_non_dict_persisted_steps backend/tests/test_api.py::test_automation_task_sanitizes_sensitive_unknown_step_type_before_persisting_responding_or_audit backend/tests/test_api.py::test_automation_task_create_cancel_retry_and_run_write_redacted_audit_events -q
# 3 passed in 1.20s

.venv/bin/python -m pytest backend/tests/test_api.py -k "automation_task or automation_worker" -q
# 56 passed, 195 deselected in 6.45s

.venv/bin/python -m pytest backend/tests -q
# 642 passed in 38.23s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.21s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- 不改变 normal automation execution、worker lease、task retry/cancel/run、runtime session、VNC/WebSocket 或 browser fingerprint 行为。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation wait-step ms release-evidence guardrail

背景：

- Release automation smoke 会读取 task get/list/cancel responses。
- Wait step execution 已要求 `ms` 是 `1..300000` 范围内的非 bool 整数；response evidence 应使用同一边界。
- 历史/手工 DB row 中的负数、bool 或超大 `ms` 不应出现在低敏 release evidence 中。

已覆盖：

- `_automation_task_redacted_steps()` 现在只输出 public `wait.ms`。
- 正常 `ms=1` 保留；invalid persisted wait ms 从 response step 中移除。
- Task get/list/cancel 仍返回 stable step shape，run invalid wait ms 仍保持原有失败语义。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_response_filters_persisted_wait_ms_boundary -q
# RED then GREEN；旧实现回显 invalid wait ms，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_task_response_filters_persisted_wait_ms_boundary backend/tests/test_api.py::test_automation_task_responses_redact_open_url_steps backend/tests/test_api.py::test_run_automation_task_marks_failed_for_invalid_wait_ms -q
# 3 passed in 2.13s

.venv/bin/python -m pytest backend/tests/test_api.py -k "automation_task or automation_worker" -q
# 57 passed, 195 deselected in 10.19s

.venv/bin/python -m pytest backend/tests -q
# 643 passed in 39.59s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.53s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- 不改变 normal automation wait execution、worker lease、task retry/cancel/run、runtime session、VNC/WebSocket 或 browser fingerprint 行为。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Automation retry persisted-step shape release-evidence guardrail

背景：

- Release automation smoke 会覆盖 failed task retry。
- Retry 应复制原 task 的 public step definitions；历史/手工污染的 non-dict step item 不应让 retry 500，也不应进入新 task response 或 audit evidence。
- 该边界应和 task get/list/cancel response step boundary 一致。

已覆盖：

- `_automation_task_persisted_steps()` 现在只处理 public dict step items。
- Non-dict persisted step 在 retry 时跳过；污染 dict step type 折叠为 `unknown`。
- Retry response 和 `automation.task.retried` audit 使用低敏 step shape。
- 正常 failed-task retry 和 open_url retry redaction 保持通过。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_retry_automation_task_skips_non_dict_persisted_steps -q
# RED then GREEN；旧实现对 string step 调用 .get() 并 500，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py::test_retry_automation_task_skips_non_dict_persisted_steps backend/tests/test_api.py::test_retry_automation_task_keeps_steps_redacted backend/tests/test_api.py::test_retry_failed_automation_task_creates_new_queued_task_without_running_script -q
# 3 passed in 1.08s

.venv/bin/python -m pytest backend/tests/test_api.py -k "automation_task or automation_worker" -q
# 58 passed, 195 deselected in 7.17s

.venv/bin/python -m pytest backend/tests -q
# 644 passed in 38.43s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.31s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 仍未完成外部验收。
- 不改变 normal retry semantics、automation execution、worker lease、task run/cancel、runtime session、VNC/WebSocket 或 browser fingerprint 行为。
- Pixelscan/IPhey 和 US/JP/DE proxy-country gates 仍保持打开；`cbim-23h.6` 继续作为 blocker，`cbim-23h.1` 仍被阻塞。

## 2026-06-03 Pixelscan blocker classification and VNC close-code release-evidence guardrail

背景：

- 产品决策：如果检测站问题已经定位到底层 patched Firefox / `invisible_playwright` / `zoom.stealth.*` fingerprint masking 可检测面，Manager 不继续硬磕绕过。
- Pixelscan 当前失败点仍是 `PXLSCN-FINGERPRINT-MASKING` / `Masking detected Fingerprint`，已有低敏证据未指向 Manager proxy、GeoIP、language、timezone、WebRTC、WebGL 或 release-evidence redaction 单点。
- Release convergence 继续推进 Manager 可控范围：日志、response、audit、diagnostics、Docker smoke、VNC viewer、Automation、Proxy Manager 和低敏外部验收证据。
- 本轮发现 VNC proxy 日志仍会直接打印 transport close code，可能让异常 close code 中的 token/header 风格文本进入 release evidence。

已覆盖：

- `cbim-23h.6` / `cbim-23h.1` 已追加 blocker classification comment：Pixelscan fingerprint masking 作为底层/第三方检测站 blocker，不作为本仓硬解目标。
- `docs/ai-docs/v1/fingerprint-consistency-qa-plan.md` 更新下一步策略：Pixelscan/IPhey 只记录低敏状态，除非上游 runtime 能力变化，否则不继续做 Manager 侧 bypass。
- `_proxy_running_vnc()` 的 client/backend close-code 日志和 disconnect metadata 现在统一走 `_public_ws_close_code()`。
- 正常整数 close code 保留；污染字符串 close code 折叠为 `None`，不会进入 VNC release logs 或 callback metadata。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_vnc_proxy_disconnect_close_code_is_public_in_logs_and_metadata -q
# RED then GREEN；旧实现日志泄露 Authorization/Bearer/token 风格 close code，最终 1 passed

.venv/bin/python -m pytest \
  backend/tests/test_api.py::test_vnc_proxy_connects_websockify_path \
  backend/tests/test_api.py::test_vnc_proxy_disconnect_close_code_is_public_in_logs_and_metadata \
  backend/tests/test_api.py::test_vnc_proxy_disconnect_does_not_dump_raw_xvnc_log \
  backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_error_type_without_raw_exception \
  backend/tests/test_api.py::test_vnc_proxy_connect_failure_logs_public_profile_id \
  backend/tests/test_session_broker.py::test_runtime_viewer_disconnect_audit_sanitizes_non_integer_close_code \
  -q
# 6 passed in 1.07s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 现在按底层/第三方检测站 blocker 管理。
- 不改变 VNC proxy forwarding、RFB filtering、viewer token validation、runtime session state machine、profile launch、Automation API、Proxy Manager、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；后续可以继续关闭 Manager 可控的 release stability/redaction/observability 缺口。

## 2026-06-03 VNC unhandled message release-evidence guardrail

背景：

- Release smoke 和远程 viewer triage 需要保留 VNC proxy 的低敏异常信号。
- VNC client-to-backend loop 对未处理 websocket message 会记录 message `keys` 和 `type`。
- 原实现信任 raw transport dict；异常 adapter 如果把 token/header/URL 风格文本放进 key 或 type，会进入 VNC release logs。

已覆盖：

- VNC proxy unhandled message 日志现在通过 public allowlist 输出 key/type。
- Public type 只允许 `websocket.receive` / `websocket.disconnect`；其它 type 折叠为 `unknown`。
- Public key 只允许 `type`、`bytes`、`text`、`code`、`reason`；其它 key 合并为 `unknown`。
- 正常 VNC connect、disconnect、Xvnc log availability、connect failure profile-id redaction、runtime viewer close-code audit 测试保持通过。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_vnc_proxy_unhandled_message_log_uses_public_keys_and_type -q
# RED then GREEN；旧实现泄露 Authorization/Bearer/token 风格 raw key/type，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k "vnc or runtime_viewer" -q
# 9 passed, 246 deselected in 1.09s

.venv/bin/python -m pytest backend/tests -q
# 646 passed in 37.66s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.67s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 VNC proxy forwarding、RFB filtering、clipboard handling、viewer token validation、runtime session state machine、profile launch、Automation API、Proxy Manager、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 VNC release evidence 日志边界。

## 2026-06-03 VNC backend subprotocol release-evidence guardrail

背景：

- VNC release smoke 会查看 proxy connect 成功日志确认 viewer 链路是否建立。
- 成功日志中的 KasmVNC backend websocket `subprotocol` 来自 backend adapter，正常是 `binary`，但 release evidence 不应直接信任 raw transport 字段。
- 异常 adapter/fake transport 如果把 token/header 文本放进 `subprotocol`，旧实现会写入日志。

已覆盖：

- VNC proxy connected 日志现在使用 `_public_runtime_viewer_subprotocol(vnc_ws.subprotocol)`。
- Public backend subprotocol 只允许 `binary`；其它值折叠为 `None`。
- 正常 client requested subprotocol 选择、KasmVNC connect、VNC frame forwarding、runtime viewer audit metadata 语义保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_vnc_proxy_connected_log_uses_public_backend_subprotocol -q
# RED then GREEN；旧实现泄露 Authorization/Bearer/token 风格 backend subprotocol，最终 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k "vnc or runtime_viewer" -q
# 10 passed, 246 deselected in 1.13s

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 37.45s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 221 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.61s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 VNC proxy forwarding、RFB filtering、clipboard handling、viewer token validation、runtime session state machine、profile launch、Automation API、Proxy Manager、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 VNC connected log release-evidence 边界。

## 2026-06-03 Frontend VNC clipboard console release-evidence guardrail

背景：

- Release smoke/triage 可能查看浏览器 console 来定位 VNC viewer 和 clipboard sync 行为。
- `ProfileViewer` 的 Host→VNC paste、VNC→Host clipboard event 和 backend clipboard polling 都可能经过真实 clipboard 内容。
- 旧实现保留了调试 console 输出，会记录 clipboard 文本前缀、异常对象和内部状态。

已覆盖：

- `ProfileViewer` 内不再调用 `console.log` / `console.warn` / `console.debug` / `console.error`。
- Host→VNC paste 仍读取 host clipboard、调用 `api.setClipboard()`，并发送 Ctrl+V key sequence。
- VNC→Host clipboard event 和 polling bridge 仍写入 host clipboard；失败时低噪声静默降级。
- Automation endpoint copy 失败不再把原始异常对象写入 console。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileViewer.test.tsx
# RED then GREEN；旧实现 console calls 包含 clipboard-token-super-secret/token=，最终 16 passed

rg -n "console\\.(log|warn|debug|error)\\(" frontend/src/components/ProfileViewer.tsx
# no matches

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 41.21s

npm --prefix frontend test -- --run
# Test Files 16 passed；Tests 222 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.72s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 VNC websocket URL 选择、noVNC RFB connect、backend clipboard API、VNC frame forwarding、runtime viewer token validation、Automation API、Proxy Manager、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 frontend VNC clipboard console release-evidence 边界。

## 2026-06-03 Frontend raw console/error release-evidence guardrail

背景：

- Release smoke/triage 可能查看浏览器 console 和页面错误状态。
- `LaunchButton` 原先会把 raw launch/stop action error message 渲染到页面，并把 raw exception 写入 `console.error`。
- `App` 初始 auth status failure 原先会把 raw exception 写入 `console.warn`。

已覆盖：

- Profile launch/stop action failure 现在只显示固定低敏 `Action failed`。
- Auth status initial failure 不再写 raw exception 到 browser console，仍显示现有 `Unable to reach the server` error state。
- `frontend/src` 已无 `console.log` / `console.warn` / `console.debug` / `console.error` 调用。

验证：

```bash
npm --prefix frontend test -- --run src/components/LaunchButton.test.tsx
# RED then GREEN；旧实现把 launch-token-super-secret/token=/data/profile-secret 渲染到页面并写入 console，最终 1 passed

npm --prefix frontend test -- --run src/App.test.tsx
# RED then GREEN；旧实现 console.warn 包含 auth-token-super-secret/token=/data/auth-secret，最终 30 passed

rg -n "console\\.(log|warn|debug|error)\\(" frontend/src
# no matches

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 43.73s

npm --prefix frontend test -- --run
# Test Files 17 passed；Tests 224 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.67s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 auth state machine、login flow、profile launch/stop API calls、VNC viewer、Automation API、Proxy Manager、profile launch backend、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 frontend UI/console raw-error release-evidence 边界。

## 2026-06-03 Frontend profile hook error release-evidence guardrail

背景：

- Release smoke 可能直接截图或记录 profile operations error state。
- `useProfiles` 的 API/transport failure reason 会进入页面可见 error state。
- 旧实现多个路径仍信任 raw `Error.message`，可显示 token/header/path 风格文本。

已覆盖：

- `useProfiles` 新增 public error sanitizer，统一过滤 URL credentials、Authorization/Bearer、token/password/secret/cookie assignment 和本地 `/data`/`/tmp`/`/home` path。
- Profile fetch、export、create、update、delete、launch、stop 以及 bulk launch/stop/tag/delete failure reason 统一使用该边界。
- 普通低敏错误摘要保持可见，便于 release triage。

验证：

```bash
npm --prefix frontend test -- --run src/hooks/useProfiles.test.ts
# RED then GREEN；旧实现 fetch error state 包含 profile-fetch-token-secret/token=/Authorization/Bearer//data/profiles，最终 28 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 40.87s

npm --prefix frontend test -- --run
# Test Files 17 passed；Tests 225 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.51s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 API request order、profile state mutations、bulk concurrency、health cache refresh、VNC viewer、Automation API、Proxy Manager、profile launch backend、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 frontend profile hook error release-evidence 边界。

## 2026-06-03 Frontend auth and automation load error release-evidence guardrail

背景：

- Release smoke 可能截图登录失败状态和 Automation task viewer load failure alert。
- `LoginPage` 和 `AutomationTaskLogViewer` 原先会把 raw API/transport `Error.message` 渲染到页面。
- Raw message 可能包含 token/header/path/internal URL 风格文本。

已覆盖：

- 登录失败固定显示 `Login failed`。
- Automation task list 加载失败固定显示 `Unable to load automation tasks`。
- 正常 login submit、task refresh、task table、status filter、search filter 和 detail drawer redaction 行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/LoginPage.test.tsx
# RED then GREEN；旧实现登录失败显示 login-token-super-secret/token=/Authorization/Bearer//data/auth，最终 1 passed

npm --prefix frontend test -- --run src/components/AutomationTaskLogViewer.test.tsx
# RED then GREEN；旧实现任务加载失败 alert 显示 automation-load-token-secret/token=/Authorization/Bearer//data/tasks，最终 7 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 40.63s

npm --prefix frontend test -- --run
# Test Files 18 passed；Tests 227 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.73s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 auth token submit flow、login success callback、automation task list request shape、task filtering、task detail redaction、VNC viewer、Automation API backend、Proxy Manager、profile launch backend、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 frontend auth/task-load error release-evidence 边界。

## 2026-06-03 Frontend import/proxy/health error release-evidence guardrail

背景：

- Release smoke 可能截图 Proxy Manager、Profile CSV import dialog、profile table/list health warning summary。
- 旧实现多处仅隐藏 URL userinfo，仍可显示 raw `Authorization`、`Bearer`、`token=` 和 `/data` path 风格错误文本。

已覆盖：

- 新增共享 frontend public error helper，并迁移 `useProfiles` 复用该边界。
- Proxy Manager 的 load/bulk check/assign/random assign/provider preset/CSV create failure 可见错误统一过滤。
- Profile CSV preview/import alert 和 row validation error 统一过滤。
- Health warning summary 统一过滤。
- 普通低敏错误摘要仍保留，便于 release triage。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# RED then GREEN；旧实现 bulk/load/import failure 显示 token/header/path，最终 23 passed

npm --prefix frontend test -- --run src/components/ProfileCsvPreviewDialog.test.tsx
# RED then GREEN；旧实现 preview/import/row validation error 显示 token/header/path，最终 3 passed

npm --prefix frontend test -- --run src/components/HealthBadge.test.tsx
# RED then GREEN；旧实现 health warning summary 显示 token/header/path，最终 6 passed

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx src/components/ProfileCsvPreviewDialog.test.tsx src/components/HealthBadge.test.tsx src/hooks/useProfiles.test.ts
# Test Files 4 passed；Tests 60 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 41.85s

npm --prefix frontend test -- --run
# Test Files 19 passed；Tests 232 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.53s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 proxy CRUD/API request payload、provider preset validation rules、CSV parser semantics、profile import backend contract、health status ranking、VNC viewer、Automation API backend、profile launch backend、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 frontend import/proxy/health error release-evidence 边界。

## 2026-06-03 Audit metadata key release-evidence guardrail

背景：

- Release evidence 会读取 audit events。
- Audit metadata value 已有清洗，但历史/手工污染 metadata key 也可能携带 `Authorization: Bearer ...`、`token=...` 或 `/data/...` 文本。

已覆盖：

- 数据库 audit sanitizer 现在会丢弃 URL/path/header/token 风格 metadata key。
- 新写入 audit metadata 和读取历史 audit metadata 都经过同一递归边界。
- 普通低敏 metadata key/value 保持可见，便于 release triage。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields -q
# RED then GREEN；旧实现保留 Authorization/Bearer/token=/data 风格 metadata key

.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields backend/tests/test_session_broker.py::test_audit_event_reader_sanitizes_historical_top_level_fields_and_metadata -q
# 2 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 46 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 39.48s

npm --prefix frontend test -- --run
# Test Files 19 passed；Tests 232 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 6.00s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 audit event schema、public event_type/actor/runtime/profile id rules、runtime session behavior、viewer behavior、Automation API backend、profile launch backend、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 audit metadata key release-evidence 边界。

## 2026-06-03 Audit metadata local-path value release-evidence guardrail

背景：

- Release evidence 会读取 audit events。
- Audit metadata value 之前会清理 token/header/URL credentials，但仍可能保留 `/data`、`/tmp`、`/home` 本地路径。

已覆盖：

- 数据库 audit sanitizer 现在会把本地路径 value 替换为 `[redacted-path]`。
- 嵌套 dict/list metadata 也走同一递归边界。
- 普通低敏上下文仍保留，便于 release triage。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields -q
# RED then GREEN；旧实现保留 /data/profiles、/tmp/xvnc、/home/jeff 风格 metadata value

.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields backend/tests/test_session_broker.py::test_audit_event_reader_sanitizes_historical_top_level_fields_and_metadata -q
# 2 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 46 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 40.82s

npm --prefix frontend test -- --run
# Test Files 19 passed；Tests 232 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.72s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 audit event schema、public event_type/actor/runtime/profile id rules、runtime session behavior、viewer behavior、Automation API backend、profile launch backend、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 audit metadata local-path value release-evidence 边界。

## 2026-06-03 Audit metadata Windows path value release-evidence guardrail

背景：

- Release evidence 会读取 audit events。
- Audit metadata value 已经清理 URL credentials、Authorization/Bearer、token/password/secret/cookie assignments 和 `/data`、`/tmp`、`/home` 本地路径。
- Windows profile/runtime 风格绝对路径仍可能以 `C:\Users\...` 或 `D:/profiles/...` 形态出现在历史/手工污染 metadata value 中。

已覆盖：

- 数据库 audit sanitizer 现在会把 Windows drive 绝对路径 value 替换为 `[redacted-path]`。
- 嵌套 dict/list metadata 也走同一递归边界。
- `http://example.test:8080` 这类低敏 proxy URL redaction 结果保持可见，不会被 Windows drive regex 误伤。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields -q
# RED then GREEN；旧实现保留 C:\Users\... 和 D:/profiles/... metadata value

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 46 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 37.11s

npm --prefix frontend test -- --run
# Test Files 19 passed；Tests 232 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.04s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 audit event schema、public event_type/actor/runtime/profile id rules、runtime session behavior、viewer behavior、Automation API backend、profile launch backend、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 audit metadata Windows path value release-evidence 边界。

## 2026-06-03 Frontend visible error Windows path release-evidence guardrail

背景：

- Release smoke 会查看前端可见错误和警告区域。
- 共享 `publicErrorText()` 已清理 URL credentials、Authorization/Bearer、token/password/secret/cookie assignments 和 `/data`、`/tmp`、`/home` 路径。
- Windows drive path 仍可能通过 API/transport/manual error text 进入 Proxy Manager、Profile CSV import、HealthBadge 或 profile hook 可见错误。

已覆盖：

- 前端共享 public error helper 现在会把 `C:\Users\...` 和 `D:/profiles/...` 替换为 `[redacted-path]`。
- 新增 direct helper regression test，避免只依赖组件侧间接覆盖。
- `http://example.test:8080/check` 这类低敏 URL redaction 结果保持可见，不会被 Windows drive regex 误伤。

验证：

```bash
npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts
# RED then GREEN；旧实现保留 C:\Users\... 和 D:/profiles/... visible error text

npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts src/components/ProfileCsvPreviewDialog.test.tsx src/components/ProxyManagerPage.test.tsx src/components/HealthBadge.test.tsx src/hooks/useProfiles.test.ts
# Test Files 5 passed；Tests 61 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 39.28s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 233 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.13s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 API response schema、backend audit sanitizer、profile/proxy business rules、VNC viewer、Automation API backend、profile launch backend、stealth prefs、seed、WebGL、WebRTC、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 frontend visible error Windows path release-evidence 边界。

## 2026-06-03 Audit metadata IPv4 value release-evidence guardrail

背景：

- Release evidence 会读取 audit events。
- Audit metadata value 已经清理 URL credentials、Authorization/Bearer、token/password/secret/cookie assignments、本地路径和 Windows drive path。
- IPv4 literal 仍可能通过 GeoIP、proxy、WebRTC 或历史/手工污染 metadata value 进入 release evidence。

已覆盖：

- 数据库 audit sanitizer 现在会把 IPv4 literal value 替换为 `[redacted-ip]`。
- 嵌套 dict/list metadata 也走同一递归边界。
- IPv4 候选值经过 `ipaddress.IPv4Address` 校验，避免误伤非 IP 数字片段。
- 域名型低敏 proxy URL redaction 结果保持可见。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields -q
# RED then GREEN；旧实现保留 203.0.113.45、198.51.100.20 和 192.0.2.44 metadata value

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 46 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 38.16s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 233 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.13s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 audit event schema、public event_type/actor/runtime/profile id rules、runtime session behavior、viewer behavior、Automation API backend、profile launch backend、GeoIP lookup、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 audit metadata IPv4 value release-evidence 边界。

## 2026-06-03 Audit metadata IPv6 value release-evidence guardrail

背景：

- Release evidence 会读取 audit events。
- Audit metadata value 已经清理 URL credentials、Authorization/Bearer、token/password/secret/cookie assignments、本地路径、Windows drive path 和 IPv4 literal。
- IPv6 literal 仍可能通过 WebRTC、GeoIP、proxy 或历史/手工污染 metadata value 进入 release evidence。

已覆盖：

- 数据库 audit sanitizer 现在会把裸 IPv6 literal 和 bracketed IPv6 literal 替换为 `[redacted-ip]`。
- 嵌套 dict/list metadata 也走同一递归边界。
- IPv4/IPv6 候选值统一经过 `ipaddress.ip_address()` 校验。
- Bracketed endpoint 会保留低敏端口上下文，例如 `[2001:db8::46]:443` 变为 `[redacted-ip]:443`。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields -q
# RED then GREEN；旧实现保留 2001:db8::45、2001:db8::46 和 2001:db8::44 metadata value

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 46 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 37.25s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 233 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.17s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 audit event schema、public event_type/actor/runtime/profile id rules、runtime session behavior、viewer behavior、Automation API backend、profile launch backend、GeoIP lookup、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 audit metadata IPv6 value release-evidence 边界。

## 2026-06-04 Audit metadata IP key release-evidence guardrail

背景：

- Release evidence 会读取 audit events。
- Audit metadata value 已经清理 IPv4/IPv6 literal，但 key 名本身仍可能携带 IP literal。
- 历史/手工污染 metadata key 如果包含 `203.0.113.99`、`client_2001:db8::99` 或 `[2001:db8::98]`，此前会原样进入 release evidence。

已覆盖：

- 数据库 audit sanitizer 现在会丢弃 IPv4/IPv6 literal 风格 metadata key。
- 嵌套 dict metadata key 也走同一递归边界。
- 普通低敏 key/value 保持可见。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields -q
# RED then GREEN；旧实现保留 IPv4/IPv6 metadata key 及其 value

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 46 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 39.21s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 233 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.15s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 audit event schema、public event_type/actor/runtime/profile id rules、runtime session behavior、viewer behavior、Automation API backend、profile launch backend、GeoIP lookup、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 audit metadata IP key release-evidence 边界。

## 2026-06-04 Frontend public error IP literal release-evidence guardrail

背景：

- Release evidence 会包含前端错误态、warning summary 和失败提示。
- 共享前端错误 helper 已清理 URL credentials、Authorization/Bearer、token/password/secret/cookie assignment、本地路径和 Windows drive path。
- 裸 IPv4/IPv6 literal 仍可能来自 API/transport/manual error text，并被渲染到 UI。

已覆盖：

- `publicErrorText()` 现在 redacts IPv4 literal、裸 IPv6 literal 和 bracketed IPv6 literal。
- Bracketed IPv6 endpoint 保留低敏端口上下文，例如 `[2001:db8::46]:443` 变为 `[redacted-ip]:443`。
- 普通域名 URL host/port 仍保持可读，便于 triage。
- Profile/Proxy table 的正常业务 IP 字段展示不走这条错误 helper，行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts
# RED then GREEN；旧实现保留 203.0.113.45、198.51.100.20、2001:db8::45 和 [2001:db8::46]

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 38.95s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 234 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.73s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 audit event schema、backend API response schemas、public event_type/actor/runtime/profile id rules、runtime session behavior、viewer behavior、Automation API backend、profile launch backend、GeoIP lookup、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 frontend public error IP literal release-evidence 边界。

## 2026-06-04 Proxy Manager persisted text release-evidence guardrail

背景：

- Release evidence 会包含 Proxy Manager 表格、tooltip 和搜索过滤结果。
- Proxy Manager 操作失败提示已走公共错误边界，但 persisted `proxy.notes` 和 `proxy.last_check_error` 仍只清 URL credentials。
- 历史/手工污染 proxy row 可能通过这些字段显示 Authorization/Bearer、token=、本地路径或 IP literal。

已覆盖：

- Proxy Manager 表格中的 `notes` 和 `last_check_error` 现在使用 `publicErrorText()`。
- 本地搜索文本对这两个字段使用同一脱敏后的内容。
- URL host/port 仍可读；credential/header/token/path/IP literal 不再进入可见 evidence。
- 正常 `last_check_ip` 业务字段展示、proxy check backend 和 assignment flows 不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# RED then GREEN；旧实现保留 Authorization/Bearer、token=、/data path、IPv4 和 IPv6

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 40.27s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 234 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.52s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 backend API response schemas、proxy CRUD/check backend、profile assignment/random assignment、GeoIP lookup、audit event schema、runtime session behavior、viewer behavior、Automation API backend、profile launch backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 proxy 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy Manager persisted text release-evidence 边界。

## 2026-06-04 Automation task error UI release-evidence guardrail

背景：

- Release evidence 会包含 Automation task table 和 task detail drawer。
- 后端 response 已有 task error redaction，但前端此前直接渲染 `task.error`。
- 历史/手工污染 task row 或异常 response 可能把 Authorization/Bearer、token=、本地路径或 IP literal 带到 UI。

已覆盖：

- Automation Task Log Viewer 的 table error column 使用 `publicErrorText()`。
- Task detail drawer 的 task error alert 使用同一公共错误边界。
- 低敏错误摘要保留；header/token/path/IP literal 不再进入可见 evidence。
- Step/result summary、状态筛选、task/profile id 搜索、readonly 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/AutomationTaskLogViewer.test.tsx
# RED then GREEN；旧实现保留 Authorization/Bearer、token=、/data|/tmp path、IPv4 和 IPv6 task.error

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 39.34s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 234 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.01s

git diff --check
# passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 backend API response schemas、automation task persistence/worker execution、task lifecycle statuses、profile launch backend、proxy、GeoIP lookup、runtime session behavior、viewer behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation task error UI release-evidence 边界。

## 2026-06-04 Automation task status UI release-evidence guardrail

背景：

- Release evidence 会包含 Automation task table、状态统计、状态筛选和 task detail drawer。
- 后端 status 聚合已经有公开状态边界，但前端此前仍直接使用 `task.status`。
- 历史/手工污染 task row 或异常 response 可能把 Authorization/Bearer、token= 这类文本带到 UI 状态位。

已覆盖：

- Automation Task Log Viewer 现在只渲染公开 task statuses：`queued`、`running`、`cancel_requested`、`cancelled`、`failed`、`succeeded`。
- 非公开状态统一显示为 `unknown`。
- 状态统计、table status pill、detail status 和本地状态 filter 使用同一公开状态边界。
- 污染状态不会进入 Failed filter 的结果集。
- Automation task error、step/result summary、task/profile id 搜索和 readonly 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/AutomationTaskLogViewer.test.tsx
# RED then GREEN；旧实现没有 unknown，且会保留 raw polluted status

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 40.49s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 235 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.23s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 backend API response schemas、automation task persistence/worker execution、task lifecycle statuses、profile launch backend、proxy、GeoIP lookup、runtime session behavior、viewer behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation task status UI release-evidence 边界。

## 2026-06-04 Automation task id UI release-evidence guardrail

背景：

- Release evidence 会包含 Automation task table、详情抽屉、details button accessible name 和本地搜索行为。
- 后端 task/profile id response 已有公开边界，但前端此前仍直接使用 `task.id` / `task.profile_id`。
- 历史/手工污染 task row 或异常 response 可能把 `token=`、Authorization/Bearer、本地路径或 IP literal 带到 UI id 位置。

已覆盖：

- Automation Task Log Viewer 现在对 task/profile id 使用公开 label 边界。
- 普通低敏 task/profile 标签保持可读；非公开 id 显示为 `unknown`。
- Table、detail drawer、details button `aria-label` 和本地搜索 corpus 使用同一公开 id label。
- 原始 id 仍保留给内部 selected task lookup，不改变 task row 打开详情行为。
- Status、error、step/result summary 和 readonly 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/AutomationTaskLogViewer.test.tsx
# RED then GREEN；旧实现找不到 unknown，说明 raw task/profile id 仍被使用

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 39.03s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 236 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.07s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 backend API response schemas、automation task persistence/worker execution、task lifecycle statuses、profile launch backend、proxy、GeoIP lookup、runtime session behavior、viewer behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation task id UI release-evidence 边界。

## 2026-06-04 Automation step/result summary UI release-evidence guardrail

背景：

- Release evidence 会包含 Automation task table 和详情抽屉里的 step/result summary。
- 前端此前对 summary label 只做字符清洗，污染值可能被拼成可见 token/header 词根。
- 后端已有 step/result 输出边界，但 release UI 不应信任异常响应或历史/手工污染 row。

已覆盖：

- Automation Task Log Viewer 现在对 step/result summary label 使用公开 label allowlist。
- 正常低敏摘要保持可读，例如 `open_url`、`page 0`、`wait_until load`、`0 open_url succeeded`。
- 非公开 `type`、`page_ref`、`wait_until`、`state`、result `type`、result `status` 显示为 `unknown`。
- Table 和 detail drawer 使用同一边界。
- Status、error、task/profile id、readonly 行为和任务导航不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/AutomationTaskLogViewer.test.tsx
# RED then GREEN；旧实现没有 unknown，污染 summary label 仍被显示

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 40.14s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 237 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.23s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 backend API response schemas、automation task persistence/worker execution、task lifecycle statuses、profile launch backend、proxy、GeoIP lookup、runtime session behavior、viewer behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation step/result summary UI release-evidence 边界。

## 2026-06-04 System diagnostics map/list label release-evidence guardrail

背景：

- Release evidence 会包含 System diagnostics 页面和 accessible snapshot。
- 前端此前直接渲染 diagnostics map key/list value；异常 response 或测试桩可能把 `token=`、Authorization/Bearer、URL 或 IP literal 带到 launch failure stages、runtime session statuses、task status counts 或 stealth categories。
- 后端 diagnostics 已有低敏聚合边界，但 release UI 不应信任异常字段名。

已覆盖：

- System diagnostics 现在对 count map key 和 category list value 使用公开 diagnostics label 边界。
- 非公开 label 统一折叠为 `unknown`，并且 count map 会把多个污染 key 聚合到同一个 unknown 计数。
- 普通低敏 label 继续可读，例如 `allocate_vnc`、`active`、`queued`、`canvas`。
- Runtime overview、storage、worker 设置、版本字段和 refresh/error 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/SystemDiagnosticsPage.test.tsx
# RED then GREEN；旧实现把 Authorization/Bearer、token=、URL 和 IP literal 原样显示在 diagnostics label

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 39.55s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 238 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.03s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 backend API response schemas、diagnostics count-query backend、automation task persistence/worker execution、runtime session behavior、viewer behavior、profile launch backend、proxy、GeoIP lookup、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 System diagnostics map/list label release-evidence 边界。

## 2026-06-04 Profile runtime status UI release-evidence guardrail

背景：

- Release evidence 会包含 Profile operations table、Profile summary Inspector、StatusIndicator accessible label 和 Proxy Manager assignment dialog。
- 前端此前直接信任 `profile.status`，异常 response 或历史/手工污染 row 可能把 `Authorization`、`Bearer`、`token=` 等值带入 runtime badge、`aria-label` 或 assignment dialog 搜索语料。
- 后端正常 profile status 仍是 `running` / `stopped`；本轮只补 frontend 公开值边界。

已覆盖：

- `publicRuntimeStatus()` 把非 `running` / `stopped` 的值折叠为 `unknown`。
- Profile table 桌面行、窄屏 card、Profile summary runtime badge 和 StatusIndicator `aria-label` 使用公开 status。
- Proxy Manager assignment dialog 的 runtime badge 和本地 assignment search text 使用公开 status。
- 正常 `running` / `stopped` UI 行为、bulk action 选择、launch/stop、profile selection 和 proxy assignment API 不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx
# RED then GREEN；旧实现把污染 runtime status 渲染到 badge 和 Runtime aria-label

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "folds non-public assignment profile runtime statuses"
# RED then GREEN；旧实现把污染 runtime status 放入 assignment search text

npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProxyManagerPage.test.tsx src/components/StatusIndicator.test.tsx
# Test Files 3 passed；Tests 65 passed

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 41.47s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 241 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.00s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 backend API response schemas、profile lifecycle、launch/stop、bulk launch/stop、Proxy Manager assignment API、runtime session behavior、viewer behavior、Automation API backend、GeoIP lookup、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 profile runtime status UI/search release-evidence 边界。

## 2026-06-04 Profile viewer handle release-evidence guardrail

背景：

- Release evidence 可能包含 ProfileViewer environment strip 的 visible text 和 DOM title 属性。
- 前端此前对 profile/business session handle 的 visible text 做短化，但 title 保留完整 `profileId` / `externalSessionId`。
- 异常 runtime viewer payload 或历史/手工污染数据可能把 Authorization/Bearer、`token=`、`viewer_token`、URL/path/query 等内容带入这些 handle。

已覆盖：

- ProfileViewer environment strip 现在对 profile handle 和 business session handle 使用公开值边界。
- 非公开 handle 显示为 `unknown`，且 title 同样是 `unknown`。
- 正常低敏 handle 继续短显示，例如 `profile-...7890` 和 `pm-remot...7890`；title 也使用短 handle，不再保存完整 id。
- noVNC 连接、runtime viewer URL 使用、clipboard sync、Automation endpoint copy 和 disconnect/error redaction 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileViewer.test.tsx
# RED then GREEN；旧实现把完整 id 放入 title，并把污染 id 的 secret 尾部显示成短 handle

.venv/bin/python -m pytest backend/tests -q
# 647 passed in 41.34s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 242 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.02s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理。
- 不改变 backend API response schemas、runtime session/viewer token schema、VNC websocket path、noVNC connection、profile lifecycle、Automation API backend、GeoIP lookup、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 ProfileViewer handle title/visible release-evidence 边界。

## 2026-06-04 Health check audit metadata release-evidence guardrail

背景：

- Release regression 会读取 `profile.health_checked` audit metadata 作为健康检查、GeoIP/proxy lookup 和运行态证据。
- 旧 metadata 生成层直接使用 `lookup_result`、`health.runtime.status`、`health.geoip.source` 和 `health.geoip.country_code`。
- 如果异常 health 对象或未来集成把 URL/query/token/header/provider 文本塞进这些字段，release evidence 可能出现非公开内容。

已覆盖：

- Health audit lookup result 增加固定公开值边界：`skipped_invalid_proxy`、`failed`、`success`、`empty`，其他值显示为 `unknown`。
- Runtime status 增加固定公开值边界：只保留 `running` / `stopped`，其他值显示为 `unknown`。
- GeoIP source/country code 在写 metadata 前复用 GeoIP public-value filters；污染 provider/source 文本不会进入 audit evidence。
- 正常 health response、profile health check route、GeoIP 持久化和 lookup success/failure/empty/invalid-proxy 行为不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py -k "health_check_audit_metadata" -q
# RED then GREEN；旧实现把污染 runtime status 写入 health audit metadata

.venv/bin/python -m pytest backend/tests/test_health.py -q
# 25 passed

.venv/bin/python -m pytest backend/tests -q
# 648 passed in 39.45s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 242 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.18s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 不改变 backend API response schemas、health warning catalog、GeoIP lookup provider 行为、profile lifecycle、VNC/runtime viewer、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 health-check audit metadata release-evidence 边界。

## 2026-06-04 Health response runtime release-evidence guardrail

背景：

- Release regression 的 Profile health evidence 不只读取 audit metadata，也会读取 health API response。
- 旧 `compute_profile_health()` 直接把 `runtime_status.status`、`vnc_ws_port`、`automation_url` 写入 response。
- 如果异常 runtime object 或测试桩把 Authorization/Bearer、`token=`、外部 URL/query 或非法端口文本塞进这些字段，health response evidence 会出现非公开内容。

已覆盖：

- Health response `runtime.status` 只保留 `running` / `stopped`，其他值折叠为 `unknown`。
- `runtime.vnc_ws_port` 只保留合法 TCP 端口整数，污染字符串、bool 和越界值输出 `null`。
- `runtime.automation_url` 只保留内部 `/api/profiles/<id>/automation` path，并拒绝 URL/query/header/token/password/secret/cookie/viewer token 文本。
- Runtime missing warning 判断改为使用公开 runtime 值，避免污染 truthy 字符串掩盖 VNC/Automation 缺失。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_health.py -k "runtime_evidence" -q
# RED then GREEN；旧实现把污染 runtime status/port/automation_url 原样写入 health response

.venv/bin/python -m pytest backend/tests/test_health.py -q
# 26 passed

.venv/bin/python -m pytest backend/tests -q
# 649 passed in 39.21s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 242 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.20s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 不改变 backend health response schema、GeoIP lookup provider 行为、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 health response runtime release-evidence 边界。

## 2026-06-04 Health response profile id release-evidence guardrail

背景：

- Release regression 的 Profile health API evidence 会包含 `profile_id`。
- Health check audit/log 边界已经隐藏污染 profile id，但 response 仍直接来自 persisted `profile.id`。
- 历史/手工污染 row 可能把 Authorization/Bearer、`token=`、URL 或空格文本放入 profile id，导致 health response evidence 泄漏。

已覆盖：

- Health response `profile_id` 增加公开值边界。
- 正常短 ASCII id 保留；非字符串、空值、包含空格、URL/header/token/password/secret/cookie/viewer-token 文本的 id 折叠为 `unknown`。
- 既有 health check audit/log profile id redaction 继续生效；本轮补齐 response 层。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_health.py -k "persisted_profile_id" -q
# RED then GREEN；旧实现把污染 profile id 写入 health response

.venv/bin/python -m pytest backend/tests/test_health.py -q
# 26 passed

.venv/bin/python -m pytest backend/tests -q
# 649 passed in 38.88s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 242 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.06s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 不改变 backend health response schema、GeoIP lookup provider 行为、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 health response profile id release-evidence 边界。

## 2026-06-04 Profile/status runtime port and display release-evidence guardrail

背景：

- Release regression 会读取 profile list/detail 和 profile status API evidence。
- 旧 response 装配直接信任 `browser_mgr.get_status()` 的 `vnc_ws_port`，profile status response 也直接信任 display。
- 异常 running object 或测试桩可能把 Authorization/Bearer、`token=` 等文本放入 port/display，造成 response validation error 或 release evidence 泄漏。

已覆盖：

- Profile list/detail/create/import/update response 的 `vnc_ws_port` 统一走公开端口边界，只保留 1..65535 的整数。
- Profile status response 的 `vnc_ws_port` 使用同一边界，异常值输出 `null`。
- Profile status response 的 `display` 只保留 `:<digits>` 形态，异常值输出 `null`。
- 正常 running/stopped status、内部 automation URL 生成、CDP URL 隐藏和 profile lifecycle 行为不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py -k "runtime_port_and_display" -q
# RED then GREEN；旧实现对污染 vnc_ws_port 触发 ProfileStatusResponse validation error

.venv/bin/python -m pytest backend/tests/test_api.py -q
# 258 passed

.venv/bin/python -m pytest backend/tests -q
# 650 passed in 40.90s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 242 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 4.95s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 不改变 backend API response schema、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 profile/status runtime port/display release-evidence 边界。

## 2026-06-04 Diagnostics active runtime display/port release-evidence guardrail

背景：

- Release diagnostics 会记录 runtime active displays 和 active VNC WebSocket ports。
- 旧实现直接对 running profile 的 raw `display` / `ws_port` 排序并写入 response。
- 异常 running object 或测试桩中的 token/header 风格字符串会导致 diagnostics 500，或在类型允许前污染 release evidence。

已覆盖：

- `active_displays` 只保留公开 display 值并输出整数 display。
- `active_vnc_ws_ports` 只保留公开 TCP port 整数。
- 污染 running object 仍计入 `counts.running`，但不会进入 display/port evidence list。
- 正常 launch failure summary、Firefox identity、stealth category、runtime session 和 automation worker diagnostics 行为不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py -k "active_runtime_ports_and_displays" -q
# RED then GREEN；旧实现对 mixed raw display 排序触发 TypeError

.venv/bin/python -m pytest backend/tests/test_api.py -k "diagnostics" -q
# 4 passed, 255 deselected

.venv/bin/python -m pytest backend/tests/test_api.py -q
# 259 passed

.venv/bin/python -m pytest backend/tests -q
# 651 passed in 38.89s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 242 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.12s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 不改变 backend API response schema、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 diagnostics active runtime display/port release-evidence 边界。

## 2026-06-04 ProxyResponse city/asn release-evidence guardrail

背景：

- Proxy Manager release evidence 会读取 proxy list/detail，并把 `city` / `asn` 展示、tooltip 和本地搜索。
- `provider`、`country_code`、`last_check_*` 已有公开值边界，但 `city` / `asn` 仍可能回显历史/手工污染文本。
- 这类污染不是底层 fingerprint 检测问题，属于 Manager 可控的 API/UI evidence 边界。

已覆盖：

- proxy detail/list response 的 `city` 只保留短公开地名标签；URL/query/header/token 风格文本输出 `null`。
- proxy detail/list response 的 `asn` 只保留 `AS` + digits，污染文本输出 `null`。
- 正常 Proxy CRUD 响应仍保留 `Tokyo`、`AS64501`，并继续隐藏 proxy URL credentials。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -k "location_labels or proxy_crud_api" -q
# RED then GREEN；旧实现把污染 city 原样写入 response

.venv/bin/python -m pytest backend/tests/test_proxies.py -q
# 42 passed

.venv/bin/python -m pytest backend/tests -q
# 652 passed in 40.75s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 242 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.32s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 不改变 backend request schema、proxy URL credential redaction、provider/country filters、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 ProxyResponse `city` / `asn` release-evidence 边界。

## 2026-06-04 Provider preset UI text release-evidence guardrail

背景：

- Proxy Manager provider preset 管理弹窗属于 release smoke 的可见 UI evidence。
- 旧卡片直接渲染 persisted preset `name` / `notes`，并把 name 放入 title 与 edit/delete aria-label。
- 历史/手工污染 preset 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入可见 evidence。

已覆盖：

- Provider preset 卡片名称、title、edit/delete aria-label、备注和备注 title 统一走前端 public error boundary。
- Save/Delete notice 也使用公开展示名，避免异常 API response name 进入 toast/notice。
- 正常 provider preset 创建、编辑、删除和普通低敏名称/备注显示保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts persisted provider preset name"
# RED then GREEN；旧实现把污染 name/notes 原样写入 rendered evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 25 passed

.venv/bin/python -m pytest backend/tests -q
# 652 passed in 41.26s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 243 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.46s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 不改变 backend request/response schema、provider preset persistence、CSV import preset matching、proxy URL credential redaction、provider/country filters、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 provider preset UI text release-evidence 边界。

## 2026-06-04 Proxy asset name UI/search release-evidence guardrail

背景：

- Proxy Manager proxy asset table 和 assign dialog 属于 release smoke 可见 UI evidence。
- 旧实现直接渲染 persisted proxy asset `name`，并把 name 放入 title、checkbox aria-label 和本地搜索文本。
- 历史/手工污染 proxy asset name 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入可见 evidence 或 searchable evidence。

已覆盖：

- Proxy asset table name、title、checkbox aria-label 和 assign dialog name/title 统一走前端 public error boundary。
- Proxy asset 本地搜索索引使用公开展示名；secret marker 不再匹配该 row，正常低敏名称仍可匹配。
- 正常 proxy table、filter、bulk selection、assign dialog 和 proxy URL credential redaction 行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts persisted proxy asset names"
# RED then GREEN；旧实现把污染 proxy name 原样写入 rendered/search evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 26 passed

.venv/bin/python -m pytest backend/tests -q
# 652 passed in 40.26s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 244 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.20s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 不改变 backend request/response schema、proxy asset persistence、proxy URL credential redaction、provider/country filters、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 proxy asset name UI/search release-evidence 边界。

## 2026-06-04 Assignment profile name UI/search release-evidence guardrail

背景：

- Proxy Manager assign-to-profiles 弹窗属于 release smoke 可见 UI evidence。
- 旧实现直接渲染 persisted profile `name`，并把 name 放入 title、checkbox aria-label 和本地搜索文本。
- 历史/手工污染 assignment profile name 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入可见 evidence 或 searchable evidence。

已覆盖：

- Assignment profile row name、title 和 checkbox aria-label 统一走前端 public error boundary。
- Assignment profile 本地搜索索引使用公开展示名；secret marker 不再匹配该 row，正常低敏名称仍可匹配。
- 正常 profile selection、assignment dialog no-match state、runtime status badge 和 proxy URL credential redaction 行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts assignment profile names"
# RED then GREEN；旧实现把污染 profile name 原样写入 rendered/search evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 27 passed

.venv/bin/python -m pytest backend/tests -q
# 652 passed in 42.35s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 245 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.10s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、profile persistence、proxy assignment backend、proxy URL credential redaction、provider/country filters、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 assignment profile name UI/search release-evidence 边界。

## 2026-06-04 Profile operations name UI/search release-evidence guardrail

背景：

- 主 Profile operations table/card、left rail 和 summary inspector 属于 release smoke 的核心可见 UI evidence。
- 旧实现直接渲染 persisted profile `name`，并把 name 放入 table/card title、select/preview/open aria-label，以及共享 profile search。
- 历史/手工污染 profile name 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入可见 evidence 或 searchable evidence。

已覆盖：

- Profile operations table/card visible name、title、select/preview/open aria-label 统一使用共享 public profile name。
- Profile summary inspector 和 left rail visible profile name/open label 使用同一公开边界。
- `filterAndSortProfiles()` 的 search 和 sort tie-breaker 使用公开 profile name；secret marker 不再匹配该 row，正常低敏名称仍可匹配。
- Profile edit form 的原始输入值保持不变，避免把用户编辑数据语义误改成展示 redaction。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx -t "redacts persisted profile names"
npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx -t "redacts persisted profile names"
npm --prefix frontend test -- --run src/components/ProfileList.test.tsx -t "redacts persisted profile names"
npm --prefix frontend test -- --run src/lib/filters.test.ts -t "uses public profile names"
# RED then GREEN；旧实现把污染 profile name 原样写入 rendered/search evidence

npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx
# 39 passed

npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx
# 4 passed

npm --prefix frontend test -- --run src/components/ProfileList.test.tsx
# 12 passed

npm --prefix frontend test -- --run src/lib/filters.test.ts src/lib/errorDisplay.test.ts
# Test Files 2 passed；Tests 7 passed

.venv/bin/python -m pytest backend/tests -q
# 652 passed in 38.76s

npm --prefix frontend test -- --run
# Test Files 20 passed；Tests 249 passed

npm --prefix frontend run build
# tsc -b && vite build succeeded；built in 5.30s
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、profile persistence、profile create/edit payload、delete semantics、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、proxy assignment/random assignment 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile operations name UI/search release-evidence 边界。

## 2026-06-04 Profile form template/delete name UI release-evidence guardrail

背景：

- ProfileForm 的 template selector 和 delete confirmation 是 create/edit/delete 回归路径上的可见 release evidence。
- 旧实现仍直接渲染 template `name` 和 delete subject，即使主 Profile operations 名称展示已经收敛到 public profile name。
- 历史/手工污染 template/profile name 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入可见 evidence。

已覆盖：

- Template option text 使用共享 public profile name boundary。
- Delete confirmation subject 使用共享 public profile name boundary。
- Profile Name 输入框继续保留原始值，避免把编辑数据本身误改为 redacted display text。
- 正常 template selection、form save payload、delete confirmation flow 和 cancel flow 保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileForm.test.tsx -t "redacts template and delete confirmation names"
# RED then GREEN；旧实现把污染 template name 原样写入 rendered evidence

npm --prefix frontend test -- --run src/components/ProfileForm.test.tsx
# 10 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、profile persistence、template application behavior、profile create/edit payload、delete semantics、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、proxy assignment/random assignment 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 ProfileForm template/delete name UI release-evidence 边界。

## 2026-06-04 CSV import provider preset selector UI release-evidence guardrail

背景：

- Proxy Manager CSV import dialog 是 proxy import / provider preset / proxy-country 回归路径上的可见 release evidence。
- 旧实现仍直接渲染 provider preset selector option 的 persisted `name`，即使 provider preset card/notice 已经收敛到 public label。
- 历史/手工污染 preset name 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入下拉选项 evidence。

已覆盖：

- CSV import provider preset option text 使用共享 provider preset public label boundary。
- 选择 preset 仍使用原始 preset id，因此正常 provider/country/tags 默认值应用、CSV preview 和 import payload 保持不变。
- 正常 provider preset 管理、CSV import dialog、proxy URL credential redaction 和 valid row import 行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts provider preset names in the CSV import selector"
# RED then GREEN；旧实现把污染 preset name 原样写入 CSV import selector option

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 28 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、proxy/provider preset persistence、CSV parsing、CSV import payload、proxy assignment/random assignment 行为、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 CSV import provider preset selector UI release-evidence 边界。

## 2026-06-04 Bulk profile feedback UI release-evidence guardrail

背景：

- Profile operations bulk action bar 的 health/export feedback 是批量回归路径上的可见 release evidence。
- 旧组件直接渲染调用方传入的 `feedback.message`，虽然当前 App 通常传固定计数摘要，但组件边界没有防御异常/历史 raw error text。
- 如果 bulk feedback 含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入 Profile operations evidence。

已覆盖：

- BulkActionBar feedback text 使用共享 public error text boundary。
- Warning/success role、aria-label、bulk health/export 操作入口和选择栏行为保持不变。
- 正常低敏计数反馈文案保持原样；空 redaction 结果回退为固定低敏文案。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx -t "redacts bulk operation feedback"
# RED then GREEN；旧实现把污染 feedback.message 原样写入 bulk feedback evidence

npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx
# 40 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、bulk action API semantics、profile health/export/tag/delete semantics、ProfileTable selection behavior、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 BulkActionBar feedback UI release-evidence 边界。

## 2026-06-04 Cookie export download filename release-evidence guardrail

背景：

- Cookie JSON/Netscape export 是 Profile operations 回归路径的一部分，导出动作会创建本地下载文件名。
- 旧实现把 raw `profile.id` 拼入 `anchor.download`；异常/历史 profile id 可能把 Authorization/Bearer、`token=`、本地路径或 IP 字面量写入 download metadata evidence。
- Cookie export 内容仍是用户明确导出的敏感数据，本轮只收 Manager 生成的下载文件名。

已覆盖：

- Cookie export download filename 使用 public filename id boundary，普通短 ASCII id 保留，非公开 id 回退 `unknown`。
- API 调用仍使用原始 profile id，保证运行中 profile cookie import/export 查找不变。
- JSON/Netscape 导入导出、explicit confirmation、summary counts 和固定错误文案保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileCookieManager.test.tsx -t "uses a public profile id"
# RED then GREEN；旧实现把污染 profile id 原样写入 cookie export download filename

npm --prefix frontend test -- --run src/components/ProfileCookieManager.test.tsx
# 7 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、cookie import/export payload、cookie document/text contents、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Cookie export download filename release-evidence 边界。

## 2026-06-04 Provider preset metadata UI release-evidence guardrail

背景：

- Proxy Manager provider preset 管理弹窗属于 proxy/proxy-country 回归路径上的可见 release evidence。
- 之前已覆盖 provider preset `name` / `notes` 和 CSV import selector 的 preset name，但 persisted `provider`、`country_code` 和 tag 文本仍直接进入 preset card summary、chip 文本和 tooltip。
- 历史/手工污染的 provider/country/tag 元数据如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入发布证据。

已覆盖：

- Provider preset card summary、provider/country/tag chips 和对应 `title` 属性使用共享 public error text boundary。
- 正常 provider/country/tag 低敏短值、preset name/notes、edit/delete、provider preset 管理弹窗和 CSV import selector 行为保持不变。
- 选择和编辑仍使用原始 preset id/raw form value，因此 provider preset persistence、CSV parsing/import payload、proxy assignment 和浏览器启动行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts persisted provider preset metadata"
# RED then GREEN；旧实现把污染 provider/country/tag 元数据写入 dialog text/title evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 29 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、provider preset persistence、provider preset edit form raw values、CSV parsing、CSV import payload、proxy assignment/random assignment 行为、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Provider preset metadata UI release-evidence 边界。

## 2026-06-04 CSV import selected preset summary release-evidence guardrail

背景：

- Proxy Manager CSV import dialog 在选择 provider preset 后，会展示 selected preset summary，属于 proxy/proxy-country 回归路径上的可见 release evidence。
- Provider preset 管理弹窗 metadata 已覆盖，但 CSV import summary 仍直接使用 selected preset 的 persisted `provider`、`country_code` 和 tag 文本。
- 历史/手工污染的 selected preset metadata 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入 import dialog 文本和 tooltip。

已覆盖：

- CSV import selected preset summary 对 provider/country/tag 使用共享 public error text boundary。
- 正常低敏 provider/country/tag 摘要、provider preset option name、CSV preview、preset 默认值合并和 valid row import 行为保持不变。
- 选择仍使用原始 preset id，导入仍使用原始 merged payload，因此 provider preset persistence、raw edit form value、CSV parsing/import payload、proxy assignment 和浏览器启动行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts selected provider preset metadata"
# RED then GREEN；旧实现把污染 selected preset metadata 写入 CSV import summary text/title evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 30 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、provider preset persistence、provider preset edit form raw values、CSV parsing、CSV import payload、proxy assignment/random assignment 行为、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 CSV import selected preset summary release-evidence 边界。

## 2026-06-04 Proxy CSV preview row metadata release-evidence guardrail

背景：

- Proxy Manager CSV import preview table 属于 proxy/proxy-country 回归路径上的可见 release evidence。
- 旧 preview row 已隐藏 proxy URL credentials，但 row `name`、`provider` 和 tags 仍直接显示用户粘贴 CSV 中的 raw metadata。
- 污染 CSV 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会在 import 前进入 preview table 文本和 tooltip。

已覆盖：

- Proxy CSV preview row name/provider/tags 和对应 `title` 属性使用共享 public error text boundary。
- Endpoint preview 继续使用现有 URL credential redaction。
- Import still submits the original parsed row data to `createProxy()`, so CSV parsing, provider preset default merge, valid/blocked row count, partial import behavior, and proxy persistence semantics remain unchanged.

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts proxy CSV preview row metadata"
# RED then GREEN；旧实现把污染 CSV row name/provider/tag 写入 preview table text/title evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 31 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、proxy/provider preset persistence、CSV parsing、CSV import payload、proxy assignment/random assignment 行为、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy CSV preview row metadata release-evidence 边界。

## 2026-06-04 Proxy asset metadata UI/search release-evidence guardrail

背景：

- Proxy Manager asset table 和本地 search/filter 是 proxy/proxy-country release smoke 的常用 evidence 面。
- 后端已经收敛 proxy city/asn/provider/country 等 response 边界，但前端仍直接显示和搜索异常 response、历史/手工污染 row 或测试桩中的 metadata。
- 污染 metadata 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入 table text/title、filter option text 或 search corpus。

已覆盖：

- Proxy table location、ASN、provider、tag chip、last-check location 和对应 title 属性使用共享 public error text boundary。
- Filter option visible labels 使用同一 public label；option values 保持 raw，因此 clean filter matching 和 random assignment request payload 语义不变。
- Local search corpus 使用 public metadata labels，raw token/path/IP marker 不再命中 search evidence；正常低敏 provider/country/tag 搜索保持可用。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts persisted proxy asset metadata"
# RED then GREEN；旧实现把污染 proxy metadata 写入 table text/title/search evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 32 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、proxy/provider preset persistence、CSV parsing、CSV import payload、filter values、random assignment payload、proxy assignment 行为、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy asset metadata UI/search release-evidence 边界。

## 2026-06-04 Profile tag label UI/filter release-evidence guardrail

背景：

- Profile table/list、CSV preview 和 filters 属于 profile operations release evidence 面。
- 旧 tag badge 和 tag filter option 会直接显示 raw persisted tag；异常/历史 profile tag 如果包含 Authorization/Bearer、`token=`、本地路径或 IP 字面量，会进入 UI text/title 或 filter option evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Profile tag badges 的可见文本和 tooltip 使用 public profile tag label boundary。
- Profile tag filter option visible label 使用同一 public label；option value 保持 raw，筛选匹配和 `onChange` payload 语义不变。
- Tag color tint、profile table/list/CSV preview 复用路径、正常低敏 tag 文案和 filter selection 行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx -t "redacts persisted profile tag labels"
# RED then GREEN；旧实现把污染 profile tag 写入 table text/title evidence

npm --prefix frontend test -- --run src/components/ProfileFilters.test.tsx -t "redacts tag option labels"
# RED then GREEN；旧实现把污染 profile tag 写入 filter option evidence

npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx src/components/ProfileFilters.test.tsx src/components/Badge.test.tsx src/components/ProfileList.test.tsx src/components/ProfileCsvPreviewDialog.test.tsx
# 5 files passed, 63 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、profile tag persistence、profile edit form raw values、filter option values、filter matching、bulk tag payload、CSV import payload、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile tag label UI/filter release-evidence 边界。

## 2026-06-04 Profile CSV preview textarea release-evidence guardrail

背景：

- Profile CSV import preview 是 profile import release evidence 面。
- 旧 preview flow 只把 pasted CSV 中的 URL credentials 脱敏后回填 textarea；Authorization/Bearer、`token=`、本地路径和 IP 字面量仍可能出现在可见 evidence。
- Import payload 必须继续使用 preview 前保存的 raw CSV，避免 UI-only 脱敏改变导入语义。

已覆盖：

- Preview CSV 成功后，textarea 可见 CSV 按行应用 public error text boundary。
- `Create valid profiles` 仍提交原始 pasted CSV，保留 profile import payload semantics。
- Preview/import errors、row validation errors 和 URL credential redaction 既有行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileCsvPreviewDialog.test.tsx -t "redacts preview textarea evidence"
# RED then GREEN；旧实现把污染 CSV metadata 留在 textarea evidence

npm --prefix frontend test -- --run src/components/ProfileCsvPreviewDialog.test.tsx
# 4 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw CSV import payload、profile persistence、profile tag persistence、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile CSV preview textarea release-evidence 边界。

## 2026-06-04 Profile CSV preview row metadata release-evidence guardrail

背景：

- Profile CSV import preview table 是 profile import release evidence 面。
- 旧 row rendering 直接渲染 preview response 中的 profile `name`、`template_id`、`platform`、`locale`、`timezone` 到 text/title；异常 response 或历史 row 可携带 Authorization/Bearer、`token=`、本地路径或 IP 字面量。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Preview row profile name、template id、platform、locale、timezone visible label 和 tooltip 统一应用 public error text boundary。
- 正常低敏 preview row、proxy credential redaction、tag badge redaction、row status 和 error rendering 保持不变。
- Raw CSV import payload、backend preview/import contract 和 profile persistence 语义保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileCsvPreviewDialog.test.tsx -t "redacts preview row profile metadata"
# RED then GREEN；旧实现把污染 preview row metadata 写入 table text/title evidence

npm --prefix frontend test -- --run src/components/ProfileCsvPreviewDialog.test.tsx
# 5 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw CSV import payload、profile persistence、profile template matching、profile tag persistence、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、GeoIP lookup provider 行为、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile CSV preview row metadata release-evidence 边界。

## 2026-06-04 Profile table GeoIP release-evidence guardrail

背景：

- Profile operations table/card 会显示 IP、country、timezone、locale，是 Manager release regression 的常用 evidence 面。
- 普通 GeoIP 值仍需要展示；但异常 response 或历史/手工污染 row 可能把 Authorization/Bearer、`token=`、本地路径或 credential URL 混入这些字段。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Profile table/card 的 IP、country、timezone、locale text/title 使用 public profile GeoIP label。
- 普通 standalone IP、country、timezone、locale 保持原样；污染值降到 public error text boundary。
- ProfileTable 普通 operations、GeoIP column/card layout、profile name/tag redaction 和 selection/open/preview 行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx -t "redacts persisted profile geoip labels"
# RED then GREEN；旧实现把污染 GeoIP 字段写入 table/card text/title evidence

npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts
# 3 passed

npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx
# 42 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、health check API、GeoIP lookup provider 行为、普通 GeoIP 值展示语义、profile persistence、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile table/card GeoIP release-evidence 边界。

## 2026-06-04 Profile summary/rail/filter GeoIP release-evidence guardrail

背景：

- Profile summary inspector、左侧 operations rail 和 Profile country filter options 都会显示或派生 GeoIP 字段，是 release regression 中容易进入截图/日志/文本 evidence 的 UI 面。
- 普通 GeoIP 值仍需要展示；但异常 response 或历史/手工污染 row 可能把 Authorization/Bearer、`token=`、本地路径、IP 字面量或 credential URL 混入 IP、country、timezone、locale。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Profile summary inspector 的 GeoIP text/title 使用 public profile GeoIP label。
- ProfileList rail 的 health GeoIP parts 使用同一 public profile GeoIP label。
- Profile country filter options 和 country filter matching 使用安全 country label；普通 `US`/`JP`/timezone/locale/IP 值保持原样。
- Backend health/GeoIP API、GeoIP lookup provider、profile persistence、Profile edit raw input 和 browser fingerprint 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx -t "redacts persisted geoip labels"
# RED then GREEN；旧实现把污染 Summary GeoIP 写入 text/title evidence

npm --prefix frontend test -- --run src/lib/filters.test.ts -t "redacts polluted geoip country options"
# RED then GREEN；旧实现把污染 country option 原样返回

npm --prefix frontend test -- --run src/components/ProfileList.test.tsx -t "redacts health geoip labels"
# RED then GREEN；旧实现把污染 rail/filter GeoIP 写入页面 evidence

npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx src/components/ProfileList.test.tsx src/lib/filters.test.ts src/lib/errorDisplay.test.ts src/components/ProfileTable.test.tsx
# 5 files passed, 69 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、health check API、GeoIP lookup provider 行为、普通 GeoIP 值展示语义、profile persistence、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile summary/rail/filter GeoIP release-evidence 边界。

## 2026-06-04 Profile summary device release-evidence guardrail

背景：

- Profile summary inspector 的 Device 区域显示 platform、screen、hardware concurrency 和 GPU renderer/vendor。
- 普通 device metadata 仍需要展示；但异常 response 或历史/手工污染 row 可能把 Authorization/Bearer、`token=`、本地路径或 IP 字面量混入这些字段。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Profile summary Device 区域的 platform、screen、cores、GPU text/title 使用 public error text boundary。
- 普通 `windows`、`1920 x 1080`、`8 cores`、`ANGLE NVIDIA` 等值保持原样。
- Profile edit raw input、backend API contract、profile persistence 和 browser fingerprint launch 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx -t "redacts persisted device labels"
# RED then GREEN；旧实现把污染 device metadata 写入 Summary text/title evidence

npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx src/lib/errorDisplay.test.ts
# 2 files passed, 9 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、profile edit raw input、profile persistence、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile summary Device release-evidence 边界。

## 2026-06-04 Profile summary runtime VNC port release-evidence guardrail

背景：

- Profile summary inspector 的 Runtime 区域显示 VNC port，是 release regression 中常见的 UI evidence。
- 正常端口仍需要展示为 `:6100`；但异常 response 或历史/手工污染 row 可能把 Authorization/Bearer、`token=`、本地路径或 IP 字面量混入 `vnc_ws_port`。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Profile summary Runtime VNC row 只展示合法 TCP port，非公开/污染值显示为 `-`。
- 正常 `6100` 端口展示语义保持 `:6100`。
- Automation availability、runtime status badge、VNC websocket path、profile launch backend 和 browser fingerprint 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx -t "folds non-public VNC ports"
# RED then GREEN；旧实现把污染 vnc_ws_port 写入 Summary text/title evidence

npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx src/lib/profileDisplay.test.ts src/lib/errorDisplay.test.ts
# 2 files passed, 10 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、VNC websocket path、profile launch backend、runtime session/viewer token schema、Automation API backend、profile persistence、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile summary Runtime VNC port release-evidence 边界。

## 2026-06-04 Proxy Manager assignment profile id release-evidence guardrail

背景：

- Proxy Manager assign-to-profiles dialog 会显示 profile id，并把 profile id 作为本地搜索字段，是 release regression 里容易被截图/文本采集的 evidence 面。
- 正常 assignment 仍需要原始 profile id 作为 selection key 和 API payload；但污染 id 不应进入 visible text、title 或 searchable evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Assignment row profile id visible text/title 使用 public id boundary。
- Authorization/Bearer/`token=`/path/IP-style profile id 显示为 `unknown`，且不能通过敏感 marker 搜索命中。
- `unknown` fallback 可搜索，便于定位不可公开 id 的 profile row。
- Raw profile id 继续用于 checkbox selection、selected id set、assign/random-assign API payload 和 backend persistence。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts assignment profile ids"
# RED then GREEN；旧实现把污染 profile id 写入 assignment dialog text/title/search evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 1 file passed, 33 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、profile persistence、proxy persistence、proxy assignment/random assignment payload、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy Manager assignment profile id release-evidence 边界。

## 2026-06-04 Profile operations id release-evidence guardrail

背景：

- Profile table desktop rows、mobile cards 和 Profile summary inspector 会显示 profile id 的短 handle，是 release regression 截图/文本 evidence 面。
- 正常 profile operations 仍需要原始 profile id 作为 selection、preview、open、health lookup 和 API payload key；但污染 id 不应进入 visible evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- ProfileTable desktop row 和 mobile card 短 id 显示使用 public profile id boundary。
- ProfileSummaryPanel header 短 id 显示使用同一 public profile id boundary。
- Authorization/Bearer/`token=`/path/IP-style profile id 显示为 `unknown`，且不进入 text/title/aria evidence。
- Raw profile id 继续用于 selection/open/preview callbacks、health map lookup、profile persistence 和 backend API payload。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx -t "redacts non-public profile ids"
# RED then GREEN；旧实现把污染 profile id 的前 8 个字符写入 Summary evidence

npm --prefix frontend test -- --run src/components/ProfileTable.test.tsx -t "redacts non-public profile ids"
# RED then GREEN；旧实现把污染 profile id 的前 8 个字符写入 table/card evidence

npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx src/components/ProfileTable.test.tsx src/lib/errorDisplay.test.ts src/lib/filters.test.ts
# 4 files passed, 60 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、profile persistence、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile operations id release-evidence 边界。

## 2026-06-04 Proxy Manager random assignment filter summary release-evidence guardrail

背景：

- Proxy Manager random assign dialog 会显示当前 country/provider/tag filters 的 summary pills，是 release regression 截图/文本 evidence 面。
- 正常 filter matching 和 random assignment API payload 仍需要原始 provider/tag；但污染 provider/tag 不应进入 visible text、title 或 aria evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Random assign dialog Provider/Tag summary 使用 public proxy metadata boundary。
- Authorization/Bearer/`token=`/path/IP-style provider/tag 片段不会进入 dialog text/title/aria evidence。
- Raw provider/tag 继续用于 filter option value、selected filter state、filter matching 和 `assignRandomProxyToProfiles` request payload。
- Country filter、selected profile ids、candidate count、assignment result contract 和 backend persistence 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts random assignment filter summary"
# RED then GREEN；旧实现把污染 provider/tag 写入 random assign dialog summary evidence
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、proxy/provider preset persistence、filter values、filter matching、random assignment payload、proxy assignment、GeoIP lookup、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy Manager random assignment filter summary release-evidence 边界。

## 2026-06-04 Proxy Manager assignment profile current proxy release-evidence guardrail

背景：

- Proxy Manager assign-to-profiles 和 random assign dialogs 的 profile rows 会展示当前 proxy，并支持按当前 proxy 搜索 profile。
- 正常 endpoint host/port 仍需要展示和搜索；但污染 profile.proxy 不应进入 visible text、title、aria 或 searchable evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Assignment profile row 当前 proxy 使用 public error-text boundary。
- URL credentials、Authorization/Bearer、`token=`、path 和 IP-style 当前 proxy 片段不会进入 dialog text/title/aria evidence。
- Search corpus 使用 public current-proxy label；敏感 marker 不命中，普通 endpoint host 仍可命中。
- Raw profile id、selected profile set、assign/random-assign request payloads、profile persistence 和 backend assignment contract 不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts assignment profile current proxy"
# RED then GREEN；旧实现把污染 profile.proxy 写入 assignment dialog summary/search evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx src/lib/errorDisplay.test.ts
# 2 files passed, 38 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、profile persistence、profile proxy raw value、proxy persistence、proxy assignment/random assignment payload、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy Manager assignment profile current proxy release-evidence 边界。

## 2026-06-04 Profile CSV preview proxy release-evidence guardrail

背景：

- Profile CSV import preview table 的 proxy 列会出现在 release regression 截图/文本 evidence 中。
- 正常 endpoint host/port 仍需要展示；但污染 preview row proxy 不应进入 visible text 或 title evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Profile CSV preview row proxy 使用 public preview label。
- URL credentials、Authorization/Bearer、`token=`、path 和 IP-style proxy 片段不会进入 table text/title evidence。
- Raw CSV 仍用于 `previewProfileImport` 和 `importProfiles`；preview textarea 脱敏和 import payload 保存继续分离。
- Row validation errors、profile metadata columns、tag rendering、backend preview/import contract 和 profile persistence 不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileCsvPreviewDialog.test.tsx -t "redacts preview row proxy evidence"
# RED then GREEN；旧实现把污染 row proxy 写入 Profile CSV preview table evidence

npm --prefix frontend test -- --run src/components/ProfileCsvPreviewDialog.test.tsx src/lib/errorDisplay.test.ts src/lib/profileDisplay.test.ts
# 2 files passed, 9 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw CSV import payload、profile persistence、profile proxy raw value、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile CSV preview proxy release-evidence 边界。

## 2026-06-04 Proxy CSV import textarea release-evidence guardrail

背景：

- Proxy Manager CSV import textarea 会在用户 paste 后立即显示 CSV，是 release regression 截图/文本 evidence 面。
- 正常 endpoint host/port 仍需要展示；但污染 CSV name/provider/tag/notes 不应进入 visible textarea evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Proxy CSV import textarea visible text 使用 public error-text boundary。
- URL credentials、Authorization/Bearer、`token=`、path 和 IP-style CSV 片段不会进入 textarea evidence。
- Raw CSV source 仍用于 parse/import；`createProxy` request payload 继续携带原始 name/url/provider 字段。
- Preview row metadata redaction、provider preset defaults、partial import failure rendering、proxy persistence 和 assignment behavior 不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts proxy CSV textarea evidence"
# RED then GREEN；旧实现把污染 CSV name/provider 写入 import textarea evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx src/lib/errorDisplay.test.ts src/lib/profileDisplay.test.ts
# 2 files passed, 39 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw CSV import payload、proxy/provider preset persistence、proxy assignment/random assignment payload、GeoIP lookup、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy CSV import textarea release-evidence 边界。

## 2026-06-04 Proxy asset endpoint URL release-evidence guardrail

背景：

- Proxy Manager asset table、CSV import preview row、assign dialog header 和本地搜索都会使用 proxy endpoint，是 release regression 截图/文本 evidence 面。
- 正常 endpoint scheme/host/port 仍需要展示和搜索；但污染 proxy URL 不应把 URL credentials、Authorization/Bearer、`token=`、path 或 IP-style 文本带入 visible/title/search evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Proxy asset table endpoint 使用 public endpoint label。
- Proxy CSV import preview row endpoint 使用同一 public endpoint label。
- Proxy assign dialog header endpoint 使用同一 public endpoint label。
- Search corpus 使用 public endpoint label；敏感 marker 不命中，普通 endpoint host 仍可命中。
- Raw proxy URL 继续用于 persistence、CSV parse/import、`createProxy` payload、assignment/random-assignment payload 和 backend API contract。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "redacts persisted proxy endpoint urls"
# RED then GREEN；旧实现把污染 proxy.url 写入 table/header/search evidence

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx src/lib/errorDisplay.test.ts src/lib/profileDisplay.test.ts
# 2 files passed, 40 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw proxy URL persistence、raw CSV import payload、proxy/provider preset persistence、proxy assignment/random assignment payload、GeoIP lookup、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy asset endpoint URL release-evidence 边界。

## 2026-06-04 Timestamp release-evidence guardrail

背景：

- Profile operations、Profile summary、Proxy Manager 和 Automation task viewer 会展示多类 timestamp，是 release regression 截图/文本 evidence 面。
- 正常 timestamp 仍需要格式化展示；但无效或污染 timestamp 不应把 Authorization/Bearer、`token=`、path 或 IP-style 文本带入 visible/title evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 evidence 边界。

已覆盖：

- Shared `formatTimestamp()` 对空值继续返回 `-`。
- 有效 timestamp 继续按原来的短日期时间格式显示。
- 无效/污染 timestamp 统一折叠为 `Invalid timestamp`。
- Profile table/card、Profile summary、Proxy Manager last-check time 和 Automation task viewer 共用这一低敏 fallback。

验证：

```bash
npm --prefix frontend test -- --run src/lib/profileDisplay.test.ts
# RED then GREEN；旧实现把污染 timestamp 原样返回

npm --prefix frontend test -- --run src/lib/profileDisplay.test.ts src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProxyManagerPage.test.tsx src/components/AutomationTaskLogViewer.test.tsx
# 5 files passed, 99 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、profile/proxy/task persistence、有效 timestamp 格式化、profile lifecycle、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 shared timestamp release-evidence 边界。

## 2026-06-04 Viewer Automation endpoint copy release-evidence guardrail

背景：

- VNC/ProfileViewer toolbar 的 Automation copy action 是 release regression 中常用的手工操作。
- 正常 `/api/profiles/{id}/automation` endpoint 仍需要复制；但污染 `automationUrl` 不应把 `viewer_token`、query、fragment 或 token-like profile id 写入剪贴板。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 viewer/evidence 边界。

已覆盖：

- Copy action 只写入同源 `/api/profiles/{public-profile-id}/automation`。
- Query string、fragment 和 token-like/path-like profile id 会被丢弃或折叠为 unavailable。
- Automation ready/unavailable button state 现在以 public copy endpoint 为准。
- runtime viewer token URL、noVNC connection、clipboard sync payload 和 Automation API backend 行为不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileViewer.test.tsx -t "copies only the public Automation API endpoint path"
# RED then GREEN；旧实现把 query/fragment token 写入 clipboard

npm --prefix frontend test -- --run src/components/ProfileViewer.test.tsx
# 1 file passed, 18 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、runtime viewer URL 使用、VNC websocket path、clipboard sync payload、profile persistence、profile lifecycle、runtime session/viewer token schema、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Viewer Automation endpoint copy release-evidence 边界。

## 2026-06-04 Shared public error URL release-evidence guardrail

背景：

- 前端 release regression 中，错误、notice、fallback metadata 经常通过 shared `publicErrorText()` 出现在截图/文本 evidence 里。
- 正常 URL host/path 仍有排障价值；但 query string 和 fragment 常携带 session、viewer、auth 或业务 token，不应进入 visible/title/aria/search evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 UI evidence 边界。

已覆盖：

- `publicErrorText()` 对 `http`、`https`、`socks5` URL 只保留 scheme/host/port/path。
- URL credentials、query string 和 fragment 会被移除。
- Authorization/Bearer、token assignment、本地路径和 IP literal redaction 行为继续保留。
- 复用该 helper 的 Proxy Manager、Profile CSV preview、Profile operations、Automation task viewer 和 ProfileViewer 自动继承。

验证：

```bash
npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts -t "removes URL query strings"
# RED then GREEN；旧实现保留 query/fragment

npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts src/components/ProxyManagerPage.test.tsx src/components/ProfileCsvPreviewDialog.test.tsx src/components/ProfileViewer.test.tsx src/components/AutomationTaskLogViewer.test.tsx src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx
# 7 files passed, 126 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw API payload、proxy/profile/task persistence、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 shared public error URL release-evidence 边界。

## 2026-06-04 Audit metadata URL release-evidence guardrail

背景：

- Release regression 中会查询 audit events 来证明 profile、runtime、viewer、automation、proxy 等流程被正确审计。
- 正常 URL host/path 对定位问题有用；但 URL credentials、query string 和 fragment 常携带 session、viewer、auth 或业务 token，不应进入 audit metadata evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 backend evidence 边界。

已覆盖：

- Audit metadata string 中的 `http`、`https`、`socks5` URL 只保留 scheme/host/port/path。
- URL username/password、query string 和 fragment 不进入 persisted/read-back audit metadata。
- Authorization/Bearer、token assignment、本地路径和 IP literal redaction 继续保留。
- 写入和读取 audit event 时都会执行同一 sanitizer。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -k "audit_metadata_sanitizer" -q
# RED then GREEN；旧 audit URL label 不符合保留低敏 path 的 evidence policy
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw API payload、proxy/profile/task persistence、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 backend audit metadata URL release-evidence 边界。

## 2026-06-04 ProfileForm chip action label release-evidence guardrail

背景：

- Release regression 中会操作 ProfileForm Advanced 面板，tag chip 和 Firefox launch argument chip 的 remove 按钮会进入可访问性/文本 evidence。
- Chip visible text 和输入框仍需要保留 raw 编辑语义；但 remove action label 不应暴露 Authorization/Bearer、`token=`、本地路径、URL credential/query/fragment 或 IP literal。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 frontend evidence 边界。

已覆盖：

- ProfileForm tag remove button `aria-label` 使用 public error-text boundary。
- ProfileForm launch argument remove button `aria-label` 使用 public error-text boundary。
- 普通 tag/launch arg action label 仍保持可读。
- Raw edit text、save payload、profile persistence、launch args runtime input、browser fingerprint behavior 不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileForm.test.tsx -t "redacts remove button labels"
# RED then GREEN；旧 remove action label 暴露 raw tag/launch arg

npm --prefix frontend test -- --run src/components/ProfileForm.test.tsx
# 1 file passed, 12 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw API payload、profile persistence、tag persistence、launch arg persistence、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 ProfileForm chip action label release-evidence 边界。

## 2026-06-04 Cookie export download filename release-evidence guardrail

背景：

- Cookie JSON/Netscape export 是 release regression 中需要人工确认的高敏操作，下载文件名也可能进入浏览器下载记录、测试日志或人工交接 evidence。
- 旧下载名只检查 profile id 是否由文件名安全字符组成；`viewer_token-cookie-secret` 这类字符串虽然可作为文件名片段，但仍是敏感/污染 id，不应进入 export metadata。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Cookie export evidence 边界。

已覆盖：

- Cookie export 下载名继续保留普通文件名安全 profile id。
- 含 Authorization/Bearer、auth token、viewer token、token、password、secret、cookie、set-cookie 等敏感词的 profile id 折叠为 `unknown`。
- 非文件名安全的 profile id 继续折叠为 `unknown`。
- Raw profile id、cookie import/export API 调用、Cookie JSON/Netscape payload、summary counts、profile persistence 和 browser behavior 不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileCookieManager.test.tsx -t "does not use sensitive filename-safe profile ids"
# RED then GREEN；旧下载名包含 viewer_token-cookie-secret

npm --prefix frontend test -- --run src/components/ProfileCookieManager.test.tsx
# 1 file passed, 8 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw API payload、profile persistence、cookie payload、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Cookie export download filename release-evidence 边界。

## 2026-06-04 Country badge release-evidence guardrail

背景：

- Country badge 会出现在 Profile operations、Profile summary、Profile rail 和 profile CSV preview 等 release regression 截图/文本 evidence 中。
- 旧 `CountryBadge` 信任调用方传入的 country 文本；若历史/异常 GeoIP country value 被污染，shared badge 的 visible text/title 仍可能保留非国家码内容。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 shared UI evidence 边界。

已覆盖：

- `CountryBadge` 只允许 2 位字母国家码，并规范成大写。
- 非国家码、污染或历史异常 country 文本在 visible/title evidence 中折叠为 `unknown`。
- 旧 ProfileTable/ProfileSummary GeoIP redaction 断言更新为确认污染 country 经 badge 层折叠。
- 普通 country code 展示、Profile health/GeoIP API、profile persistence 和 browser fingerprint behavior 不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/Badge.test.tsx -t "folds non-public country badge labels"
# RED then GREEN；旧 CountryBadge 暴露污染 country text/title

npm --prefix frontend test -- --run src/components/Badge.test.tsx
# 1 file passed, 4 tests passed

npm --prefix frontend test -- --run src/components/ProfileList.test.tsx src/components/ProfileTable.test.tsx src/components/ProfileSummaryPanel.test.tsx src/components/ProfileCsvPreviewDialog.test.tsx src/components/Badge.test.tsx
# 5 files passed, 74 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、GeoIP lookup/provider behavior、profile persistence、profile health API、runtime session/viewer token schema、VNC websocket path、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 CountryBadge release-evidence 边界。

## 2026-06-04 Frontend path parameter release-evidence guardrail

背景：

- Release regression 会经过 profile CRUD、cookie import/export、profile health、launch/stop、proxy assignment、provider preset 管理、clipboard sync 和 regular VNC viewer 等前端 API adapter 路径。
- 旧 adapter 把 path id 直接拼进 URL；异常 id 里的 `/`、`?`、`#` 会成为额外 path/query/fragment，污染 request URL evidence 并可能改变路由。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 frontend request URL 边界。

已覆盖：

- `api.ts` 对 profile/proxy/template/provider preset 相关 path params 统一编码为单个 URL segment。
- Cookie JSON/Netscape import/export、clipboard set/get、health check、launch/stop、proxy check/assign、save profile proxy asset 等路径继承同一编码边界。
- `ProfileViewer` regular profile VNC websocket URL 对 profile id 做 path segment 编码。
- 已使用 `URLSearchParams` 的 automation task list query 保持原逻辑。
- Raw id 业务语义不变；只防止 URL delimiter 被浏览器解释为请求结构。

验证：

```bash
npm --prefix frontend test -- --run src/lib/api.test.ts -t "encodes path ids"
# RED then GREEN；旧 api request URL 暴露 raw / ? #

npm --prefix frontend test -- --run src/components/ProfileViewer.test.tsx -t "encodes regular profile ids"
# RED then GREEN；旧 noVNC wsUrl 暴露 raw / ? #

npm --prefix frontend test -- --run src/lib/api.test.ts
# 1 file passed, 40 tests passed

npm --prefix frontend test -- --run src/components/ProfileViewer.test.tsx
# 1 file passed, 19 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 这不是 raw id 脱敏；异常 id 仍作为 URL-encoded path segment 传给 backend。
- 不改变 backend request/response schema、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 frontend path parameter release-evidence 边界。

## 2026-06-04 Diagnostics scalar identity release-evidence guardrail

背景：

- Release regression 的 System diagnostics 页面会展示 Manager status、binary label、managed UA version、engine package version、Firefox binary version 和 BuildID。
- 旧 frontend 直接渲染这些 scalar identity fields；正常后端值是低敏的，但异常 diagnostics payload 可能把 token/header/path text 带进 visible/aria evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 diagnostics evidence 边界。

已覆盖：

- Diagnostics status 仅 `ok` 可见，其他值显示 `unknown`。
- Binary label 仅固定 `invisible-playwright` 可见。
- Managed UA、engine package、Firefox binary version 只保留数字版本格式。
- Firefox BuildID 只保留 8-20 位数字。
- 正常 release diagnostics evidence 仍能展示 Manager/Firefox identity 对比所需的低敏版本信息。

验证：

```bash
npm --prefix frontend test -- --run src/components/SystemDiagnosticsPage.test.tsx -t "folds non-public diagnostics scalar identity fields"
# RED then GREEN；旧 UI/aria 暴露污染 diagnostics scalar text

npm --prefix frontend test -- --run src/components/SystemDiagnosticsPage.test.tsx
# 1 file passed, 5 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend diagnostics schema、diagnostics count-query behavior、runtime session/viewer token schema、VNC forwarding、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 diagnostics scalar release-evidence 边界。

## 2026-06-04 Shared frontend error assignment release-evidence guardrail

背景：

- Release regression 会经过 Profile operations、Proxy Manager、Profile CSV import、Automation task viewer、health labels 等多个前端错误/提示出口。
- 这些出口复用 `publicErrorText()`，旧边界已覆盖 URL query、Authorization/Bearer、token/password/secret/cookie、本地路径和 IP literal，但常见 provider/API assignment 名称如 `api_key`、`access_token`、`refresh_token`、`session_id`、`client_secret` 仍可能原样进入 visible/aria evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 shared frontend error evidence 边界。

已覆盖：

- `publicErrorText()` 现在 redacts `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` assignment/header-style text。
- `publicProfileIdLabel()` 同步把含有这些 marker 的异常 id label 折叠为 `unknown`。
- 既有 URL/path/IP/header redaction 和正常低敏错误上下文展示保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts -t "redacts common API key and session assignment names"
# RED then GREEN；旧 shared error text 暴露 api_key/access_token/session_id/client_secret/x-api-key values

npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts
# 1 file passed, 5 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 backend request/response schema、raw API payload、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 shared frontend error assignment release-evidence 边界。

## 2026-06-04 Backend audit API key metadata release-evidence guardrail

背景：

- Release regression 会读取 runtime/audit evidence；这些事件的 metadata 可能来自 runtime service、viewer/session failure path 或历史持久化 JSON。
- 旧 backend audit sanitizer 已覆盖 proxy URL、Authorization/Bearer、token/password/secret/cookie、path/IP/query/fragment，但常见 provider/API assignment 名称如 `api_key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` 仍可能出现在 audit metadata evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 backend audit evidence 边界。

已覆盖：

- Backend audit metadata sanitizer 会删除 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` dict keys。
- Backend audit metadata string redaction 会处理 `api_key=...`、`x-api-key: ...`、`access_token=...`、`refresh_token=...`、`session_id=...`、`client_secret=...`、`private_key=...`。
- 历史 audit event reader 继续在读取时重新 sanitize metadata，避免旧 JSON 污染 release evidence。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "audit_metadata_sanitizer"
# RED then GREEN；旧 backend audit metadata 暴露 api_key/access_token/session_id/client_secret/private_key/x-api-key values

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "audit_metadata"
# 1 passed, 45 deselected
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 backend audit API key metadata release-evidence 边界。

## 2026-06-04 Backend audit external session id release-evidence guardrail

背景：

- Release regression 会读取 audit event top-level `external_session_id`，用于 runtime/session evidence 对账。
- 旧 public external session id 边界能挡 URL/query/header/token-assignment，但常见 API/provider marker 如 `api_key-*`、`access_token-*`、`session_id-*`、`client_secret-*` 仍可能作为符合字符集的 ID 出现在 evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 backend audit release-evidence 边界。

已覆盖：

- Audit event reader 对 top-level `external_session_id` 增加 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker 防护。
- 含这些 marker 的 external session id 在 list/get audit evidence 中显示为 `None`，不会进入序列化 release evidence。
- 普通 `pm-session-*` 低敏 external session id 继续保留；runtime session 原始存储、viewer behavior、API payload 和 browser fingerprint behavior 不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "sensitive_external_session_id_markers"
# RED then GREEN；旧 audit event reader 暴露 api_key/access_token/session_id/client_secret/private_key marker external_session_id

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "external_session_id or audit_event_reader"
# 4 passed, 43 deselected
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 backend audit external session id release-evidence 边界。

## 2026-06-04 Runtime session response external id release-evidence guardrail

背景：

- Release regression 会读取 `/api/runtime/sessions/{id}` response，用于 runtime/session API evidence 对账。
- 旧 runtime response sanitizer 已覆盖 URL/query/header/token-assignment 形式的 external session id，但常见 API/provider marker 如 `api_key-*`、`access_token-*`、`session_id-*`、`client_secret-*` 仍可能作为符合字符集的 ID 出现在 response evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 runtime API release-evidence 边界。

已覆盖：

- Runtime session response 对 persisted `external_session_id` 增加 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker 防护。
- 含这些 marker 的 external session id 在 runtime get response 中显示为 `unknown`，不会进入序列化 release evidence。
- 普通 `pm-session-*` 低敏 external session id 继续保留；runtime session 原始存储、create request payload、viewer behavior、audit metadata 和 browser fingerprint behavior 不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "runtime_session_response_omits_sensitive_external_session_id_markers"
# RED then GREEN；旧 runtime session response 暴露 api_key/access_token/session_id/client_secret/private_key marker external_session_id

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "external_session_id or audit_event_reader"
# 5 passed, 43 deselected
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation API backend、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 runtime session response external id release-evidence 边界。

## 2026-06-04 Automation console assignment release-evidence guardrail

背景：

- Release regression 可能读取 automation console logs 和 network summary 作为 debug evidence。
- 旧 automation redaction 已覆盖 URL query/fragment/credential、Authorization/Bearer、Cookie 和旧 token/password/secret assignment，但常见 API/provider assignment 名称如 `api_key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` 仍可能进入 console text evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Automation release-evidence 边界。

已覆盖：

- Automation text redaction 会处理 `api_key=...`、`x-api-key: ...`、`access_token=...`、`refresh_token=...`、`session_id=...`、`client_secret=...`、`private_key=...`。
- Automation console log response 继续保留低敏 URL scheme/host/path context，同时剥离 credentials/query/fragment。
- Automation task payload execution、stored steps、worker lease, runtime session/viewer token schema 和 browser fingerprint behavior 不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py -q -k "automation_console_logs_redacts_sensitive_text_and_location_urls"
# RED then GREEN；旧 automation console text 暴露 api_key/access_token/session_id/client_secret/private_key assignment values

.venv/bin/python -m pytest backend/tests/test_api.py -q -k "automation_console_logs or automation_network_summary"
# 7 passed, 252 deselected
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 automation console assignment release-evidence 边界。

## 2026-06-04 Health runtime evidence release guardrail

背景：

- Release regression 会读取 profile health response，里面包含 runtime status、VNC port 和 Automation URL。
- 旧 health runtime evidence boundary 已覆盖 URL、Authorization/Bearer、token/password/cookie/secret marker，但 `api_key-*`、`access_token-*`、`session_id-*`、`client_secret-*` 这类符合公开字符集的 marker 仍可能从 runtime profile id/Automation URL 出现在 health response。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 health release-evidence 边界。

已覆盖：

- Health runtime evidence sanitizer 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker。
- 含这些 marker 的 Automation URL 在 health response 中折叠为 `None`，不会进入序列化 release evidence。
- GeoIP lookup/provider behavior、profile health status calculation、runtime session behavior、Automation API backend 和 browser fingerprint behavior 不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_health.py -q -k "health_response_sanitizes_non_public_runtime_evidence"
# RED then GREEN；旧 health runtime evidence 暴露 api_key marker Automation URL

.venv/bin/python -m pytest backend/tests/test_health.py -q
# 26 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 health runtime evidence release boundary。

## 2026-06-04 Browser launch identity marker release guardrail

背景：

- Release convergence 会继续检查 BrowserManager launch kwargs、fingerprint pin 和 low-sensitive browser identity evidence。
- 旧 BrowserManager sensitive-text filter 已覆盖 URL、Authorization/Bearer、`token`/`password`/`secret`/`cookie` marker，但 `api_key-*`、`session_id-*` 等 marker 仍可能作为合法 GPU/WebGL text 进入 launch identity pin。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 launch identity release-evidence 边界。

已覆盖：

- BrowserManager launch identity filter 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker。
- 含这些 marker 的 GPU vendor/renderer 不再进入 invisible fingerprint pin，也不会作为 coherent WebGL renderer override。
- 正常 GPU/WebGL low-sensitive text、screen/hardware pin、locale/timezone and profile dir validation behavior 不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_browser_manager.py -q -k "build_invisible_pin_drops_non_public_gpu_text"
# RED then GREEN；旧 launch pin 接受 api_key/session_id marker GPU text

.venv/bin/python -m pytest backend/tests/test_browser_manager.py -q
# 74 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 BrowserManager launch identity marker release boundary。

## 2026-06-04 System diagnostics marker label release guardrail

背景：

- Release convergence 会继续读取 System diagnostics UI 作为低敏 runtime/worker/status evidence。
- 旧 frontend diagnostics label boundary 已覆盖 URL、Authorization/Bearer、token/password/secret/cookie marker，但 `api_key-*`、`x-api-key-*`、`session_id-*`、`private_key-*` 等 marker 仍可能作为 aggregate map/list label 被渲染。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 diagnostics release-evidence 边界。

已覆盖：

- System diagnostics map/list labels 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker。
- 污染 label 合并显示为 `unknown`，普通低敏 stage/status/category label 继续显示。
- Backend diagnostics API、count-query schema、runtime/viewer/Automation behavior 和 browser fingerprint behavior 不变。

验证：

```bash
npm --prefix frontend test -- --run SystemDiagnosticsPage.test.tsx
# RED then GREEN；旧 diagnostics UI label 暴露 api_key/x-api-key/session_id/private_key marker
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 System diagnostics marker label release boundary。

## 2026-06-04 Automation task viewer marker label release guardrail

背景：

- Release convergence 会继续读取 Automation task viewer 作为任务执行、结果和错误的低敏 UI evidence。
- 旧 Automation task viewer label boundary 已覆盖 URL、Authorization/Bearer、token/password/secret/cookie marker，但 `api_key-*`、`x-api-key-*`、`session_id-*`、`private_key-*` 等 marker 仍可能作为 task/profile/step/result label 被渲染。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Automation release-evidence 边界。

已覆盖：

- Automation task viewer task/profile id、step labels、result labels 和 detail button aria label 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker。
- 污染 label 显示为 `unknown`，普通低敏 task id、profile id、step type/status、page index 和 wait/state label 继续显示。
- Backend task API、stored task payloads、Automation worker lease、runtime/viewer 和 browser fingerprint behavior 不变。

验证：

```bash
npm --prefix frontend test -- --run AutomationTaskLogViewer.test.tsx
# RED then GREEN；旧 Automation task viewer label 暴露 api_key/x-api-key/session_id/private_key marker
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation task viewer marker label release boundary。

## 2026-06-04 ProfileViewer handle marker release guardrail

背景：

- Release convergence 会继续读取 ProfileViewer environment strip、toolbar title/aria 和 Automation endpoint copy evidence。
- 旧 ProfileViewer handle boundary 已覆盖 URL、Authorization/Bearer、viewer_token、token/password/secret/cookie marker，但 `api_key-*`、`session_id-*`、`private_key-*` 等 marker 仍可能作为 profile/session handle 或 copyable Automation endpoint path id 被渲染。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 ProfileViewer release-evidence 边界。

已覆盖：

- ProfileViewer profile handle、business session handle 和 Automation endpoint path id 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker。
- 污染 handle 显示为 `unknown`，污染 Automation endpoint copy action 显示 unavailable 并禁用。
- Regular VNC websocket path encoding、runtime viewer token URL usage、clipboard sync、backend Automation API、runtime/viewer behavior 和 browser fingerprint behavior 不变。

验证：

```bash
npm --prefix frontend test -- --run ProfileViewer.test.tsx
# RED then GREEN；旧 ProfileViewer handle/copy evidence 暴露 api_key/session_id/private_key marker
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 ProfileViewer handle marker release boundary。

## 2026-06-04 Cookie export filename marker release guardrail

背景：

- Release convergence 会继续检查 cookie export download metadata，避免 filename-safe profile ids 把敏感 marker 写进本地下载文件名和 evidence。
- 旧 cookie export filename boundary 已覆盖 viewer_token、token/password/secret/cookie marker，但 `api_key-*`、`x-api-key-*`、`session_id-*`、`private_key-*` 等 marker 仍可能作为 filename-safe profile id 被使用。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 cookie export release-evidence 边界。

已覆盖：

- Cookie JSON/Netscape export download filenames 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker。
- 污染 profile id 的下载文件名使用 `unknown`，普通 filename-safe profile id 继续可用。
- Cookie JSON/Netscape payload、raw profile id API semantics、cookie import/export API calls、summary counts、runtime/viewer 和 browser fingerprint behavior 不变。

验证：

```bash
npm --prefix frontend test -- --run ProfileCookieManager.test.tsx
# RED then GREEN；旧 cookie export filename 暴露 api_key/x-api-key/session_id/private_key marker
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 cookie export filename marker release boundary。

## 2026-06-04 Proxy Manager assignment profile id marker release guardrail

背景：

- Release convergence 会继续检查 Proxy Manager assignment dialog，因为它会把 profile id 纳入 visible/title/aria/search evidence。
- 旧 assignment profile id boundary 已覆盖 URL、Authorization/Bearer、viewer_token、token/password/secret/cookie marker，但 `x-api-key-*`、`session-id-*`、`private-key-*` 等 path-safe marker 仍可能作为 profile id label 被渲染。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Proxy Manager release-evidence 边界。

已覆盖：

- Proxy Manager assignment profile id label 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker。
- 污染 profile id 在 assignment dialog 中显示为 `unknown`，并且不能通过原 marker 搜索命中。
- Checkbox selection 和 `assignProxyToProfiles` payload 继续使用原始 profile id，普通低敏 profile id 继续显示和可分配。

验证：

```bash
npm --prefix frontend test -- --run ProxyManagerPage.test.tsx
# RED then GREEN；旧 assignment profile id label 暴露 x-api-key/session-id/private-key marker；GREEN 38 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy Manager assignment profile id marker release boundary。

## 2026-06-04 Shared profile id marker release guardrail

背景：

- Release convergence 会继续检查 ProfileTable、ProfileSummaryPanel 等共享 profile id UI evidence。
- 旧 shared profile id boundary 已覆盖 URL、Authorization/Bearer、api_key、access_token、refresh_token、session_id、viewer_token、token/password/secret/cookie marker，但 `client_secret-*`、`private_key-*` 等 profile-id-safe marker 仍可能被截断后显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 shared profile id release-evidence 边界。

已覆盖：

- `publicProfileIdLabel` 会拒绝 `x-api-key`、`auth_token`、`viewer-token`、`client_secret`、`private_key` marker。
- 污染 profile id 在共享 UI evidence 中显示为 `unknown`，普通公开 profile id 继续使用原有短 label。
- ProfileTable/ProfileSummaryPanel 等调用方继承该共享边界；raw profile id API/persistence 语义不变。

验证：

```bash
npm --prefix frontend test -- --run errorDisplay.test.ts
# RED then GREEN；旧 publicProfileIdLabel 将 client_secret-profile-marker 渲染为 client_s；GREEN 6 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 shared profile id marker release boundary。

## 2026-06-04 Shared GeoIP label marker release guardrail

背景：

- Release convergence 会继续检查 ProfileTable、ProfileSummaryPanel 和 health/filter 的 GeoIP visible/title/search evidence。
- 旧 shared GeoIP label boundary 已覆盖 Authorization/Bearer、token/password/secret/cookie assignment、path 和 URL credential 情况，但 `api_key-geoip-marker`、`client_secret-geoip-marker`、`private_key-geoip-marker` 这类 marker-only 字符串仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 shared GeoIP release-evidence 边界。

已覆盖：

- `publicProfileGeoipLabel` 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only GeoIP labels。
- 污染 marker-only GeoIP label 显示为 `unknown`；已有 path/IP/header/URL credential redaction 继续保留。
- 普通 IP、country code、timezone、locale 等低敏 GeoIP evidence 继续显示。

验证：

```bash
npm --prefix frontend test -- --run errorDisplay.test.ts
# RED then GREEN；旧 publicProfileGeoipLabel 原样返回 api_key-geoip-marker；GREEN 7 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 shared GeoIP label marker release boundary。

## 2026-06-04 Shared profile tag label marker release guardrail

背景：

- Release convergence 会继续检查 TagBadge、ProfileFilters tag select、ProfileTable/ProfileCard tag evidence。
- 旧 shared tag label boundary 已覆盖 Authorization/Bearer、assignment-style token/password/secret/cookie、path 和 URL credential 情况，但 `api_key-tag-marker`、`client_secret-tag-marker`、`private_key-tag-marker` 这类 marker-only 字符串仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 shared tag release-evidence 边界。

已覆盖：

- `publicProfileTagLabel` 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only tag labels。
- 污染 marker-only tag label 显示为 `unknown`，普通公开 tag label 继续显示。
- TagBadge/ProfileFilters/ProfileTable 等调用方继承该共享边界；raw tag values、filter values 和 persistence 语义不变。

验证：

```bash
npm --prefix frontend test -- --run errorDisplay.test.ts
# RED then GREEN；旧 publicProfileTagLabel 原样返回 api_key-tag-marker；GREEN 8 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw tag values、filter values、raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 shared profile tag label marker release boundary。

## 2026-06-04 Shared profile name marker release guardrail

背景：

- Release convergence 会继续检查 ProfileList、ProfileTable、ProfileSummaryPanel、ProfileFilters search/sort 和 Proxy Manager assignment profile name evidence。
- 旧 shared profile name boundary 已覆盖 Authorization/Bearer、assignment-style token/password/secret/cookie、path 和 URL credential 情况，但 `api_key-profile-name-marker`、`client_secret-profile-name-marker`、`private_key-profile-name-marker` 这类 marker-only 字符串仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 shared profile name release-evidence 边界。

已覆盖：

- `publicProfileName` 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only profile names。
- 污染 marker-only profile name 显示为 `unknown`，普通公开 profile name 继续显示。
- ProfileList/ProfileTable/ProfileSummaryPanel/ProfileFilters/Proxy Manager assignment 等调用方继承该共享边界；raw profile name、form input、filter value 和 persistence 语义不变。

验证：

```bash
npm --prefix frontend test -- --run errorDisplay.test.ts
# RED then GREEN；旧 publicProfileName 原样返回 api_key-profile-name-marker；GREEN 9 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw profile names、form inputs、filter values、raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 shared profile name marker release boundary。

## 2026-06-04 ProfileSummary device label marker release guardrail

背景：

- Release convergence 会继续检查 ProfileSummaryPanel 的 Device section，因为 platform、screen、hardware concurrency、GPU label 会进入 visible/title evidence。
- 旧设备标签 boundary 已覆盖 Authorization/Bearer、assignment-style token/password/secret/cookie、path、IP 和 URL credential 情况，但 `api_key-device-platform-marker`、`client_secret-device-screen-width-marker`、`private_key-device-screen-height-marker` 这类 marker-only 字符串仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 ProfileSummary release-evidence 边界。

已覆盖：

- ProfileSummary device label 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only device labels。
- 污染 marker-only 设备值显示为 `unknown`；screen 显示为 `unknown x unknown`，cores 显示为 `unknown cores`。
- 既有带 Authorization/token/path/IP 的设备字段 redaction 继续保留，普通平台、屏幕、核心数和 GPU label 继续显示。

验证：

```bash
npm --prefix frontend test -- --run ProfileSummaryPanel.test.tsx
# RED then GREEN；旧 ProfileSummary Device section 暴露 api_key/client_secret/private_key/x-api-key/access_token marker；GREEN 9 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw profile device values、form inputs、raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 ProfileSummary device label marker release boundary。

## 2026-06-04 Health warning summary marker release guardrail

背景：

- Release convergence 会继续检查 HealthBadge、ProfileList、ProfileSummaryPanel 等健康 warning visible/title evidence。
- 旧 shared health warning boundary 已覆盖 Authorization/Bearer、assignment-style token/password/secret/cookie、path、IP 和 URL credential 情况，但 `api_key-health-warning-marker`、`client_secret-health-warning-marker`、`private_key-health-warning-marker` 这类 marker-only 字符串仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 health warning release-evidence 边界。

已覆盖：

- `getHealthWarningSummary` 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only warning summaries。
- 污染 marker-only warning summary 显示为 `unknown`，并覆盖 HealthBadge visible/title evidence。
- 既有带 Authorization/token/path/IP 的 warning summary redaction 继续保留，普通健康 warning 继续显示。

验证：

```bash
npm --prefix frontend test -- --run HealthBadge.test.tsx
# RED then GREEN；旧 HealthBadge warning summary 暴露 api_key/client_secret/private_key marker；GREEN 7 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw health response、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 shared health warning summary marker release boundary。

## 2026-06-04 Proxy Manager label marker release guardrail

背景：

- Release convergence 会继续检查 Proxy Manager provider presets、proxy asset rows/details、CSV import preview/summary、assignment dialog profile/proxy labels 这些 visible/title/search/aria evidence。
- 旧 Proxy Manager label boundary 已覆盖 Authorization/Bearer、assignment-style token/password/secret/cookie、path、IP 和 URL credential 情况，但 `api_key-provider-marker`、`client_secret-country-marker`、`private_key-tag-marker` 这类 marker-only 字符串仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Proxy Manager release-evidence 边界。

已覆盖：

- Proxy Manager shared public label sanitizer 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only labels。
- provider preset metadata 污染值显示为 `unknown`，并覆盖 dialog summary、token chips、visible text、`title` 和 aria evidence。
- 既有带 Authorization/token/path/IP 的 proxy/provider redaction 继续保留，普通低敏 proxy/provider metadata 继续显示。

验证：

```bash
npm --prefix frontend test -- --run ProxyManagerPage.test.tsx
# RED then GREEN；旧 provider preset metadata 暴露 api_key/client_secret/private_key marker；GREEN 39 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw proxy assets、provider presets、CSV import payload、profile assignment payload、raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy Manager label marker release boundary。

## 2026-06-04 Proxy CSV textarea marker release guardrail

背景：

- Release convergence 会继续检查 Proxy CSV import dialog，因为 raw source text 与 textarea visible evidence 是分离路径。
- 旧 textarea visible boundary 已覆盖 URL credentials、Authorization/Bearer、assignment-style token/password/secret/cookie、path 和 IP，但 `api_key-proxy-csv-name-marker`、`client_secret-proxy-csv-provider-marker`、`private_key-proxy-csv-tag-marker` 这类 marker-only CSV 字段仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Proxy CSV release-evidence 边界。

已覆盖：

- Proxy CSV textarea visible text 会把含 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only 的 CSV 字段折叠为 `unknown`。
- URL credential redaction 继续隐藏 username/password，同时保留低敏 endpoint host/port。
- `importSourceText`、CSV parser、preview source 和 `createProxy` payload 继续使用 raw CSV source；redaction 只影响 textarea visible evidence。

验证：

```bash
npm --prefix frontend test -- --run ProxyManagerPage.test.tsx
# RED then GREEN；旧 CSV textarea visible value 暴露 api_key/client_secret/private_key marker；GREEN 40 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw CSV source、CSV parser、CSV import payload、proxy asset persistence、provider presets、profile assignment payload、raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy CSV textarea marker release boundary。

## 2026-06-04 Profile CSV textarea marker release guardrail

背景：

- Release convergence 会继续检查 Profile CSV import preview dialog，因为 backend preview/import raw CSV 与 textarea visible evidence 是分离路径。
- 旧 textarea visible boundary 已覆盖 URL credentials、Authorization/Bearer、assignment-style token/password/secret/cookie、path 和 IP，但 `api_key-profile-csv-name-marker`、`client_secret-profile-csv-tag-marker`、`private_key-profile-csv-notes-marker` 这类 marker-only CSV 字段仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Profile CSV release-evidence 边界。

已覆盖：

- Profile CSV textarea visible text 会把含 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only 的 CSV 字段折叠为 `unknown`。
- URL credential redaction 继续隐藏 username/password，同时保留低敏 endpoint host/port。
- `lastPreviewCsvText`、backend preview request 和 import payload 继续使用 raw CSV source；redaction 只影响 textarea visible evidence。

验证：

```bash
npm --prefix frontend test -- --run ProfileCsvPreviewDialog.test.tsx
# RED then GREEN；旧 Profile CSV textarea visible value 暴露 api_key/client_secret/private_key marker；GREEN 7 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw CSV source、CSV parser、backend preview/import payload、profile persistence、provider/proxy/template persistence、raw API payload、backend schemas、database persistence、automation step execution、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile CSV textarea marker release boundary。

## 2026-06-04 Profile CSV preview row marker release guardrail

背景：

- Release convergence 会继续检查 Profile CSV import preview table，因为 backend preview 返回的 profile name、template id、platform、locale、timezone、proxy label 会进入 visible/title evidence。
- 旧 preview row label boundary 已覆盖 Authorization/Bearer、assignment-style token/password/secret/cookie、path、IP 和 URL credential 情况，但 `api_key-profile-row-name-marker`、`client_secret-profile-row-template-marker`、`private_key-profile-row-platform-marker` 这类 marker-only metadata 仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Profile CSV preview release-evidence 边界。

已覆盖：

- `publicProfileCsvPreviewLabel` 会拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only preview row labels。
- 污染 marker-only row metadata 显示为 `unknown`，并覆盖 visible text 和 `title` evidence。
- 既有带 Authorization/token/path/IP/URL credential 的 preview row redaction 继续保留，普通低敏 preview metadata 继续显示。

验证：

```bash
npm --prefix frontend test -- --run ProfileCsvPreviewDialog.test.tsx
# RED then GREEN；旧 Profile CSV preview row 暴露 api_key/client_secret/private_key/x-api-key/access_token/session_id marker；GREEN 8 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw CSV source、CSV parser、backend preview/import payload、profile persistence、provider/proxy/template persistence、raw API payload、backend schemas、database persistence、automation step execution、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile CSV preview row marker release boundary。

## 2026-06-04 Profile CSV validation error marker release guardrail

背景：

- Release convergence 会继续检查 Profile CSV import preview table，因为 backend row validation errors 会进入 visible evidence。
- 旧 validation error boundary 已覆盖 Authorization/Bearer、assignment-style token/password/secret/cookie、path 和 IP，但 `api_key-profile-row-error-marker`、`client_secret-profile-row-error-marker`、`private_key-profile-row-error-marker` 这类 marker-only error text 仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Profile CSV validation release-evidence 边界。

已覆盖：

- Profile CSV row validation errors 复用 `publicProfileCsvPreviewLabel`，拒绝 `api_key`、`x-api-key`、`access_token`、`refresh_token`、`session_id`、`client_secret`、`private_key` marker-only error text。
- 污染 marker-only validation error 显示为 `unknown`，既有 Authorization/token/path/IP redaction 继续保留。
- backend preview response 和 raw import payload 不变。

验证：

```bash
npm --prefix frontend test -- --run ProfileCsvPreviewDialog.test.tsx
# RED then GREEN；旧 row validation error 暴露 api_key/client_secret/private_key marker；GREEN 9 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw CSV source、CSV parser、backend preview/import payload、profile persistence、provider/proxy/template persistence、raw API payload、backend schemas、database persistence、automation step execution、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile CSV validation error marker release boundary。

## 2026-06-04 ProfileForm tag / launch arg marker release guardrail

背景：

- Release convergence 会继续检查 ProfileForm Advanced section，因为 persisted tags 和 Firefox launch args 会进入 chip visible text 与 remove button aria evidence。
- 旧 remove button boundary 已覆盖 Authorization/Bearer、assignment-style token/password/secret/cookie、path、IP 和 URL credential 情况，但 chip visible text 仍使用 raw tag / launch arg；`api_key-profile-form-tag-marker`、`client_secret-profile-form-launch-marker` 这类 marker-only 值可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 ProfileForm release-evidence 边界。

已覆盖：

- ProfileForm persisted tag chip 复用 `publicProfileTagLabel()`，marker-only tag 显示为 `unknown`。
- ProfileForm persisted launch arg chip 通过 `publicProfileLaunchArgLabel()`，marker-only launch arg 显示为 `unknown`。
- chip visible text 与 remove button aria label 使用同一安全文本；普通含 URL credential、Authorization、token、path、IP 的 tag / launch arg 继续显示 redacted 摘要。
- raw tag、raw launch arg、remove action 和 save payload 不变。

验证：

```bash
npm --prefix frontend test -- --run ProfileForm.test.tsx -t "folds marker-bearing persisted tags"
# RED then GREEN；旧 ProfileForm chip visible text 暴露 api_key/client_secret marker；GREEN 1 passed, 12 skipped

npm --prefix frontend test -- --run ProfileForm.test.tsx
# 13 passed

npm --prefix frontend test -- --run errorDisplay.test.ts ProfileForm.test.tsx
# 2 files passed, 22 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw form state、profile tags、launch args、template application、raw API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 ProfileForm tag / launch arg marker release boundary。

## 2026-06-04 Bulk feedback marker release guardrail

背景：

- Release convergence 会继续检查 ProfileTable / BulkActionBar bulk operation feedback，因为 bulk health/export/launch/stop/tag/delete 汇总错误会进入 visible/aria evidence。
- 旧 shared error text boundary 已覆盖 Authorization/Bearer、assignment-style token/password/secret/cookie、path、IP 和 URL credential 情况，但 `api_key-bulk-feedback-marker`、`client_secret-bulk-feedback-marker`、`private_key-bulk-feedback-marker` 这类 marker-only error token 仍可能原样显示。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 bulk feedback release-evidence 边界。

已覆盖：

- `publicErrorText()` 会把 provider/session/private-key 风格 marker-only error tokens 替换为 `[redacted]`。
- ProfileTable / BulkActionBar feedback 保留低敏上下文，例如 `Export failed`，但不显示 marker token。
- profile name/tag/GeoIP/launch arg 等 label helper 继续把纯 marker label 折叠为 `unknown`，不会因为共享 error redaction 变成 `[redacted]`。

验证：

```bash
npm --prefix frontend test -- --run ProfileTable.test.tsx -t "redacts marker-bearing bulk operation feedback"
# RED then GREEN；旧 bulk feedback 暴露 api_key/client_secret/private_key marker；GREEN 1 passed, 43 skipped

npm --prefix frontend test -- --run errorDisplay.test.ts ProfileTable.test.tsx
# 2 files passed, 54 tests passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw operation errors、profile/proxy/task API payload、backend schemas、database persistence、automation step execution、profile/proxy/template persistence、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 bulk feedback marker release boundary。

## 2026-06-04 Profile CSV source marker release guardrail

背景：

- Release convergence 继续检查 Profile CSV preview/import API response，因为 `row.source` 会作为低敏 release evidence 进入调试和回归记录。
- 旧后端 source redaction 已覆盖 URL/path/Auth/token/secret/password/cookie，但 `api_key-profile-csv-source-marker`、`x-api-key-profile-csv-source-marker`、`session_id-profile-csv-source-marker`、`private_key-profile-csv-source-marker` 这类 marker-only 字段仍可能出现在 response JSON。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 API release-evidence 边界。

已覆盖：

- Profile CSV preview 和正式 import response 的 `row.source` 现在会把 marker-only name/tags/notes/template 字段折叠为 `[redacted]`。
- marker 词覆盖 `access_token`、`api_key`、`auth_token`、`client_secret`、`private_key`、`refresh_token`、`runtime_service_token`、`session_id`、`service_token`、`viewer_token`、`x-api-key`。
- raw CSV request、CSV parser、profile create data、database persistence、frontend textarea/table visible redaction 和 browser fingerprint 行为不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_bulk.py -q -k marker_source_fields
# RED then GREEN；旧 row.source.name 暴露 api_key-profile-csv-source-marker；GREEN 1 passed, 20 deselected

.venv/bin/python -m pytest backend/tests/test_bulk.py -q
# 21 passed

.venv/bin/python -m pytest backend/tests -q
# 655 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw CSV source、CSV parser、backend import request payload、profile persistence、provider/proxy/template persistence、raw API payload schemas、database persistence、automation step execution、cookie payload、GeoIP lookup/provider behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile CSV source marker release boundary。

## 2026-06-04 Automation console marker release guardrail

背景：

- Release convergence 继续检查 Automation console logs API，因为 page console message 会作为 automation worker/runtime 的低敏 evidence。
- 旧 console text redaction 已覆盖 URL、Authorization/Bearer、Cookie 和赋值型 sensitive fields，但 `api_key-console-marker`、`x-api-key-console-marker`、`session_id-console-marker`、`private_key-console-marker` 这类 marker-only 文本仍可能进入 response JSON。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Automation API release-evidence 边界。

已覆盖：

- Automation console log response 现在会把 marker-only sensitive text token 折叠为 `[redacted]`。
- marker 词覆盖 access/api/auth/client/private/refresh/runtime/service/session/viewer/x-api-key 相关 token。
- 赋值型 `api_key=...`、`x-api-key: ...`、URL、Authorization/Bearer 和 Cookie redaction 输出保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py -q -k "automation_console_logs_redacts_sensitive_text"
# RED then GREEN；旧 console log response 暴露 api_key-console-marker / x-api-key-console-marker / session_id-console-marker / private_key-console-marker；GREEN 1 passed, 258 deselected

.venv/bin/python -m pytest backend/tests/test_api.py -q -k "automation_console_logs or automation_network_summary or run_"
# 55 passed, 204 deselected

.venv/bin/python -m pytest backend/tests -q
# 655 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw page console storage、automation task storage、automation worker lease/run behavior、profile/proxy/template persistence、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation console marker release boundary。

## 2026-06-04 GeoIP source marker release guardrail

背景：

- Release convergence 继续检查 GeoIP/proxy source evidence，因为 `last_geoip_source`、`last_check_source` 会进入 profile/proxy response、health 和 diagnostics。
- 旧 GeoIP source boundary 已覆盖 URL/path/query/Auth/token/secret/password/cookie，但 `api_key-geoip-source-marker`、`x-api-key-geoip-source-marker`、`session_id-geoip-source-marker`、`private_key-geoip-source-marker` 这类 marker-only source label 仍可能被当成公开 source。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 GeoIP/proxy release-evidence 边界。

已覆盖：

- `public_geoip_source()` 现在会把 marker-only sensitive source label 折叠为 `unknown`。
- marker 词覆盖 access/api/client/private/refresh/runtime/service/session/viewer/x-api-key 相关 source。
- `ip-api`、`ipapi.co`、`ipwho.is`、`qa` 等低敏 source 继续保留。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_geoip.py -q -k marker_only_sensitive_sources
# RED then GREEN；旧 public_geoip_source 暴露 api_key-geoip-source-marker；GREEN 1 passed, 15 deselected

.venv/bin/python -m pytest backend/tests/test_geoip.py -q
# 16 passed

.venv/bin/python -m pytest backend/tests/test_health.py backend/tests/test_proxies.py -q -k "source or geoip_source or last_check_source or success_source"
# 3 passed, 65 deselected

.venv/bin/python -m pytest backend/tests -q
# 656 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 GeoIP provider 请求、proxy URL、profile/proxy persistence、automation worker behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 GeoIP source marker release boundary。

## 2026-06-04 Proxy metadata marker release guardrail

背景：

- Release convergence 继续检查 Proxy Manager/proxy-country evidence，因为 provider/city metadata 会进入 proxy list/detail response、assignment UI 和 smoke 记录。
- 旧 backend proxy metadata boundary 已覆盖 URL/path/query/Auth/token/secret/password/cookie，但 `api_key-proxy-provider-marker`、`session_id-proxy-city-marker` 这类 marker-only provider/city label 仍可能被当成公开 metadata。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 proxy release-evidence 边界。

已覆盖：

- Proxy provider/city sanitizer 现在会把 marker-only sensitive metadata 折叠为 `null`。
- audit name sanitizer 同步拒绝同类 marker-only name。
- 低敏 provider/city/audit name 继续保留，proxy URL、proxy check、GeoIP 和 persistence 行为不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py -q -k marker_only_provider_and_city_labels
# RED then GREEN；旧 proxy detail/list response 暴露 api_key-proxy-provider-marker；GREEN 1 passed, 42 deselected

.venv/bin/python -m pytest backend/tests/test_proxies.py -q -k "provider or location_labels or selection_fields or proxy_crud_api or audit_name"
# 9 passed, 34 deselected

.venv/bin/python -m pytest backend/tests -q
# 657 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 proxy asset persistence、proxy URL、proxy check behavior、GeoIP provider 请求、profile persistence、automation worker behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 proxy metadata marker release boundary。

## 2026-06-04 Audit metadata marker release guardrail

背景：

- Release convergence 继续检查 audit metadata evidence，因为 runtime/profile/proxy/automation 事件会被用于排查 release smoke 和回归。
- 旧 audit metadata sanitizer 已覆盖 URL、Authorization/Bearer、赋值型 sensitive fields、path 和 IP，但 `api_key-audit-message-marker`、`x-api-key-audit-message-marker`、`session_id-audit-message-marker`、`private_key-audit-message-marker` 这类 marker-only message text 仍可能进入 audit event JSON。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 audit release-evidence 边界。

已覆盖：

- Audit metadata message 现在会把 marker-only sensitive text token 折叠为 `[redacted]`。
- marker 词覆盖 access/api/auth/client/private/refresh/runtime/service/session/viewer/x-api-key 相关 token。
- 赋值型 `api_key=...`、`x-api-key: ...`、URL、Authorization/Bearer、path 和 IP redaction 输出保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k audit_metadata_sanitizer_removes_sensitive_fields
# RED then GREEN；旧 audit metadata message 暴露 api_key-audit-message-marker / x-api-key-audit-message-marker / session_id-audit-message-marker / private_key-audit-message-marker；GREEN 1 passed, 47 deselected

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "audit_metadata_sanitizer or audit_event_reader"
# 3 passed, 45 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 657 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 audit schema、runtime session/profile/proxy persistence、automation worker behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 audit metadata marker release boundary。

## 2026-06-04 Audit event type marker release guardrail

背景：

- Release convergence 继续检查 audit event 顶层字段，因为 `event_type` 会直接出现在 audit API、release triage 和低敏 evidence。
- 旧 event type public filter 只校验 dotted lowercase 格式，`api_key.audit`、`runtime.api_key`、`viewer_token.audit` 这类 marker-only event type 仍可能被当成公开 audit label。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 audit release-evidence 边界。

已覆盖：

- Audit event reader 现在会把含敏感 event-type segment 的 historical/manual event type 折叠为 `unknown`。
- marker 词覆盖 access/api/auth/client/private/refresh/runtime/service/session/viewer/x-api-key 相关 segment。
- 低敏 `runtime.test`、现有业务事件 `runtime.viewer_token.created` 等正常 event type 保持可见。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k audit_event_reader_omits_sensitive_event_type_markers
# RED then GREEN；旧 audit event reader 暴露 api_key.audit / runtime.api_key / viewer_token.audit；GREEN 1 passed, 48 deselected

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "audit_event_reader or runtime_service_actions_write_redacted_audit_events or viewer_token_created"
# 4 passed, 45 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 658 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 audit schema、audit write call sites、runtime session/profile/proxy persistence、automation worker behavior、runtime session/viewer token schema、VNC forwarding、Automation worker lease behavior、WebRTC behavior、stealth prefs、seed、WebGL、UA、locale/timezone 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 audit event type marker release boundary。

## 2026-06-04 Browser launch hyphen marker release guardrail

背景：

- Release convergence 继续检查 BrowserManager launch identity 输入，因为 GPU/WebGL pin 和 Firefox launch args 会直接进入 managed browser 启动边界。
- 旧 launch sensitive-text filter 已覆盖 URL、Authorization/Bearer、query、下划线形式 `api_key` / `session_id` / `private_key`，但 `api-key-gpu-marker`、`private-key-gpu-marker`、`api-key-launch-marker`、`private-key-launch-marker` 这类短横线 marker 仍可能通过。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 launch identity release-evidence 边界。

已覆盖：

- BrowserManager shared sensitive text regex 现在识别 `_` 和 `-` 两种 marker 分隔形式。
- GPU/WebGL pin、Firefox extra launch args、profile dir/log id 等复用该过滤器的 launch 边界会拒绝短横线 sensitive marker。
- `test_launch_does_not_block_on_existing_page_init_script_timeout` 隔离 GeoIP/network fingerprint 解析，避免测试在页面 init timeout 之前被外部网络卡住。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_browser_manager.py -q -k "non_public_gpu_text or drops_non_public_launch_args"
# RED then GREEN；旧 launch identity 暴露 api-key/private-key marker 到 GPU pin 和 extra_args；GREEN 2 passed, 72 deselected

.venv/bin/python -m pytest backend/tests/test_browser_manager.py -q -k "gpu_text or launch_args or coherent_webgl or locale or timezone or init_script"
# 16 passed, 58 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 658 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 `invisible_playwright` 包、stealth prefs、fingerprint seed 生成、WebGL coherence bucket、UA、locale/timezone、WebRTC behavior、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 BrowserManager launch hyphen-marker release boundary。

## 2026-06-04 Profile response launch arg marker release guardrail

背景：

- Release convergence 继续检查 profile API response evidence，因为 profile list/detail 会把 persisted `launch_args` 显示给 UI 和回归记录。
- 旧 profile response launch arg sanitizer 已覆盖 URL、Authorization/Bearer、query 和 assignment-style token/password/secret/cookie，但 `--note=api-key-profile-response-marker`、`--title=private-key-profile-response-marker` 这类短横线 marker-only arg 仍可能被当成普通 public launch arg。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 profile response release-evidence 边界。

已覆盖：

- Profile response launch arg sanitizer 现在拒绝 access/api/auth/client/private/refresh/runtime/service/session/viewer/x-api-key 相关 marker。
- marker 词同时覆盖 `_` 和 `-` 分隔形式。
- 普通低敏 launch args 继续保留；raw profile create/update/persistence 语义不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py -q -k profile_responses_sanitize_persisted_identity_fields
# RED then GREEN；旧 profile list/detail response 暴露 --note=api-key-profile-response-marker / --title=private-key-profile-response-marker；GREEN 1 passed, 258 deselected

.venv/bin/python -m pytest backend/tests/test_api.py backend/tests/test_templates.py backend/tests/test_bulk.py -q -k "profile_responses_sanitize_persisted_identity_fields or profile_launch_args or launch_args or export_profile_bundle_sanitizes_persisted_identity_fields or bulk_export_profile_configs_sanitizes_persisted_identity_fields or profile_template_api_sanitizes_persisted_identity_fields or create_profile_from_template_sanitizes_persisted_identity_fields"
# 9 passed, 284 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 658 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 raw profile launch arg persistence、profile create/update request contract、BrowserManager launch behavior、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 profile response launch arg marker release boundary。

## 2026-06-04 Profile CSV source hyphen marker release guardrail

背景：

- Release convergence 继续检查 Profile CSV preview/import response，因为 row `source` 会进入 API/UI 和回归证据。
- 旧 CSV source sanitizer 已覆盖 URL/path/Auth、token/secret/password/cookie 以及下划线 marker，但 `api-key-profile-csv-source-marker`、`session-id-profile-csv-source-marker`、`private-key-profile-csv-source-marker` 这类短横线 marker 仍可能作为普通 source text。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 CSV response release-evidence 边界。

已覆盖：

- Profile CSV source sanitizer 现在拒绝 key/id 型短横线 marker。
- Preview 和 import responses 的 supported source fields 对同类 marker 返回 `[redacted]`。
- 原始 CSV request、parser、profile create data、proxy URL redaction、confirmation 和 bulk audit 语义保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_bulk.py -q -k profile_csv_import_responses_redact_marker_source_fields
# RED then GREEN；旧 CSV source response 暴露 api-key-profile-csv-source-marker；GREEN 1 passed, 20 deselected

.venv/bin/python -m pytest backend/tests/test_bulk.py -q -k "source_fields or marker_source_fields or missing_template_ref or proxy_error_detail or import_writes_redacted_bulk_audit_event"
# 9 passed, 12 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 658 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 CSV 原始输入、profile persistence、BrowserManager launch behavior、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile CSV source hyphen-marker release boundary。

## 2026-06-04 Audit metadata hyphen assignment release guardrail

背景：

- Release convergence 继续检查 audit metadata，因为这些 JSON 会进入回归证据、runtime/viewer triage 和本地长期记录。
- 旧 audit metadata sanitizer 已覆盖 `api_key=...`、`session_id=...`、`private_key=...` 等下划线赋值，但 `api-key=...`、`client-secret=...`、`session-id=...`、`private-key=...` 这类短横线赋值仍可能作为普通文本。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 audit release-evidence 边界。

已覆盖：

- Audit metadata value 中的敏感赋值 sanitizer 现在同时覆盖 `_` 和 `-` 分隔形式。
- Audit metadata key 名中的短横线敏感 key/assignment key 也会被整体丢弃。
- 原有 URL credential、Authorization/Bearer、local path、IP literal、underscore assignment 和 marker-only redaction 行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k audit_metadata_sanitizer_removes_sensitive_fields
# RED then GREEN；旧 audit metadata evidence 保留 api-key/client-secret/session-id/private-key 短横线赋值；GREEN 1 passed, 48 deselected

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "audit_metadata_sanitizer or audit_event_reader_omits_sensitive or audit_allows_only_public_metadata_shapes or runtime_viewer_connected_audit"
# 5 passed, 44 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 658 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Audit metadata hyphen-assignment release boundary。

## 2026-06-04 Audit metadata hyphen key alias release guardrail

背景：

- Release convergence 继续检查 audit metadata key 名，因为 key/value JSON 会进入回归证据、runtime/viewer triage 和本地长期记录。
- 前一轮已覆盖短横线赋值，但 `proxy-url`、`viewer-url`、`viewer-token-hash` 这类 key-only alias 仍可能作为普通 metadata key 留下。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 audit release-evidence 边界。

已覆盖：

- Audit metadata key 判断现在将 `-` 归一为 `_` 后复用现有敏感 key 和 token/hash 后缀规则。
- `proxy-url`、`viewer-url`、`viewer-token-hash` 等短横线 alias 会整体丢弃。
- 原有普通低敏 key、URL credential、Authorization/Bearer、local path、IP literal、assignment 和 marker-only redaction 行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k audit_metadata_sanitizer_removes_sensitive_fields
# RED then GREEN；旧 audit metadata evidence 保留 proxy-url/viewer-url/viewer-token-hash key alias；GREEN 1 passed, 48 deselected

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "audit_metadata_sanitizer or audit_event_reader_omits_sensitive or audit_allows_only_public_metadata_shapes or runtime_viewer_connected_audit"
# 5 passed, 44 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 658 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Audit metadata hyphen-key-alias release boundary。

## 2026-06-04 Runtime external session hyphen marker release guardrail

背景：

- Release convergence 继续检查 runtime session response 和 audit 顶层 `external_session_id`，因为这些字段会进入 runtime/viewer 回归证据和本地 audit 记录。
- 旧 filter 已覆盖下划线 marker，但 `api-key-runtime-external-marker`、`client-secret-runtime-external-marker`、`session-id-audit-external-marker`、`private-key-audit-external-marker` 等短横线 marker 仍可能符合 public id 规则。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 runtime/audit release-evidence 边界。

已覆盖：

- Runtime session response external_session_id sanitizer 现在拒绝 `_` 和 `-` 两种分隔的敏感 marker。
- Audit event reader 顶层 external_session_id sanitizer 同步覆盖短横线 marker。
- 普通 public id、URL/Auth/path/query 过滤、下划线 marker 过滤和 runtime lookup 语义保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "external_session_id_markers"
# RED then GREEN；旧 runtime/audit external_session_id evidence 保留 api-key/session-id/private-key 短横线 marker；GREEN 2 passed, 47 deselected

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "external_session_id or runtime_viewer_failure_audit or runtime_viewer_origin_failure_audit or audit_event_reader_omits_sensitive_external"
# 6 passed, 43 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 658 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Runtime external session hyphen-marker release boundary。

## 2026-06-04 Health runtime hyphen marker release guardrail

背景：

- Release convergence 继续检查 profile health response，因为 health panel 和 release evidence 会显示 profile/runtime 状态。
- 旧 health runtime sanitizer 已覆盖下划线 marker，但 `api-key-health-runtime-marker`、`session-id-health-runtime-marker`、`private-key-health-runtime-marker` 这类短横线 marker 仍可能作为 profile id 或 automation URL evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 health release-evidence 边界。

已覆盖：

- Health runtime sensitive text filter 现在拒绝 `_` 和 `-` 两种分隔的敏感 marker。
- Profile health response 对短横线 marker profile id 返回 `unknown`，runtime `automation_url` 返回 `null`。
- 普通 public health response、runtime missing warnings、audit metadata、URL/Auth/token 和下划线 marker 过滤保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_health.py -q -k health_response_sanitizes_non_public_runtime_evidence
# RED then GREEN；旧 health runtime evidence 保留 api-key-health-runtime-marker automation_url；GREEN 1 passed, 25 deselected

.venv/bin/python -m pytest backend/tests/test_health.py -q -k "health_response_sanitizes_non_public_runtime_evidence or health_warns_when_running_runtime_urls_are_missing or health_check_audit or runtime_lookup or persisted_profile_id"
# 3 passed, 23 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 658 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Health runtime hyphen-marker release boundary。

## 2026-06-04 Automation console hyphen assignment release guardrail

背景：

- Release convergence 继续检查 Automation console log response，因为 console text 会进入 Automation API、UI task/debug evidence 和 release triage。
- 旧 Automation console text sanitizer 已覆盖 URL、Authorization/Bearer、Cookie 和下划线 assignment，例如 `api_key=...`、`session_id=...`。
- 短横线 assignment 例如 `api-key=...`、`client-secret=...`、`session-id=...`、`private-key=...` 仍可能在 response text 中保留真实值。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 这类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Automation response evidence 边界。

已覆盖：

- Automation console text assignment sanitizer 现在统一支持 `_` 和 `-` 分隔的 access/api/auth/client/private/refresh/runtime/service/session/viewer/x-api-key 字段。
- Console log response 对 `api-key`、`client-secret`、`session-id`、`private-key` assignment 返回 `[redacted]`。
- 现有 URL/Auth/Cookie、underscore assignment、marker-only console text、location URL 和 console type redaction 行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py -q -k automation_console_logs_redacts_hyphen_sensitive_assignments
# RED: 旧 Automation console response 保留 api-key/session-id/private-key 短横线 assignment secret；GREEN: 1 passed, 259 deselected

.venv/bin/python -m pytest backend/tests/test_api.py -q -k "automation_console_logs"
# 5 passed, 255 deselected

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 659 passed

npm --prefix frontend test -- --run
# 21 files / 306 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation console hyphen-assignment release boundary。

## 2026-06-06 Frontend runtime service token error release guardrail

背景：

- Release convergence 继续检查 Manager UI 可见错误文本，因为 runtime/profile/proxy/automation 操作失败时，错误提示会成为人工回归和问题定位 evidence。
- 旧 `publicErrorText()` 已覆盖多种 secret assignment 和 marker-only 文本，但 `runtime_service_token` / `service_token` alias 还需要显式覆盖。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 和 IPhey 类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 frontend error evidence 边界。

已覆盖：

- Frontend visible error sanitizer 现在覆盖 `runtime_service_token`、`runtime-service-token`、`service_token`、`service-token` assignment。
- marker-only frontend error evidence 中的 runtime/service token alias 会被折叠为 `[redacted]`。
- 现有 URL/Auth/path/IP/generic token/secret redaction 行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts -t "runtime and service token"
# RED then GREEN；旧 frontend error evidence 保留 runtime_service_token/service_token alias；GREEN 1 passed, 10 skipped

npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts
# 11 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Frontend runtime/service token error release boundary。

## 2026-06-06 Frontend profile label runtime service token release guardrail

背景：

- Release convergence 继续检查 profile-visible UI evidence，因为 profile name/id/tag/GeoIP/launch-arg label 会进入表格、卡片、筛选、确认弹窗和人工回归截图范围。
- `publicErrorText()` 已覆盖 runtime/service token alias，但 profile label helpers 需要把 marker-only alias 折叠为 `unknown`，避免只显示 `[redacted]` 或截断后的敏感字段前缀。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 和 IPhey 类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 frontend label evidence 边界。

已覆盖：

- `publicProfileName`、`publicProfileIdLabel`、`publicProfileTagLabel`、`publicProfileGeoipLabel` 和 `publicProfileLaunchArgLabel` 现在都拒绝 runtime/service token marker alias。
- 覆盖 `_` 和 `-` 两种 alias：`runtime_service_token`、`runtime-service-token`、`service_token`、`service-token`。
- 普通公开 profile label、profile id、tag、GeoIP 和 launch arg 文案保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts -t "runtime and service token aliases from profile-visible labels"
# RED then GREEN；旧 profile-visible label evidence 对 runtime_service_token marker 返回 [redacted]；GREEN 1 passed, 11 skipped

npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts
# 12 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Frontend profile label runtime/service token release boundary。

## 2026-06-06 BrowserManager runtime service token release guardrail

背景：

- Release convergence 继续检查 BrowserManager launch/log evidence，因为 GPU/WebGL pin、Firefox launch args 和 profile lifecycle log id 会进入 runtime/profile 回归证据。
- 旧 `SENSITIVE_TEXT_RE` 覆盖常见 secret marker，但 `runtime_service_token_*` / `service_token_*` 下划线 marker 会绕过旧 word-boundary 结尾。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 和 IPhey 类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 BrowserManager evidence 边界。

已覆盖：

- BrowserManager 共享敏感文本过滤现在覆盖 runtime/service token alias。
- GPU/WebGL launch pin、Firefox `extra_args` 和 profile log id evidence 会拒绝 runtime/service token 下划线 marker。
- 普通公开 GPU text、Firefox args 和 profile log id 保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_browser_manager.py -q -k "runtime_service_token_marker or public_profile_log_id_rejects_runtime_service_token"
# RED then GREEN；旧 BrowserManager evidence 保留 runtime_service_token/service_token 下划线 marker；GREEN 3 passed, 74 deselected

.venv/bin/python -m pytest backend/tests/test_browser_manager.py -q
# 77 passed
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL coherence、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 BrowserManager runtime/service token release boundary。

## 2026-06-06 Health warning runtime service token release guardrail

背景：

- Release convergence 继续检查 HealthBadge warning summary，因为 profile health warning 会进入状态徽标 visible text、tooltip/title 和人工回归证据。
- `publicErrorText()` 已能 redacts runtime/service token marker-only text，但 HealthBadge 自己的折叠判断没有复用 marker detector。
- 下划线 marker 例如 `runtime_service_token_health_warning_marker` / `service_token_health_warning_marker` 会显示成 `[redacted] [redacted]`，不是最低敏的 `unknown`。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 和 IPhey 类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 frontend health evidence 边界。

已覆盖：

- `getHealthWarningSummary()` 现在把 `hasSensitiveMarkerText()` 作为敏感 warning 判断的一部分。
- runtime/service token 下划线 marker-only health warning summary 会折叠为 `unknown`。
- HealthBadge visible text 和 `title` evidence 不包含 `runtime_service_token` / `service_token` marker。
- 普通 warning summary、已有敏感错误文本 redaction 和 compact mode 行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/HealthBadge.test.tsx -t "underscore runtime service token"
# RED then GREEN；旧 HealthBadge 对 runtime_service_token/service_token 下划线 marker 显示 [redacted] [redacted]；GREEN 1 passed, 7 skipped

npm --prefix frontend test -- --run src/components/HealthBadge.test.tsx
# 8 passed

npm --prefix frontend test -- --run src/lib/errorDisplay.test.ts src/components/HealthBadge.test.tsx
# 20 passed

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 662 passed

npm --prefix frontend test -- --run
# 21 files / 309 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/health/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Health warning runtime/service token release boundary。

## 2026-06-06 Backend health runtime service token release guardrail

背景：

- Release convergence 继续检查 backend Health API response evidence，因为 `profile_id` 和 `runtime.automation_url` 会进入 Profile health UI、API 回归和人工 triage。
- 旧 `_SENSITIVE_RUNTIME_TEXT_RE` 能覆盖 URL、Authorization/Bearer 和常见 secret 字段，但 `runtime_service_token_*` / `service_token_*` 下划线 marker 会绕过旧 word-boundary 结尾。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING` 和 IPhey 类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 backend health response evidence 边界。

已覆盖：

- Backend Health runtime text sanitizer 现在覆盖 runtime/service token alias。
- `compute_profile_health()` 会把 runtime/service token marker profile id 折叠为 `unknown`。
- 含这类 marker profile id 的 `runtime.automation_url` 会返回 `None`。
- 普通 runtime status、VNC port、公开 profile id 和正常 automation URL 行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_health.py -q -k "runtime_evidence"
# RED then GREEN；旧 backend health response 保留 /api/profiles/runtime_service_token_health_runtime_marker/automation；GREEN 1 passed, 25 deselected

.venv/bin/python -m pytest backend/tests/test_health.py -q
# 26 passed

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 662 passed

npm --prefix frontend test -- --run
# 21 files / 309 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这不是 Pixelscan fingerprint masking 修复；`PXLSCN-FINGERPRINT-MASKING` 继续按底层/第三方检测站 blocker 管理，不在 Manager 侧硬解。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/health/runtime/evidence 边界。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Backend health runtime/service token release boundary。

## 2026-06-06 Runtime external session service token release guardrail

背景：

- Release convergence 继续检查 RuntimeSessionResponse 和 audit reader evidence，因为 `external_session_id` 会进入 runtime API response、audit API output 和人工 release triage。
- 旧 runtime/audit external session id sanitizer 覆盖 URL、authorization、api/session/private-key marker 和短横线 marker，但 `runtime_service_token_*` / `service_token_*` 下划线 marker 会绕过旧 word-boundary 结尾。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 runtime/audit response evidence 边界。

已覆盖：

- Runtime response 的 sensitive external session id matcher 现在覆盖 runtime/service token alias。
- Audit event reader 的 top-level `external_session_id` matcher 同步覆盖这些 alias。
- `runtime_service_token_*` / `service_token_*` marker external session id 在 runtime response 中折叠为 `unknown`。
- 这些 marker 在 audit reader output 中折叠为 `None`。
- 普通公开 `pm-session-*` external session id 继续保留。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py -q -k "external_session_id_markers"
# RED then GREEN；旧 runtime response/audit reader 保留 runtime_service_token/service_token 下划线 marker；GREEN 2 passed, 47 deselected

.venv/bin/python -m pytest backend/tests/test_session_broker.py -q
# 49 passed

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 662 passed

npm --prefix frontend test -- --run
# 21 files / 309 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这是 Manager-controlled runtime/audit response evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/health/runtime/proxy/profile evidence。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Runtime external session runtime/service token release boundary。

## 2026-06-06 Profile launch arg service token release guardrail

背景：

- Release convergence 继续检查 profile/template/export `launch_args` evidence，因为这些字段会进入 Profile API、template API、config export、bundle export 和人工 release triage。
- 旧 `_SENSITIVE_TEMPLATE_ARG_RE` 已覆盖 URL、authorization、api/session/private-key marker 和 runtime/service token alias，但敏感 token 分支结尾仍用 `\b`。
- Python 正则中 `_` 属于 word 字符，所以 `runtime_service_token_*` / `service_token_*` 下划线 marker launch arg 会绕过旧边界。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 profile/template/export response evidence 边界。

已覆盖：

- Profile/template/config shared launch arg matcher 现在用 `(?=$|[^A-Za-z0-9])` 识别 `_` / `-` marker 边界。
- Profile list/detail response 丢弃 runtime/service token marker launch args。
- Profile template list/detail response 丢弃 runtime/service token marker launch args。
- Profile config export 和 bundle export 丢弃 runtime/service token marker launch args。
- 普通公开 launch arg 例如 `--private-window` 继续保留。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_profile_responses_sanitize_persisted_identity_fields backend/tests/test_templates.py::test_profile_template_api_sanitizes_persisted_identity_fields backend/tests/test_api.py::test_export_profile_bundle_sanitizes_persisted_identity_fields backend/tests/test_bulk.py::test_bulk_export_profile_configs_sanitizes_persisted_identity_fields -q
# RED then GREEN；旧 profile response launch_args 保留 runtime_service_token/service_token 下划线 marker；GREEN 4 passed

.venv/bin/python -m pytest backend/tests/test_api.py -q -k "profile_responses_sanitize_persisted_identity_fields or export_profile_bundle_sanitizes_persisted_identity_fields"
# 2 passed, 258 deselected

.venv/bin/python -m pytest backend/tests/test_templates.py -q
# 13 passed

.venv/bin/python -m pytest backend/tests/test_bulk.py -q
# 21 passed

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 662 passed

npm --prefix frontend test -- --run
# 21 files / 309 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这是 Manager-controlled profile/template/export launch_args evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/health/runtime/proxy/profile evidence。
- 不改变 raw profile persistence、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile launch arg runtime/service token release boundary。

## 2026-06-06 GeoIP source service token release guardrail

背景：

- Release convergence 继续检查 GeoIP/proxy source label evidence，因为 `GeoIPResult.as_dict()` 会进入 profile/proxy/health API response 和人工 release triage。
- 旧 `_SENSITIVE_GEOIP_SOURCE_RE` 已覆盖 URL、Auth、常见 token/key/secret marker 和 runtime/service token alias，但敏感 token 分支结尾仍用 `\b`。
- Python 正则中 `_` 属于 word 字符，所以短 source label 例如 `runtime_service_token_x` / `service_token_x` 会绕过旧边界，并且仍符合 public source 长度和字符集。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 GeoIP/proxy source evidence 边界。

已覆盖：

- GeoIP source sensitive matcher 现在用 `(?=$|[^A-Za-z0-9])` 识别 `_` / `-` marker 边界。
- `public_geoip_source()` 对短 runtime/service token marker source 返回 `unknown`。
- `GeoIPResult.as_dict()` 不再暴露这些 marker source label。
- 普通低敏 source 例如 `ip-api` 和 `qa` 继续保留。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_geoip.py -q -k "marker_only_sensitive_sources"
# RED then GREEN；旧 public_geoip_source 返回 runtime_service_token_x；GREEN 1 passed, 15 deselected

.venv/bin/python -m pytest backend/tests/test_geoip.py -q
# 16 passed

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 662 passed

npm --prefix frontend test -- --run
# 21 files / 309 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这是 Manager-controlled GeoIP/proxy source evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/health/runtime/proxy/profile evidence。
- 不改变 GeoIP lookup behavior、proxy resolution、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 GeoIP source runtime/service token release boundary。

## 2026-06-06 Frontend viewer and summary service token release guardrail

背景：

- Release convergence 继续检查前端 VNC viewer / runtime session / profile summary 的可见 evidence，因为这些字段会进入人工 release triage 和截图前的低敏检查。
- `ProfileViewer` 的本地 viewer handle 规则已覆盖 URL/Auth/api/session/private/viewer token 形态，但没有显式覆盖 `runtime_service_token` / `service_token` alias。
- `ProfileSummaryPanel` 的 Device label 本地规则也缺少 runtime/service token alias，导致 marker-only device 字段渲染为 `[redacted]` evidence，而不是更低敏的 `unknown`。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 UI evidence 边界。

已覆盖：

- `ProfileViewer` 对 `runtime_service_token-profile-viewer-marker` 和 `service_token-runtime-viewer-marker` 折叠为 `unknown`。
- `ProfileViewer` 对 runtime/service token marker profile automation path 显示 `Automation unavailable`，不会暴露为可复制 endpoint。
- `ProfileSummaryPanel` Device 区域对 runtime/service token marker platform/screen/cores/GPU label 折叠为 `unknown`。
- 普通公开 viewer handle、business session id、device label、VNC connection、Automation toolbar 和 clipboard sync 行为保持不变。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileViewer.test.tsx -t "runtime and service token marker handles"
# RED then GREEN；旧 ProfileViewer 渲染 runtime_...rker / service_...rker，并显示 Automation ready；GREEN 1 passed, 20 skipped

npm --prefix frontend test -- --run src/components/ProfileViewer.test.tsx
# 21 passed

npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx -t "runtime and service token device labels"
# RED then GREEN；旧 ProfileSummaryPanel Device 区域渲染 [redacted] / [redacted] cores；GREEN 1 passed, 9 skipped

npm --prefix frontend test -- --run src/components/ProfileSummaryPanel.test.tsx
# 10 passed

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 662 passed

npm --prefix frontend test -- --run
# 21 files / 311 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这是 Manager-controlled frontend VNC/viewer/profile summary UI evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/health/runtime/proxy/profile evidence。
- 不改变 VNC forwarding、runtime session storage、viewer token schema、Automation worker lease behavior、raw profile persistence、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 frontend viewer/profile summary runtime/service token release boundary。

## 2026-06-07 Proxy CSV textarea service token release guardrail

背景：

- Release convergence 继续检查 Proxy Manager CSV import UI evidence，因为 textarea、preview 和 import dialog 经常进入人工 triage。
- Proxy CSV import 保持双轨语义：UI textarea 显示低敏内容，但 import source payload 必须保留原始 CSV，避免把用户要导入的字段改坏。
- 旧 CSV marker 字段规则已把 `api_key` / `client_secret` / `private_key` marker-only 字段显示为 `unknown`，但 `runtime_service_token` / `service_token` alias 只会被通用 sanitizer 渲染成 `[redacted]`。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Proxy Manager UI evidence 边界。

已覆盖：

- Proxy CSV textarea visible text 对 `runtime_service_token-*` / `service_token-*` marker-only 字段显示 `unknown`。
- endpoint host/port 低敏 evidence 继续保留，URL credential userinfo 继续隐藏。
- `createProxy()` 仍收到原始 raw CSV name/provider/tag/url，确认 UI 脱敏不改变 import payload。
- ProxyManagerPage 邻近测试覆盖 proxy table、assignment dialog、provider presets、random assignment、CSV preview/import 和错误脱敏。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "runtime and service token marker proxy CSV textarea"
# RED then GREEN；旧 textarea 显示 "[redacted]" 字段而不是 "unknown"；GREEN 1 passed, 40 skipped

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 41 passed

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 662 passed

npm --prefix frontend test -- --run
# 21 files / 312 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这是 Manager-controlled Proxy Manager CSV import UI evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 raw proxy persistence、proxy resolution、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy CSV textarea runtime/service token release boundary。

## 2026-06-07 Profile CSV runtime service token release guardrail

背景：

- Release convergence 继续检查 Profile CSV import dialog，因为 textarea、preview table 和 row title 经常进入人工 triage evidence。
- Profile CSV import 保持双轨语义：UI textarea 和 preview table 显示低敏内容，但 import source payload 必须保留原始 CSV，避免把用户要导入的 profile 字段改坏。
- 旧 Profile CSV marker 字段规则已把 `api_key` / `client_secret` / `private_key` marker-only 字段显示为 `unknown`，但 `runtime_service_token` / `service_token` alias 只会被通用 sanitizer 渲染成 `[redacted]`。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Profile CSV UI evidence 边界。

已覆盖：

- Profile CSV textarea visible text 对 `runtime_service_token-*` / `service_token-*` marker-only 字段显示 `unknown`。
- Profile CSV preview table 的 name/template/platform/locale/timezone/proxy/tag evidence 和 `title` 属性同样折叠这些 marker。
- endpoint host/port 低敏 evidence 继续保留，URL credential userinfo 继续隐藏。
- `importProfiles()` 仍收到原始 raw CSV，确认 UI 脱敏不改变 import payload。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProfileCsvPreviewDialog.test.tsx -t "runtime and service token marker profile CSV evidence"
# RED then GREEN；旧 textarea 显示 "[redacted]" 字段而不是 "unknown"；GREEN 1 passed, 9 skipped

npm --prefix frontend test -- --run src/components/ProfileCsvPreviewDialog.test.tsx
# 10 passed

git diff --check
# passed

.venv/bin/python -m pytest backend/tests -q
# 662 passed in 41.62s

npm --prefix frontend test -- --run
# 21 files / 313 tests passed

npm --prefix frontend run build
# tsc -b && vite build succeeded
```

边界：

- 这是 Manager-controlled Profile CSV import UI evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 raw profile persistence、profile import request contract、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Profile CSV runtime/service token release boundary。

## 2026-06-07 Proxy assignment service token release guardrail

背景：

- Release convergence 继续检查 Proxy Manager assignment dialog，因为候选 profile name/id/current proxy 会进入人工 UI evidence、搜索结果、`title` 和 checkbox `aria-label`。
- Proxy assignment 保持双轨语义：UI 只显示低敏 evidence，但 assign API 仍必须使用原始 profile id。
- 旧 assignment profile id/name/current proxy 规则已覆盖 `api_key`、`session_id`、`private_key` 等 marker，但 `runtime_service_token` / `service_token` alias 仍会暴露为 marker 文本或 `[redacted]` evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮继续收 Manager 自己可控的 Proxy Manager UI evidence 边界。

已覆盖：

- Proxy assignment dialog 对 `runtime_service_token-*` / `service_token-*` profile id、profile name 和 current proxy marker evidence 显示 `unknown`。
- 搜索 marker alias 不会命中污染候选项；搜索 `unknown` 仍能找到折叠后的候选 profile。
- dialog 的可见文本、`title` 和 `aria-label` 不再包含 marker alias、`[redacted]`、URL userinfo 或 proxy password evidence。
- `assignProxyToProfiles()` 仍收到原始 profile id，确认 UI 脱敏不改变 assignment payload。

验证：

```bash
npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx -t "runtime and service token marker assignment profile evidence"
# RED then GREEN；旧 dialog 没有足够 unknown，并可渲染 runtime_service_token profile id/current proxy evidence；GREEN 1 passed, 41 skipped

npm --prefix frontend test -- --run src/components/ProxyManagerPage.test.tsx
# 42 passed
```

边界：

- 这是 Manager-controlled Proxy Manager assignment UI evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 raw profile persistence、raw proxy persistence、proxy resolution、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Proxy assignment runtime/service token release boundary。

## 2026-06-07 Audit tuple metadata persistence release guardrail

背景：

- Release convergence 继续检查审计持久化边界，因为 audit metadata 是 Manager 可控、长期保留、会进入诊断和发布 triage 的 evidence 面。
- 旧 sanitizer 会递归处理 `dict/list/str`，但 Python `tuple` 会被 `json.dumps()` 自动写成数组；如果调用方误把 tuple 放进 metadata，tuple 内部敏感字符串和敏感键会在落库前绕过递归脱敏。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮只收 Manager 自己可控的 audit persistence 边界。

已覆盖：

- `_sanitize_audit_metadata()` 现在把 tuple 作为 list-like 容器递归脱敏。
- tuple 内部 `token=...`、`Authorization=Bearer ...`、`runtime_service_token...` 文本在写入 `audit_events.metadata` 前被替换。
- tuple 内部 dict 的敏感键，例如 `viewer_token`，会在持久化前移除。
- 历史 audit event reader 的顶层 id/event_type/actor/external_session_id 和 metadata 低敏读取行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_sanitizes_tuple_values_before_persistence -q
# RED then GREEN；旧 raw audit_events.metadata 持久化 audit-tuple-secret、viewer_token、Authorization=Bearer 和 runtime_service_token evidence；GREEN 1 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_removes_sensitive_fields backend/tests/test_session_broker.py::test_audit_metadata_sanitizer_sanitizes_tuple_values_before_persistence backend/tests/test_session_broker.py::test_audit_event_reader_sanitizes_historical_top_level_fields_and_metadata -q
# 3 passed
```

边界：

- 这是 Manager-controlled audit metadata persistence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 audit tuple metadata persistence release boundary。

## 2026-06-07 Automation console structured text release guardrail

背景：

- Release convergence 继续检查 Automation diagnostics evidence，因为 console logs 会在 triage 中展示页面脚本输出摘要。
- 正常 Playwright console text 是字符串；但历史/异常 cached entries 可能把 `text` 存成 dict/list。
- 旧 response helper 会把非字符串 text 直接 `str(...)`，导致结构化对象里的 token/header/viewer/runtime marker 值可能绕过普通字符串脱敏。

已覆盖：

- Automation console log response 只接受字符串 text；非字符串 cached text 返回空字符串。
- 既有字符串 console text 的 URL/userinfo/query/fragment、Authorization、Cookie、token assignment 和 marker 脱敏行为保持不变。
- console type 和 location URL/line/column 低敏规则保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_console_logs_drops_non_string_cached_text_values -q
# RED then GREEN；旧响应把 structured-token-secret 和 structured-viewer-secret 通过 str(dict/list) 暴露；GREEN 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_console_logs_returns_in_memory_page_logs backend/tests/test_api.py::test_automation_console_logs_redacts_existing_in_memory_entries backend/tests/test_api.py::test_automation_console_logs_drops_non_string_cached_text_values backend/tests/test_api.py::test_automation_console_logs_captures_recent_console_messages backend/tests/test_api.py::test_automation_console_logs_redacts_sensitive_text_and_location_urls backend/tests/test_api.py::test_automation_console_logs_redacts_hyphen_sensitive_assignments backend/tests/test_api.py::test_automation_network_summary_redacts_existing_in_memory_events -q
# 7 passed
```

边界：

- 这是 Manager-controlled Automation diagnostics response 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 Automation worker lease behavior、task execution semantics、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation console structured text release boundary。

## 2026-06-07 Automation about URL release guardrail

背景：

- Release convergence 继续检查 Automation pages response，因为页面 URL 会进入 API、UI task/debug evidence 和 release triage。
- 旧 http/https URL helper 会剥离 userinfo、query 和 fragment，但 `about:` URL 直接原样返回。
- 这会让 `about:blank?token=...#frag` 一类历史/异常 URL 的 query/fragment 出现在 Manager response；`about:newtab?token=...#frag` 也会绕过内部页过滤。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮只收 Manager 自己可控的 Automation pages evidence 边界。

已覆盖：

- `about:` URL 现在统一规范化为 `about:<path>`，query 和 fragment 不再进入 Automation pages response。
- 内部页过滤使用同一低敏 about URL 规范化结果，所以带 query/fragment 的 `about:home`、`about:newtab`、`about:welcome` 仍被过滤。
- 普通 `about:blank`、正常 http/https page URL、title redaction、console/network summary 行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_pages_redacts_about_url_query_and_fragment backend/tests/test_api.py::test_automation_pages_filters_internal_about_pages_with_query_or_fragment -q
# RED then GREEN；旧响应暴露 about-page-secret/internal-secret query 和 fragment evidence；GREEN 2 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k 'automation_pages or automation_console_logs or automation_network_summary or automation_page_' -q
# 19 passed, 244 deselected
```

边界：

- 这是 Manager-controlled Automation pages API evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 Automation worker lease behavior、task execution semantics、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation about URL release boundary。

## 2026-06-07 Runtime viewer failure reason release guardrail

背景：

- Release convergence 继续检查 runtime/VNC viewer audit evidence，因为 viewer failures 会在诊断和发布 triage 中说明 VNC 连接失败原因。
- 旧 `runtime.viewer.failed` audit metadata 直接写入 `reason_code`。
- 如果内部调用或未来异常路径传入 `reason_code` 污染文本，通用 audit sanitizer 会替换 token 值，但仍会把污染文本保留为可见 reason evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮只收 Manager 自己可控的 runtime/VNC audit evidence 边界。

已覆盖：

- `runtime.viewer.failed` reason_code 现在只允许固定低敏原因：`viewer_credential_missing`、`viewer_credential_invalid`、`viewer_credential_expired`、`origin_not_allowed`、`runtime_session_not_live`、`profile_not_running`、`backend_vnc_unavailable`。
- 污染或未知 reason_code 统一折叠为 `unknown`。
- viewer token 校验、origin 拒绝、session live 检查、profile running 检查、backend VNC 连接失败和 connected/disconnected audit 语义保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_viewer_failure_audit_sanitizes_reason_code_metadata -q
# RED then GREEN；旧 metadata 保留污染 reason_code 文本；GREEN 1 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py -k 'runtime_vnc or runtime_viewer' -q
# 17 passed, 34 deselected
```

边界：

- 这是 Manager-controlled runtime/VNC audit evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 viewer token schema、VNC forwarding、runtime session storage、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、proxy resolution、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Runtime viewer failure reason release boundary。

## 2026-06-07 Random proxy assignment selection tag release guardrail

背景：

- Release convergence 继续检查 Proxy Manager API evidence，因为 random proxy assignment 会把 provider/country/tag selection summary、candidate count 和 selected proxy summary 返回给调用方。
- 旧 selection summary 会原样回显 provider preset/request 合并后的 tag；如果历史/异常 tag 包含 `runtime_service_token...` 或 token/secret/header marker，会进入 release/debug evidence。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮只收 Manager 自己可控的 random proxy assignment response evidence 边界。

已覆盖：

- Random proxy assignment 内部 candidate matching 继续使用原 normalized tags，不因为响应脱敏而扩大候选范围。
- Response selection `tags` 过滤 token/secret/header/runtime-service marker tag。
- Response result 内嵌 proxy summary 过滤敏感 tag；普通 proxy/preset/profile tag CRUD/list/detail contract 不变。
- Audit 仍只写 provider/country/tag_count/candidate/profile/assigned/missing counts，不写 raw tag。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_proxies.py::test_random_proxy_assignment_redacts_sensitive_selection_tags_without_broadening_match -q
# RED then GREEN；旧响应在 data["tags"] 中保留 mobile-runtime_service_token_random_tag_marker；GREEN 1 passed

.venv/bin/python -m pytest backend/tests/test_proxies.py -k "random_proxy_assignment" -q
# 6 passed, 38 deselected
```

边界：

- 这是 Manager-controlled Proxy Manager API response evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 raw proxy persistence、raw provider preset persistence、proxy selection matching、proxy resolution、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、VNC forwarding、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 random proxy assignment selection tag release boundary。

## 2026-06-07 Automation non-http URL release guardrail

背景：

- Release convergence 继续检查 Automation URL evidence，因为 pages、console location 和 network summary 会进入 API/debug/release triage。
- 旧通用 URL sanitizer 对任意带 hostname 的 scheme 都会保留 scheme、host 和 path；历史/异常 `file://localhost/tmp/profile-...` URL 会把本地路径带进 Manager response。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮只收 Manager 自己可控的 Automation URL evidence 边界。

已覆盖：

- 通用 Automation URL sanitizer 只输出 `http`/`https` URL 的低敏 scheme、host、port 和 path。
- `file://`、`chrome://`、`data:` 等非 http(s) URL 折叠为空字符串，不暴露内部路径、query 或 fragment。
- `about:` URL 仍走专用低敏规范化逻辑；正常 http/https pages、console location、network summary 行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_pages_redacts_non_http_internal_url_paths -q
# RED then GREEN；旧响应保留 file://localhost/tmp/profile-automation-internal-url-secret/state.html；GREEN 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k 'automation_pages or automation_console_logs or automation_network_summary or automation_page_' -q
# 20 passed, 244 deselected
```

边界：

- 这是 Manager-controlled Automation URL response evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 Automation worker lease behavior、task execution semantics、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation non-http URL release boundary。

## 2026-06-07 VNC WebSocket origin host marker release guardrail

背景：

- Release convergence 继续检查 VNC/WebSocket log evidence，因为 rejected Origin 会出现在 diagnostics/triage 日志中。
- 旧 `_websocket_public_host_label()` 会剥离 path/query/fragment，但不会识别 hostname 自身的 marker；`runtime_service_token...example` 会作为 host label 写入日志。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮只收 Manager 自己可控的 VNC/WebSocket log evidence 边界。

已覆盖：

- VNC WebSocket Origin mismatch log 中，含 token/header/runtime-service marker 的 origin host 折叠为 `unknown`。
- 普通 host、missing/malformed host 和非默认端口 host label 行为保持不变。
- Origin rejection、close code、viewer token handling、backend VNC connect/proxy 行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_vnc_ws_origin_rejection_redacts_sensitive_origin_host_marker -q
# RED then GREEN；旧日志保留 runtime_service_token_origin_marker.example；GREEN 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k 'vnc_ws_origin or ws_allows or vnc_proxy_' -q
# 11 passed, 254 deselected
```

边界：

- 这是 Manager-controlled VNC/WebSocket log evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 WebSocket Origin 校验语义、VNC forwarding、viewer token schema、runtime session storage、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、proxy resolution、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 VNC WebSocket origin host marker release boundary。

## 2026-06-07 Automation URL host marker release guardrail

背景：

- Release convergence 继续检查 Automation URL evidence，因为 pages、console location 和 network summary 会进入 API/debug/release triage。
- 旧 `_automation_safe_url()` 会剥离 HTTP URL 的 userinfo/query/fragment，但不会识别 hostname 自身的 marker；`runtime_service_token...example` 会作为 URL host 写入 Manager response。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮只收 Manager 自己可控的 Automation URL evidence 边界。

已覆盖：

- Automation pages URL、console location URL 和 network summary URL 中，含 token/header/runtime-service marker 的 HTTP host 折叠为空字符串。
- 普通 http/https URL、non-http URL 拦截、about URL 规范化、console text redaction 和 network summary allowlist 行为保持不变。
- Automation worker lease、task execution、browser runtime 和 fingerprint 行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_api.py::test_automation_url_evidence_redacts_sensitive_http_host_markers -q
# RED then GREEN；旧响应保留 https://runtime_service_token_automation_host_marker.example/app；GREEN 1 passed

.venv/bin/python -m pytest backend/tests/test_api.py -k 'automation_pages or automation_console_logs or automation_network_summary or automation_page_' -q
# 20 passed, 246 deselected
```

边界：

- 这是 Manager-controlled Automation URL response evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 Automation worker lease behavior、task execution semantics、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、proxy resolution、VNC forwarding 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Automation URL host marker release boundary。

## 2026-06-07 Runtime audit non-dict metadata release guardrail

背景：

- Release convergence 继续检查 runtime service/viewer audit evidence，因为这些 event 会进入 diagnostics、triage 和长期 audit history。
- 旧 runtime audit allowlist helper 已固定 dict metadata 的低敏 shape，但如果内部调用误传 `str`/`list`/`tuple` metadata，会在 `.get()` 处抛 `AttributeError`，导致 Manager-controlled audit 路径不稳定。
- 当前策略下，Pixelscan `PXLSCN-FINGERPRINT-MASKING`、IPhey 以及同类底层/第三方 fingerprint 检测失败先标阻塞，不在 Manager 侧硬解；本轮只收 Manager 自己可控的 runtime audit evidence 边界。

已覆盖：

- Runtime service/viewer audit metadata helper 现在只接受 dict；非 dict metadata 按空对象处理。
- `runtime.session.created`、`runtime.viewer_token.created`、`runtime.session.renewed`、`runtime.viewer.connected`、`runtime.viewer.disconnected` 仍输出固定低敏 metadata shape。
- Runtime session lifecycle、viewer token schema、VNC proxy/audit、runtime/profile/external session top-level sanitization 行为保持不变。

验证：

```bash
.venv/bin/python -m pytest backend/tests/test_session_broker.py::test_runtime_viewer_audit_handles_non_dict_metadata_without_leaking backend/tests/test_session_broker.py::test_runtime_service_audit_handles_non_dict_metadata_without_leaking -q
# RED then GREEN；旧 helper 在 string/list metadata 上 AttributeError；GREEN 2 passed

.venv/bin/python -m pytest backend/tests/test_session_broker.py -k 'runtime_service_audit or runtime_viewer_connected_audit or runtime_viewer_disconnect_audit or runtime_viewer_failure_audit or runtime_vnc_success_writes_redacted_connect_and_disconnect_audit or runtime_vnc_backend_connect_failure_writes_redacted_failure_audit' -q
# 9 passed, 44 deselected
```

边界：

- 这是 Manager-controlled runtime audit stability/evidence 防御，不是 Pixelscan/IPhey 或 `PXLSCN-FINGERPRINT-MASKING` 修复。
- 同类底层/第三方 fingerprint 检测站失败先标阻塞项，再继续推进 Manager 可控 API/UI/log/audit/diagnostics/runtime/proxy/profile evidence。
- 不改变 runtime session storage、viewer token schema、VNC forwarding、browser runtime、`invisible_playwright` 包、stealth prefs、fingerprint seed、WebGL/canvas/noise、UA、locale/timezone、WebRTC、proxy resolution、Automation worker lease behavior 或 browser fingerprint 行为。
- `cbim-23h.1` 的最终 all-clear 仍不能声称 Pixelscan/IPhey 全通过；本轮只收 Runtime audit non-dict metadata release boundary。
