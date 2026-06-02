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
- [ ] language 与 Accept-Language 一致。
- [x] BrowserScan 无 `Language mismatch`。
- [x] BrowserScan 无 `Different time zones`。
- [x] BrowserScan browser-checker 内核版本与 UA 一致。
- [x] BrowserScan WebRTC 不泄漏 local IP。
- [x] BrowserLeaks WebRTC / Canvas / WebGL / Fonts 无明显平台不一致。
- [ ] CreepJS 无 webdriver/headless/lie detection 严重红灯。
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
