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
